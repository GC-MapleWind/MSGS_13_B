from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db
from schemas.user_dto import UserCreate, UserResponse, Token
from services import user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    회원가입
    """
    return await user_service.signup(db, user_data)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    로그인 (JWT 토큰 발급)
    """
    return await user_service.login(db, form_data.username, form_data.password)
