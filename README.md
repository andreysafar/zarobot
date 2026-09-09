# Zero Bot Platform

> **1 Bot = 1 Docker Container. 1 Skill = 1 Repo. 1 Personality = 1 Repo.**

Платформа массовой разработки AI-ботов с токеномикой.  
Каждый бот — Tamagotchi, которого пользователь растит, обучает, монетизирует.

## Architecture

```
                     ┌──────────────┐
                     │   Core API   │  FastAPI + SQLite + IAM ledger
                     └──────┬───────┘
                            │
   ┌───────────┬────────────┼────────────┬───────────┐
   │           │            │            │           │
┌──┴──────┐ ┌──┴──────┐ ┌───┴──────┐ ┌───┴─────┐ ┌───┴──────┐
│IA-Mother│ │ Скрепка │ │  Helper  │ │Дервалер │ │ Zero Bot │ ...
│(master) │ │ (admin) │ │  (group) │ │(archive)│ │ Clone #N │
└──┬──────┘ └──┬──────┘ └──────────┘ └─────────┘ └──────────┘
   │           │
   │     Docker socket → health checks, restarts
   └──→ spawns zero_bot_<id>

                  Redis · Langflow
```

| Container | Purpose |
|-----------|---------|
| `core-api` | Backend: users, balances, marketplace, bug reports |
| `ia-mother` | Master bot: marketplace, exchange, cloning |
| `zero_bot_{id}` | Individual bot instance (1 per user) |
| `helper-bot` | Group helper: answers from chat history, FAQ |
| `dervaler` | Archivist worker: ingests chat history via a user session |
| `skrepka` | AI admin: container health, restarts, bug triage |
| `redis` | State, pub/sub, skill cache |
| `langflow` | Admin UI, flow builder |

## Quick Start

```bash
cp .env.example .env
docker compose up -d --build
```

Minimum required in `.env`:

| Variable | Why |
|----------|-----|
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | Telegram API credentials |
| `IA_MOTHER_BOT_TOKEN` | Master bot token from BotFather |
| `CORE_API_TOKEN` | Shared secret between services — Core API refuses to serve without it (`openssl rand -hex 32`) |

Core API listens on `127.0.0.1:8000` only. See [STATUS_REPORT.md](STATUS_REPORT.md)
for what is implemented, partially implemented, or still a stub.

## Project Structure

```
zero-bot/
├── services/
│   ├── core_api/           # FastAPI backend (SQLite + IAM ledger)
│   ├── ia-mother/          # Master bot (marketplace + exchange + cloning)
│   ├── bot-instance/       # Bot template (cloned per user)
│   ├── dervaler/           # Chat archivist (Telethon user session)
│   └── skrepka/            # AI admin agent
├── sdk/                    # zero-bot-sdk (PyPI package)
│   └── zero_bot_sdk/       # BaseSkill, BasePersonality, CLI
├── personalities/
│   ├── ia/                 # Default personality (Ия)
│   └── dervaler/           # Archivist personality
├── examples/
│   ├── skill-weather/      # Reference skill
│   └── skill-helper-kb/    # Group helper: KB retrieval + FAQ
├── ci/
│   ├── templates/          # GitLab CI shared pipelines
│   └── scripts/            # register_on_ton.py
├── tests/                  # pytest suite
├── docs/                   # Developer documentation
├── docker-compose.yml      # Production stack
├── STATUS_REPORT.md        # What actually works right now
└── ARCHITECTURE.md         # Full architecture spec
```

## For Developers

### Create a Skill

```bash
pip install zero-bot-sdk
zero-bot-sdk new skill my-awesome-skill
cd my-awesome-skill
# Edit handler.py, manifest.json
zero-bot-sdk test
git push && git tag v1.0.0 && git push --tags
```

### Create a Personality

```bash
zero-bot-sdk new personality my-cool-persona
cd my-cool-persona
# Edit prompts/system.txt, training/examples.jsonl
zero-bot-sdk test
git push && git tag v1.0.0 && git push --tags
```

See [Developer Guide](docs/DEVELOPER_GUIDE.md) for full documentation.

## Tokenomics

Two currencies, deliberately kept in two different stores:

| | Stars | IA-Coins (IAM) |
|---|---|---|
| Store | SQLite (`balances`) | JSON ledger (`IAMCoinService`) |
| Pays for | a bot's services, owed to its owner | AI tokens, skills, personalities |
| Future | stays in the platform | moves to on-chain NFT/jetton mint |

- Chain: **TON** (jettons + NFT passports). Earlier docs said Solana — that is out of date.
- Revenue split: **60% creator** / 30% platform / 10% Telegram, paid out of the
  buyer's wallet, so a purchase never changes the total coin supply.
- Rate is server-side: 1 Star = 0.01 IAM, 1 IAM = 100 Stars.

Not yet implemented: earning Stars (no Telegram Payments integration), metering
AI token usage, and on-chain mint/burn. See [STATUS_REPORT.md](STATUS_REPORT.md).

## Default Personality: Ия

The platform ships with "Ия" (IA) — a friendly, female-persona AI assistant by [НейроРанчо](https://neurorancho.ru).

Features: multilingual, user profiling, chat summarization, web search, image generation, meme creation, voice recognition, scheduled notifications.

See [personalities/ia/](personalities/ia/) for the full personality spec.

## Docs

- [STATUS_REPORT.md](STATUS_REPORT.md) — Verified current state: what works, what is a stub
- [ARCHITECTURE.md](ARCHITECTURE.md) — Full infrastructure spec (target design)
- [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) — How to build skills & personalities
- [personalities/ia/](personalities/ia/) — Default personality reference

## License

Proprietary. All rights reserved.
