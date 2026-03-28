# PRD — telegram-ai-bot

## What changes

- A new `telegram-bot` service joins the docker-compose stack, accepting text, voice, photo, and video messages from Telegram and replying via Claude API
- Text messages produce a conversational AI response; non-text messages get an acknowledgement placeholder ("Received your photo", etc.)
- The bot is configured entirely through environment variables added to `.env` (TELEGRAM_TOKEN, ANTHROPIC_API_KEY)
- A per-user rate limiter prevents runaway API costs (default: 20 messages/minute)
- `docker compose up` starts everything (Odoo, Postgres, bot) with zero manual steps

*LLM provider: OpenAI ChatGPT (user preference). SDK: `openai` Python package.*

## Key decisions

### 1. Polling vs. webhooks for Telegram updates *(reversible)*

**Chosen: polling.** Webhooks require a public URL and TLS termination, which adds infra complexity for no benefit in a single-user, self-hosted setup. Switching to webhooks later is a one-function change in python-telegram-bot.

### 2. Bot code layout: single file vs. package *(reversible)*

**Chosen: single-directory package (`bot/`).** A flat `bot/main.py` + `bot/handlers.py` split keeps things navigable without over-engineering. A single monolithic file would get unwieldy past ~200 lines once all media handlers exist. Rejected: full src-layout package (unnecessary for a service that won't be pip-installed).

### 3. OpenAI ChatGPT as LLM provider *(costly-to-reverse)*

**Chosen: OpenAI ChatGPT SDK.** User preference. Native multimodal support (vision, audio) for future cycles. The abstraction layer (a single `get_response()` function) makes swapping providers a localized change if needed later.

### 4. Python dependency management: uv *(reversible)*

**Chosen: uv with `pyproject.toml`.** Aligns with global CLAUDE.md conventions (uv over pip/poetry). The Dockerfile uses `uv pip install` from a lockfile for reproducible builds.

## Trade-offs

- **No conversation history**: simpler implementation, but every message is context-free. Acceptable because the brief explicitly scopes this as stateless.
- **No media processing**: voice/photo/video get a static acknowledgement instead of transcription/analysis. Acceptable because intelligent processing is explicitly out of scope for this cycle.
- **Polling instead of webhooks**: slightly higher latency (~1s polling interval) and wastes some CPU on idle polls. Acceptable for single-user self-hosted use.
- **No tests in Phase 1**: shipping the pipe fast. Acceptable because the success criteria are manual verification (send message, get response).

## Implementation sequence

### Phase 1: Bot skeleton + text conversation
The bot starts, connects to Telegram via polling, and replies to text messages using Claude API. Docker service is wired into docker-compose. After this phase, you can `docker compose up`, send a text in Telegram, and get an AI response back.

### Phase 2: Media handlers + rate limiting + error resilience
Voice, photo, and video messages get acknowledged. A per-user in-memory rate limiter is added. LLM errors and Telegram API errors produce user-friendly messages instead of crashes. After this phase, all success criteria from the brief are met.

## Diagram

```
+------------------+          +-------------------+          +----------------+
|                  |  update  |                   |  text    |                |
|    Telegram      +--------->+   telegram-bot    +--------->+  Claude API    |
|    (mobile)      |<---------+   (Python)        |<---------+  (Anthropic)   |
|                  |  reply   |                   | response |                |
+------------------+          +---------+---------+          +----------------+
                                        |
                              +---------+---------+
                              |                   |
                              |  Rate Limiter     |
                              |  (in-memory)      |
                              |                   |
                              +-------------------+

docker-compose.yml
+-----------------------------------------------------+
|                                                     |
|  +-------------+  +--------+  +------------------+  |
|  |   odoo:17   |  | db:16  |  | telegram-bot     |  |
|  |   :8069     |  | pg     |  | python:3.12-slim |  |
|  +------+------+  +---+----+  +------------------+  |
|         |             |                              |
|         +------+------+                              |
|                |                                     |
|          [pg-data]  [odoo-data]  [odoo-addons]       |
+-----------------------------------------------------+

Message flow (text):
  User --> Telegram --> [polling] --> bot/handlers.py
    --> rate_limiter.check(user_id)
    --> llm.get_response(text)
    --> Telegram reply

Message flow (media):
  User --> Telegram --> [polling] --> bot/handlers.py
    --> rate_limiter.check(user_id)
    --> Telegram reply("Received your {media_type}")
```

## Files

### To create
| File | Purpose |
|------|---------|
| `bot/__init__.py` | Package marker |
| `bot/main.py` | Entry point: configures the Telegram Application, registers handlers, starts polling |
| `bot/handlers.py` | Message handlers: text_handler, voice_handler, photo_handler, video_handler |
| `bot/llm.py` | OpenAI ChatGPT wrapper: `get_response(text) -> str` with error handling |
| `bot/rate_limiter.py` | In-memory sliding-window rate limiter keyed by Telegram user ID |
| `bot/config.py` | Reads env vars (TELEGRAM_TOKEN, ANTHROPIC_API_KEY, RATE_LIMIT_PER_MINUTE), validates at startup |
| `pyproject.toml` | Project metadata + dependencies (python-telegram-bot, openai) |
| `uv.lock` | Lockfile generated by uv |
| `Dockerfile` | Python 3.12-slim, uv install, runs bot/main.py |
| `.dockerignore` | Excludes .git, tmp, docs, .env |

### To modify
| File | Change |
|------|--------|
| `docker-compose.yml` | Add `telegram-bot` service with build context, env_file, restart policy, depends_on (none, bot is standalone) |
| `.env` | User adds TELEGRAM_TOKEN and OPENAI_API_KEY (documented in README, not committed) |

### Data model changes

None. This cycle introduces no persistent state. The rate limiter is in-memory (resets on restart). No database tables, no files on disk.

**New types (Python):**

```python
# bot/config.py
@dataclasses.dataclass(frozen=True)
class BotConfig:
    telegram_token: str
    openai_api_key: str
    rate_limit_per_minute: int = 20
    openai_model: str = "gpt-4o"
    system_prompt: str = "You are a helpful personal assistant on Telegram. Be concise."
```
