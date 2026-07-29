"""闂瓟璁板綍妯″瀷"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import ARRAY, ForeignKey, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class QARecord(Base):
    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    resource_ids: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), default=list)
    qa_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 鍏宠仈
    user = relationship("User", back_populates="qa_records")

    def __repr__(self) -> str:
        return f"<QARecord(id={self.id}, user={self.user_id})>"
