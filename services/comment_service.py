from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment
from models.user import User
from repositories import comment_repo
from schemas.comment_dto import CommentCreate


async def get_comments(db: AsyncSession, page: int = 1, limit: int = 20) -> list[Comment]:
    skip = (page - 1) * limit
    return await comment_repo.get_all(db, skip=skip, limit=limit)


async def create_comment(db: AsyncSession, data: CommentCreate, user: User) -> Comment:
    comment = Comment(
        user_id=user.id,
        author=user.name,  # 로그인한 유저의 이름을 작성자로 자동 설정
        content=data.content,
    )
    return await comment_repo.create(db, comment)