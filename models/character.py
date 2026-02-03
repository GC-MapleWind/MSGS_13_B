from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    detail_txt: Mapped[str | None] = mapped_column(String, nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    job: Mapped[str] = mapped_column(String, nullable=False)
    server: Mapped[str] = mapped_column(String, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)

    settlements = relationship("Settlement", back_populates="character", cascade="all, delete-orphan")
