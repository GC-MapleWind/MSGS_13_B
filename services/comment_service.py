import random

from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment
from models.user import User
from repositories import comment_repo
from schemas.comment_dto import CommentCreate, CommentDeleteRequest, CommentResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ANON_PREFIXES = ["별빛", "단풍", "구름", "노을", "바람", "은하"]
ANON_SUFFIXES = ["토끼", "사슴", "고래", "여우", "펭귄", "호랑이"]


def _random_nickname() -> str:
    return f"{random.choice(ANON_PREFIXES)}{random.choice(ANON_SUFFIXES)}{random.randint(10, 99)}"


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
            update={
                "is_mine": bool(current_user and comment.user_id == current_user.id),
                "is_anonymous": comment.user_id is None,
            }
        )
        for comment in comments
    ]


def _resolve_user_author(user: User) -> str:
    nickname = (user.nickname or "").strip()
    if nickname:
        return nickname

    name = (user.name or "").strip()
    if name:
        return name

    return "익명"


async def create_comment(
    db: AsyncSession,
    data: CommentCreate,
    user: User | None,
) -> Comment:
    if user:
        author = _resolve_user_author(user)
        password_hash = None
    else:
        author = _random_nickname()
        password_hash = pwd_context.hash(data.password) if data.password else None

    comment = Comment(
        user_id=user.id if user else None,
        author=author,
        content=data.content,
        password_hash=password_hash,
    )
    return await comment_repo.create(db, comment)


async def delete_comment(
    db: AsyncSession,
    comment_id: int,
    user: User | None,
    payload: CommentDeleteRequest | None = None,
) -> None:
    comment = await comment_repo.get_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")

    if comment.user_id is not None:
        if user is None:
            raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
        if comment.user_id != user.id:
            raise HTTPException(
                status_code=403, detail="본인 댓글만 삭제할 수 있습니다."
            )
        await comment_repo.delete(db, comment)
        return

    if comment.password_hash:
        password = (payload.password if payload else None) or ""
        if not password:
            raise HTTPException(status_code=400, detail="비밀번호를 입력해주세요.")

        if not pwd_context.verify(password, comment.password_hash):
            raise HTTPException(status_code=403, detail="비밀번호가 올바르지 않습니다.")

    await comment_repo.delete(db, comment)
