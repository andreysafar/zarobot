# Zero Bot Platform — Infrastructure Architecture

## Philosophy

> **"1 Bot = 1 Docker Container. 1 Skill = 1 Repo. 1 Personality = 1 Repo."**

Zero Bot — это платформа массовой разработки AI-ботов с токеномикой.
Каждый бот — Tamagotchi, которого пользователь растит, обучает, монетизирует.

---

## Repository Topology

```
CORE (only platform devs)
├── zero-bot/zero-bot          ← Main repo. Bot runtime + IA-Mother + infra
│
REGISTRY (public, curated)
├── zero-bot/skill-registry    ← Index of approved skills (like npm registry)
├── zero-bot/personality-registry  ← Index of approved personalities
│
COMMUNITY (anyone can create)
├── alice/skill-weather        ← Example: weather skill by developer "alice"
├── bob/personality-sarcastic  ← Example: sarcastic personality by "bob"
├── carol/skill-code-review    ← Example: code review skill by "carol"
└── ...                        ← Unlimited community repos
```

### Access Model

| Repo Type | Who can write | Who can read | Deployment |
|-----------|--------------|-------------|------------|
| `zero-bot/zero-bot` | Core team only | Public | GitLab Runner → all containers |
| `zero-bot/skill-registry` | Core team (merge) | Public | Auto-index |
| `zero-bot/personality-registry` | Core team (merge) | Public | Auto-index |
| `*/skill-*` | Anyone (owner) | Public | PR → Registry → Runner |
| `*/personality-*` | Anyone (owner) | Public | PR → Registry → Runner |

---

## Container Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host / K8s                      │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  IA-Mother   │  │  Zero Bot   │  │  Zero Bot   │     │
│  │  (master)    │  │  Clone #1   │  │  Clone #2   │ ... │
│  │             │  │  "Алиса"    │  │  "Макс"     │     │
│  │  Port 8001  │  │  Port auto  │  │  Port auto  │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │              │
│  ┌──────┴────────────────┴────────────────┴──────┐      │
│  │                   Redis                        │      │
│  │         (pub/sub + state + registry)           │      │
│  └────────────────────┬──────────────────────────┘      │
│                       │                                  │
│  ┌────────────────────┴──────────────────────────┐      │
│  │                  Langflow                      │      │
│  │        (Admin UI + Flow Builder + API)         │      │
│  │              Port 7860                         │      │
│  └────────────────────────────────────────────────┘      │
│                                                           │
│  ┌────────────────────────────────────────────────┐      │
│  │              GitLab Runner                      │      │
│  │     (CI/CD: build, test, deploy containers)     │      │
│  └────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

### Containers

| Container | Image | Purpose | Replicas |
|-----------|-------|---------|----------|
| `ia-mother` | `zero-bot/ia-mother:latest` | Master bot. Marketplace, exchange, cloning | 1 |
| `zero-bot-{id}` | `zero-bot/bot-instance:latest` | Individual bot instance (Tamagotchi) | N (1 per user bot) |
| `redis` | `redis:7-alpine` | State, pub/sub, skill/personality cache | 1 |
| `langflow` | `langflowai/langflow:latest` | Admin UI, flow builder, API | 1 |
| `gitlab-runner` | `gitlab/gitlab-runner:latest` | CI/CD pipeline execution | 1+ |

---

## IA-Mother Bot — Master Bot

IA-Mother is the entry point. It does NOT process messages for users.
It manages the ecosystem:

```
User → /start → IA-Mother
         │
         ├── "🥚 Создать бота" → Clone zero-bot → New container
         ├── "🏪 Маркетплейс"  → Browse skills/personalities
         ├── "💱 Обменник"      → Stars ↔ IA-Coins
         ├── "📊 Статистика"    → Platform stats
         └── "🤖 Мои боты"     → List user's bot containers
```

### Clone Flow

```
1. User clicks "Создать бота" in IA-Mother
2. IA-Mother creates BotPassport (NFT on Solana)
3. IA-Mother requests new bot token from BotFather API
4. GitLab Runner spins up new container:
   - Image: zero-bot/bot-instance:latest
   - Env: BOT_TOKEN, BOT_ID, OWNER_ID
   - Mounts: personality config, skill manifests
5. New bot sends /start to owner: "Привет! Я твой новый Tamagotchi!"
6. Training begins (user interacts, bot levels up)
```

