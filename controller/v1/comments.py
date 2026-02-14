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
    새 댓글을 생성하고 생성된 댓글을 반환합니다.
    
    Parameters:
        data (CommentCreate): 생성할 댓글의 내용과 관련 메타데이터.
        current_user (User): 댓글 작성자(현재 인증된 사용자).
    
    Returns:
        CommentResponse: 생성된 댓글 객체.
    """
    return await comment_service.create_comment(db, data, current_user)