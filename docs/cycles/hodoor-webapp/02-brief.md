# Brief — hodoor-webapp

Add a mobile-first PWA (HODOOR) on top of the existing Python bot, exposing its AI conversation, appliance scan, and maintenance features through a web interface with user authentication.

## Current state

| Component | Status |
|-----------|--------|
| AI conversation (text, photo, voice, video) | Working via Telegram handlers |
| Appliance identification + onboarding flow | Working, OpenAI function-calling + Odoo |
| Maintenance reminders (Odoo calendar) | Working via polling loop |
| Core logic (llm.py, tools.py, odoo.py) | Transport-agnostic, no Telegram dependency |
| Conversation history | In-memory, keyed by Telegram user ID (int) |
| Frontend | Streamlit test UI only |

## Capabilities

- Sign up and log in with email + password from any mobile browser
- Chat with the HomeOps AI assistant (text + photo upload)
- Run the appliance onboarding/scan flow through the web
- Browse appliance inventory pulled from Odoo
- View maintenance history and upcoming reminders per appliance
- Install as PWA on home screen for app-like experience

## Decisions

- **Backend**: FastAPI endpoints added to the existing bot process, not a separate service. Reuses `llm.py`, `tools.py`, `odoo.py` directly.
- **Auth**: Email + password with bcrypt hashing, JWT access tokens. User store in SQLite (lightweight, no new infra).
- **Frontend**: React + Vite + Tailwind CSS, built as a PWA with service worker and manifest.
- **Chat transport**: REST endpoints (POST message, GET history). WebSocket streaming deferred.
- **History**: Extend `ConversationHistory` to persist per web-user (string ID) alongside existing Telegram int IDs.

## Out of scope

Voice input/STT, real-time camera detection, push notifications, native app distribution, multi-household, file management, WebSocket streaming, admin panel, Telegram bot migration (both run in parallel).

## Risks

- **Shared process stability.** FastAPI + Telegram polling in the same process could compete for the event loop. Mitigation: run FastAPI via uvicorn with the Telegram bot as a background task, test under concurrent load.
- **Auth surface area.** Rolling custom auth introduces credential management. Mitigation: bcrypt + short-lived JWTs, no session cookies, rate-limit login endpoint.
- **State divergence.** Telegram and web users may see different appliance data if history drifts. Mitigation: single Odoo source of truth for all appliance/maintenance data.

## Success

- A user can sign up, log in, and chat with the AI from a mobile browser
- Photo upload identifies an appliance and creates it in Odoo
- Appliance list and maintenance schedule render from live Odoo data
- PWA installs on iOS/Android home screen and loads offline shell
- Telegram bot continues working without regression
