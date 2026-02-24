from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character


ADMIN_TEAM_NAME = "단풍바람 운영팀"


async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Character]:
    result = await db.execute(
        select(Character)
        .where(Character.name != ADMIN_TEAM_NAME)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_admin_team(db: AsyncSession) -> Character | None:
    result = await db.execute(
        select(Character).where(Character.name == ADMIN_TEAM_NAME)
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, char_id: int) -> Character | None:
    result = await db.execute(select(Character).where(Character.id == char_id))
    return result.scalar_one_or_none()