---

## Zero Bot Instance — The Tamagotchi

Each cloned bot runs in its own container with:

```
zero-bot-instance/
├── bot.py              ← Telethon bot runtime
├── config.json         ← Bot configuration (personality, skills, level)
├── skills/             ← Installed skills (loaded at runtime)
│   ├── weather/
│   │   └── manifest.json
│   └── code-review/
│       └── manifest.json
├── personality/        ← Active personality
│   └── manifest.json
└── data/
    ├── conversations.db  ← SQLite (conversation history)
    └── state.json        ← Bot state (XP, level, stats)
```

### Bot Lifecycle

```
🥚 Created  →  👶 Newborn (Level 0)  →  🧒 Learning (Level 1-5)
    │              │                        │
    │              │ First message           │ Skills installed
    │              ▼                        ▼
    │         🤖 Active (Level 5-20)  →  🧠 Expert (Level 20+)
    │              │                        │
    │              │ Revenue earned          │ Can teach others
    │              ▼                        ▼
    │         💰 Earning              →  👑 Master
    │
    └── 💀 Abandoned (no interaction 30 days) → Container stopped
```

---

## Skill System

### Skill Repository Structure

Every skill is a separate GitHub/GitLab repository:

```
alice/skill-weather/
├── manifest.json        ← Skill metadata (REQUIRED)
├── handler.py           ← Skill logic (REQUIRED)
├── requirements.txt     ← Python dependencies
├── tests/
│   └── test_handler.py  ← Tests (REQUIRED for approval)
├── README.md            ← Documentation
├── .gitlab-ci.yml       ← CI pipeline (auto-generated from template)
└── icon.png             ← Skill icon for marketplace
```

### manifest.json (Skill)

```json
{
  "schema_version": "1.0",
  "name": "weather",
  "display_name": "Weather Forecast",
  "description": "Get weather forecasts for any city worldwide",
  "version": "1.2.0",
  "author": {
    "name": "alice",
    "github": "alice",
    "solana_address": "ALiCe..."
  },
  "category": "utilities",
  "tags": ["weather", "forecast", "api"],
  "icon": "icon.png",

  "entry_point": "handler.py",
  "handler_class": "WeatherSkill",

  "commands": [
    {
      "trigger": "/weather",
      "description": "Get current weather",
      "usage": "/weather Moscow"
    }
  ],

  "message_patterns": [
    "какая погода",
    "weather in",
    "прогноз"
  ],

  "config_schema": {
    "api_key": {
      "type": "string",
      "required": true,
      "description": "OpenWeatherMap API key"
    }
  },

  "requirements": ["httpx>=0.27"],

  "pricing": {
    "price_ia_coins": 0,
    "is_free": true,
    "revenue_share": {
      "creator": 0.60,
      "platform": 0.30,
      "telegram": 0.10
    }
  },

  "compatibility": {
    "min_bot_level": 1,
    "max_skills_conflict": [],
    "required_skills": []
  },

  "solana": {
    "registry_address": null,
    "tx_hash": null
  }
}
```

### handler.py (Skill Template)

```python
"""
Skill: Weather Forecast
Every skill MUST implement BaseSkill interface.
"""

from zero_bot_sdk import BaseSkill, SkillContext, SkillResponse


class WeatherSkill(BaseSkill):
    """Weather forecast skill"""

    async def on_install(self, ctx: SkillContext):
        """Called once when skill is installed on a bot"""
        self.api_key = ctx.config.get("api_key")

    async def on_command(self, ctx: SkillContext, command: str, args: str) -> SkillResponse:
        """Handle /weather command"""
        if command == "/weather":
            city = args or "Moscow"
            weather = await self._fetch_weather(city)
            return SkillResponse(text=f"🌤 {city}: {weather}")
        return SkillResponse.skip()

    async def on_message(self, ctx: SkillContext, text: str) -> SkillResponse:
        """Handle natural language messages matching patterns"""
        # Return SkillResponse.skip() to pass to next skill
        return SkillResponse.skip()

    async def on_uninstall(self, ctx: SkillContext):
        """Cleanup when skill is removed"""
        pass

    async def _fetch_weather(self, city: str) -> str:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": self.api_key, "units": "metric", "lang": "ru"}
            )
            data = resp.json()
            return f"{data['weather'][0]['description']}, {data['main']['temp']}°C"
```

