import datetime
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str
    nickname: str | None = Field(
        default=None, min_length=2, max_length=10, pattern=r"^[a-zA-Z0-9가-힣]+$"
    )
    password: str | None = Field(default=None, min_length=4, max_length=20)


class CommentDeleteRequest(BaseModel):
    password: str | None = Field(default=None, min_length=4, max_length=20)


class CommentResponse(BaseModel):
    id: int
    user_id: int | None
    author: str
    content: str
    is_anonymous: bool = False
    created_at: datetime.datetime
    is_mine: bool = False

    model_config = {"from_attributes": True}
