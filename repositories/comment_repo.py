from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment


async def get_all(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> list[Comment]:
    result = await db.execute(
        select(Comment)
        .order_by(Comment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_total_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Comment.id)))
    return result.scalar_one()


async def create(db: AsyncSession, comment: Comment) -> Comment:
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment
