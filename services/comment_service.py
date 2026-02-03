from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment
from repositories import comment_repo
from schemas.comment_dto import CommentCreate


async def get_comments(db: AsyncSession, page: int = 1, limit: int = 20) -> list[Comment]:
    skip = (page - 1) * limit
    return await comment_repo.get_all(db, skip=skip, limit=limit)


async def create_comment(db: AsyncSession, data: CommentCreate) -> Comment:
    comment = Comment(
        author=data.author,
        content=data.content,
        password=data.password,
    )
    return await comment_repo.create(db, comment)
