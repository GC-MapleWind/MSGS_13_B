import datetime

from pydantic import BaseModel, Field

from models.application import (
    AcademicStatusType,
    ApplicationStatus,
    ApplicationType,
    GenderType,
    InterviewDateOption,
    MilitaryMemberOption,
    OpeningPartyIntent,
)


STUDENT_ID_REGEX = r"^\d{9}$"
PHONE_REGEX = r"^01\d{8,9}$"


class MemberBase(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    student_id: str = Field(pattern=STUDENT_ID_REGEX)
    department: str = Field(min_length=1, max_length=100)
    phone_number: str = Field(pattern=PHONE_REGEX)
    gender: GenderType
    academic_status: AcademicStatusType


class ApplicationBase(BaseModel):
    term: str = Field(min_length=3, max_length=20)
    nickname: str = Field(min_length=1, max_length=30)
    job: str = Field(min_length=1, max_length=50)
    world: str = Field(min_length=1, max_length=30)
    level: int = Field(ge=1, le=400)
    union_level: int = Field(ge=0, le=20000)
    rule_agreed: bool
    opening_party_intent: OpeningPartyIntent


class NewApplicationCreate(MemberBase, ApplicationBase):
    interview_date_option: InterviewDateOption
    student_card_confirmed: bool
    privacy_agreed: bool


class RenewApplicationCreate(MemberBase, ApplicationBase):
    military_member_option: MilitaryMemberOption
    free_chat_participation: bool
    alliance_chat_participation: bool
    fee_notice_ack: bool
    reason_for_reregistration: str = Field(min_length=1, max_length=2000)
    desired_event_style: str | None = Field(default=None, max_length=2000)
    suggestions: str = Field(min_length=1, max_length=2000)


class ApplicationResponse(BaseModel):
    id: int
    application_type: ApplicationType
    status: ApplicationStatus
    term: str
    nickname: str
    job: str
    world: str
    level: int
    union_level: int
    submitted_at: datetime.datetime

    model_config = {"from_attributes": True}


class NewApplicationDetailResponse(BaseModel):
    interview_date_option: InterviewDateOption | None = None
    student_card_confirmed: bool | None = None
    privacy_agreed: bool | None = None


class RenewApplicationDetailResponse(BaseModel):
    military_member_option: MilitaryMemberOption | None = None
    free_chat_participation: bool | None = None
    alliance_chat_participation: bool | None = None
    fee_notice_ack: bool | None = None
    reason_for_reregistration: str | None = None
    desired_event_style: str | None = None
    suggestions: str | None = None


class MyApplicationResponse(BaseModel):
    member: MemberBase
    application: ApplicationResponse
    new_detail: NewApplicationDetailResponse | None = None
    renew_detail: RenewApplicationDetailResponse | None = None
