from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories import settlement_repo, character_repo
from src.models.settlement import Settlement


async def get_settlements_by_character(
    db: AsyncSession, character_id: int
) -> list[Settlement]:
    character = await character_repo.get_by_id(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return await settlement_repo.get_by_character_id(db, character_id)


async def get_settlement_detail(db: AsyncSession, settlement_id: int) -> Settlement:
    settlement = await settlement_repo.get_by_id(db, settlement_id)
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement


async def get_settlements_by_character_pagination(
    db: AsyncSession, character_id: int, page: int, limit: int
) -> dict[str, object]:
    character = await character_repo.get_by_id(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    offset = (page - 1) * limit
    items = await settlement_repo.get_by_character_id_paginated(
        db, character_id, skip=offset, limit=limit
    )
    total = await settlement_repo.count_by_character_id(db, character_id)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }
