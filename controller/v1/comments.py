from fastapi import APIRouter, Body, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from controller.dependencies import get_db, get_current_user_optional
from models.user import User
from schemas.comment_dto import CommentCreate, CommentDeleteRequest, CommentResponse
from services import comment_service

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("", response_model=list[CommentResponse])
async def get_comments(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    return await comment_service.get_comments(db, page=page, limit=limit, current_user=current_user)


@router.post("", response_model=CommentResponse, status_code=201)
async def create_comment(
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    created = await comment_service.create_comment(db, data, current_user)
    return CommentResponse.model_validate(created.comment, from_attributes=True).model_copy(
        update={
            "is_mine": bool(current_user and created.comment.user_id == current_user.id),
            "is_anonymous": created.comment.user_id is None,
            "delete_token": created.delete_token,
        }
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    payload: CommentDeleteRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    request: Request = None,
):
    forwarded_for = request.headers.get("x-forwarded-for") if request else None
    client_host = (request.client.host if request and request.client else None) or "unknown"
    client_key = (forwarded_for.split(",", 1)[0].strip() if forwarded_for else client_host) or "unknown"

    await comment_service.delete_comment(
        db,
        comment_id,
        current_user,
        payload,
        client_key=client_key,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
