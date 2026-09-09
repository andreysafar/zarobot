"""
Helper KB — скилл хелпера: отвечает на вопросы по архиву чата и ведёт FAQ.

Публичные команды:  /faq, /ask
Команды админов:    /faq_add, /faq_edit, /faq_del, /faq_publish, /ingest_status

Логика ответа (из CLAUDE.md):
  — молчим на обычную болтовню;
  — отвечаем, если нашли что-то полезное в базе знаний или FAQ;
  — если база пуста — короткое «не нашёл».
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from loguru import logger

try:
    from zero_bot_sdk import BaseSkill, SkillContext, SkillResponse
except ImportError:  # локальный запуск без SDK
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sdk"))
    from zero_bot_sdk import BaseSkill, SkillContext, SkillResponse

def _load_sibling(filename: str, module_name: str):
    """
    Подключить соседний модуль скилла по пути.

    Скилл грузится в двух режимах — как пакет (ботом) и как одиночный файл
    (тестами и загрузчиком навыков) — поэтому импортируем явно по файлу.
    """
    here = Path(__file__).resolve().parent
    import importlib.util as _ilu

    spec = _ilu.spec_from_file_location(module_name, here / filename)
    module = _ilu.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_perms = _load_sibling("permissions.py", "helper_kb_permissions")
can_manage_faq = _perms.can_manage_faq
format_faq_list = _perms.format_faq_list
parse_qa = _perms.parse_qa

judge = _load_sibling("judge.py", "helper_kb_judge")


def _load_gate_question_check():
    """
    Взять эвристику вопроса из group_gate, если рантайм доступен.

    Скилл работает и отдельно (в тестах), поэтому отсутствие модуля
    не ошибка — тогда используем локальный вариант.
    """
    try:
        from group_gate import looks_like_question

        return looks_like_question
    except Exception:
        return None


_gate_looks_like_question = _load_gate_question_check()


class HelperKbSkill(BaseSkill):
    """База знаний чата + FAQ с админ-командами."""

    name = "helper-kb"
    version = "0.1.0"
    commands = ["/faq", "/ask", "/faq_add", "/faq_edit", "/faq_del",
                "/faq_publish", "/ingest_status"]

    def __init__(self, store=None, telegram_client=None, llm_call=None):
        # store, клиент и LLM внедряются снаружи (их создаёт рантайм бота),
        # но скилл должен работать и без них — в тестах и при «сухом» старте.
        self.store = store
        self.client = telegram_client
        # llm_call(system: str, user: str) -> str | None; подменяется в тестах.
        self.llm_call = llm_call
        # Сколько сообщений архива отдаём судье как цитаты.
        self.context_limit = int(os.getenv("HELPER_CONTEXT_LIMIT", "10"))

    async def on_install(self, ctx: SkillContext) -> None:
        """Подключаем хранилище и модель, если рантайм их не передал."""
        if self.store is None:
            self.store = self._open_store()
        if self.llm_call is None:
            self.llm_call = self._open_llm()
        logger.info("helper-kb установлен (store={}, судья={})",
                    "подключён" if self.store else "нет",
                    "включён" if self.llm_call else "выключен")

    async def on_uninstall(self, ctx: SkillContext) -> None:
        if self.store is not None:
            try:
                self.store.close()
            except Exception:
                pass

    def _open_store(self):
        """
        Открыть SQLite-архив, с которым работает Дервалер.

        Ошибки логируем как error, а не warning: без хранилища скилл
        превращается в молчаливую заглушку, и это должно быть видно в логах,
        а не выясняться в живом чате.
        """
        db_path = os.getenv("KB_DB_PATH", "/data/dervaler/archive.sqlite3")
        try:
            from dervaler.store import Store
        except ImportError as e:
            # Пакет dervaler обязан лежать в образе бота (см. Dockerfile).
            logger.error("Модуль dervaler недоступен, база знаний отключена: {}", e)
            return None

        # Store создаёт файл, если его нет. Для неверно заданного KB_DB_PATH это
        # означало бы пустой архив вместо ошибки — предупреждаем заранее.
        if not Path(db_path).exists():
            logger.warning(
                "Файла базы знаний {} нет. Если Дервалер уже отработал — "
                "проверьте KB_DB_PATH и точку монтирования тома.", db_path
            )

        try:
            return Store(db_path)
        except Exception as e:
            logger.error("Не удалось открыть базу знаний {}: {}", db_path, e)
            return None

    def _open_llm(self):
        """
        Взять LLM-клиент рантайма бота.

        Без ключей провайдера судья не поднимается — скилл продолжает
        работать в лексическом режиме и отдаёт цитаты, как раньше.
        """
        try:
            from llm import LLMClient, has_any_provider
        except ImportError as e:
            logger.warning("Рантайм LLM недоступен, судья выключен: {}", e)
            return None

        if not has_any_provider():
            logger.warning("Ни один LLM-провайдер не настроен — судья выключен.")
            return None

        client = LLMClient()

        async def call(system: str, user: str) -> str | None:
            # fallback="" — чтобы отличить отказ провайдеров от ответа модели:
            # LLMClient.call не бросает исключение, а возвращает fallback.
            return await client.call(system, [{"role": "user", "content": user}],
                                     fallback="")

        return call

    # ── Команды ──

    async def on_command(
        self, ctx: SkillContext, command: str, args: str
    ) -> SkillResponse:
        command = str(command).split("@")[0].lower()
        # Рантайм всегда шлёт строку, но принимаем и число — это дешевле,
        # чем падать с AttributeError на .strip().
        args = "" if args is None else str(args)

        if command == "/faq":
            return await self._cmd_faq(ctx)

        if command == "/ask":
            return await self._cmd_ask(ctx, args)

        if command == "/ingest_status":
            return await self._cmd_ingest_status(ctx)

        # Всё ниже — только админы.
        if command in ("/faq_add", "/faq_edit", "/faq_del", "/faq_publish"):
            return await self._cmd_faq_admin(ctx, command, args)

        return SkillResponse.skip()

    async def _cmd_faq(self, ctx: SkillContext) -> SkillResponse:
        """Показать опубликованный FAQ."""
        if self.store is None:
            return SkillResponse(text="📋 FAQ пока пуст.")
        items = self.store.list_faq(ctx.chat_id, status="published")
        return SkillResponse(text=format_faq_list(items))

    async def _cmd_ask(self, ctx: SkillContext, args: str) -> SkillResponse:
        """Явный вопрос к базе знаний: /ask <вопрос>"""
        if not args.strip():
            return SkillResponse(text="Напиши вопрос: /ask как деплоить?")
        answer, _ = await self._build_answer(ctx.chat_id, args)
        return SkillResponse(text=answer)

    async def _cmd_ingest_status(self, ctx: SkillContext) -> SkillResponse:
        """Сколько выгружено и где курсор — для админов и в личке."""
        if self.store is None:
            return SkillResponse(text="База знаний не подключена.")
        total = self.store.message_count(ctx.chat_id)
        cursor = self.store.get_checkpoint(ctx.chat_id)
        drafts = len(self.store.list_faq(ctx.chat_id, status="draft"))
        published = len(self.store.list_faq(ctx.chat_id, status="published"))
        return SkillResponse(
            text=(
                f"📚 **База знаний**\n"
                f"Сообщений в архиве: {total}\n"
                f"Курсор инжеста: {cursor}\n"
                f"FAQ: {published} опубликовано, {drafts} черновиков"
            )
        )

    async def _cmd_faq_admin(
        self, ctx: SkillContext, command: str, args: str
    ) -> SkillResponse:
        """Команды управления FAQ — только для админов чата."""
        if self.store is None:
            return SkillResponse(text="База знаний не подключена.")

        if not await self._check_admin(ctx):
            return SkillResponse(
                text="⛔ Эта команда только для администраторов чата."
            )

        if command == "/faq_add":
            return await self._faq_add(ctx, args)
        if command == "/faq_edit":
            return await self._faq_edit(ctx, args)
        if command == "/faq_del":
            return await self._faq_del(ctx, args)
        if command == "/faq_publish":
            return await self._faq_publish(ctx, args)
        return SkillResponse.skip()

    async def _faq_add(self, ctx: SkillContext, args: str) -> SkillResponse:
        """/faq_add вопрос | ответ — создаёт черновик."""
        parsed = parse_qa(args)
        if parsed is None:
            return SkillResponse(
                text="Формат: /faq_add вопрос | ответ\n"
                     "Например: /faq_add Как деплоить? | docker compose up -d"
            )
        question, answer = parsed
        faq_id = self.store.add_faq(
            ctx.chat_id, question, answer, status="draft", updated_by=ctx.user_id
        )
        return SkillResponse(
            text=f"✅ Черновик #{faq_id} создан. Опубликовать: /faq_publish {faq_id}"
        )

    async def _faq_edit(self, ctx: SkillContext, args: str) -> SkillResponse:
        """/faq_edit <id> | новый текст ответа"""
        if "|" not in args:
            return SkillResponse(text="Формат: /faq_edit <id> | новый ответ")
        raw_id, _, new_text = args.partition("|")
        raw_id, new_text = raw_id.strip(), new_text.strip()

        if not raw_id.isdigit() or not new_text:
            return SkillResponse(text="Формат: /faq_edit <id> | новый ответ")

        if not self.store.get_faq(int(raw_id)):
            return SkillResponse(text=f"❌ Запись #{raw_id} не найдена.")

        self.store.update_faq(
            int(raw_id), answer=new_text, updated_by=ctx.user_id
        )
        return SkillResponse(text=f"✅ Запись #{raw_id} обновлена.")

    async def _faq_del(self, ctx: SkillContext, args: str) -> SkillResponse:
        """/faq_del <id>"""
        raw_id = args.strip()
        if not raw_id.isdigit():
            return SkillResponse(text="Формат: /faq_del <id>")
        if not self.store.delete_faq(int(raw_id)):
            return SkillResponse(text=f"❌ Запись #{raw_id} не найдена.")
        return SkillResponse(text=f"🗑 Запись #{raw_id} удалена.")

    async def _faq_publish(self, ctx: SkillContext, args: str) -> SkillResponse:
        """/faq_publish <id> — черновик становится видимым в /faq."""
        raw_id = args.strip()
        if not raw_id.isdigit():
            return SkillResponse(text="Формат: /faq_publish <id>")
        item = self.store.get_faq(int(raw_id))
        if item is None:
            return SkillResponse(text=f"❌ Запись #{raw_id} не найдена.")
        self.store.update_faq(
            int(raw_id), status="published", updated_by=ctx.user_id
        )
        return SkillResponse(
            text=f"✅ Запись #{raw_id} опубликована: {item['question']}"
        )

    async def _check_admin(self, ctx: SkillContext) -> bool:
        """Проверка прав с учётом лички."""
        is_private = bool(ctx.config.get("is_private", False))
        return await can_manage_faq(self.client, ctx.chat_id, ctx.user_id, is_private)

    # ── Обычные сообщения ──

    async def on_message(self, ctx: SkillContext, text: str) -> SkillResponse:
        """
        Отвечаем на вопросы по архиву.

        Возвращаем skip, если в базе ничего нет — тогда хелпер промолчит,
        а не будет спамить «не знаю» на каждое сообщение.
        """
        if self.store is None:
            return SkillResponse.skip()

        if not self._looks_like_question(text):
            return SkillResponse.skip()

        answer, found = await self._build_answer(ctx.chat_id, text)
        if not found:
            # В личке можно честно сказать, что не нашли; в группе — молчим,
            # чтобы не засорять чат (решение вызывающей стороны).
            if ctx.config.get("is_private"):
                return SkillResponse(text=answer)
            return SkillResponse.skip()
        return SkillResponse(text=answer)

    # Урезанное зеркало _SOCIAL_WORDS из group_gate — только на случай, когда
    # рантайм недоступен (изолированный запуск скилла). Источник истины —
    # group_gate.is_smalltalk; здесь достаточно самых частых приветствий.
    _FALLBACK_SOCIAL = frozenset({
        "привет", "приветик", "здравствуй", "здравствуйте", "хай", "доброе",
        "добрый", "утро", "день", "вечер", "спасибо", "пока", "всем", "народ",
        "ребят", "ребята", "дела", "жизнь", "как", "что", "кто", "тут", "здесь",
        "ты", "вы", "я", "мы", "а", "и", "ну", "вот", "у", "нас", "вас",
    })

    def _looks_like_question(self, text: str) -> bool:
        """
        Эвристика вопроса.

        Берём ту же функцию, что и групповой гейт: две расходящиеся
        реализации — это когда хелпер отвечает на «привет всем, как дела?».
        """
        if not text:
            return False
        if _gate_looks_like_question is not None:
            return _gate_looks_like_question(text)

        lowered = text.strip().lower()
        # Приветствие с вопросительным знаком вопросом не является.
        words = re.findall(r"[\wёЁ]+", lowered)
        if words and all(w in self._FALLBACK_SOCIAL for w in words):
            return False
        return "?" in lowered or bool(
            re.match(
                r"^(что|кто|как|где|куда|откуда|когда|почему|зачем|какой|"
                r"какая|какое|какие|чей|сколько|можно|подскажи|расскажи|объясни)",
                lowered,
            )
        )

    async def _build_answer(self, chat_id: int, query: str) -> tuple[str, bool]:
        """
        Собрать ответ: сначала точное совпадение в FAQ, потом поиск по архиву.

        Возвращает (текст, нашли_ли_что-то).
        """
        # 1. FAQ — самый надёжный источник.
        faq_hits = self.store.search_faq(chat_id, query, limit=2)
        if faq_hits:
            parts = [f"**{h['question']}**\n{h['answer']}" for h in faq_hits]
            return "\n\n".join(parts), True

        # 2. Полнотекстовый поиск по архиву.
        hits = self.store.search(chat_id, query, limit=self.context_limit)
        if not hits:
            return "Не нашёл в истории чата.", False

        # 3. Судья решает, отвечают ли найденные цитаты на вопрос. FTS ищет по
        #    основам слов и намеренно перебирает, поэтому «нашлось» само по
        #    себе ещё не значит «полезно».
        outcome, answer = await self._ask_judge(query, hits)
        if outcome == judge.ANSWER:
            return answer, True
        if outcome == judge.NO_ANSWER:
            # Цитаты не по делу — для вызывающей стороны это «не нашли»,
            # значит в группе бот промолчит.
            return "Не нашёл в истории чата.", False

        # 4. Судьи нет или он не ответил — деградируем до цитат. Хуже, но
        #    молчать из-за недоступной модели нельзя.
        lines = [f"💬 Нашёл в истории чата ({len(hits)}):\n"]
        for h in hits:
            who = h.get("sender_name") or "участник"
            when = (h.get("date") or "")[:10]
            snippet = (h.get("text") or "").strip()
            if len(snippet) > 300:
                snippet = snippet[:300] + "…"
            lines.append(f"• [{when}] {who}: {snippet}")
        return "\n".join(lines), True

    async def _ask_judge(self, query: str, hits: list[dict]) -> tuple[str, str | None]:
        """
        Спросить модель, отвечают ли цитаты на вопрос.

        Любой сбой — это UNAVAILABLE, а не отказ: молчать из-за упавшего
        провайдера бот не должен.
        """
        if self.llm_call is None:
            return judge.UNAVAILABLE, None
        try:
            raw = await self.llm_call(
                judge.JUDGE_SYSTEM, judge.build_user_prompt(query, hits)
            )
        except Exception as e:
            logger.warning("Судья недоступен, отдаю цитаты: {}", e)
            return judge.UNAVAILABLE, None
        return judge.parse_verdict(raw)
