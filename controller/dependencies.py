import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from database import get_db
from repositories import user_repo
from models.user import User

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError(
        "FATAL: JWT_SECRET_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요."
    )

ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/users/login", auto_error=False
)


async def _resolve_user_from_token(
    token: str,
    db: AsyncSession,
    *,
    raise_on_error: bool,
) -> User | None:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except ExpiredSignatureError:
        if raise_on_error:
            raise expired_exception
        return None
    except JWTError:
        if raise_on_error:
            raise credentials_exception
        return None

    user = await user_repo.get_by_username(db, username=username)
    if user is None:
        if raise_on_error:
            raise credentials_exception
        return None

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    user = await _resolve_user_from_token(token, db, raise_on_error=True)
    assert user is not None, (
        "_resolve_user_from_token with raise_on_error=True should not return None"
    )
    return user


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not token:
        return None
    return await _resolve_user_from_token(token, db, raise_on_error=False)


__all__ = ["get_db", "get_current_user", "get_current_user_optional"]
