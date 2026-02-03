import datetime

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    img_url: Mapped[str | None] = mapped_column(String, nullable=True)
    acquired_at: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    character = relationship("Character", back_populates="settlements")
