import datetime
import os
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
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def signup(db: AsyncSession, user_data: UserCreate) -> User:
    # 중복 체크
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

async def login(db: AsyncSession, username: str, password: str) -> Token:
    user = await user_repo.get_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")
