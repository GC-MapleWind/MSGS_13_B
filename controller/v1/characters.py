from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db
from schemas.character_dto import (
    CharacterDetailResponse,
    CharacterResponse,
    CharactersPaginationResponse,
)
from schemas.settlement_dto import SettlementResponse
from services import character_service, settlement_service

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("", response_model=list[CharacterResponse])
async def get_characters(db: AsyncSession = Depends(get_db)):
    return await character_service.get_all_characters(db)


@router.get("/characters/pagination", response_model=CharactersPaginationResponse)
@router.get("/charactors_pagenation", response_model=CharactersPaginationResponse)
async def get_characters_pagination(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await character_service.get_characters_pagination(db, page, limit)


@router.get("/{character_id}", response_model=CharacterDetailResponse)
async def get_character(character_id: int, db: AsyncSession = Depends(get_db)):
    return await character_service.get_character_info(db, character_id)


@router.get("/{character_id}/settlements", response_model=list[SettlementResponse])
async def get_character_settlements(
    character_id: int, db: AsyncSession = Depends(get_db)
):
    return await settlement_service.get_settlements_by_character(db, character_id)
