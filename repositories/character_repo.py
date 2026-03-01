from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.character import Character
from models.settlement import Settlement


ADMIN_TEAM_NAME = "단풍바람 운영팀"


async def get_all(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    exclude_name: str | None = None,
    require_settlement: bool = False,
) -> list[Character]:
    query = select(Character)
    if exclude_name:
        query = query.where(Character.name != exclude_name)
    if require_settlement:
        query = query.where(exists().where(Settlement.character_id == Character.id))

    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_admin_team(db: AsyncSession) -> Character | None:
    result = await db.execute(
        select(Character).where(Character.name == ADMIN_TEAM_NAME)
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, char_id: int) -> Character | None:
    result = await db.execute(select(Character).where(Character.id == char_id))
    return result.scalar_one_or_none()


async def count(
    db: AsyncSession,
    exclude_name: str | None = None,
    require_settlement: bool = False,
) -> int:
    query = select(func.count(Character.id))
    if exclude_name:
        query = query.where(Character.name != exclude_name)
    if require_settlement:
        query = query.where(exists().where(Settlement.character_id == Character.id))

    result = await db.execute(query)
    return int(result.scalar_one())