---

## Personality System

### Personality Repository Structure

```
bob/personality-sarcastic/
├── manifest.json        ← Personality metadata (REQUIRED)
├── prompts/
│   ├── system.txt       ← System prompt (REQUIRED)
│   ├── greeting.txt     ← First message template
│   └── fallback.txt     ← Default response template
├── training/
│   ├── examples.jsonl   ← Few-shot examples
│   └── style_guide.md   ← Writing style description
├── tests/
│   └── test_personality.py
├── README.md
├── .gitlab-ci.yml
├── avatar.png           ← Bot avatar
└── banner.png           ← Marketplace banner
```

### manifest.json (Personality)

```json
{
  "schema_version": "1.0",
  "name": "sarcastic-friend",
  "display_name": "Саркастичный Друг",
  "description": "Остроумный AI с тонким чувством юмора и долей сарказма",
  "version": "2.0.0",
  "author": {
    "name": "bob",
    "github": "bob",
    "solana_address": "B0b..."
  },
  "category": "entertainment",
  "tags": ["humor", "sarcasm", "friend", "russian"],
  "language": "ru",
  "avatar": "avatar.png",
  "banner": "banner.png",

  "prompts": {
    "system": "prompts/system.txt",
    "greeting": "prompts/greeting.txt",
    "fallback": "prompts/fallback.txt"
  },

  "training": {
    "examples": "training/examples.jsonl",
    "style_guide": "training/style_guide.md"
  },

  "ai_model": {
    "preferred": "claude-sonnet-4-20250514",
    "fallback": "gpt-4o-mini",
    "temperature": 0.8,
    "max_tokens": 1024
  },

  "behavior": {
    "response_style": "casual",
    "emoji_usage": "moderate",
    "formality": "low",
    "humor_level": "high"
  },

  "pricing": {
    "price_ia_coins": 15,
    "is_free": false,
    "revenue_share": {
      "creator": 0.60,
      "platform": 0.30,
      "telegram": 0.10
    }
  },

  "compatibility": {
    "min_bot_level": 0,
    "conflicts_with": []
  },

  "solana": {
    "registry_address": null,
    "tx_hash": null
  }
}
```

---

## CI/CD Pipeline (GitLab Runner)

### Pipeline Architecture

```
Developer pushes to skill/personality repo
         │
         ▼
┌─────────────────────────────────┐
│        GitLab CI Pipeline        │
│                                  │
│  Stage 1: VALIDATE              │
│  ├── Check manifest.json schema │
│  ├── Lint Python code           │
│  └── Security scan              │
│                                  │
│  Stage 2: TEST                  │
│  ├── Run unit tests             │
│  ├── Test in sandbox container  │
│  └── Generate coverage report   │
│                                  │
│  Stage 3: BUILD                 │
│  ├── Package skill/personality  │
│  ├── Build Docker layer         │
│  └── Push to registry           │
│                                  │
│  Stage 4: PUBLISH               │
│  ├── Register on Solana         │
│  ├── Update skill-registry      │
│  ├── Notify IA-Mother           │
│  └── Available in marketplace   │
│                                  │
│  Stage 5: DEPLOY (on install)   │
│  ├── Pull into bot container    │
│  ├── Hot-reload skill           │
│  └── Verify health              │
└─────────────────────────────────┘
```

### .gitlab-ci.yml (Skill Template)

```yaml
# Auto-generated by zero-bot platform
# DO NOT EDIT — managed by zero-bot/zero-bot

include:
  - project: 'zero-bot/zero-bot'
    ref: main
    file: '/ci/templates/skill.gitlab-ci.yml'

variables:
  SKILL_NAME: "weather"
  SKILL_VERSION: "1.2.0"
  AUTHOR_SOLANA_ADDRESS: "ALiCe..."
```

### .gitlab-ci.yml (Personality Template)

```yaml
include:
  - project: 'zero-bot/zero-bot'
    ref: main
    file: '/ci/templates/personality.gitlab-ci.yml'

variables:
  PERSONALITY_NAME: "sarcastic-friend"
  PERSONALITY_VERSION: "2.0.0"
  AUTHOR_SOLANA_ADDRESS: "B0b..."
```

### Core CI Template (in zero-bot/zero-bot repo)

```yaml
# ci/templates/skill.gitlab-ci.yml
# Shared pipeline for all skills

stages:
  - validate
  - test
  - build
  - publish

validate:manifest:
  stage: validate
  image: python:3.12-slim
  script:
    - pip install jsonschema
    - python -c "
      import json, jsonschema;
      schema = json.load(open('ci/schemas/skill-manifest.schema.json'));
      manifest = json.load(open('manifest.json'));
      jsonschema.validate(manifest, schema);
      print('Manifest valid')
      "

validate:lint:
  stage: validate
  image: python:3.12-slim
  script:
    - pip install ruff
    - ruff check .

test:unit:
  stage: test
  image: python:3.12-slim
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-asyncio zero-bot-sdk
    - pytest tests/ -v

test:sandbox:
  stage: test
  image: zero-bot/bot-instance:latest
  script:
    - python -c "
      from handler import *;
      import asyncio;
      # Sandbox test: skill loads and responds
      "

build:package:
  stage: build
  script:
    - tar czf skill-${SKILL_NAME}-${SKILL_VERSION}.tar.gz
        manifest.json handler.py requirements.txt
    - echo "Package built"
  artifacts:
    paths:
      - "skill-*.tar.gz"

publish:registry:
  stage: publish
  only:
    - tags
  script:
    - |
      curl -X POST "${REGISTRY_API}/skills/publish" \
        -H "Authorization: Bearer ${REGISTRY_TOKEN}" \
        -F "package=@skill-${SKILL_NAME}-${SKILL_VERSION}.tar.gz" \
        -F "manifest=@manifest.json"
    - echo "Published to registry"

publish:solana:
  stage: publish
  only:
    - tags
  script:
    - python ci/scripts/register_on_solana.py
        --name="${SKILL_NAME}"
        --version="${SKILL_VERSION}"
        --author="${AUTHOR_SOLANA_ADDRESS}"
        --price="$(jq -r '.pricing.price_ia_coins' manifest.json)"
```

---

## Zero Bot SDK

The `zero-bot-sdk` package is published to PyPI and provides base classes:

```python
# zero_bot_sdk/__init__.py

from .base_skill import BaseSkill
from .base_personality import BasePersonality
from .context import SkillContext, PersonalityContext
from .response import SkillResponse
from .decorators import command, on_pattern, on_event
from .testing import SkillTestHarness, PersonalityTestHarness
```

### Installation

```bash
pip install zero-bot-sdk
```

### Scaffold New Skill

```bash
zero-bot-sdk new skill my-awesome-skill
# Creates:
#   my-awesome-skill/
#   ├── manifest.json (template)
#   ├── handler.py (template)
#   ├── requirements.txt
#   ├── tests/test_handler.py
#   ├── .gitlab-ci.yml
#   └── README.md
```

### Scaffold New Personality

```bash
zero-bot-sdk new personality my-cool-persona
# Creates:
#   my-cool-persona/
#   ├── manifest.json (template)
#   ├── prompts/system.txt
#   ├── prompts/greeting.txt
#   ├── training/examples.jsonl
#   ├── tests/test_personality.py
#   ├── .gitlab-ci.yml
#   └── README.md
```

---

## Tokenomics Integration

### Revenue Flow

```
User installs Skill (25 IA-Coins)
         │
         ├── 60% → Skill Creator (15 IA-Coins)     ← Solana transfer
         ├── 30% → Platform (7.5 IA-Coins)          ← Platform wallet
         └── 10% → Telegram fee (2.5 IA-Coins)      ← Stars conversion
```

### On-Chain Registration

Every published skill/personality is registered on Solana:

