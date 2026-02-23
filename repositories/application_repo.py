from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application, ApplicationType, Member


async def get_member_by_user_id(db: AsyncSession, user_id: int) -> Member | None:
    result = await db.execute(select(Member).where(Member.user_id == user_id))
    return result.scalar_one_or_none()


async def get_member_by_student_id(db: AsyncSession, student_id: str) -> Member | None:
    result = await db.execute(select(Member).where(Member.student_id == student_id))
    return result.scalar_one_or_none()


async def create_member(db: AsyncSession, member: Member) -> Member:
    db.add(member)
    await db.flush()
    return member


async def update_member(db: AsyncSession, member: Member, **fields) -> Member:
    for key, value in fields.items():
        setattr(member, key, value)
    await db.flush()
    return member


async def get_application_by_member_term_type(
    db: AsyncSession,
    member_id: int,
    term: str,
    application_type: ApplicationType,
) -> Application | None:
    result = await db.execute(
        select(Application).where(
            Application.member_id == member_id,
            Application.term == term,
            Application.application_type == application_type,
        )
    )
    return result.scalar_one_or_none()


async def create_application(db: AsyncSession, application: Application) -> Application:
    db.add(application)
    await db.flush()
    return application


async def update_application(db: AsyncSession, application: Application, **fields) -> Application:
    for key, value in fields.items():
        setattr(application, key, value)
    await db.flush()
    return application


async def get_latest_application_by_member(db: AsyncSession, member_id: int) -> Application | None:
    result = await db.execute(
        select(Application)
        .where(Application.member_id == member_id)
        .order_by(Application.submitted_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
