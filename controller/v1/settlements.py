from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db
from schemas.settlement_dto import SettlementDetailResponse
from services import settlement_service

router = APIRouter(prefix="/settlements", tags=["settlements"])


@router.get("/{settlement_id}", response_model=SettlementDetailResponse)
async def get_settlement_detail(
    settlement_id: int, db: AsyncSession = Depends(get_db)
):
    return await settlement_service.get_settlement_detail(db, settlement_id)
