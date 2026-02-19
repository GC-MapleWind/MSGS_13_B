import random
import secrets
import time
from dataclasses import dataclass

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

PAGE_LIMIT_MAX = 100
PAGE_LIMIT_DEFAULT = 20

ANON_DELETE_MAX_ATTEMPTS = 5
ANON_DELETE_WINDOW_SECONDS = 60
_anon_delete_attempts: dict[str, list[float]] = {}


@dataclass(slots=True)
class CreateCommentResult:
    comment: Comment
    delete_token: str | None = None


def _random_nickname() -> str:
    return f"{random.choice(ANON_PREFIXES)}{random.choice(ANON_SUFFIXES)}{random.randint(10, 99)}"


async def get_comments(
    db: AsyncSession,
    page: int = 1,
    limit: int = PAGE_LIMIT_DEFAULT,
    current_user: User | None = None,
) -> list[CommentResponse]:
    page = max(1, page)
    limit = max(1, min(limit, PAGE_LIMIT_MAX))
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


def _purge_old_attempts(now: float, attempts: list[float]) -> list[float]:
    return [ts for ts in attempts if now - ts < ANON_DELETE_WINDOW_SECONDS]


def _assert_anon_delete_not_rate_limited(client_key: str, comment_id: int) -> None:
    key = f"{client_key}:{comment_id}"
    now = time.monotonic()
    attempts = _purge_old_attempts(now, _anon_delete_attempts.get(key, []))
    _anon_delete_attempts[key] = attempts
    if len(attempts) >= ANON_DELETE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
        )


def _record_anon_delete_failure(client_key: str, comment_id: int) -> None:
    key = f"{client_key}:{comment_id}"
    now = time.monotonic()
    attempts = _purge_old_attempts(now, _anon_delete_attempts.get(key, []))
    attempts.append(now)
    _anon_delete_attempts[key] = attempts


def _clear_anon_delete_failures(client_key: str, comment_id: int) -> None:
    _anon_delete_attempts.pop(f"{client_key}:{comment_id}", None)


async def create_comment(
    db: AsyncSession,
    data: CommentCreate,
    user: User | None,
) -> CreateCommentResult:
    delete_token: str | None = None

    if user:
        author = _resolve_user_author(user)
        password_hash = None
    else:
        author = _random_nickname()
        delete_token = data.password or secrets.token_urlsafe(16)
        password_hash = pwd_context.hash(delete_token)

    comment = Comment(
        user_id=user.id if user else None,
        author=author,
        content=data.content,
        password_hash=password_hash,
    )
    created = await comment_repo.create(db, comment)
    return CreateCommentResult(comment=created, delete_token=delete_token)


async def delete_comment(
    db: AsyncSession,
    comment_id: int,
    user: User | None,
    payload: CommentDeleteRequest | None = None,
    client_key: str = "anonymous",
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

    if not comment.password_hash:
        raise HTTPException(status_code=403, detail="삭제할 수 없는 댓글입니다.")

    _assert_anon_delete_not_rate_limited(client_key, comment_id)

    password = (payload.password if payload else None) or ""
    if not password:
        _record_anon_delete_failure(client_key, comment_id)
        raise HTTPException(status_code=400, detail="비밀번호를 입력해주세요.")

    if not pwd_context.verify(password, comment.password_hash):
        _record_anon_delete_failure(client_key, comment_id)
        raise HTTPException(status_code=403, detail="비밀번호가 올바르지 않습니다.")

    _clear_anon_delete_failures(client_key, comment_id)
    await comment_repo.delete(db, comment)
