from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)   # 실명
    detail_txt: Mapped[str | None] = mapped_column(String, nullable=True)    # 닉네임
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    job: Mapped[str] = mapped_column(String, nullable=False)
    server: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)

    user = relationship("User", back_populates="characters")
    settlements = relationship(
        "Settlement", back_populates="character", cascade="all, delete-orphan"
    )
