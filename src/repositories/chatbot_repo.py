import datetime
from typing import Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.chatbot import ActivitySubmission, SubmitterProfile, TemporaryImage, InfoList, EventInfo


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

    async def delete_data(self, db: AsyncSession, user_key: str, field_name: str) -> TemporaryImage:
        """JSON 데이터 필드에서 특정 정보를 삭제합니다."""
        session = await self.get_or_create_session(db, user_key)
        
        new_data = dict(session.data or {})
        if field_name in new_data:
            del new_data[field_name]
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

    async def delete_image_url(self, db: AsyncSession, user_key: str, image_url: str) -> TemporaryImage:
        """이미지 URL 목록에서 특정 URL 하나를 찾아 삭제합니다."""
        session = await self.get_or_create_session(db, user_key)
        if session.image_urls:
            urls = [url.strip() for url in session.image_urls.split(",") if url.strip()]
            if image_url in urls:
                urls.remove(image_url)
                session.image_urls = ",".join(urls)
                await db.flush()
        return session

    async def clear_image_urls(self, db: AsyncSession, user_key: str) -> TemporaryImage:
        """사용자의 모든 이미지 URL을 삭제합니다. (정보는 유지)"""
        session = await self.get_or_create_session(db, user_key)
        session.image_urls = ""
        await db.flush()
        return session

    async def clear_data(self, db: AsyncSession, user_key: str) -> TemporaryImage:
        """사용자의 모든 데이터(정보)를 초기화합니다. (이미지는 유지)"""
        session = await self.get_or_create_session(db, user_key)
        
        # 이벤트 정보와 시작 플래그는 유지하여 바로 질문으로 넘어가게 함
        new_data = {}
        if session.data:
            if "active_event" in session.data:
                new_data["active_event"] = session.data["active_event"]
            if "__started__" in session.data:
                new_data["__started__"] = session.data["__started__"]
        
        session.data = new_data
        await db.flush()
        return session

    async def delete_session(self, db: AsyncSession, user_key: str) -> bool:
        """사용자의 세션 정보를 완전히 삭제합니다."""
        result = await db.execute(
            delete(TemporaryImage).where(TemporaryImage.user_key == user_key)
        )
        return result.rowcount > 0

    # --- SubmitterProfile ---

    async def get_submitter_profile(self, db: AsyncSession, user_key: str) -> SubmitterProfile | None:
        result = await db.execute(
            select(SubmitterProfile).where(SubmitterProfile.user_key == user_key)
        )
        return result.scalars().first()

    async def upsert_submitter_profile(
        self,
        db: AsyncSession,
        user_key: str,
        name: str,
        student_id: str,
        member_type: str | None = None,
    ) -> SubmitterProfile:
        profile = await self.get_submitter_profile(db, user_key)
        if profile:
            profile.name = name
            profile.student_id = student_id
            if member_type:
                profile.member_type = member_type
        else:
            profile = SubmitterProfile(
                user_key=user_key, name=name, student_id=student_id, member_type=member_type
            )
            db.add(profile)
        await db.flush()
        return profile

    async def update_member_type(self, db: AsyncSession, user_key: str, member_type: str) -> None:
        profile = await self.get_submitter_profile(db, user_key)
        if profile:
            profile.member_type = member_type
            await db.flush()

    # --- ActivitySubmission ---

    async def create_submission(
        self,
        db: AsyncSession,
        user_key: str,
        submitter_name: str,
        submitter_student_id: str,
        photo_urls: str,
        activity_date: str,
        activity_type: str,
        newbie_count: int,
        existing_count: int,
        score: int = 0,
    ) -> ActivitySubmission:
        submission = ActivitySubmission(
            user_key=user_key,
            submitter_name=submitter_name,
            submitter_student_id=submitter_student_id,
            photo_urls=photo_urls,
            activity_date=activity_date,
            activity_type=activity_type,
            newbie_count=newbie_count,
            existing_count=existing_count,
            score=score,
            submitted_at=datetime.datetime.utcnow(),
        )
        db.add(submission)
        await db.flush()
        return submission

    async def get_submissions_by_user(self, db: AsyncSession, user_key: str, limit: int = 5) -> list[ActivitySubmission]:
        result = await db.execute(
            select(ActivitySubmission)
            .where(ActivitySubmission.user_key == user_key)
            .order_by(ActivitySubmission.submitted_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_submission_photo_urls(self, db: AsyncSession, submission_id: int, photo_urls: str) -> None:
        result = await db.execute(
            select(ActivitySubmission).where(ActivitySubmission.id == submission_id)
        )
        submission = result.scalars().first()
        if submission:
            submission.photo_urls = photo_urls
            await db.flush()


chatbot_repo = ChatbotRepository()
