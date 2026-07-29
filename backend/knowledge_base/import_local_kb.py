"""Migrate pgvector to BGE-M3 and import the prepared multimodal knowledge base."""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import async_session_factory, init_db
from app.models.course import Course
from app.models.document import Document, DocumentChunk
from app.services.embedder import Embedder

KB_DIR = Path(__file__).resolve().parents[3] / "knowledge-base"
METADATA_PATH = KB_DIR / "embeddings" / "metadata.json"
IMPORT_KEY = "bge_m3_multimodal_kb_v1"
PREVIOUS_IMPORT_KEY = "offline_multimodal_kb_v1"
DIMENSIONS = 1024
BATCH_SIZE = 16


def load_chunks() -> list[dict[str, Any]]:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Knowledge-base metadata not found: {METADATA_PATH}")
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


async def choose_course(db) -> Course:
    course = (
        await db.execute(select(Course).where(Course.seed_course.is_(True)).limit(1))
    ).scalar_one_or_none()
    if course is None:
        course = (await db.execute(select(Course).limit(1))).scalar_one_or_none()
    if course is None:
        course = Course(
            title="人工智能导论",
            description="由本地多模态知识库导入",
            seed_course=True,
            is_active=True,
        )
        db.add(course)
        await db.flush()
    return course


async def migrate_vector_dimension() -> None:
    async with async_session_factory() as db:
        await db.execute(text("DROP INDEX IF EXISTS idx_document_chunks_embedding"))
        await db.execute(text("UPDATE document_chunks SET embedding = NULL"))
        await db.execute(
            text(
                "ALTER TABLE document_chunks "
                "ALTER COLUMN embedding TYPE vector(1024) "
                "USING NULL::vector(1024)"
            )
        )
        await db.commit()


async def remove_previous_imports(db) -> int:
    documents = (await db.execute(select(Document))).scalars().all()
    imported = [
        document
        for document in documents
        if (document.doc_metadata or {}).get("import_key")
        in {IMPORT_KEY, PREVIOUS_IMPORT_KEY}
    ]
    for document in imported:
        await db.delete(document)
    await db.flush()
    return len(imported)


async def import_chunks() -> None:
    chunks = load_chunks()
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        grouped[(chunk.get("source", "unknown"), chunk.get("type", "unknown"))].append(chunk)

    await init_db()
    await migrate_vector_dimension()
    embedder = Embedder()

    async with async_session_factory() as db:
        course = await choose_course(db)
        removed = await remove_previous_imports(db)
        imported_chunks = 0

        for (source, doc_type), items in grouped.items():
            document = Document(
                title=f"{source} [{doc_type}]",
                file_type="local_kb",
                file_path=str(KB_DIR),
                course_id=course.id,
                page_count=len({str(item.get("locator", "")) for item in items}),
                status="ready",
                doc_metadata={
                    "import_key": IMPORT_KEY,
                    "source": source,
                    "type": doc_type,
                    "embedding": "BAAI/bge-m3",
                },
            )
            db.add(document)
            await db.flush()

            for offset in range(0, len(items), BATCH_SIZE):
                batch = items[offset : offset + BATCH_SIZE]
                vectors = await embedder.embed_batch(
                    [item.get("text", "") for item in batch]
                )
                for index, (item, vector) in enumerate(zip(batch, vectors), start=offset):
                    db.add(
                        DocumentChunk(
                            document_id=document.id,
                            chunk_index=index,
                            content=item.get("text", ""),
                            embedding=vector,
                            chunk_metadata={
                                "import_key": IMPORT_KEY,
                                "source": source,
                                "locator": item.get("locator", ""),
                                "title": item.get("title", ""),
                                "type": doc_type,
                                "assets": item.get("assets", []),
                                "original_chunk_id": item.get("id"),
                            },
                        )
                    )
                    imported_chunks += 1
                await db.flush()
                print(f"[BGE] encoded {imported_chunks}/{len(chunks)} chunks")

        await db.execute(
            text(
                "CREATE INDEX idx_document_chunks_embedding "
                "ON document_chunks USING ivfflat "
                "(embedding vector_cosine_ops) WITH (lists = 100)"
            )
        )
        await db.commit()
        print(
            f"[DONE] removed_documents={removed}, documents={len(grouped)}, "
            f"chunks={imported_chunks}, dimensions={DIMENSIONS}"
        )


if __name__ == "__main__":
    asyncio.run(import_chunks())
