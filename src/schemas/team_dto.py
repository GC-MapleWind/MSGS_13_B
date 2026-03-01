from pydantic import BaseModel


class TeamMessageBase(BaseModel):
    title: str
    content: str
    detail_img_url: str | None = None


class TeamMessageResponse(TeamMessageBase):
    id: int
    model_config = {"from_attributes": True}


class TeamMemberBase(BaseModel):
    name: str
    role: str
    profile_img_url: str | None = None


class TeamMemberResponse(TeamMemberBase):
    id: int
    model_config = {"from_attributes": True}


class TeamMemberDetailResponse(TeamMemberResponse):
    message: TeamMessageResponse | None = None
