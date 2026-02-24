from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./maplewind.db"

engine = create_async_engine(DATABASE_URL, echo=False)


# SQLite 외래 키(Foreign Key) 제약 조건 활성화
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
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
