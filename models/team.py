from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    profile_img_url: Mapped[str] = mapped_column(String, nullable=True)
    
    # Relationship to detailed message
    message: Mapped["TeamMessage"] = relationship("TeamMessage", back_populates="member", uselist=False)

class TeamMessage(Base):
    __tablename__ = "team_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("team_members.id"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    detail_img_url: Mapped[str] = mapped_column(String, nullable=True)

    # Relationship back to member
    member: Mapped["TeamMember"] = relationship("TeamMember", back_populates="message")
