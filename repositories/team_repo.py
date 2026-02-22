from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from models.team import TeamMember, TeamMessage

async def get_all_members(db: AsyncSession) -> list[TeamMember]:
    result = await db.execute(select(TeamMember))
    return list(result.scalars().all())

async def get_member_by_id(db: AsyncSession, member_id: int) -> TeamMember | None:
    result = await db.execute(
        select(TeamMember)
        .options(joinedload(TeamMember.message))
        .filter(TeamMember.id == member_id)
    )
    return result.scalar_one_or_none()
