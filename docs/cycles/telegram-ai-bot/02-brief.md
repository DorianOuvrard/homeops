# Brief — telegram-ai-bot

Add a Telegram bot service to homeops that accepts all message types (text, voice, photo, video) and replies via an LLM, establishing the end-to-end pipe from mobile capture to AI.

## Current state

| Component | Status |
|-----------|--------|
| Odoo 17 + Postgres 16 | Running in docker-compose |
| Telegram bot | Does not exist |
| AI/LLM integration | Does not exist |
| Bot service code | No Python code in repo |

## Capabilities

- Send a text message to the Telegram bot and receive a conversational AI response
- Send voice, photo, or video messages; bot acknowledges receipt and forwards to orchestrator
- Bot runs as a docker-compose service alongside the existing Odoo stack
- Configuration via environment variables (Telegram token, LLM API key)

## Decisions

- **Runtime**: Python (smallest path to a working Telegram bot)
- **Telegram library**: python-telegram-bot (mature, async, well-documented)
- **LLM provider**: OpenAI ChatGPT SDK (user preference)
- **Deployment**: New service in existing docker-compose.yml, no separate infra
- **Conversation scope**: Stateless per-message (no history, no memory)
- **Media handling**: Bot accepts and stores all media types from Telegram. Text content goes to LLM. Media files are acknowledged with a placeholder response ("received your photo/voice/video") until intelligent processing is added in a future cycle.

## Out of scope

Intelligent media processing (transcription, vision, video analysis), Odoo integration, persistent memory, conversation history, multi-user auth, web UI, autonomous actions, workflow automation.

## Risks

- **Telegram token exposure.** Token in .env could leak if repo goes public. Mitigation: .env already in .gitignore.
- **API cost runaway.** No rate limiting means accidental loops could burn credits. Mitigation: single-user scope, add basic rate limit in code.

## Success

- Bot responds to a text message in Telegram within 5 seconds
- Bot acknowledges voice, photo, and video messages without crashing
- `docker compose up` starts all services (Odoo, Postgres, bot) without manual steps
- Bot gracefully handles LLM API errors (returns a user-friendly message, does not crash)
- Configuration requires only adding two env vars (TELEGRAM_TOKEN, OPENAI_API_KEY)
