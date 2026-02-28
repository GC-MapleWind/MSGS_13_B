from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import character_repo
from models.character import Character


async def get_all_characters(db: AsyncSession) -> list[Character]:
    return await character_repo.get_all(db)


async def get_character_info(db: AsyncSession, char_id: int) -> Character:
    character = await character_repo.get_by_id(db, char_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


async def get_charactors_pagenation(
    db: AsyncSession, page: int, limit: int
) -> dict[str, object]:
    offset = (page - 1) * limit
    items = await character_repo.get_all(db, skip=offset, limit=limit)
    total = await character_repo.count(db)
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }
