import os
from collections.abc import AsyncGenerator
from typing import Any
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# 챗봇 전용 DB 경로 설정 (data/ 디렉토리에 저장 → 볼륨 마운트로 영속성 보장)
_chatbot_db_path = os.path.join(
    os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")),
    "chatbot.db"
)
CHATBOT_DATABASE_URL = f"sqlite+aiosqlite:///{_chatbot_db_path}"

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
                    InfoList(step_order=1, field_name="이름", question_text="이름을 알려달람!", event_name="메생결산"),
                    InfoList(step_order=2, field_name="학번", question_text="이제 학번을 입력해 줘야 한담 (예: 202612345)", event_name="메생결산"),
                    InfoList(step_order=3, field_name="한마디", question_text="마지막으로 사진과 함께 들어갈 한마디를 남겨달람! 혹시 사진이 많으면 1. 반갑담 2. 졸리담 처럼 입력해 주면 좋겠담!", event_name="메생결산")
                ]
                db.add_all(steps)
                await db.commit()
        except Exception as e:
            print(f"Seeding Error: {e}")

async def init_chatbot_db() -> None:
    async with chatbot_engine.begin() as conn:
        await conn.run_sync(ChatbotBase.metadata.create_all)
    await seed_registration_steps()
