"""瀛︿範琛屼负鏃ュ織妯″瀷"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearningBehavior(Base):
    __tablename__ = "learning_behaviors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    behavior_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 鍏宠仈
    user = relationship("User", back_populates="learning_behaviors")

    def __repr__(self) -> str:
        return f"<LearningBehavior(id={self.id}, user={self.user_id}, action={self.action_type})>"
