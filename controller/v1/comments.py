from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db, get_current_user
from models.user import User
from schemas.comment_dto import CommentCreate, CommentResponse
from services import comment_service

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("", response_model=list[CommentResponse])
async def get_comments(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await comment_service.get_comments(db, page=page, limit=limit)


@router.post("", response_model=CommentResponse, status_code=201)
async def create_comment(
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    댓글 작성 (로그인 필수)
    """
    return await comment_service.create_comment(db, data, current_user)