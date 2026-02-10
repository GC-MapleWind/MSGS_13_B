import datetime
import os
import secrets
import hashlib
from fastapi import HTTPException, status
from jose import jwt
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

def create_refresh_token() -> str:
    """안전한 랜덤 문자열 RT 생성"""
    return secrets.token_urlsafe(32)

# --- 서비스 로직 ---

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
