from datetime import date, datetime
from sqlalchemy import String, Integer, DateTime, Date, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # 카카오 연동 및 추가 정보 필드
    kakao_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    student_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)  # male / female
    
    # Refresh Token 보안을 위한 필드 추가
    refresh_token_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
