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


async def get_characters(db: AsyncSession, page: int, limit: int):
    offset = (page - 1) * limit

    # 기존 repo의 get_all을 그대로 재사용 (리스크 최소)
    items = await character_repo.get_all(db, skip=offset, limit=limit)
    total = await character_repo.count(db)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }