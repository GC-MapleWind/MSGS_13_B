from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User

async def create(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_by_kakao_id(db: AsyncSession, kakao_id: int) -> User | None:
    result = await db.execute(select(User).where(User.kakao_id == kakao_id))
    return result.scalar_one_or_none()

async def get_by_phone_number(db: AsyncSession, phone_number: str) -> User | None:
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one_or_none()

async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_by_rt_hash(db: AsyncSession, rt_hash: str) -> User | None:
    """RT 해시값으로 유저를 조회합니다 (Refresh Token 검증용)."""
    result = await db.execute(select(User).where(User.refresh_token_hash == rt_hash))
    return result.scalar_one_or_none()

async def delete(db: AsyncSession, user: User) -> None:
    """유저 정보를 DB에서 삭제합니다."""
    await db.delete(user)
    await db.commit()
