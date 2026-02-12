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
COOKIE_PATH = "/api/v1/users"

def _set_refresh_cookie(response: Response, rt: str):
    """
    응답에 HttpOnly 'refresh_token' 쿠키를 설정한다.

    쿠키는 Secure/SameSite 속성이 적용되고 만료 시간은 REFRESH_TOKEN_EXPIRE_DAYS 환경값을 기준으로 설정된다.

    Parameters:
    	rt (str): 설정할 리프레시 토큰 문자열.
    """
    response.set_cookie(
        key="refresh_token",
        value=rt,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=COOKIE_PATH,
    )

def _clear_refresh_cookie(response: Response):
    """Refresh Token 쿠키를 삭제하는 공통 유틸리티"""
    response.delete_cookie(
        key="refresh_token",
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax"
    )

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    새 사용자를 생성합니다.

    Parameters:
        user_data (UserCreate): 회원 가입에 필요한 입력 데이터.

    Returns:
        생성된 사용자의 응답 데이터 (UserResponse).
    """
    return await user_service.signup(db, user_data)

@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 자격증명을 검증하여 액세스 토큰을 발급하고 리프레시 토큰을 HttpOnly 쿠키에 저장한다.

    Returns:
        Token: 발급된 액세스 토큰과 관련 메타데이터(예: 토큰 타입, 만료 시간).
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
    카카오 인가 코드로 로그인 흐름을 처리하여 기존 사용자는 액세스 토큰과 리프레시 토큰 쿠키를 설정하고, 신규 사용자는 등록 토큰을 반환한다.

    Parameters:
        code (str): 카카오에서 발급된 인가 코드.

    Returns:
        KakaoLoginResponse: 기존 회원인 경우 `is_new_user=False`와 `access_token`을 포함; 신규 회원인 경우 `is_new_user=True`와 `register_token`을 포함.
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

@router.post("/auth/kakao/register", response_model=Token, status_code=201)
async def kakao_register(
    response: Response,
    data: KakaoRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    카카오로 시작된 가입을 최종 완료하고 인증 토큰을 발급한다.

    Parameters:
        response (Response): 응답 객체 — 호출 후 HttpOnly `refresh_token` 쿠키가 설정된다.
        data (KakaoRegisterRequest): 카카오 가입 마무리에 필요한 데이터 (`register_token`, `student_id`, `nickname`).
        db (AsyncSession): 데이터베이스 세션 (의존성 주입).

    Returns:
        Token: 발급된 액세스 토큰과 관련 토큰 정보를 담은 스키마.
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
    Refresh token 쿠키를 사용해 새로운 액세스 토큰과 리프레시 토큰을 발급하고 리프레시 쿠키를 갱신(토큰 회전)한다.

    Raises:
        HTTPException: `refresh_token` 쿠키가 없으면 상태 코드 401(Unauthorized)을 발생시킨다.

    Returns:
        dict: 새 액세스 토큰과 관련 메타정보를 포함한 토큰 데이터.
    """
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    
    new_token_data, new_rt = await user_service.refresh_access_token(db, rt)
    
    # 새 RT로 쿠키 업데이트 (Rotation)
    _set_refresh_cookie(response, new_rt)
    
    return new_token_data

@router.post("/logout", response_model=dict)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 로그아웃을 수행하고 서버·클라이언트 측에서 인증 정보를 제거한다.

    로그아웃 시 데이터베이스에서 사용자의 리프레시 토큰을 삭제하고, 클라이언트의 `refresh_token` 쿠키를 만료(삭제)한다.

    Returns:
        dict: 키 `"detail"`에 로그아웃 성공 메시지를 담은 사전, 예: `{"detail": "Successfully logged out"}`
    """
    await user_service.logout(db, current_user)
    _clear_refresh_cookie(response)
    
    return {"detail": "Successfully logged out"}

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    현재 사용자를 탈퇴 처리하고, 카카오 연동이 있으면 해당 연결을 끊은 뒤 리프레시 토큰 쿠키를 삭제한다.

    Returns:
    	HTTP 204 No Content 응답
    """
    await user_service.withdraw_user(db, current_user)
    _clear_refresh_cookie(response)
