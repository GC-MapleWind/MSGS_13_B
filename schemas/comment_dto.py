import datetime

from pydantic import BaseModel


class CommentCreate(BaseModel):
    author: str
    content: str
    password: str | None = None


class CommentResponse(BaseModel):
    id: int
    author: str
    content: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
