from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.settlement import Settlement


async def get_by_character_id(
    db: AsyncSession, character_id: int
) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(Settlement.character_id == character_id)
        .order_by(Settlement.acquired_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, settlement_id: int) -> Settlement | None:
    result = await db.execute(
        select(Settlement).where(Settlement.id == settlement_id)
    )
    return result.scalar_one_or_none()
