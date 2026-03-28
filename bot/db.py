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

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id       TEXT NOT NULL,
    endpoint      TEXT NOT NULL UNIQUE,
    p256dh        TEXT NOT NULL,
    auth          TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user_id ON push_subscriptions (user_id);
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


async def upsert_push_subscription(
    user_id: str,
    endpoint: str,
    p256dh: str,
    auth: str,
    path: str | None = None,
) -> None:
    db_path = path or _DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET
              user_id = excluded.user_id,
              p256dh = excluded.p256dh,
              auth = excluded.auth
            """,
            (user_id, endpoint, p256dh, auth),
        )
        await db.commit()


async def list_push_subscriptions(
    user_id: str | None = None,
    path: str | None = None,
) -> list[dict]:
    db_path = path or _DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        if user_id:
            cursor = await db.execute(
                """
                SELECT id, user_id, endpoint, p256dh, auth, created_at
                FROM push_subscriptions
                WHERE user_id = ?
                """,
                (user_id,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, user_id, endpoint, p256dh, auth, created_at
                FROM push_subscriptions
                """
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_push_subscription(endpoint: str, path: str | None = None) -> None:
    db_path = path or _DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
        await db.commit()
