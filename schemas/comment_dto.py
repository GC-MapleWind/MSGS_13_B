import datetime
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str
    nickname: str | None = Field(default=None, min_length=2, max_length=10, pattern=r"^[a-zA-Z0-9가-힣]+$")


class CommentResponse(BaseModel):
    id: int
    user_id: int | None
    author: str
    content: str
    created_at: datetime.datetime
    is_mine: bool = False

    model_config = {"from_attributes": True}
