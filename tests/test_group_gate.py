"""Tests for group gating — the bot must not reply to ordinary chatter."""

import pytest

from group_gate import (
    Trigger,
    decide,
    is_command_for_bot,
    is_smalltalk,
    looks_like_question,
    parse_command,
)


class TestParseCommand:
    def test_plain_command(self):
        parsed = parse_command("/faq")
        assert parsed.command == "faq"
        assert parsed.args == ""

    def test_command_with_args(self):
        parsed = parse_command("/faq_add Как запустить бота? | Ответ")
        assert parsed.command == "faq_add"
        assert parsed.args == "Как запустить бота? | Ответ"

    def test_command_with_bot_target(self):
        parsed = parse_command("/faq@MyHelperBot")
        assert parsed.command == "faq"

    def test_not_a_command(self):
        assert parse_command("привет всем") is None


class TestCommandTargeting:
    def test_plain_command_is_ours(self):
        assert is_command_for_bot("/faq", "my_helper_bot")

    def test_targeted_at_us(self):
        assert is_command_for_bot("/faq@my_helper_bot", "my_helper_bot")

    def test_targeted_at_other_bot_is_not_ours(self):
        assert not is_command_for_bot("/faq@other_bot", "my_helper_bot")


class TestQuestionHeuristic:
    @pytest.mark.parametrize(
        "text",
        [
            "Как запустить бота?",
            "Где лежит конфиг?",
            "Это работает, да?",
            "Кто дежурный сегодня",
        ],
    )
    def test_questions(self, text):
        assert looks_like_question(text)

    @pytest.mark.parametrize(
        "text",
        [
            "привет всем",
            "сегодня хорошая погода",
            "я пошёл домой",
        ],
    )
    def test_not_questions(self, text):
        assert not looks_like_question(text)


class TestGroupDecisions:
    def test_chatter_ignored(self):
        d = decide("просто болтаю ни о чём", is_private=False,
                   bot_username="my_helper_bot")
        assert d.trigger is Trigger.NONE
        assert not d.should_handle

    def test_mention_triggers(self):
        d = decide("@my_helper_bot где конфиг?", is_private=False,
                   bot_username="my_helper_bot")
        assert d.trigger is Trigger.MENTION
        assert "@my_helper_bot" not in d.clean_text

    def test_activation_phrase_triggers(self):
        d = decide("Ия, расскажи про деплой", is_private=False,
                   bot_username="my_helper_bot", activation_phrase="ия")
        assert d.trigger is Trigger.MENTION
        assert "Ия" not in d.clean_text

    def test_reply_to_bot_triggers(self):
        d = decide("а это точно работает?", is_private=False,
                   bot_username="my_helper_bot", is_reply_to_bot=True)
        assert d.trigger is Trigger.REPLY

    def test_question_triggers_and_needs_retrieval(self):
        d = decide("Как запустить бота?", is_private=False,
                   bot_username="my_helper_bot")
        assert d.trigger is Trigger.QUESTION
        assert d.needs_retrieval_check

    def test_command_in_group(self):
        d = decide("/faq", is_private=False, bot_username="my_helper_bot")
        assert d.trigger is Trigger.COMMAND
        assert d.parsed.command == "faq"

    def test_other_bots_command_ignored(self):
        d = decide("/faq@other_bot", is_private=False,
                   bot_username="my_helper_bot")
        assert d.trigger is Trigger.NONE

    def test_mention_plus_command_routes_as_command(self):
        d = decide("@my_helper_bot /faq", is_private=False,
                   bot_username="my_helper_bot")
        assert d.trigger is Trigger.COMMAND
        assert d.parsed.command == "faq"

    def test_empty_text_ignored(self):
        assert decide("", is_private=False).trigger is Trigger.NONE

    def test_private_chat_always_handles(self):
        d = decide("какая погода", is_private=True)
        assert d.trigger is Trigger.PRIVATE
        assert d.should_handle

    def test_private_command(self):
        d = decide("/stats", is_private=True)
        assert d.trigger is Trigger.COMMAND
        assert d.parsed.command == "stats"


class TestSmalltalk:
    """
    Дешёвый отсев болтовни перед дорогими шагами.

    Это только пре-фильтр: он экономит вызов модели на очевидном приветствии,
    а решение «отвечают ли найденные цитаты на вопрос» принимает LLM-судья
    в скилле. Поэтому здесь проверяется граница поведения, а не словарь:
    список социальных слов заведомо неполон и полнотой быть не обязан.
    """

    def test_greeting_with_question_mark_is_not_a_question(self):
        """Тот самый случай: знак вопроса не делает приветствие вопросом."""
        assert is_smalltalk("привет всем, как дела?")
        assert not looks_like_question("привет всем, как дела?")

    def test_greeting_prefix_does_not_swallow_the_question(self):
        """Приветствие перед вопросом не должно глушить сам вопрос."""
        assert not is_smalltalk("привет, как задеплоить проект?")
        assert looks_like_question("привет, как задеплоить проект?")

    def test_greeting_in_group_is_not_handled(self):
        assert decide("привет всем, как дела?", is_private=False).trigger is Trigger.NONE

    def test_greeting_still_answered_when_bot_is_mentioned(self):
        """Прямое обращение важнее фильтра болтовни."""
        d = decide("@helper привет, как дела?", is_private=False, bot_username="helper")
        assert d.trigger is Trigger.MENTION

    def test_unknown_greeting_is_left_to_the_judge(self):
        """
        Чего нет в словаре — проходит дальше, а не режется здесь.

        Фильтр настроен на полноту: пропустить болтовню к судье дёшево,
        потерять настоящий вопрос — нет.
        """
        assert not is_smalltalk("здарова, народ!")
