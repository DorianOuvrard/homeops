"""FastAPI application with lifespan that co-hosts the Telegram bot."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bot.api.appliances import router as appliances_router
from bot.api.maintenance import router as maintenance_router
from bot.bran.api import router as bran_router
from bot.api.auth import build_auth_router
from bot.api.chat import router as chat_router
from bot.api.deps import CurrentUser, set_jwt_secret, set_shared_deps
from bot.api.models import UserResponse
from bot.api.push import router as push_router
from bot.db import init_db, set_db_path

logger = logging.getLogger(__name__)

_WEB_DIST = Path(__file__).parent.parent.parent / "web" / "dist"


def create_app(config, shared_deps: dict) -> FastAPI:
    """Build the FastAPI app. `config` is BotConfig, `shared_deps` contains history, odoo, etc."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Initialize SQLite
        set_db_path(config.sqlite_path)
        await init_db(config.sqlite_path)

        # Wire up shared state for dependency injection
        set_jwt_secret(config.jwt_secret)
        set_shared_deps(shared_deps)

        # Start Telegram bot as background asyncio task
        tg_app = shared_deps.get("telegram_app")
        if tg_app is not None:
            await tg_app.initialize()
            await tg_app.start()
            await tg_app.updater.start_polling()
            logger.info("Telegram bot polling started inside FastAPI lifespan")

            # Start calendar reminder loop
            start_reminder = shared_deps.get("start_reminder_loop")
            if start_reminder is not None:
                asyncio.create_task(start_reminder())

        yield

        # Shutdown Telegram bot
        if tg_app is not None:
            await tg_app.updater.stop()
            await tg_app.stop()
            await tg_app.shutdown()
            logger.info("Telegram bot stopped")

        # Cancel reminder loop if running
        task = shared_deps.get("reminder_task")
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    fastapi_app = FastAPI(title="HODOOR API", version="1.0.0", lifespan=lifespan)

    # CORS: allow the React dev server (vite) and same-origin in production
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix="/api/v1")

    # Auth
    auth_router = build_auth_router(config.jwt_secret)
    api.include_router(auth_router)

    # Me endpoint (separate from build_auth_router to avoid closure complexity)
    me_router = APIRouter(prefix="/auth", tags=["auth"])

    @me_router.get("/me", response_model=UserResponse)
    async def me(current_user: CurrentUser):
        return current_user

    api.include_router(me_router)
    api.include_router(chat_router)
    api.include_router(appliances_router)
    api.include_router(maintenance_router)
    api.include_router(bran_router)
    api.include_router(push_router)

    @api.get("/health")
    async def health():
        return {"status": "ok"}

    fastapi_app.include_router(api)

    # Serve uploaded photos/audio (mounted on main app so catch-all doesn't intercept)
    _uploads = Path("data/uploads")
    _uploads.mkdir(parents=True, exist_ok=True)
    fastapi_app.mount("/api/v1/uploads", StaticFiles(directory=str(_uploads)), name="uploads")

    # Serve React PWA from web/dist if it exists
    if _WEB_DIST.exists():
        # Serve static assets (JS, CSS, images)
        fastapi_app.mount("/assets", StaticFiles(directory=str(_WEB_DIST / "assets")), name="assets")
        # Serve other static files (manifest, sw, icons)
        fastapi_app.mount("/public", StaticFiles(directory=str(_WEB_DIST)), name="public")

        # SPA catch-all: serve index.html for any non-API route
        @fastapi_app.get("/{path:path}")
        async def spa_catchall(request: Request, path: str):
            # Never intercept API routes (let FastAPI/StaticFiles handle them)
            if path.startswith("api/"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            # Serve actual files if they exist (manifest.json, sw.js, etc.)
            file_path = _WEB_DIST / path
            if file_path.is_file():
                return FileResponse(file_path)
            # Otherwise serve index.html for React Router
            return FileResponse(_WEB_DIST / "index.html", media_type="text/html")

        logger.info("Serving React PWA from %s", _WEB_DIST)
    else:
        logger.info("No web/dist found; skipping static file serving")

    return fastapi_app
