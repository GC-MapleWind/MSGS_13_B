from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, JSON
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
