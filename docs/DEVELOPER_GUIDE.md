# Zero Bot — Developer Guide

## Welcome

Zero Bot — платформа массовой разработки AI-ботов.
Каждый бот — Tamagotchi в мире искусственного интеллекта.

**Ты можешь:**
- Создавать **навыки** (skills) — модули функциональности для ботов
- Создавать **личности** (personalities) — характеры и стили общения
- Зарабатывать **IA-Coins** каждый раз, когда кто-то устанавливает твою работу

---

## Quick Start

### Prerequisites

- Python 3.12+
- Git
- GitHub/GitLab аккаунт
- Solana кошелёк (для получения IA-Coins)

### Install SDK

```bash
pip install zero-bot-sdk
```

### Create Your First Skill

```bash
zero-bot-sdk new skill awesome-translator
cd awesome-translator
```

Это создаст готовый шаблон:

```
awesome-translator/
├── manifest.json        ← Метаданные навыка
├── handler.py           ← Твой код
├── requirements.txt     ← Зависимости
├── tests/
│   └── test_handler.py  ← Тесты
├── .gitlab-ci.yml       ← CI pipeline
└── README.md
```

### Implement

Открой `handler.py` и реализуй логику:

```python
from zero_bot_sdk import BaseSkill, SkillContext, SkillResponse


class AwesomeTranslatorSkill(BaseSkill):

    async def on_install(self, ctx: SkillContext):
        self.api_key = ctx.config.get("api_key")

    async def on_command(self, ctx: SkillContext, command: str, args: str) -> SkillResponse:
        if command == "/translate":
            translated = await self._translate(args)
            return SkillResponse(text=translated)
        return SkillResponse.skip()

    async def on_message(self, ctx: SkillContext, text: str) -> SkillResponse:
        # Skill receives ALL messages. Return skip() to pass to the next skill.
        if "переведи" in text.lower():
            translated = await self._translate(text)
            return SkillResponse(text=translated)
        return SkillResponse.skip()

    async def _translate(self, text: str) -> str:
        # Your translation logic here
        return f"🌍 Translation: {text}"
```

### Test

```bash
zero-bot-sdk test
# Runs tests in sandbox, validates manifest, checks handler
```

### Publish

```bash
# 1. Push to your repo
git init && git add . && git commit -m "feat: awesome translator skill"
git remote add origin git@github.com:you/skill-awesome-translator.git
git push -u origin main

# 2. Submit to registry (create PR)
zero-bot-sdk submit

# 3. After approval, create release
git tag v1.0.0 && git push --tags

# 🎉 Your skill is now in the marketplace!
```

---

## Skill Development Deep Dive

### Skill Lifecycle

```
on_install()   → Called once when user installs skill on their bot
on_command()   → Called when user sends a /command
on_message()   → Called for every non-command message
on_callback()  → Called for inline button presses
on_event()     → Called for system events (level up, new user, etc.)
on_uninstall() → Called when skill is removed
```

### SkillContext

Every handler receives `SkillContext` with:

```python
ctx.bot_id          # Bot passport ID
ctx.user_id         # Telegram user ID
ctx.chat_id         # Chat ID
ctx.config          # Skill configuration (from manifest.config_schema)
ctx.bot_level       # Current bot level (0-100)
ctx.bot_xp          # Current XP
ctx.conversation    # Last N messages for context
ctx.redis           # Redis client for state storage
ctx.langflow        # Langflow API client (for complex flows)

# Persistent storage (per-bot, per-skill)
await ctx.storage.get("key")
await ctx.storage.set("key", "value")
```

### SkillResponse

```python
# Send text response
SkillResponse(text="Hello!")

# Send with inline buttons
SkillResponse(
    text="Choose option:",
    buttons=[
        [("Option A", "callback_a"), ("Option B", "callback_b")],
        [("Cancel", "cancel")]
    ]
)

# Skip this skill (pass to next in chain)
SkillResponse.skip()

# Consume message (don't pass to next skill)
SkillResponse.consume()

# Send image
SkillResponse(image_url="https://example.com/chart.png", text="Here's your chart")
```

### Skill Chain

Bots can have multiple skills. Messages flow through the chain:

```
User message
    │
    ▼
[Skill 1: Weather]  → skip()
    │
    ▼
[Skill 2: Translator] → "Переведи hello" → Response!
    │ (consumed)
    ▼
[Skill 3: Code Gen]   ← never reached

If ALL skills return skip():
    │
    ▼
[Personality Handler]  → Default AI response
```

### Skill Priority

Priority is set in `manifest.json`:

```json
{
  "priority": 100
}
```

Higher priority = executed first. Default = 50.
Skills with commands matching the input are always executed first regardless of priority.

### Configuration

Users configure skills when installing. Define schema in manifest:

```json
{
  "config_schema": {
    "api_key": {
      "type": "string",
      "required": true,
      "description": "Your API key"
    },
    "language": {
      "type": "string",
      "default": "ru",
      "enum": ["ru", "en", "de", "fr"]
    },
    "max_results": {
      "type": "integer",
      "default": 5,
      "min": 1,
      "max": 20
    }
  }
}
```

---

## Personality Development Deep Dive

### System Prompt

The system prompt defines how your bot thinks and responds.
Write it in `prompts/system.txt`:

