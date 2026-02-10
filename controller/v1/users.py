import os
from fastapi import APIRouter, Depends, status, Response, Request, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db, get_current_user
from models.user import User
from schemas.user_dto import UserCreate, UserResponse, Token, KakaoLoginResponse, KakaoRegisterRequest
from services import user_service

router = APIRouter(prefix="/users", tags=["users"])

# 환경 변수에서 쿠키 보안 설정 로드
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "True").lower() == "true"
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 14))

def _set_refresh_cookie(response: Response, rt: str):
    """Refresh Token을 쿠키에 설정하는 공통 유틸리티"""
    response.set_cookie(
        key="refresh_token",
        value=rt,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/users/refresh",
    )

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    회원가입 (일반)
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
    _set_refresh_cookie(response, rt)
    return token_data

@router.post("/auth/kakao/login", response_model=KakaoLoginResponse)
async def kakao_login(
    response: Response,
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Phase 1: 카카오 인가 코드로 로그인 시도
    기존 회원이면 AT/RT 발급, 신규 회원이면 Register Token 발급
    """
    result = await user_service.process_kakao_login(db, code)
    
    if not result["is_new_user"]:
        # 기존 회원인 경우 RT 쿠키 설정
        _set_refresh_cookie(response, result["refresh_token"])
        return KakaoLoginResponse(
            is_new_user=False,
            access_token=result["access_token"]
        )
    else:
        # 신규 회원인 경우 Register Token 반환
        return KakaoLoginResponse(
            is_new_user=True,
            register_token=result["register_token"]
        )

@router.post("/auth/kakao/register", response_model=Token)
async def kakao_register(
    response: Response,
    data: KakaoRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Phase 2: 학번과 닉네임을 입력하여 최종 회원가입 완료
    나머지 정보(전화번호, 생일, 성명)는 카카오 인증 정보를 활용함
    """
    token_data, rt = await user_service.finalize_kakao_registration(
        db, 
        data.register_token,
        data.student_id,
        data.nickname
    )
    _set_refresh_cookie(response, rt)
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

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    회원 탈퇴: 카카오 연결 끊기(카카오 유저인 경우) 및 로컬 DB 삭제
    """
    # 헤더에서 카카오 액세스 토큰 추출 (있을 경우)
    kakao_at = request.headers.get("X-Kakao-Access-Token")
    
    await user_service.withdraw_user(db, current_user, kakao_at)
    
    # 쿠키 삭제
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/users/refresh",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax"
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

