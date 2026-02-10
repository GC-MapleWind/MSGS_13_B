import os
from fastapi import APIRouter, Depends, status, Response, Request, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db, get_current_user
from models.user import User
from schemas.user_dto import UserCreate, UserResponse, Token
from services import user_service

router = APIRouter(prefix="/users", tags=["users"])

# 환경 변수에서 쿠키 보안 설정 로드
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "True").lower() == "true"
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 14))

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    회원가입
    """
    return await user_service.signup(db, user_data)

@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    로그인: AT는 JSON으로, RT는 HttpOnly 쿠키로 발급
    """
    token_data, rt = await user_service.login(db, form_data.username, form_data.password)
    
    # Refresh Token을 쿠키에 저장
    response.set_cookie(
        key="refresh_token",
        value=rt,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # 초 단위
        path="/api/v1/users/refresh",  # RT는 갱신 경로로만 전송되도록 제한
    )
    
    return token_data

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Silent Refresh: 쿠키의 RT를 사용하여 새로운 AT/RT 발급 (Rotation)
    """
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    
    new_token_data, new_rt = await user_service.refresh_access_token(db, rt)
    
    # 새 RT로 쿠키 업데이트 (Rotation)
    response.set_cookie(
        key="refresh_token",
        value=new_rt,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/users/refresh",
    )
    
    return new_token_data

@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    로그아웃: DB의 RT 삭제 및 쿠키 만료 처리
    """
    await user_service.logout(db, current_user)
    
    # 쿠키 삭제
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/users/refresh",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax"
    )
    
    return {"detail": "Successfully logged out"}
