"""文档 Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DocumentCreate(BaseModel):
    course_id: int
    title: str = Field(..., max_length=200)
    file_type: str = Field(..., pattern=r"^(pdf|docx|pptx|md|txt)$")


class DocumentResponse(BaseModel):
    id: int
    course_id: int
    title: str
    file_type: str
    file_path: str
    file_size: int
    page_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    metadata: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
