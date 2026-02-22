# Zero Bot Platform

> **1 Bot = 1 Docker Container. 1 Skill = 1 Repo. 1 Personality = 1 Repo.**

Платформа массовой разработки AI-ботов с токеномикой.  
Каждый бот — Tamagotchi, которого пользователь растит, обучает, монетизирует.

## Architecture

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  IA-Mother   │  │  Zero Bot   │  │  Zero Bot   │  ...
│  (master)    │  │  Clone #1   │  │  Clone #2   │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
┌──────┴────────────────┴────────────────┴──────┐
│                     Redis                      │
├────────────────────────────────────────────────┤
│                    Langflow                    │
├────────────────────────────────────────────────┤
│                 GitLab Runner                  │
└────────────────────────────────────────────────┘
```

| Container | Purpose |
|-----------|---------|
| `ia-mother` | Master bot: marketplace, exchange, cloning |
| `zero-bot-{id}` | Individual bot instance (1 per user) |
| `redis` | State, pub/sub, skill cache |
| `langflow` | Admin UI, flow builder |
| `gitlab-runner` | CI/CD pipelines |

## Quick Start

```bash
cp .env.example .env
# Fill in TELEGRAM_API_ID, TELEGRAM_API_HASH, IA_MOTHER_BOT_TOKEN
docker-compose up -d
```

## Project Structure

```
zero-bot/
├── services/
│   ├── ia-mother/          # Master bot (marketplace + exchange)
│   └── bot-instance/       # Bot template (cloned per user)
├── sdk/                    # zero-bot-sdk (PyPI package)
│   └── zero_bot_sdk/       # BaseSkill, BasePersonality, CLI
├── personalities/
│   └── ia/                 # Default personality (Ия)
├── ci/
│   ├── templates/          # GitLab CI shared pipelines
│   └── schemas/            # JSON schemas for manifests
├── docs/                   # Developer documentation
├── docker-compose.yml      # Production stack
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

- **IA-Coins** — platform currency (Solana)
- Revenue split: **60% creator** / 30% platform / 10% Telegram
- Every skill and personality registered on Solana blockchain
- Bot ownership via NFT passport

## Default Personality: Ия

The platform ships with "Ия" (IA) — a friendly, female-persona AI assistant by [НейроРанчо](https://neurorancho.ru).

Features: multilingual, user profiling, chat summarization, web search, image generation, meme creation, voice recognition, scheduled notifications.

See [personalities/ia/](personalities/ia/) for the full personality spec.

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — Full infrastructure spec
- [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) — How to build skills & personalities
- [personalities/ia/](personalities/ia/) — Default personality reference

## License

Proprietary. All rights reserved.
