from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User

async def create(db: AsyncSession, user: User) -> User:
    """
    새 User 인스턴스를 데이터베이스에 저장하고, 커밋 후 최신 상태로 갱신합니다.
    
    Parameters:
        user (User): 저장할 User 엔티티 인스턴스.
    
    Returns:
        User: 데이터베이스에 커밋되고 refresh 되어 최신 상태인 User 객체.
    """
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_by_username(db: AsyncSession, username: str) -> User | None:
    """
    주어진 사용자 이름으로 일치하는 사용자 레코드를 조회합니다.
    
    Returns:
        `User` 인스턴스 또는 일치하는 사용자가 없으면 `None`.
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_by_kakao_id(db: AsyncSession, kakao_id: int) -> User | None:
    """
    카카오 ID로 데이터베이스에서 사용자 엔티티를 조회한다.
    
    Parameters:
        kakao_id (int): 카카오 플랫폼에서 발급된 사용자 식별자.
    
    Returns:
        `User` 인스턴스 조회 결과, 없으면 `None`.
    """
    result = await db.execute(select(User).where(User.kakao_id == kakao_id))
    return result.scalar_one_or_none()

async def get_by_phone_number(db: AsyncSession, phone_number: str) -> User | None:
    """
    전화번호로 데이터베이스에서 사용자 엔티티를 조회한다.
    
    Parameters:
        phone_number (str): 조회할 전화번호
    
    Returns:
        `User` 인스턴스이면 해당 사용자, 없으면 `None`.
    """
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one_or_none()

async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    """
    주어진 ID에 해당하는 사용자 엔티티를 조회합니다.
    
    Returns:
        User 또는 None: 일치하는 사용자가 있으면 해당 `User` 인스턴스를 반환하고, 없으면 `None`을 반환합니다.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_by_rt_hash(db: AsyncSession, rt_hash: str) -> User | None:
    """
    리프레시 토큰의 해시값으로 사용자(User)를 조회합니다.
    
    Parameters:
        rt_hash (str): 검증에 사용할 리프레시 토큰의 해시값.
    
    Returns:
        User | None: 일치하는 `User` 인스턴스를 반환하며, 없으면 `None`을 반환합니다.
    """
    result = await db.execute(select(User).where(User.refresh_token_hash == rt_hash))
    return result.scalar_one_or_none()

async def delete(db: AsyncSession, user: User) -> None:
    """유저 정보를 DB에서 삭제합니다."""
    await db.delete(user)
    await db.commit()