"""文档 API - 上传与管理"""

from __future__ import annotations

import os
import uuid
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, async_session_factory
from app.core.security import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentResponse, DocumentChunkResponse
from app.services.document_parser import DocumentParser
from app.services.chunker import TextChunker
from app.services.embedder import Embedder
from loguru import logger
from app.services.document_queue import enqueue_document, get_document_task_status
from app.services.redis_client import invalidate_cache

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
        .where(Document.course_id == course_id, Document.user_id == current_user.id)
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

    file_size = 0
    with save_path.open("wb") as destination:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > settings.MAX_UPLOAD_SIZE:
                destination.close()
                save_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File size exceeds upload limit")
            await asyncio.to_thread(destination.write, chunk)
    # 创建记录
    doc = Document(
        course_id=course_id,
        title=title,
        file_type=file_type,
        file_path=str(save_path),
        file_size=file_size,
        status="pending",
        user_id=current_user.id,
    )
    db.add(doc)
    await db.flush()
    await db.commit()
    await db.refresh(doc)

    # 后台处理：解析 → 切片 → 向量化
    try:
        await enqueue_document(doc.id)
    except Exception as exc:
        doc.status = "error"
        await db.commit()
        logger.exception(f"Failed to enqueue document #{doc.id}: {exc}")
        raise HTTPException(status_code=503, detail="Document processing queue is unavailable")

    return DocumentResponse.model_validate(doc)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档详情"""
    query = select(Document).where(Document.id == doc_id)
    if not current_user.is_admin:
        query = query.where(Document.user_id == current_user.id)
    result = await db.execute(query)
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
    query = select(DocumentChunk).join(Document).where(DocumentChunk.document_id == doc_id)
    if not current_user.is_admin:
        query = query.where(Document.user_id == current_user.id)
    result = await db.execute(query.order_by(DocumentChunk.chunk_index))
    chunks = result.scalars().all()
    return [DocumentChunkResponse.model_validate(c) for c in chunks]


@router.get("/{doc_id}/task", response_model=dict)
async def get_document_task(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Document).where(Document.id == doc_id)
    if not current_user.is_admin:
        query = query.where(Document.user_id == current_user.id)
    if (await db.execute(query)).scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return await get_document_task_status(doc_id)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档"""
    query = select(Document).where(Document.id == doc_id)
    if not current_user.is_admin:
        query = query.where(Document.user_id == current_user.id)
    result = await db.execute(query)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除物理文件
    file_path = Path(doc.file_path)
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
    await db.commit()
    await invalidate_cache("retrieval:*")


async def process_document(doc_id: int):
    """后台处理文档：解析 → 切片 → 向量化"""
    logger.info(f"开始处理文档 #{doc_id}")
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if not doc:
                logger.error(f"文档 #{doc_id} 不存在")
                raise FileNotFoundError(f"Document #{doc_id} does not exist")

            # 更新状态为处理中
            doc.status = "processing"
            await db.flush()

            # 1. 解析文档
            logger.info(f"解析文档: {doc.file_path}")
            text = await DocumentParser.parse(doc.file_path, doc.file_type)
            doc.content = text

            # 2. 切片
            chunker = TextChunker(
                chunk_size=settings.MAX_CHUNK_SIZE,
                overlap=max(1, settings.MAX_CHUNK_SIZE // 10),
            )
            chunks_data = chunker.chunk(text, metadata={"document_id": doc.id, "course_id": doc.course_id})
            logger.info(f"文档 #{doc_id} 切分为 {len(chunks_data)} 个切片")

            if not chunks_data:
                doc.status = "ready"
                await db.commit()
                await invalidate_cache("retrieval:*")
                logger.info(f"文档 #{doc_id} 处理完成（无内容）")
                return

            # 3. 向量化（批量）
            embedder = Embedder()
            texts = [c["content"] for c in chunks_data]
            embeddings = []
            batch_size = settings.DOCUMENT_EMBED_BATCH_SIZE
            for start in range(0, len(texts), batch_size):
                embeddings.extend(await embedder.embed_batch(texts[start : start + batch_size]))

            # 4. 保存切片
            for i, chunk_data in enumerate(chunks_data):
                chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk_data["chunk_index"],
                    content=chunk_data["content"],
                    embedding=embeddings[i] if i < len(embeddings) else None,
                    chunk_metadata={
                        "document_id": doc.id,
                        "course_id": doc.course_id,
                        "chunk_index": chunk_data["chunk_index"],
                    },
                )
                db.add(chunk)

            doc.status = "ready"
            await db.commit()
            await invalidate_cache("retrieval:*")
            logger.info(f"文档 #{doc_id} 处理完成，生成 {len(chunks_data)} 个切片")

    except Exception as e:
        logger.error(f"文档 #{doc_id} 处理失败: {e}")
        try:
            async with async_session_factory() as db:
                result = await db.execute(select(Document).where(Document.id == doc_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "error"
                    await db.commit()
        except Exception as e:
            logger.warning(f"文档处理错误状态保存失败: {e}")
        raise
