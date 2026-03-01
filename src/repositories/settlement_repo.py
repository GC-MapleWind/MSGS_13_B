from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.settlement import Settlement


async def get_by_character_id(db: AsyncSession, character_id: int) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(Settlement.character_id == character_id)
        .order_by(Settlement.acquired_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, settlement_id: int) -> Settlement | None:
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    return result.scalar_one_or_none()


async def get_by_character_id_paginated(
    db: AsyncSession, character_id: int, skip: int, limit: int
) -> list[Settlement]:
    result = await db.execute(
        select(Settlement)
        .where(Settlement.character_id == character_id)
        .order_by(Settlement.acquired_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_by_character_id(db: AsyncSession, character_id: int) -> int:
    result = await db.execute(
        select(func.count(Settlement.id)).where(Settlement.character_id == character_id)
    )
    return int(result.scalar_one())
