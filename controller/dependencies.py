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
    raise ValueError("FATAL: JWT_SECRET_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    현재 요청의 JWT 액세스 토큰을 검증하고 토큰에 명시된 사용자명에 대응하는 User 객체를 반환합니다.
    
    검증 실패나 토큰 만료 시 401 Unauthorized HTTPException을 발생시킵니다. 토큰 만료인 경우 detail은 "Token has expired"이고, 그 외 인증 실패(토큰 무효, 페이로드에 사용자명 없음, 데이터베이스에 사용자 미발견 포함)인 경우 detail은 "Could not validate credentials"입니다.
    
    Returns:
        User: 토큰의 "sub" 클레임에 대응하는 사용자 엔터티
    
    Raises:
        HTTPException: 인증 실패 또는 토큰 만료로 인해 401 상태 코드를 가진 예외가 발생합니다.
    """
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
        raise expired_exception
    except JWTError:
        raise credentials_exception
        
    user = await user_repo.get_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

__all__ = ["get_db", "get_current_user"]