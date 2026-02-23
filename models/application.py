import datetime
import enum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ApplicationType(str, enum.Enum):
    NEW = "NEW"
    RENEW = "RENEW"


class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"


class GenderType(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class AcademicStatusType(str, enum.Enum):
    UNDERGRAD = "UNDERGRAD"
    GRADUATE = "GRADUATE"
    LEAVE_GENERAL = "LEAVE_GENERAL"
    LEAVE_MILITARY = "LEAVE_MILITARY"
    ALUMNI = "ALUMNI"
    STAFF = "STAFF"


class InterviewDateOption(str, enum.Enum):
    SAT_0913 = "SAT_0913"
    SUN_0914 = "SUN_0914"
    OTHER = "OTHER"


class OpeningPartyIntent(str, enum.Enum):
    ATTEND = "ATTEND"
    ABSENT = "ABSENT"
    FLEXIBLE = "FLEXIBLE"


class MilitaryMemberOption(str, enum.Enum):
    APPLY = "APPLY"
    NOT_APPLY = "NOT_APPLY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    student_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    department: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    gender: Mapped[GenderType] = mapped_column(Enum(GenderType), nullable=False)
    academic_status: Mapped[AcademicStatusType] = mapped_column(Enum(AcademicStatusType), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("member_id", "term", "application_type", name="uq_member_term_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    term: Mapped[str] = mapped_column(String, nullable=False, index=True)
    application_type: Mapped[ApplicationType] = mapped_column(Enum(ApplicationType), nullable=False, index=True)
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.SUBMITTED)

    # game profile
    nickname: Mapped[str] = mapped_column(String, nullable=False)
    job: Mapped[str] = mapped_column(String, nullable=False)
    world: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    union_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # common consent/intent
    rule_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    opening_party_intent: Mapped[OpeningPartyIntent] = mapped_column(Enum(OpeningPartyIntent), nullable=False)

    # new only
    interview_date_option: Mapped[InterviewDateOption | None] = mapped_column(Enum(InterviewDateOption), nullable=True)
    student_card_confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    privacy_agreed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # renew only
    military_member_option: Mapped[MilitaryMemberOption | None] = mapped_column(Enum(MilitaryMemberOption), nullable=True)
    free_chat_participation: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    alliance_chat_participation: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fee_notice_ack: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason_for_reregistration: Mapped[str | None] = mapped_column(Text, nullable=True)
    desired_event_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