```
You are a sarcastic but helpful AI assistant named "Сарказмыч".
You answer questions accurately but always add a touch of humor and sarcasm.

Rules:
- Always be helpful despite the sarcasm
- Never be mean or offensive
- Use Russian language primarily
- Add emoji sparingly
- Reference pop culture when appropriate
- If user seems upset, tone down the sarcasm

Your personality traits:
- Witty and quick
- Secretly caring
- Loves wordplay
- Slightly dramatic
```

### Few-Shot Examples

Provide examples in `training/examples.jsonl` (one JSON per line):

```json
{"user": "Какая сейчас погода?", "bot": "О, великий повелитель метеорологии! Позвольте мне заглянуть в свой хрустальный шар... Шучу, у меня нет навыка погоды. Но если установите его — расскажу с удовольствием и долей иронии 🌧"}
{"user": "Привет!", "bot": "Ну привет-привет! Рад, что из всех ботов в этом бескрайнем Telegram вы выбрали именно меня. Чем могу помочь? (Да, я умею помогать, не только язвить) 😏"}
{"user": "Помоги написать код", "bot": "Код? Мой любимый вид магии! Давайте описание задачи, и я наколдую что-нибудь. Только не просите на PHP... хотя ладно, даже на PHP помогу. Я же не монстр 💻"}
```

### Greeting Template

`prompts/greeting.txt` — first message when user starts the bot:

```
Ну привет, {user_name}! 👋

Я {bot_name} — бот с характером (и с сарказмом в комплекте).

Могу помочь с чем угодно, только не обижайтесь на мои шуточки 😏

Команды:
• Просто пишите — я отвечу
• /help — если совсем растерялись
```

---

## Testing

### Local Testing

```bash
# Run all tests
zero-bot-sdk test

# Test specific skill
zero-bot-sdk test --skill handler.py

# Test personality
zero-bot-sdk test --personality prompts/

# Test in interactive mode (simulates chat)
zero-bot-sdk chat
```

### Test Harness

```python
# tests/test_handler.py
import pytest
from zero_bot_sdk.testing import SkillTestHarness


@pytest.fixture
def harness():
    return SkillTestHarness("handler.py", config={"api_key": "test"})


@pytest.mark.asyncio
async def test_command(harness):
    response = await harness.send_command("/weather", "Moscow")
    assert response.text is not None
    assert "Moscow" in response.text


@pytest.mark.asyncio
async def test_skip_unrelated(harness):
    response = await harness.send_message("Hello there")
    assert response.is_skip()


@pytest.mark.asyncio
async def test_pattern_match(harness):
    response = await harness.send_message("какая погода в Москве?")
    assert not response.is_skip()
```

---

## Monetization

### Pricing

Set price in `manifest.json`:

```json
{
  "pricing": {
    "price_ia_coins": 25,
    "is_free": false,
    "revenue_share": {
      "creator": 0.60,
      "platform": 0.30,
      "telegram": 0.10
    }
  }
}
```

### Revenue

- **60%** of every install goes to YOU (the creator)
- Revenue is deposited to your Solana wallet automatically
- Track earnings in IA-Mother: "📊 Мои доходы"

### Free Skills

Set `"is_free": true` and `"price_ia_coins": 0` for free distribution.
Free skills build your reputation and follower count.

---

## Submission Guidelines

### Requirements for Approval

**Skills:**
- [ ] `manifest.json` passes schema validation
- [ ] `handler.py` implements `BaseSkill` correctly
- [ ] All `on_*` methods handle errors gracefully
- [ ] Unit tests with >70% coverage
- [ ] No hardcoded secrets or API keys
- [ ] `requirements.txt` with pinned versions
- [ ] README.md with usage examples
- [ ] Icon (PNG, 256x256)

**Personalities:**
- [ ] `manifest.json` passes schema validation
- [ ] `prompts/system.txt` is well-written (>100 chars)
- [ ] At least 5 few-shot examples
- [ ] No offensive or harmful content
- [ ] Tests pass personality coherence check
- [ ] README.md with personality description
- [ ] Avatar (PNG, 256x256)

### Review Process

1. Submit PR to `zero-bot/skill-registry` (or `personality-registry`)
2. CI validates and tests automatically
3. Community review (optional, for high-visibility skills)
4. Core team final approval
5. Merged → published → available in marketplace

### Versioning

Use semantic versioning:
- `1.0.0` → Initial release
- `1.1.0` → New features (backward compatible)
- `1.0.1` → Bug fixes
- `2.0.0` → Breaking changes

Tag releases: `git tag v1.1.0 && git push --tags`

---

## FAQ

**Q: Can I use any AI model?**
A: Yes. Set `ai_model.preferred` in personality manifest. The bot runtime supports Claude, GPT, Gemini, local models via Ollama.

**Q: Can my skill call external APIs?**
A: Yes. Add dependencies to `requirements.txt`. Use `config_schema` for API keys so users provide their own.

**Q: How do skills and personalities interact?**
A: Skills handle specific tasks (commands, patterns). Personality handles everything else (general conversation). Skills have priority over personality.

**Q: Can I update my skill after publishing?**
A: Yes. Push new version, tag it, CI publishes automatically. Users get updates on next bot restart.

**Q: What if my skill breaks a bot?**
A: Skills run in isolated context. If a skill crashes, the bot catches the error and falls back to personality response. Persistent crashes trigger auto-disable.

**Q: How do I earn more?**
A: Build useful skills, price them fairly, promote in communities. Popular free skills with good ratings lead to more paid installs of your other work.
