import datetime
from pydantic import BaseModel, field_validator

# 한국 시간(KST) 설정
KST = datetime.timezone(datetime.timedelta(hours=9))

class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    user_id: int | None
    author: str
    content: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}

    @field_validator("created_at")
    @classmethod
    def convert_to_kst(cls, v: datetime.datetime) -> datetime.datetime:
        """UTC로 저장된 시간을 응답 시 KST로 변환합니다."""
        if v.tzinfo is None:
            # DB에서 가져온 시간이 타임존 정보가 없다면 UTC로 가정
            v = v.replace(tzinfo=datetime.timezone.utc)
        # 한국 시간으로 변환하여 반환
        return v.astimezone(KST)