from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_current_user, get_db
from models.user import User
from schemas.application_dto import (
    ApplicationResponse,
    MyApplicationResponse,
    NewApplicationCreate,
    RenewApplicationCreate,
)
from services import application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/new", response_model=ApplicationResponse, status_code=201)
async def submit_new_application(
    data: NewApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await application_service.submit_new_application(db, current_user, data)


@router.post("/renew", response_model=ApplicationResponse, status_code=201)
async def submit_renew_application(
    data: RenewApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await application_service.submit_renew_application(db, current_user, data)


@router.get("/me", response_model=MyApplicationResponse)
async def get_my_application(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await application_service.get_my_latest_application(db, current_user)
