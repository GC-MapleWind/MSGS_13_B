import datetime
from pydantic import BaseModel, Field, field_validator


class CommentCreate(BaseModel):
    content: str
    nickname: str | None = Field(
        default=None, min_length=2, max_length=10, pattern=r"^[a-zA-Z0-9가-힣]+$"
    )
    password: str | None = Field(default=None, min_length=4, max_length=20)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("내용은 비워둘 수 없습니다.")
        return stripped

    @field_validator("nickname", "password", mode="before")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


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
