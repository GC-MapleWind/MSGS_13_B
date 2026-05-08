import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")

# SQLite is kept as an explicit test/local-dry-run mode only. Production must set PostgreSQL.
if DATABASE_URL.startswith("sqlite"):
    _db_path = DATABASE_URL.split("///", 1)[-1]
    if _db_path.startswith("./"):
        _db_path = _db_path[2:]
    _db_dir = Path(_db_path).parent
    if str(_db_dir) not in ("", "."):
        _db_dir.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(DATABASE_URL, echo=False)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Create tables directly for one-off local tooling/tests.

    Runtime deployments should use `alembic upgrade head` instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
