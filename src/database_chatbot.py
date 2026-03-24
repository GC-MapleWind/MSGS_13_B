import os
from collections.abc import AsyncGenerator
from typing import Any
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# 챗봇 전용 DB 경로 설정
CHATBOT_DATABASE_URL = "sqlite+aiosqlite:///./chatbot.db"

chatbot_engine = create_async_engine(CHATBOT_DATABASE_URL, echo=False)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

chatbot_async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    chatbot_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class ChatbotBase(DeclarativeBase):
    pass

async def get_chatbot_db() -> AsyncGenerator[AsyncSession, None]:
    async with chatbot_async_session() as session:
        yield session

async def seed_registration_steps() -> None:
    """기본 질문 항목 초기화"""
    from src.models.chatbot import InfoList
    async with chatbot_async_session() as db:
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM infolist"))
            if result.scalar() == 0:
                steps = [
                    InfoList(step_order=1, field_name="name", question_text="본인의 **실명**을 입력해달람."),
                    InfoList(step_order=2, field_name="student_id", question_text="이제 **학번**을 입력해달람. (예: 20241234)"),
                    InfoList(step_order=3, field_name="comment", question_text="마지막으로 사진과 함께 들어갈 **한마디**를 입력해달람.")
                ]
                db.add_all(steps)
                await db.commit()
        except Exception as e:
            print(f"Seeding Error: {e}")

async def init_chatbot_db() -> None:
    async with chatbot_engine.begin() as conn:
        await conn.run_sync(ChatbotBase.metadata.create_all)
    await seed_registration_steps()
