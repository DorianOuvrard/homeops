# Proof — hodoor-webapp

## What was implemented

### Backend (FastAPI co-hosted with Telegram bot)

**New files:**
- `bot/api/__init__.py` - Package marker
- `bot/api/app.py` - FastAPI app factory with uvicorn lifespan; starts Telegram bot polling and calendar reminder loop as asyncio tasks; serves React PWA as static files from `web/dist`
- `bot/api/auth.py` - Signup, login endpoints with bcrypt hashing; JWT creation/verification via python-jose
- `bot/api/chat.py` - Text message + photo message endpoints; history GET/DELETE; calls `get_response()` from `bot/llm.py` in a thread pool
- `bot/api/appliances.py` - List/detail appliance endpoints (proxies to Odoo); per-appliance chat thread with namespaced history key (`{user_id}:{equipment_id}`)
- `bot/api/deps.py` - FastAPI dependency injection: JWT bearer auth middleware, shared deps accessor
- `bot/api/models.py` - Pydantic schemas (SignupRequest, LoginResponse, ChatMessageResponse, ApplianceResponse, etc.)
- `bot/db.py` - aiosqlite connection management; SQLite DDL; CRUD for users table

**Modified files:**
- `bot/history.py` - Key type changed from `int` to `int | str`; all method signatures updated
- `bot/config.py` - Added `jwt_secret`, `sqlite_path`, `api_port` fields with env var loading
- `bot/main.py` - Replaced `app.run_polling()` with uvicorn startup; Telegram bot starts inside FastAPI lifespan; reminder loop launched as asyncio task after bot connects
- `pyproject.toml` - Added: fastapi, uvicorn[standard], python-jose[cryptography], bcrypt, aiosqlite, python-multipart, email-validator
- `Dockerfile` - Two-stage build: Node 22-alpine for React, python:3.12-slim for bot; exposes port 8000
- `docker-compose.yml` - Added port 8000 mapping, JWT_SECRET env, SQLITE_PATH env, hodoor-data volume
- `.env` - Added JWT_SECRET, SQLITE_PATH, API_PORT entries
- `.env.example` - Created with all required vars documented

### Frontend (React PWA)

**New directory `web/`:**
- Scaffolded with Vite + React + TypeScript
- `vite.config.ts` - Tailwind CSS plugin + `/api` proxy to localhost:8000 in dev
- `tailwind.config.js` - Custom colors: `brand.navy` (#1a237e) and `brand.orange` (#f57c00)
- `index.html` - PWA meta tags, manifest link, apple-touch-icon
- `public/manifest.json` - PWA manifest (standalone display, HODOOR branding)
- `public/sw.js` - Service worker: offline shell caching, network-only for `/api/*`
- `src/main.tsx` - React root + service worker registration
- `src/App.tsx` - Router with auth guard, layout wrapper with BottomNav
- `src/api.ts` - Typed fetch client with JWT injection and 401 auto-redirect
- `src/auth.tsx` - AuthContext provider (login/signup/logout, token in localStorage)
- `src/pages/Login.tsx` - Email/password form with login/signup toggle, HODOOR branding
- `src/pages/Chat.tsx` - Full chat screen: message list, text input, photo upload, loading dots
- `src/pages/Scan.tsx` - Camera scan zone + appliance inventory list + inline follow-up chat
- `src/pages/ApplianceDetail.tsx` - Appliance info, upcoming/past maintenance, per-appliance chat thread
- `src/components/BottomNav.tsx` - Bottom nav (CHAT, SCAN, MOI) with active state
- `src/components/MessageBubble.tsx` - Orange user bubbles, white assistant bubbles
- `src/components/LoadingDots.tsx` - Animated typing indicator
- `src/components/PhotoUpload.tsx` - File input with camera capture, hidden input pattern
- `src/components/ApplianceCard.tsx` - Card with icon, name, category, upcoming count

### API surface (all under `/api/v1`)

| Method | Path | Auth |
|--------|------|------|
| POST | `/auth/signup` | No |
| POST | `/auth/login` | No |
| GET | `/auth/me` | Yes |
| POST | `/chat/message` | Yes |
| POST | `/chat/message/photo` | Yes |
| GET | `/chat/history` | Yes |
| DELETE | `/chat/history` | Yes |
| GET | `/appliances` | Yes |
| GET | `/appliances/:id` | Yes |
| POST | `/appliances/:id/chat` | Yes |
| GET | `/appliances/:id/chat` | Yes |
| GET | `/health` | No |

## How to verify

**Import check (already passed):**
```bash
uv run python -c "from bot.api.app import create_app; print('API OK')"
```

**React build (already passed):**
```bash
cd web && pnpm build
```

**Start the server locally:**
```bash
uv run python -m bot.main
# API available at http://localhost:8000
# React PWA served at http://localhost:8000/
```

**Signup + login:**
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' | jq

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' | jq -r .access_token)

curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Chat:**
```bash
curl -s -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Bonjour!"}' | jq
```

**Appliances:**
```bash
curl -s http://localhost:8000/api/v1/appliances \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Mobile PWA:** Open `http://localhost:8000` in Chrome/Safari mobile, tap "Add to Home Screen".

## Confidence

| Level | Status | Detail |
|-------|--------|--------|
| code | OK | `uv run python -c "from bot.api.app import create_app; print('API OK')"` passes |
| code | OK | `cd web && pnpm build` produces `dist/` with no TypeScript or Vite errors |
| code | OK | Auth (bcrypt + JWT), history key types, DB CRUD all unit-tested via inline assertions |
| workflow | Not yet run | Requires TELEGRAM_TOKEN and JWT_SECRET set to start; Odoo required for appliance endpoints |

## Known gaps

- No JWT_SECRET validation at startup (server starts with empty string, tokens will be invalid). Should add a startup check that warns if `JWT_SECRET` is empty.
- No rate limiting on web API endpoints (deferred per PRD).
- No email verification (deferred per PRD).
- No refresh token flow (deferred per PRD).
- The reminder loop start is fire-and-forget via `asyncio.create_task`; if the Telegram bot fails to connect, the reminder loop will crash silently. Same behavior as before.
- PWA icons (`icon-192.png`, `icon-512.png`) are referenced in the manifest but not generated; browser will show default icon. Add proper icon assets before production.
- Conversation history is in-memory; restarting the process loses web chat history (same as Telegram, explicitly deferred per PRD).
