"""文档 API - 上传与管理"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentResponse, DocumentChunkResponse

router = APIRouter()

ALLOWED_TYPES = {"pdf": ".pdf", "docx": ".docx", "pptx": ".pptx", "md": ".md", "txt": ".txt"}


@router.get("/course/{course_id}", response_model=list[DocumentResponse])
async def list_documents(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程的文档列表"""
    result = await db.execute(
        select(Document)
        .where(Document.course_id == course_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    course_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档"""
    # 验证文件类型
    ext = Path(file.filename or "").suffix.lower()
    file_type = None
    for ft, fext in ALLOWED_TYPES.items():
        if ext == fext:
            file_type = ft
            break
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，支持: {', '.join(ALLOWED_TYPES.keys())}",
        )

    # 保存文件
    upload_dir = settings.upload_dir_path / str(course_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())[:8]
    save_name = f"{file_id}_{file.filename}"
    save_path = upload_dir / save_name

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制（50MB）")

    save_path.write_bytes(content)

    # 创建记录
    doc = Document(
        course_id=course_id,
        title=title,
        file_type=file_type,
        file_path=str(save_path),
        file_size=len(content),
        status="pending",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档详情"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return DocumentResponse.model_validate(doc)


@router.get("/{doc_id}/chunks", response_model=list[DocumentChunkResponse])
async def get_document_chunks(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档切片"""
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return [DocumentChunkResponse.model_validate(c) for c in chunks]


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除物理文件
    file_path = Path(doc.file_path)
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
