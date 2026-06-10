"""用户认证模型"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联
    profile = relationship("StudentProfile", back_populates="user", uselist=False, lazy="selectin")
    study_paths = relationship("StudyPath", back_populates="user", lazy="selectin")
    learning_resources = relationship("LearningResource", back_populates="user", lazy="selectin")
    qa_records = relationship("QARecord", back_populates="user", lazy="selectin")
    learning_behaviors = relationship("LearningBehavior", back_populates="user", lazy="selectin")
    evaluations = relationship("Evaluation", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
