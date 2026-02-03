from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import settlement_repo, character_repo
from models.settlement import Settlement


async def get_settlements_by_character(
    db: AsyncSession, character_id: int
) -> list[Settlement]:
    character = await character_repo.get_by_id(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return await settlement_repo.get_by_character_id(db, character_id)


async def get_settlement_detail(
    db: AsyncSession, settlement_id: int
) -> Settlement:
    settlement = await settlement_repo.get_by_id(db, settlement_id)
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement
