"""SQLite connection management and user CRUD for HODOOR auth."""

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

_DB_PATH: str = "data/hodoor.db"
_SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    email         TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
"""


def set_db_path(path: str) -> None:
    global _DB_PATH
    _DB_PATH = path


async def init_db(path: str | None = None) -> None:
    db_path = path or _DB_PATH
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(_DDL)
        await db.commit()
    logger.info("SQLite DB initialized at %s", db_path)


async def create_user(email: str, password_hash: str, path: str | None = None) -> dict | None:
    """Insert a new user. Returns the created user dict or None if email already taken."""
    db_path = path or _DB_PATH
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?) RETURNING id, email, created_at",
                (email, password_hash),
            )
            row = await cursor.fetchone()
            await db.commit()
            if row:
                return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}
    except aiosqlite.IntegrityError:
        return None
    return None


async def get_user_by_email(email: str, path: str | None = None) -> dict | None:
    """Fetch user by email. Returns dict with id, email, password_hash or None."""
    db_path = path or _DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (email,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None


async def get_user_by_id(user_id: str, path: str | None = None) -> dict | None:
    """Fetch user by UUID. Returns dict with id, email, created_at or None."""
    db_path = path or _DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, email, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None
