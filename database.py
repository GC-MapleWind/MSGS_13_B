import os
from pathlib import Path

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./data/maplewind.db"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _sqlite_db_path(database_url: str) -> Path | None:
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if database_url.startswith(prefix):
            raw_path = database_url[len(prefix) :].split("?", 1)[0]
            if raw_path in {"", ":memory:"}:
                return None
            if raw_path.startswith("/"):
                return Path(raw_path)
            return Path(raw_path)
    return None


def ensure_sqlite_directory(database_url: str) -> None:
    sqlite_path = _sqlite_db_path(database_url)
    if sqlite_path is None:
        return
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)


DATABASE_URL = get_database_url()
ensure_sqlite_directory(DATABASE_URL)

engine = create_async_engine(DATABASE_URL, echo=False)

# SQLite 외래 키(Foreign Key) 제약 조건 활성화
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # NOTE: this compatibility patch is intentionally SQLite-specific.
        # For broader DB portability/versioned schema changes, use a migration tool (e.g. Alembic).
        if conn.dialect.name != "sqlite":
            return

        has_comments_table = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).has_table("comments")
        )
        if not has_comments_table:
            return

        result = await conn.execute(text("PRAGMA table_info(comments)"))
        columns = {row[1] for row in result.fetchall()}
        if "password_hash" not in columns:
            await conn.execute(
                text("ALTER TABLE comments ADD COLUMN password_hash VARCHAR")
            )
