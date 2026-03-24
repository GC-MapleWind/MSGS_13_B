from typing import Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.chatbot import TemporaryImage, InfoList, EventInfo


class ChatbotRepository:
    async def get_event_info(self, db: AsyncSession, event_name: str) -> EventInfo | None:
        """특정 이벤트 정보를 가져옵니다."""
        result = await db.execute(
            select(EventInfo).where(EventInfo.name == event_name)
        )
        return result.scalars().first()

    async def get_all_events(self, db: AsyncSession) -> list[EventInfo]:
        """모든 이벤트 정보를 가져옵니다."""
        result = await db.execute(select(EventInfo))
        return list(result.scalars().all())

    async def get_steps(self, db: AsyncSession) -> list[InfoList]:
        """질문 항목 목록을 순서대로 가져옵니다."""
        result = await db.execute(select(InfoList).order_by(InfoList.step_order))
        return list(result.scalars().all())

    async def get_steps_by_event(self, db: AsyncSession, event_name: str) -> list[InfoList]:
        """특정 이벤트에 속한 질문 항목 목록을 순서대로 가져옵니다."""
        result = await db.execute(
            select(InfoList)
            .where(InfoList.event_name == event_name)
            .order_by(InfoList.step_order)
        )
        return list(result.scalars().all())

    async def get_session(self, db: AsyncSession, user_key: str) -> TemporaryImage | None:
        """사용자의 세션 정보를 가져옵니다."""
        result = await db.execute(
            select(TemporaryImage).where(TemporaryImage.user_key == user_key)
        )
        return result.scalars().first()

    async def get_or_create_session(self, db: AsyncSession, user_key: str) -> TemporaryImage:
        """사용자의 세션을 가져오거나 새로 생성합니다."""
        session = await self.get_session(db, user_key)
        if not session:
            session = TemporaryImage(user_key=user_key, data={}, image_urls="")
            db.add(session)
            await db.flush()
        return session

    async def update_data(self, db: AsyncSession, user_key: str, field_name: str, value: str) -> TemporaryImage:
        """JSON 데이터 필드에 정보를 업데이트합니다."""
        session = await self.get_or_create_session(db, user_key)
        
        # SQLAlchemy의 JSON 필드 변경을 명시적으로 알리기 위해 딕셔너리 복사 후 업데이트
        new_data = dict(session.data or {})
        new_data[field_name] = value
        session.data = new_data
        
        await db.flush()
        return session

    async def add_image_url(self, db: AsyncSession, user_key: str, image_url: str) -> TemporaryImage:
        """이미지 URL을 기존 목록에 추가합니다."""
        session = await self.get_or_create_session(db, user_key)
        if session.image_urls:
            session.image_urls += f",{image_url}"
        else:
            session.image_urls = image_url
        await db.flush()
        return session

    async def delete_session(self, db: AsyncSession, user_key: str) -> bool:
        """사용자의 세션 정보를 완전히 삭제합니다."""
        result = await db.execute(
            delete(TemporaryImage).where(TemporaryImage.user_key == user_key)
        )
        return result.rowcount > 0

    # 기존 호환성 유지
    async def add_image(self, db: AsyncSession, user_key: str, image_url: str) -> TemporaryImage:
        return await self.add_image_url(db, user_key, image_url)

    async def get_all_by_user(self, db: AsyncSession, user_key: str) -> list[Any]:
        session = await self.get_session(db, user_key)
        if not session or not session.image_urls:
            return []
        from dataclasses import dataclass
        @dataclass
        class MockImage:
            image_url: str
        return [MockImage(url.strip()) for url in session.image_urls.split(",") if url.strip()]

    async def delete_all_by_user(self, db: AsyncSession, user_key: str) -> int:
        return 1 if await self.delete_session(db, user_key) else 0


chatbot_repo = ChatbotRepository()
