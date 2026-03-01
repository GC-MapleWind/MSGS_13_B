import datetime

from pydantic import BaseModel


class SettlementBase(BaseModel):
    title: str
    description: str | None = None
    img_url: str | None = None
    acquired_at: datetime.date


class SettlementResponse(SettlementBase):
    id: int
    character_id: int

    model_config = {"from_attributes": True}


class SettlementDetailResponse(SettlementResponse):
    pass
