from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment
from models.user import User
from repositories import comment_repo
from schemas.comment_dto import CommentCreate, CommentResponse


async def get_comments(
    db: AsyncSession,
    page: int = 1,
    limit: int = 20,
    current_user: User | None = None,
) -> list[CommentResponse]:
    skip = (page - 1) * limit
    comments = await comment_repo.get_all(db, skip=skip, limit=limit)

    return [
        CommentResponse.model_validate(comment, from_attributes=True).model_copy(
            update={"is_mine": bool(current_user and comment.user_id == current_user.id)}
        )
        for comment in comments
    ]


async def create_comment(
    db: AsyncSession,
    data: CommentCreate,
    user: User | None,
) -> Comment:
    author = user.name if user else (data.nickname or "").strip()
    if not user and not author:
        raise HTTPException(status_code=400, detail="비로그인 댓글 작성 시 닉네임이 필요합니다.")

    comment = Comment(
        user_id=user.id if user else None,
        author=author,
        content=data.content,
    )
    return await comment_repo.create(db, comment)


async def delete_comment(db: AsyncSession, comment_id: int, user: User) -> None:
    comment = await comment_repo.get_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")

    if comment.user_id is None:
        raise HTTPException(status_code=403, detail="비로그인 댓글은 삭제할 수 없습니다.")

    if comment.user_id != user.id:
        raise HTTPException(status_code=403, detail="본인 댓글만 삭제할 수 있습니다.")

    await comment_repo.delete(db, comment)
