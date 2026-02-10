import datetime
from pydantic import BaseModel

class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    user_id: int
    author: str
    content: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True