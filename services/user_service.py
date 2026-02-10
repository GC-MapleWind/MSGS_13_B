import datetime
import os
import secrets
import hashlib
from fastapi import HTTPException, status
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from models.user import User
from repositories import user_repo
from schemas.user_dto import UserCreate, Token

# 환경 변수 로드
load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("FATAL: JWT_SECRET_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # AT 수명 단축 (기본값 30분)
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 14))     # RT 수명 (기본값 14일)

# 카카오 설정
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_ADMIN_KEY = os.getenv("KAKAO_ADMIN_KEY")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- 보안 유틸리티 ---

# 한국 시간(KST) 설정을 위한 상수
KST = datetime.timezone(datetime.timedelta(hours=9))

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def hash_refresh_token(token: str) -> str:
    """Refresh Token을 SHA-256으로 해싱합니다."""
    return hashlib.sha256(token.encode()).hexdigest()

def create_access_token(data: dict):
    to_encode = data.copy()
    # JWT 표준 검증(jose)은 UTC를 기준으로 하므로, exp는 UTC로 설정해야 정확히 만료됩니다.
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_register_token(data: dict):
    """회원가입 전용 임시 토큰 (5분 만료)"""
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=5)
    to_encode.update({"exp": expire, "is_register": True})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token() -> str:
    """안전한 랜덤 문자열 RT 생성"""
    return secrets.token_urlsafe(32)

# --- 서비스 로직 ---

import httpx

async def _issue_service_tokens(db: AsyncSession, user: User) -> tuple[Token, str]:
    """유저에게 AT와 RT를 발급하고 DB에 저장하는 공통 로직"""
    at = create_access_token(data={"sub": user.username})
    rt = create_refresh_token()
    
    now_kst = datetime.datetime.now(KST).replace(tzinfo=None)
    user.refresh_token_hash = hash_refresh_token(rt)
    user.refresh_token_expires_at = now_kst + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    await db.commit()
    
    return Token(access_token=at, token_type="bearer"), rt

async def process_kakao_login(db: AsyncSession, code: str) -> dict:
    """Phase 1: 카카오 로그인 처리 및 분기"""
    async with httpx.AsyncClient() as client:
        # 1. 카카오 액세스 토큰 요청
        token_res = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": KAKAO_CLIENT_ID,
                "redirect_uri": KAKAO_REDIRECT_URI,
                "code": code,
                "client_secret": KAKAO_CLIENT_SECRET,
            }
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid kakao authorization code")
        
        kakao_access_token = token_res.json().get("access_token")

        # 2. 카카오 유저 정보 요청
        user_res = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {kakao_access_token}"}
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to fetch kakao user info")
        
        kakao_data = user_res.json()
        kakao_id = kakao_data.get("id")
        kakao_account = kakao_data.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        
                # 카카오에서 제공하는 추가 정보 추출 및 한국식 번호 변환 (+82 10-XXXX-XXXX -> 010-XXXX-XXXX)
                raw_phone = kakao_account.get("phone_number")
                phone_number = raw_phone.replace("+82 ", "0").replace("+82", "0").replace(" ", "") if raw_phone else None
                
                birthyear = kakao_account.get("birthyear")
                birthday = kakao_account.get("birthday")
                birthdate = f"{birthyear}-{birthday[:2]}-{birthday[2:]}" if birthyear and birthday else None
                gender = kakao_account.get("gender") # male / female
        
                # 3. 기존 회원 여부 확인 (1순위: kakao_id, 2순위: phone_number 연동)
                user = await user_repo.get_by_kakao_id(db, kakao_id)
                
                if not user and phone_number:
                    # 카카오 ID는 없지만 동일한 전화번호의 기존 계정이 있는지 확인
                    existing_user = await user_repo.get_by_phone_number(db, phone_number)
                    if existing_user:
                        # 계정 자동 연동: 기존 계정에 kakao_id 부여
                        existing_user.kakao_id = kakao_id
                        await db.commit()
                        user = existing_user
        
                if user:
                    # CASE A: 기존 유저 또는 연동된 유저 -> 즉시 로그인
                    tokens, rt = await _issue_service_tokens(db, user)
                    return {
                        "is_new_user": False,
                        "access_token": tokens.access_token,
                        "refresh_token": rt
                    }
                else:
                    # CASE B: 완전히 새로운 유저 -> Register Token 발급
                    # 실명(name)을 최우선으로, 없으면 닉네임을 사용
                    real_name = kakao_account.get("name") or profile.get("nickname") or "카카오사용자"
                    reg_token = create_register_token({
                        "kakao_id": kakao_id,
                        "phone_number": phone_number,
                        "birthdate": birthdate,
                        "gender": gender,
                        "temp_name": real_name
                    })
                    return {
                        "is_new_user": True,
                        "register_token": reg_token
                    }
        
        async def finalize_kakao_registration(
            db: AsyncSession, 
            register_token: str,
            student_id: str,
            nickname: str
        ) -> tuple[Token, str]:
            """Phase 2: 추가 정보(학번, 닉네임) 입력 및 최종 회원가입"""
            try:
                payload = jwt.decode(register_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
                if not payload.get("is_register"):
                    raise HTTPException(status_code=401, detail="Invalid register token")
                
                kakao_id = payload.get("kakao_id")
                phone_number = payload.get("phone_number")
                birthdate = payload.get("birthdate")
                gender = payload.get("gender")
                temp_name = payload.get("temp_name")
            except JWTError:
                raise HTTPException(status_code=401, detail="Register token expired or invalid")
        
            # 1. 신규 유저 생성
            new_user = User(
                username=str(kakao_id), # 카카오 고유 ID를 username으로 사용
                name=temp_name,
                kakao_id=kakao_id,
                student_id=student_id,
                nickname=nickname, # 사용자가 직접 입력한 닉네임
                phone_number=phone_number,
                birthdate=birthdate,
                gender=gender
            )    
    user = await user_repo.create(db, new_user)
    return await _issue_service_tokens(db, user)

async def signup(db: AsyncSession, user_data: UserCreate) -> User:
    existing_user = await user_repo.get_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    new_user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        name=user_data.name
    )
    return await user_repo.create(db, new_user)

async def login(db: AsyncSession, username: str, password: str) -> tuple[Token, str]:
    """로그인 시 AT와 RT(평문)를 반환하며, DB에는 RT 해시를 저장합니다."""
    user = await user_repo.get_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 토큰 생성
    at = create_access_token(data={"sub": user.username})
    rt = create_refresh_token()
    
    # RT 정보 업데이트 (DB) - 한국 시간 기준의 Naive datetime 사용
    now_kst = datetime.datetime.now(KST).replace(tzinfo=None)
    user.refresh_token_hash = hash_refresh_token(rt)
    user.refresh_token_expires_at = now_kst + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    await db.commit()
    
    return Token(access_token=at, token_type="bearer"), rt

async def refresh_access_token(db: AsyncSession, refresh_token: str) -> tuple[Token, str]:
    """RT를 검증하고 새로운 AT와 RT를 발급합니다 (Rotation)."""
    rt_hash = hash_refresh_token(refresh_token)
    
    # 해시로 유저 조회
    user = await user_repo.get_by_rt_hash(db, rt_hash)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    # 만료 체크 (한국 시간 기준의 Naive 시각끼리 비교)
    now_kst = datetime.datetime.now(KST).replace(tzinfo=None)
    if user.refresh_token_expires_at < now_kst:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    
    # 새로운 토큰 발급 (Rotation)
    new_at = create_access_token(data={"sub": user.username})
    new_rt = create_refresh_token()
    
    user.refresh_token_hash = hash_refresh_token(new_rt)
    user.refresh_token_expires_at = now_kst + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    await db.commit()
    
    return Token(access_token=new_at, token_type="bearer"), new_rt

async def logout(db: AsyncSession, user: User):
    """DB에서 RT 정보를 삭제하여 무효화합니다."""
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None
    await db.commit()

async def withdraw_user(db: AsyncSession, user: User, kakao_access_token: str | None = None):
    """
    회원 탈퇴: 카카오 연결 끊기(Admin Key 사용) 성공 후 DB 삭제
    """
    # 1. 카카오 연동 유저인 경우 처리
    if user.kakao_id:
        if not KAKAO_ADMIN_KEY:
            raise HTTPException(status_code=500, detail="KAKAO_ADMIN_KEY is not configured in .env")
            
        async with httpx.AsyncClient() as client:
            unlink_url = "https://kapi.kakao.com/v1/user/unlink"
            # Admin Key 방식은 'KakaoAK ' 접두사를 사용합니다.
            headers = {
                "Authorization": f"KakaoAK {KAKAO_ADMIN_KEY}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            # target_id로 탈퇴 대상을 지정 (JWT에서 나온 현재 유저의 kakao_id만 사용)
            data = {
                "target_id_type": "user_id",
                "target_id": user.kakao_id
            }
            
            res = await client.post(unlink_url, headers=headers, data=data)
            
            # 카카오 서버 응답 확인
            if res.status_code != 200:
                error_detail = res.json().get("msg", "Unknown error")
                raise HTTPException(status_code=400, detail=f"Kakao Unlink Error: {error_detail}")

    # 2. DB 삭제 진행
    await user_repo.delete(db, user)
