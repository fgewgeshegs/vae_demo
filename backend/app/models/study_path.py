"""学习路径模型"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, Float, ForeignKey, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StudyPath(Base):
    __tablename__ = "study_paths"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    path_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联
    user = relationship("User", back_populates="study_paths")

    def __repr__(self) -> str:
        return f"<StudyPath(id={self.id}, user={self.user_id}, progress={self.progress})>"