```
┌──────────────────────────────────────┐
│         Solana Program               │
│                                      │
│  PDA: skill_registry/{skill_name}    │
│  ├── creator: Pubkey                 │
│  ├── version: string                 │
│  ├── price: u64 (lamports)           │
│  ├── installs: u64                   │
│  ├── revenue: u64                    │
│  ├── content_hash: [u8; 32]         │
│  ├── status: Active/Deprecated       │
│  └── created_at: i64                 │
│                                      │
│  PDA: personality_registry/{name}    │
│  ├── (same structure)                │
│  └── ...                             │
│                                      │
│  PDA: bot_passport/{bot_id}          │
│  ├── owner: Pubkey                   │
│  ├── level: u8                       │
│  ├── xp: u64                         │
│  ├── skills: Vec<Pubkey>             │
│  ├── personality: Pubkey             │
│  └── created_at: i64                 │
└──────────────────────────────────────┘
```

### IA-Coin Economy

```
Earn IA-Coins:
  ├── Create skill    → Earn from installs
  ├── Create personality → Earn from usage
  ├── Bot interactions → Earn XP → Level up → Unlock earning
  └── Referrals       → Earn from referral installs

Spend IA-Coins:
  ├── Install skills
  ├── Buy personalities
  ├── Premium features
  └── Exchange → Stars → Real money
```

---

## docker-compose.yml (New Architecture)

```yaml
version: '3.8'

services:
  # IA-Mother — Master Bot (Marketplace + Exchange)
  ia-mother:
    build:
      context: .
      dockerfile: services/ia-mother/Dockerfile
    container_name: ia_mother
    restart: unless-stopped
    environment:
      - TELEGRAM_API_ID=${TELEGRAM_API_ID}
      - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
      - IA_MOTHER_BOT_TOKEN=${IA_MOTHER_BOT_TOKEN}
      - REDIS_URL=redis://redis:6379/0
      - LANGFLOW_URL=http://langflow:7860
      - SOLANA_RPC_URL=${SOLANA_RPC_URL}
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - zero_bot_net

  # Redis — State + Pub/Sub + Registry Cache
  redis:
    image: redis:7-alpine
    container_name: zero_bot_redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb
    volumes:
      - redis_data:/data
    networks:
      - zero_bot_net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Langflow — Admin UI + Flow Builder
  langflow:
    image: langflowai/langflow:latest
    container_name: zero_bot_langflow
    restart: unless-stopped
    ports:
      - "7860:7860"
    environment:
      - LANGFLOW_DATABASE_URL=sqlite:///./langflow.db
      - LANGFLOW_AUTO_LOGIN=true
    volumes:
      - langflow_data:/app/langflow.db
    networks:
      - zero_bot_net

  # GitLab Runner — CI/CD
  gitlab-runner:
    image: gitlab/gitlab-runner:latest
    container_name: zero_bot_runner
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - runner_config:/etc/gitlab-runner
    networks:
      - zero_bot_net

  # Bot instances are created dynamically by IA-Mother
  # Template (not started by default):
  # zero-bot-template:
  #   build:
  #     context: .
  #     dockerfile: services/bot-instance/Dockerfile
  #   environment:
  #     - TELEGRAM_API_ID=${TELEGRAM_API_ID}
  #     - TELEGRAM_API_HASH=${TELEGRAM_API_HASH}
  #     - TELEGRAM_BOT_TOKEN=<dynamic>
  #     - BOT_ID=<dynamic>
  #     - OWNER_ID=<dynamic>
  #     - REDIS_URL=redis://redis:6379/0
  #     - LANGFLOW_URL=http://langflow:7860

volumes:
  redis_data:
  langflow_data:
  runner_config:

networks:
  zero_bot_net:
    driver: bridge
```

---

## File Structure (Final)

