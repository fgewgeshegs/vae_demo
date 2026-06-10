"""评估报告模型"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import ARRAY, ForeignKey, Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    suggestions: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=list)
    strategy_signals: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    report_data: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 关联
    user = relationship("User", back_populates="evaluations")

    def __repr__(self) -> str:
        return f"<Evaluation(id={self.id}, user={self.user_id})>"
