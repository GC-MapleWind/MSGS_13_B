from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories import character_repo
from src.models.character import Character

ADMIN_TEAM_NAME = "단풍바람 운영팀"


async def get_all_characters(db: AsyncSession) -> list[Character]:
    return await character_repo.get_all(
        db,
        exclude_name=ADMIN_TEAM_NAME,
        require_settlement=True,
    )


async def get_character_info(db: AsyncSession, char_id: int) -> Character:
    character = await character_repo.get_by_id(db, char_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


async def get_admin_character(db: AsyncSession) -> Character | None:
    return await character_repo.get_admin_team(db)


async def get_characters_pagination(
    db: AsyncSession, page: int, limit: int
) -> dict[str, object]:
    offset = (page - 1) * limit
    items = await character_repo.get_all(
        db,
        skip=offset,
        limit=limit,
        exclude_name=ADMIN_TEAM_NAME,
        require_settlement=True,
    )
    total = await character_repo.count(
        db,
        exclude_name=ADMIN_TEAM_NAME,
        require_settlement=True,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }
