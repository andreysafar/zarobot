# Zero Bot — instructions for Claude Code

You are implementing a **group Helper bot** on the Zero Bot platform. Do what was asked; do not invent extra product surface. Comment code in English. User-facing Telegram copy is Russian.

This file is the source of truth for the helper-bot work. Read it before editing runtime, personalities, or ingest.

---

## Mission

Build a helper that is added to a public Telegram chat and:

1. Learns the **entire existing chat history**.
2. Keeps a living knowledge base, updated as new messages arrive.
3. Answers questions from that knowledge (not from a 20-message private buffer).
4. Maintains a separate **FAQ** of frequent questions.
5. Lets **chat admins edit** the FAQ.

The public helper is a BotFather bot. History ingest is **not** done with the bot token.

---

## Two personalities (do not collapse them)

| | Public helper | Dervaler (`dervaler`) |
|---|---|---|
| Who | The bot users talk to in the group | Second personality / worker |
| Telegram identity | Bot token (`TELEGRAM_BOT_TOKEN`) | **Admin user account** via Telethon |
| Client type | `TelegramClient.start(bot_token=...)` | `TelegramClient` + **user session** of the chat admin |
| Job | Answer, FAQ, group UX | **Paginate the full archive** and keep ingest running |

### Dervaler — hard rules

Dervaler logs in as the **admin’s own Telegram user**, not as a bot.

- Use Telethon **user client** (`api_id` + `api_hash` + session file or `StringSession`).
- Session is equivalent to the admin password. Never commit it. Env only: `DERVALER_SESSION` or a mounted file under `/data/dervaler/` that is gitignored.
- **Do not** use Bot API / bot token to fetch history. Bots cannot read messages from before they were added.
- Load the archive with `client.iter_messages(chat, reverse=True)` (oldest → newest) and **pagination checkpoints**, not `get_messages(limit=N)` as the full ingest.
- Persist `last_ingested_id` (and chat_id) after each batch so a restart resumes with `min_id=last_ingested_id` (or `offset_id` depending on direction). Incremental live updates use `min_id` = last checkpoint.
- Handle `FloodWaitError`: sleep `e.seconds + 1`, then continue. For large chats set `wait_time` (Telethon defaults to 1s when `limit > 3000`; for a full archive pass `limit=None` and an explicit `wait_time>=1`).
- `iter_messages` is read-only and does not mark history as read. Keep it that way. Dervaler must not send messages into the public chat unless an explicit admin command asks it to (status in DM to the admin is OK).
- First login (phone/QR) is a one-shot operator step. Runtime only reuses the saved session.

```python
# Ingest sketch (implement in services/dervaler/, not inside bot-instance message handlers)
from telethon.errors import FloodWaitError

async def ingest_archive(client, chat, checkpoint: int = 0):
    kwargs = {"reverse": True, "wait_time": 1}
    if checkpoint:
        kwargs["min_id"] = checkpoint
    try:
        async for message in client.iter_messages(chat, **kwargs):
            yield message
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 1)
        raise  # caller retries from last saved checkpoint
```

Personality files live at `personalities/dervaler/` (manifest + prompts). The **worker** is a separate process/container (`services/dervaler/`), not a second BotFather clone. The helper bot **reads** the KB/FAQ that Dervaler writes.

Default public personality remains `personalities/ia/` unless the helper gets its own later. Do not reuse Ия prompts for Dervaler.

---

## Current platform gaps (fix these; do not assume they work)

Runtime today (`services/bot-instance/bot.py`) is a private-chat LLM loop:

- Skills SDK exists (`sdk/zero_bot_sdk/`) but **skills are not loaded** in the instance.
- `ConversationManager` keeps **20 messages per user**, not group knowledge.
- Personality flags `chat_summarization` / `context_aggregation` are **not wired**.
- Handlers reply to **every** text message — fatal in a public group.
- `docker_manager.spawn_bot()` does **not** pass `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`.
- Dockerfile copies `personalities/` to `/data/personality/` (nested `ia/`), while `PersonalityLoader` expects `manifest.json` at that path — mismatch.
- Container limits: 256MB / 0.5 CPU — too small for ingest + embeddings. Dervaler and helper need higher limits (start at 1GB RAM / 1 CPU for Dervaler).
- Docker images are not built until you build them. LLM keys: add OpenRouter to `.env`; do not commit secrets.

Example skill to copy patterns from: `examples/skill-weather/`.

---

## Target architecture

```
Public group
    │
    ├─ Helper bot (bot token, personality ia or helper)
    │     replies only to: mention, /cmd, reply-to-bot, or clear question
    │     reads KB + FAQ → LLM → answer
    │     admin commands: FAQ CRUD
    │
    └─ Dervaler (admin user Telethon session)
          iter_messages pagination → chunks → store
          live NewMessage on that chat → update KB
          never spam the group
                │
                ▼
         Shared store (SQLite under /data + Redis)
           messages, chunks, faq_items, ingest_checkpoint
```

### Skill

Implement helper behaviour as skill `examples/skill-helper-kb/` (or `skills/helper-kb/`) with `BaseSkill`:

- `on_message` — detect questions; retrieve KB+FAQ; answer or `skip()`.
- Commands (public): `/faq`, `/ask`
- Commands (admins only): `/faq_add`, `/faq_edit`, `/faq_del`, `/faq_publish`, `/ingest_status`
- Admin check: Telegram chat admin/creator (`get_permissions` / `iter_participants` with admin filter). Owner id from `OWNER_ID` is also admin.

### Knowledge base

- Store raw messages (id, date, sender_id, text, reply_to).
- Build/update a compact **chat summary** (use `personalities/ia/prompts/summary_agent.txt` as a starting prompt, or a Dervaler-specific one).
- Retrieval: start with SQLite FTS5 + recent summary in the prompt. Add embeddings later only if FTS is not enough. Do not add a vector DB in the first pass unless retrieval quality is clearly insufficient.
- Update on each new group message (debounce: batch every N messages or T seconds).

### FAQ

- Separate table/document from the raw archive.
- Fields: `id`, `question`, `answer`, `source_message_ids`, `status` (`draft` | `published`), `updated_by`, `updated_at`.
- Auto-draft from repeated questions; **admins publish/edit**. Unpublished drafts are not used as answers.
- `/faq` shows published items only.

### Group UX

- Default: **do not reply** to ordinary chatter.
- Reply when: bot mentioned, command, reply to the bot, or the message is a question **and** retrieval found something useful.
- If retrieval is empty: one short “не нашёл в истории чата” only when directly asked.

---

## Implementation order

Do this in order. Do not skip ingest-identity.

1. **Runtime plumbing**
   - Load skills from `/data/skills` in `bot-instance`.
   - Fix personality path (`/data/personality/ia` or flatten copy).
   - Pass LLM keys in `spawn_bot()` and compose.
   - Group-aware handler: ignore chatter; pass events into skill chain then personality.

2. **Dervaler worker + personality**
   - `personalities/dervaler/manifest.json` + prompts (operator/archivist, not a chatty assistant).
   - `services/dervaler/`: login as admin user, `iter_messages` full pagination, checkpoint, FloodWait.
   - Compose service + volume for session. Document one-time session bootstrap in comments, not in git.

3. **Store + skill-helper-kb**
   - SQLite schema: messages, checkpoints, faq.
   - Skill: retrieve, answer, FAQ admin commands.
   - Wire skill into the helper instance.

4. **Live update**
   - Dervaler (or helper, if it can see the message) appends new messages and refreshes summary/FTS.
   - Helper answers from updated store.

5. **Verify**
   - Unit tests for FAQ ACL and retrieve-or-skip.
   - Local test: ingest a small chat with the admin session, then ask the helper a fact that exists only in old history.

---

## Constraints

- No secrets in git (`.env`, session strings, API keys).
- Do not mark group messages as read during ingest.
- Do not scrape other chats than the configured `HELPER_CHAT_ID` / allow-list.
- Do not reply to every group message.
- Keep files under ~500 lines; split ingest / store / skill.
- Follow existing Telethon + loguru + FastAPI style.
- TON/NFT/marketplace are out of scope for this order unless a change is required to spawn the bot.

---

## Key paths

- `services/bot-instance/bot.py` — clone runtime (skill loader missing)
- `services/bot-instance/handlers.py` — commands; add group gating
- `services/ia-mother/docker_manager.py` — spawn env + memory
- `sdk/zero_bot_sdk/` — `BaseSkill`, `SkillContext`, `SkillResponse`
- `personalities/ia/` — public default personality
- `personalities/dervaler/` — **create** (admin-user archivist)
- `services/dervaler/` — **create** (Telethon user ingest)
- `examples/skill-weather/` — skill shape to copy
- `docker-compose.yml` — add dervaler service; pass `OPENROUTER_API_KEY` into bots

---

## Claude Code Router (this machine)

Claude Code is routed through CCR (`~/.claude-code-router/config.json`). After config edits: `ccr restart`.

| Route | Model | Use |
|---|---|---|
| `default` | `openrouter,deepseek/deepseek-v4-flash-0731` | Everyday coding |
| `think` | `openrouter,tencent/hy4-preview` | Plan mode, multi-step, tool-heavy |
| `longContext` | `openrouter,tencent/hy4-preview` | Large repo / long ingest code |
| `background` | `openrouter,nvidia/nemotron-3-ultra-550b-a55b:free` | Light tasks only |

OpenRouter key lives in `~/.claude-code-router/env`. If CCR shows `401 User not found`, regenerate the key at https://openrouter.ai/keys and run `ccr restart`.

Manual switch:

```
/model openrouter,tencent/hy4-preview
/model openrouter,deepseek/deepseek-v4-flash-0731
/model openrouter,nvidia/nemotron-3-ultra-550b-a55b:free
```

Docs: [Hy4 preview](https://openrouter.ai/tencent/hy4-preview), [DeepSeek V4 Flash 0731](https://openrouter.ai/deepseek/deepseek-v4-flash-0731), [Nemotron 3 Ultra free](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free).
