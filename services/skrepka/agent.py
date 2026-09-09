"""
Скрепка — AI Admin Agent.

Responsibilities:
1. Monitor bot containers (health, uptime, resource usage)
2. Auto-debug bug reports (read logs + code → analysis)
3. Orchestrate containers (restart failed, scale on demand)
4. Report to Core API

Runs as a background process in its own Docker container.
Communicates with Core API and Docker socket.
"""

import asyncio
import json
import os
import traceback
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger

CORE_API_URL = os.getenv("CORE_API_URL", "http://core-api:8000")
# Shared secret for Core API; without it every call comes back 401.
CORE_API_TOKEN = os.getenv("CORE_API_TOKEN", "")
CORE_API_HEADERS = {"X-Core-API-Token": CORE_API_TOKEN} if CORE_API_TOKEN else {}
DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "unix:///var/run/docker.sock")
MONITOR_INTERVAL = int(os.getenv("SKREPKA_MONITOR_INTERVAL", "300"))  # 5 min
AUTO_RESTART = os.getenv("SKREPKA_AUTO_RESTART", "true").lower() == "true"

# Чат отладки: куда Скрепка пишет о новых багах и инцидентах.
# Раньше пользователю отвечали «разработчики будут уведомлены», но уведомлять
# было некому — отчёты просто ложились в таблицу, и никто о них не узнавал.
SKREPKA_BOT_TOKEN = os.getenv("SKREPKA_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
TELEGRAM_API = "https://api.telegram.org"


class SkrepkaAgent:
    """
    Скрепка — AI-админ платформы Zero Bot.
    Мониторит ботов, дебажит баги, оркестрирует контейнеры.
    """

    def __init__(self):
        self._running = False
        self._docker = None
        # Об отсутствии чата отладки предупреждаем один раз, а не каждый цикл.
        self._warned_no_admin_chat = False

    async def notify_admin(self, text: str) -> bool:
        """
        Отправить сообщение в чат отладки через Bot API.

        Обычный HTTPS-вызов: Telethon ради одного sendMessage не нужен.
        Возвращает True, если сообщение ушло.
        """
        if not (SKREPKA_BOT_TOKEN and ADMIN_CHAT_ID):
            if not self._warned_no_admin_chat:
                logger.warning(
                    "Чат отладки не настроен (SKREPKA_BOT_TOKEN/ADMIN_CHAT_ID) — "
                    "баги и инциденты останутся только в базе."
                )
                self._warned_no_admin_chat = True
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{TELEGRAM_API}/bot{SKREPKA_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": ADMIN_CHAT_ID,
                        "text": text[:4000],
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                )
                if r.status_code == 200:
                    return True
                logger.warning("Не удалось написать в чат отладки: {}", r.text[:200])
        except Exception as e:
            logger.error("Ошибка отправки в чат отладки: {}", e)
        return False

    async def start(self):
        """Start the agent."""
        self._running = True
        logger.info("Скрепка запущена")

        # Ensure Docker connection
        await self._init_docker()

        # Run main loop
        while self._running:
            try:
                await self.monitor_cycle()
            except Exception as e:
                logger.error(f"Скрепка monitor cycle error: {e}")

            await asyncio.sleep(MONITOR_INTERVAL)

    async def stop(self):
        self._running = False
        logger.info("Скрепка остановлена")

    async def _init_docker(self):
        """Initialize Docker client."""
        try:
            import docker
            self._docker = docker.from_env()
            # Test connection
            self._docker.ping()
            logger.info("Docker connection OK")
        except Exception as e:
            logger.error(f"Docker connection failed: {e}")
            self._docker = None

    async def monitor_cycle(self):
        """Single monitoring cycle: check all bots, report errors."""
        logger.info("Скрепка: monitor cycle started")

        # 1. Check bot containers health
        await self._check_containers_health()

        # 2. Check for unresolved bug reports
        await self._check_bug_reports()

        # 3. Check for error logs
        await self._check_error_logs()

        # 4. Report platform stats
        await self._report_stats()

        logger.info("Скрепка: monitor cycle complete")

    async def _check_containers_health(self):
        """Check health of all bot containers."""
        if not self._docker:
            return

        try:
            containers = self._docker.containers.list(
                filters={"label": "app=zero-bot"}
            )

            for container in containers:
                container.reload()
                status = container.status
                bot_id = container.labels.get("bot-id", "unknown")

                if status == "running":
                    # Check if responsive (health check)
                    health = container.attrs["State"].get("Health", {}).get("Status", "unknown")
                    if health == "unhealthy":
                        logger.warning(f"Bot {bot_id} is unhealthy")
                        if AUTO_RESTART:
                            await self._restart_bot(bot_id, container)

                elif status in ("exited", "dead"):
                    logger.warning(f"Bot {bot_id} is {status}")
                    if AUTO_RESTART:
                        await self._restart_bot(bot_id, container)

        except Exception as e:
            logger.error(f"Container health check failed: {e}")

    async def _restart_bot(self, bot_id: str, container):
        """Restart a bot container."""
        try:
            logger.info(f"Restarting bot {bot_id}")
            container.restart(timeout=30)
            await asyncio.sleep(5)

            # Check if it came back
            container.reload()
            if container.status == "running":
                logger.info(f"Bot {bot_id} restarted successfully")
            else:
                logger.error(f"Bot {bot_id} failed to restart")
                await self._report_incident(bot_id, "restart_failed", f"Container status: {container.status}")

        except Exception as e:
            logger.error(f"Failed to restart bot {bot_id}: {e}")

    async def _check_bug_reports(self):
        """Check for unresolved bug reports and auto-analyze."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get open bug reports
                r = await client.get(
                    f"{CORE_API_URL}/api/v1/feedback/bugs/",
                    headers=CORE_API_HEADERS,
                    params={"status": "open", "limit": "10"},
                )
                if r.status_code != 200:
                    return

                bugs = r.json()

                for bug in bugs:
                    bug_id = bug["id"]
                    # Check if already analyzed
                    if bug.get("ai_analysis"):
                        continue

                    # Auto-analyze
                    analysis = await self._analyze_bug(bug)
                    if analysis:
                        await self._submit_analysis(bug_id, analysis)

        except Exception as e:
            logger.error(f"Bug report check failed: {e}")

    async def _analyze_bug(self, bug: dict) -> Optional[str]:
        """
        Analyze a bug report using available context.
        In production, this would call an LLM.
        For now, rule-based analysis.
        """
        title = bug.get("title", "")
        description = bug.get("description", "")
        logs = bug.get("logs", "")

        analysis_parts = []
        analysis_parts.append(f"## Анализ бага: {title}")
        analysis_parts.append(f"**Описание:** {description[:200]}")

        # Check for common patterns
        if logs:
            if "ConnectionError" in logs or "Timeout" in logs:
                analysis_parts.append("\n**Вероятная причина:** Проблема с сетью или внешним API.")
                analysis_parts.append("**Рекомендация:** Проверить доступность внешнего сервиса, добавить retry.")
            elif "KeyError" in logs or "AttributeError" in logs:
                analysis_parts.append("\n**Вероятная причина:** Ошибка в коде — отсутствующий ключ или атрибут.")
                analysis_parts.append("**Рекомендация:** Добавить проверку на None, использовать .get().")
            elif "PermissionError" in logs:
                analysis_parts.append("\n**Вероятная причина:** Недостаточно прав доступа.")
                analysis_parts.append("**Рекомендация:** Проверить права на файлы/директории.")
            elif "MemoryError" in logs or "OOM" in logs:
                analysis_parts.append("\n**Вероятная причина:** Нехватка памяти.")
                analysis_parts.append("**Рекомендация:** Оптимизировать использование памяти, увеличить лимит.")
            else:
                analysis_parts.append(f"\n**Логи:** {logs[:500]}")
                analysis_parts.append("**Рекомендация:** Требуется ручной анализ разработчиком.")

        analysis_parts.append(f"\n**Приоритет:** medium")
        analysis_parts.append(f"\n*Анализ выполнен Скрепкой автоматически*")

        return "\n".join(analysis_parts)

    async def _submit_analysis(self, bug_id: str, analysis: str):
        """Submit bug analysis to Core API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{CORE_API_URL}/api/v1/skrepka/bug-analysis/",
                    headers=CORE_API_HEADERS,
                    json={
                        "bug_id": bug_id,
                        "analysis": analysis,
                    },
                )
                if r.status_code == 200:
                    logger.info(f"Bug {bug_id} analyzed")
                    await self.notify_admin(
                        f"🐞 *Новый баг* `{bug_id}`\n\n{analysis[:1500]}"
                    )
                else:
                    logger.warning(f"Failed to submit analysis for {bug_id}")
        except Exception as e:
            logger.error(f"Failed to submit analysis: {e}")

    async def _check_error_logs(self):
        """Check for recent error logs from bots."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{CORE_API_URL}/api/v1/feedback/error-logs/",
                    headers=CORE_API_HEADERS,
                    params={"limit": "20"},
                )
                if r.status_code != 200:
                    return

                logs = r.json()

                # Group by bot_id
                bot_errors: dict[str, list] = {}
                for log in logs:
                    bid = log.get("bot_id", "unknown")
                    if bid not in bot_errors:
                        bot_errors[bid] = []
                    bot_errors[bid].append(log)

                # Report bots with many errors
                for bot_id, errors in bot_errors.items():
                    if len(errors) >= 5:
                        await self._report_incident(
                            bot_id,
                            "high_error_rate",
                            f"{len(errors)} errors in last check",
                        )

        except Exception as e:
            logger.error(f"Error log check failed: {e}")

    async def _report_incident(self, bot_id: str, incident_type: str, message: str):
        """Report an incident to Core API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/feedback/error-logs/",
                    headers=CORE_API_HEADERS,
                    json={
                        "bot_id": bot_id,
                        "error_type": f"incident_{incident_type}",
                        "message": message,
                    },
                )
        except Exception as e:
            logger.error(f"Failed to report incident: {e}")

        # Инциденты — то, ради чего чат отладки и нужен: упавший бот должен
        # быть виден человеку, а не только строкой в error_logs.
        await self.notify_admin(
            f"🚨 *Инцидент* `{incident_type}`\nБот: `{bot_id}`\n\n{message[:1000]}"
        )

    async def _report_stats(self):
        """Report platform stats."""
        if not self._docker:
            return

        try:
            containers = self._docker.containers.list(
                all=True,
                filters={"label": "app=zero-bot"}
            )
            active = sum(1 for c in containers if c.status == "running")

            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{CORE_API_URL}/api/v1/skrepka/health/",
                    headers=CORE_API_HEADERS,
                    json={
                        "status": "ok",
                        "agent": "skrepka",
                        "active_bots": active,
                        "total_bots": len(containers),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            logger.error(f"Failed to report stats: {e}")


async def main():
    agent = SkrepkaAgent()
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Скрепка stopped by user")
    except Exception as e:
        logger.error(f"Скрепка crashed: {e}")
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
