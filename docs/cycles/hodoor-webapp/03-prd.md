# PRD — hodoor-webapp

## What changes

- A FastAPI HTTP server starts alongside the Telegram bot in the same process, exposing REST endpoints for authentication, chat, and appliance data.
- Users sign up and log in with email/password. Credentials stored in SQLite with bcrypt hashing. JWT access tokens authorize API requests.
- A React + Vite + Tailwind CSS PWA provides a mobile-first interface with five screens: Login, Chat (general assistant), Scan (photo upload + appliance list), Conversation (per-appliance thread), and a bottom navigation bar.
- `ConversationHistory` accepts `str` keys (web user UUIDs) alongside existing `int` keys (Telegram user IDs), keeping both transports on the same in-memory store.
- The Dockerfile and docker-compose gain a new `web/` build stage and expose port 8000 for the API alongside the existing Telegram bot.

## Key decisions

### 1. Co-hosting FastAPI + Telegram bot *(costly-to-reverse)*

| Option | Pros | Cons |
|--------|------|------|
| **A. uvicorn + Telegram bot as asyncio background task** | Single process, shared memory (history, odoo client, config). Simple deployment. One container. | Telegram polling and FastAPI share one event loop. A slow LLM call blocks both. |
| **B. Separate processes (two containers)** | Full isolation. Independent scaling. | Need shared state (Redis/DB for history). Double the deployment complexity. Duplicated config. |
| **C. uvicorn with lifespan + python-telegram-bot webhook mode** | Both use the same ASGI event loop natively. No polling thread. | Requires public HTTPS endpoint for Telegram webhooks. More complex local dev. Breaks existing polling setup. |

**Chosen: A.** The bot's LLM calls already run synchronously in a thread pool (OpenAI client is sync), so they don't block the async event loop. `python-telegram-bot`'s `Application` can be started manually with `app.initialize()` + `app.start()` + `app.updater.start_polling()` inside a FastAPI lifespan handler, then stopped on shutdown. This preserves the current polling approach while adding HTTP. If load becomes a concern, migrating to option B later only requires extracting the FastAPI app to its own entry point.

### 2. SQLite schema for user accounts *(costly-to-reverse)*

| Option | Pros | Cons |
|--------|------|------|
| **A. Single `users` table, raw SQL via aiosqlite** | Zero ORM overhead. Direct control. Tiny dependency footprint. Easy to inspect with `sqlite3` CLI. | Manual migration management. No relationship abstctions. |
| **B. SQLAlchemy + Alembic** | Structured migrations. ORM for future tables. | Heavy for one table. Adds 2 dependencies + migration boilerplate. |

**Chosen: A.** One table, three fields beyond the primary key (email, password_hash, created_at). Raw SQL is more readable than ORM for this. If we add more tables later (e.g., user preferences, device tokens), we can introduce Alembic then. Schema versioning via a `schema_version` pragma in the DB file.

Schema:
```sql
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Using a hex UUID as `id` instead of autoincrement so it can serve as the conversation history key and JWT subject without leaking sequential IDs.

### 3. JWT token strategy *(reversible)*

Access tokens only, no refresh tokens. 24-hour expiry. Stored in `localStorage` on the client. The `sub` claim contains the user's UUID. Signed with a `JWT_SECRET` env var using HS256.

**Why no refresh tokens:** single-user household app, not a multi-tenant SaaS. If the token expires, the user logs in again. Adding refresh tokens later is additive, not a rewrite.

### 4. React app structure and routing *(reversible)*

React Router with three routes: `/login`, `/chat`, `/scan`. The scan route has a sub-view for per-appliance conversation (`/scan/:equipmentId`). Bottom nav visible on all authenticated routes. Rejected alternative: Next.js (SSR unnecessary for a PWA that talks to a local API, and adds build complexity).

### 5. Extending ConversationHistory for web users *(reversible)*

Change the key type from `int` to `int | str`. Web users use their UUID string. Telegram users keep their int ID. The `defaultdict` with `deque` approach works identically for both. No persistence change in this cycle (history remains in-memory).

**Why not persist history to SQLite now:** the brief explicitly defers WebSocket streaming and advanced history features. In-memory keeps this cycle focused on the transport layer. Adding SQLite persistence for history is additive.

### 6. API endpoint design *(reversible)*

All endpoints under `/api/v1`. Versioned prefix to allow breaking changes later without affecting the frontend URL space.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/auth/signup` | No | Create account (email, password) |
| POST | `/api/v1/auth/login` | No | Get JWT (email, password) |
| GET | `/api/v1/auth/me` | Yes | Current user profile |
| POST | `/api/v1/chat/message` | Yes | Send text message, get AI reply |
| POST | `/api/v1/chat/message/photo` | Yes | Send text + photo, get AI reply |
| GET | `/api/v1/chat/history` | Yes | Get conversation history |
| DELETE | `/api/v1/chat/history` | Yes | Clear conversation |
| GET | `/api/v1/appliances` | Yes | List equipment from Odoo |
| GET | `/api/v1/appliances/:id` | Yes | Single equipment details + maintenance history |
| POST | `/api/v1/appliances/:id/chat` | Yes | Send message in per-appliance thread |
| GET | `/api/v1/appliances/:id/chat` | Yes | Get per-appliance conversation history |

## Trade-offs

- **No WebSocket streaming.** Chat responses wait for the full LLM reply before returning. Acceptable because the brief explicitly defers streaming, and REST is simpler to build, test, and debug. Users see a loading spinner.
- **No persistent conversation history.** Restarting the bot process loses web chat history (same as Telegram today). Acceptable because Odoo remains the source of truth for appliance/maintenance data, and chat history is reconstructible.
- **No rate limiting on API endpoints in phase 1.** The Telegram rate limiter is per-user-ID. Web endpoints will add rate limiting in a follow-up. Acceptable for a single-household app behind auth.
- **No email verification.** Signup creates an active account immediately. Acceptable for a private household app. Email verification is additive if needed.

## Implementation sequence

### Phase 1: API skeleton + auth

FastAPI app with lifespan that starts the Telegram bot. Auth endpoints (signup, login, me). SQLite user store. JWT middleware. Health check endpoint. Docker config updated to expose port 8000. The Telegram bot works exactly as before. At the end of this phase, you can `curl` the signup/login/me endpoints and get valid JWTs.

### Phase 2: Chat API + history generalization

Generalize `ConversationHistory` key type to `int | str`. Build the chat message endpoint (text only first, then photo). Wire it to `get_response` from `llm.py`. GET history and DELETE history endpoints. At the end of this phase, you can have a full AI conversation via `curl`/Postman.

### Phase 3: Appliance endpoints

Appliance list and detail endpoints that proxy to Odoo. Per-appliance chat threads (separate conversation history keyed by `{user_id}:{equipment_id}`). At the end of this phase, the full API surface is complete.

### Phase 4: React PWA shell

Vite + React + Tailwind project scaffolding. React Router setup. Login screen. Auth context with JWT storage. API client module. PWA manifest and service worker for offline shell. At the end of this phase, you can log in from a mobile browser and see an empty authenticated shell.

### Phase 5: Chat and scan screens

Chat screen with text input, message list, and loading state. Photo upload via file input. Scan screen with appliance list pulled from the API. Per-appliance conversation view. Bottom navigation bar. At the end of this phase, the full product is usable.

## Diagram

```
+----------------------------------------------------------+
|                    Browser (PWA)                          |
|                                                          |
|  +------------+  +------------+  +-------------------+   |
|  |   Login    |  |    Chat    |  |    Scan / Detail  |   |
|  |   Screen   |  |   Screen   |  |     Screens       |   |
|  +-----+------+  +-----+------+  +--------+---------+   |
|        |              |                   |               |
|        +-------+------+-------------------+               |
|                |                                          |
|          [API Client - fetch + JWT in headers]            |
+----------------|-----------------------------------------+
                 | HTTP :8000
+----------------v-----------------------------------------+
|              FastAPI (uvicorn)                            |
|                                                          |
|  /api/v1/auth/*    /api/v1/chat/*    /api/v1/appliances/*|
|       |                  |                   |           |
|  +----v----+    +--------v--------+    +-----v------+   |
|  | auth.py |    |   chat routes   |    | appliance  |   |
|  | SQLite  |    |                 |    |   routes   |   |
|  | + JWT   |    +--------+--------+    +-----+------+   |
|  +---------+             |                   |           |
|                  +-------v-------+     +-----v------+   |
|                  | llm.py        |     | odoo.py    |   |
|                  | get_response()|     | OdooClient |   |
|                  +-------+-------+     +-----+------+   |
|                          |                   |           |
|                  +-------v-------+           |           |
|                  | tools.py      |------->---+           |
|                  | dispatch()    |                       |
|                  +---------------+                       |
|                                                          |
|  +----------------------------------------------------+  |
|  | ConversationHistory (int|str keys, in-memory)      |  |
|  +----------------------------------------------------+  |
|                                                          |
|  +----------------------------------------------------+  |
|  | Telegram Bot (python-telegram-bot, polling)         |  |
|  | Started as background task in FastAPI lifespan      |  |
|  +----------------------------------------------------+  |
+----------------------------------------------------------+
                 |                        |
                 v                        v
         +------+------+          +------+------+
         | OpenAI API  |          |   Odoo ERP  |
         | (GPT, TTS)  |          |  (XML-RPC)  |
         +-------------+          +-------------+
```

## Files

### To create

| File | Purpose |
|------|---------|
| `bot/api/__init__.py` | FastAPI app factory |
| `bot/api/app.py` | FastAPI application with lifespan, CORS, static file serving |
| `bot/api/auth.py` | Signup, login, me endpoints + JWT utilities |
| `bot/api/chat.py` | Chat message (text + photo) and history endpoints |
| `bot/api/appliances.py` | Appliance list, detail, per-appliance chat endpoints |
| `bot/api/deps.py` | Dependency injection (get current user, get shared services) |
| `bot/api/models.py` | Pydantic request/response schemas |
| `bot/db.py` | SQLite connection management + user CRUD (aiosqlite) |
| `web/` | React app root directory |
| `web/package.json` | Dependencies: react, react-router-dom, tailwindcss, vite |
| `web/vite.config.ts` | Vite config with proxy to API in dev |
| `web/tailwind.config.js` | Tailwind configuration |
| `web/index.html` | HTML entry point |
| `web/public/manifest.json` | PWA manifest (name, icons, theme color) |
| `web/public/sw.js` | Service worker for offline shell caching |
| `web/src/main.tsx` | React entry point |
| `web/src/App.tsx` | Router setup, auth guard |
| `web/src/api.ts` | API client (fetch wrapper with JWT injection) |
| `web/src/auth.tsx` | Auth context provider (login state, token storage) |
| `web/src/pages/Login.tsx` | Email/password login + signup form |
| `web/src/pages/Chat.tsx` | General chat screen (message list + text input + photo upload) |
| `web/src/pages/Scan.tsx` | Photo upload + appliance inventory list |
| `web/src/pages/ApplianceDetail.tsx` | Single appliance details + maintenance history + per-appliance chat |
| `web/src/components/BottomNav.tsx` | Bottom navigation bar (Accueil/Chat, Scan, Profile) |
| `web/src/components/MessageBubble.tsx` | Chat message bubble (user vs assistant styling) |
| `web/src/components/PhotoUpload.tsx` | Photo capture/upload component (camera + gallery) |
| `web/src/components/ApplianceCard.tsx` | Appliance list item card |
| `web/src/components/LoadingDots.tsx` | Typing/loading indicator for AI responses |

### To modify

| File | Change |
|------|--------|
| `bot/main.py` | Replace `app.run_polling()` with uvicorn startup that runs both FastAPI and Telegram bot via lifespan. Add `--host`/`--port` CLI args. |
| `bot/history.py` | Change key type from `int` to `int \| str`. Update type hints on all methods. |
| `bot/config.py` | Add `jwt_secret`, `sqlite_path`, `api_port` fields to `BotConfig`. Load from env vars `JWT_SECRET`, `SQLITE_PATH`, `API_PORT`. |
| `bot/handlers.py` | Extract core chat logic (the `get_response` call pattern with history management) into a shared helper that both Telegram handlers and API routes can call. |
| `pyproject.toml` | Add dependencies: `fastapi`, `uvicorn[standard]`, `python-jose[cryptography]`, `bcrypt`, `aiosqlite`, `python-multipart`. |
| `Dockerfile` | Add Node.js build stage for `web/`. Copy built frontend to be served as static files by FastAPI. Expose port 8000. |
| `docker-compose.yml` | Add port mapping `8000:8000` to the bot service. Add `JWT_SECRET` and `SQLITE_PATH` env vars. Mount a volume for the SQLite file. |
| `.env.example` | Add `JWT_SECRET`, `SQLITE_PATH`, `API_PORT` entries. |

### Data model changes

New SQLite database (default path: `data/hodoor.db`):

```sql
-- Schema version 1
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    email         TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
```

New Pydantic models in `bot/api/models.py`:

```python
class SignupRequest(BaseModel):
    email: EmailStr
    password: str  # min_length=8 via Field

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str

class ChatMessageRequest(BaseModel):
    text: str
    # photo sent as multipart form data, not in JSON body

class ChatMessageResponse(BaseModel):
    reply: str
    timestamp: str

class ApplianceResponse(BaseModel):
    id: int
    name: str
    category: str | None
    create_date: str
    maintenance_requests: list[dict]
```

ConversationHistory type change:

```python
# Before
self._store: dict[int, deque[dict]]
def get(self, user_id: int) -> list[dict]:

# After
self._store: dict[int | str, deque[dict]]
def get(self, user_id: int | str) -> list[dict]:
```
