import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, Text, Integer, JSON, func
from src.database_chatbot import ChatbotBase

class InfoList(ChatbotBase):
    """
    질문 항목 및 순서를 정의하는 테이블
    """
    __tablename__ = "infolist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    step_order: Mapped[int] = mapped_column(Integer, unique=True) # 질문 순서 (1, 2, 3...)
    field_name: Mapped[str] = mapped_column(String, unique=True) # 저장될 필드명 (name, student_id...)
    question_text: Mapped[str] = mapped_column(String)           # 사용자에게 던질 질문
    event_name: Mapped[str | None] = mapped_column(String, nullable=True) # 이벤트 이름

class EventInfo(ChatbotBase):
    """
    이벤트 정보를 저장하는 테이블
    """
    __tablename__ = "eventinfo"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    start_day: Mapped[str] = mapped_column(String)
    end_day: Mapped[str] = mapped_column(String)

class TemporaryImage(ChatbotBase):
    """
    카카오 챗봇 등록 과정에서의 임시 세션 데이터
    """
    __tablename__ = "temporary_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_key: Mapped[str] = mapped_column(unique=True, index=True) # 사용자 고유 키
    
    # 동적 데이터 저장 (이름, 학번, 한마디 등을 JSON으로 저장)
    data: Mapped[dict | None] = mapped_column(JSON, default=dict, server_default='{}')
    
    # 이미지 목록
    image_urls: Mapped[str | None] = mapped_column(Text, nullable=True, default="")


class SubmitterProfile(ChatbotBase):
    """
    친바방 제출자 프로필 - 카카오 user_key 기반 최초 1회 저장 후 자동 불러오기
    """
    __tablename__ = "submitter_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    student_id: Mapped[str] = mapped_column(String)


class ActivitySubmission(ChatbotBase):
    """
    친바방 제출 내역
    """
    __tablename__ = "activity_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_key: Mapped[str] = mapped_column(String, index=True)
    submitter_name: Mapped[str] = mapped_column(String)
    submitter_student_id: Mapped[str] = mapped_column(String)
    photo_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_date: Mapped[str] = mapped_column(String)
    activity_type: Mapped[str] = mapped_column(String)
    newbie_count: Mapped[int] = mapped_column(Integer, default=0)
    existing_count: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
