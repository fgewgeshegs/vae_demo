"""Knowledge-base search APIs."""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.document import DocumentChunkResponse
from app.services.retriever import Retriever

router = APIRouter()


@router.get("/local", response_model=dict)
async def local_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """Search the legacy local FAISS knowledge base."""
    from app.services.local_knowledge_base import get_local_knowledge_base

    results = await asyncio.to_thread(get_local_knowledge_base().search, q, limit)
    return {
        "query": q,
        "total": len(results),
        "results": results,
        "method": "legacy_local_hybrid",
    }


@router.get("/", response_model=dict)
async def semantic_search(
    q: str = Query(..., min_length=1),
    course_id: int | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Keyword search retained for diagnostics."""
    query = (
        select(DocumentChunk)
        .join(Document)
        .where(DocumentChunk.content.ilike(f"%{q}%"), Document.user_id == current_user.id)
    )
    if course_id:
        query = query.where(Document.course_id == course_id)
    chunks = (await db.execute(query.limit(limit))).scalars().all()
    return {
        "query": q,
        "total": len(chunks),
        "results": [DocumentChunkResponse.model_validate(c).model_dump() for c in chunks],
        "method": "keyword",
    }


@router.get("/vector", response_model=dict)
async def vector_search(
    q: str = Query(..., min_length=1),
    course_id: int | None = Query(None),
    limit: int = Query(5, ge=1, le=5),
    current_user: User = Depends(get_current_user),
):
    """BGE-M3 pgvector Top 20 followed by BGE reranker Top 5."""
    results = await Retriever().retrieve(
        q, course_id=course_id, limit=limit, user_id=current_user.id
    )
    return {
        "query": q,
        "total": len(results),
        "results": results,
        "method": "bge_m3_pgvector_bge_reranker",
        "vector_search": True,
    }