```
zero-bot/zero-bot/                    ← MAIN REPO
├── README.md
├── ARCHITECTURE.md                   ← This document
├── LICENSE
│
├── docker-compose.yml                ← Production stack
├── .env.example                      ← Environment template
│
├── services/
│   ├── ia-mother/                    ← IA-Mother bot
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── ia_mother.py              ← Standalone Telethon bot
│   │   └── marketplace.py            ← Marketplace logic
│   │
│   └── bot-instance/                 ← Zero Bot template
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── bot.py                    ← Bot runtime
│       ├── skill_loader.py           ← Dynamic skill loading
│       ├── personality_loader.py     ← Personality loading
│       └── state.py                  ← XP, level, stats
│
├── sdk/                              ← zero-bot-sdk (PyPI package)
│   ├── pyproject.toml
│   └── zero_bot_sdk/
│       ├── __init__.py
│       ├── base_skill.py
│       ├── base_personality.py
│       ├── context.py
│       ├── response.py
│       ├── decorators.py
│       ├── testing.py
│       └── cli.py                    ← `zero-bot-sdk new skill/personality`
│
├── ci/                               ← CI/CD templates
│   ├── templates/
│   │   ├── skill.gitlab-ci.yml
│   │   └── personality.gitlab-ci.yml
│   ├── schemas/
│   │   ├── skill-manifest.schema.json
│   │   └── personality-manifest.schema.json
│   └── scripts/
│       ├── register_on_solana.py
│       ├── validate_manifest.py
│       └── deploy_to_container.py
│
├── blockchain/                       ← Solana programs
│   └── solana/
│       ├── registry.py
│       ├── passport.py
│       └── billing.py
│
└── docs/                             ← Developer documentation
    ├── DEVELOPER_GUIDE.md
    ├── SKILL_DEVELOPMENT.md
    ├── PERSONALITY_DEVELOPMENT.md
    ├── TOKENOMICS.md
    └── API_REFERENCE.md
```

---

## Developer Workflow

### Creating a New Skill

```bash
# 1. Install SDK
pip install zero-bot-sdk

# 2. Scaffold
zero-bot-sdk new skill my-skill

# 3. Implement
cd my-skill
# Edit handler.py — implement your skill logic
# Edit manifest.json — set metadata, pricing, tags

# 4. Test locally
zero-bot-sdk test

# 5. Push to your repo
git init && git add . && git commit -m "Initial skill"
git remote add origin git@github.com:yourname/skill-my-skill.git
git push -u origin main

# 6. Submit to registry
# Create PR to zero-bot/skill-registry with your manifest
# CI runs automatically: validate → test → review

# 7. After approval: tag release
git tag v1.0.0 && git push --tags
# GitLab Runner: build → publish → register on Solana
# Skill appears in IA-Mother marketplace
```

### Creating a New Personality

```bash
# 1. Scaffold
zero-bot-sdk new personality my-persona

# 2. Write prompts
cd my-persona
# Edit prompts/system.txt — main system prompt
# Edit prompts/greeting.txt — first message
# Edit training/examples.jsonl — few-shot examples
# Edit manifest.json — metadata, pricing, AI model config

# 3. Test locally
zero-bot-sdk test

# 4. Push & submit (same as skills)
```

### Updating Main Platform (Core Devs Only)

```bash
# Changes to zero-bot/zero-bot affect ALL containers
# This triggers rolling update of all bot instances

git checkout main
# Make changes to services/bot-instance/bot.py
git commit -m "feat: improve message handling"
git push origin main

# GitLab Runner automatically:
# 1. Builds new bot-instance image
# 2. Rolling restart of all bot containers
# 3. Health checks verify each container
```

---

## Comparison with OpenClaw

| Feature | OpenClaw | Zero Bot |
|---------|----------|----------|
| Architecture | Single agent + plugins | 1 bot = 1 container |
| Skills | Local plugins in one repo | Separate repos + marketplace |
| Monetization | None | IA-Coin tokenomics (Solana) |
| Deployment | Single process | Docker containers via GitLab CI |
| Admin UI | CLI/Config | Langflow visual builder |
| Bot identity | One agent | Each bot = unique Tamagotchi |
| Ownership | Developer owns agent | User owns bot (NFT passport) |
| Revenue | None | 60% creator / 30% platform / 10% Telegram |
| Discovery | README list | IA-Mother marketplace bot |
| Registry | GitHub topics | On-chain Solana registry |

---

## Next Steps

1. [ ] Create `zero-bot-sdk` package with BaseSkill, BasePersonality
2. [ ] Create manifest JSON schemas for validation
3. [ ] Create CI template files for GitLab Runner
4. [ ] Rewrite `services/bot-instance/bot.py` with skill/personality loader
5. [ ] Rewrite `services/ia-mother/ia_mother.py` with container management
6. [ ] Set up GitLab Runner configuration
7. [ ] Create example skill repo (weather)
8. [ ] Create example personality repo (sarcastic-friend)
9. [ ] Remove Django dependency completely
10. [ ] Deploy Langflow as admin UI
