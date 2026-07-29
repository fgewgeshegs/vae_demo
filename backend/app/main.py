"""FastAPI 应用入口"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import init_db, close_db, load_runtime_configs
from app.core.database import async_session_factory
from app.api.v1 import v1_router
from knowledge_base.seed_courses import seed_course
from knowledge_base.seed_resources import seed_resources
from pathlib import Path
from app.services.retrieval_errors import RetrievalBusyError, RetrievalUnavailableError
from app.services.embedder import Embedder
from app.services.reranker import Reranker
from app.services.vector_store import VectorStore
from app.services.bge_runtime import runtime_status
from sqlalchemy import text
from app.core.llm_gateway import close_llm_http_client
from app.services.document_queue import run_document_worker
from app.services.event_processor import run_event_processor
from app.services.redis_client import close_redis, get_redis
from app.services.inference_client import close_inference_client
from app.services.inference_client import enabled as remote_inference_enabled
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"LLM 供应商: {settings.LLM_PROVIDER}")
    await init_db()
    await load_runtime_configs()
    await seed_course()
    if settings.SEED_RESOURCES_ON_STARTUP:
        await seed_resources()
    document_worker = asyncio.create_task(run_document_worker())
    event_worker = asyncio.create_task(run_event_processor())
    yield
    document_worker.cancel()
    event_worker.cancel()
    await asyncio.gather(document_worker, event_worker, return_exceptions=True)
    await close_redis()
    await close_inference_client()
    await close_llm_http_client()
    await close_db()
    logger.info("应用已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 个性化学习平台后端 API",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(v1_router)


@app.exception_handler(RetrievalUnavailableError)
async def retrieval_unavailable_handler(request: Request, exc: RetrievalUnavailableError):
    headers = {"Retry-After": "3"} if isinstance(exc, RetrievalBusyError) else None
    return JSONResponse(status_code=503, content={"detail": str(exc)}, headers=headers)

# 健康检查
@app.get("/health")
async def health_check(response: Response):
    bge_model = Path(settings.BGE_MODEL_PATH)
    reranker_model = Path(settings.BGE_RERANKER_PATH)
    remote_inference = remote_inference_enabled()
    checks = {
        "database": {"ok": False, "error": None},
        "embedding": {"ok": False, "error": None},
        "vector_search": {"ok": False, "error": None},
        "reranker": {"ok": False, "error": None},
        "redis": {"ok": False, "error": None},
    }
    embedding = None
    try:
        await asyncio.wait_for(
            get_redis().ping(),
            timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS,
        )
        checks["redis"]["ok"] = True
    except Exception as exc:
        checks["redis"]["error"] = f"{type(exc).__name__}: {exc}"
    try:
        async with async_session_factory() as db:
            await asyncio.wait_for(
                db.execute(text("SELECT 1")),
                timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS,
            )
        checks["database"]["ok"] = True
    except Exception as exc:
        checks["database"]["error"] = f"{type(exc).__name__}: {exc}"

    try:
        embedding = await asyncio.wait_for(
            Embedder().embed("health check"),
            timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS,
        )
        checks["embedding"]["ok"] = True
    except Exception as exc:
        checks["embedding"]["error"] = f"{type(exc).__name__}: {exc}"

    if embedding is not None:
        try:
            await asyncio.wait_for(
                VectorStore().search(embedding, limit=1),
                timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS,
            )
            checks["vector_search"]["ok"] = True
        except Exception as exc:
            checks["vector_search"]["error"] = f"{type(exc).__name__}: {exc}"

    try:
        await asyncio.wait_for(
            Reranker().rerank("health check", [{"content": "health check"}], 1),
            timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS,
        )
        checks["reranker"]["ok"] = True
    except Exception as exc:
        checks["reranker"]["error"] = f"{type(exc).__name__}: {exc}"

    healthy = all(check["ok"] for check in checks.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "healthy" if healthy else "unhealthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "retrieval": {
            "method": "bge_m3_pgvector_bge_reranker",
            "inference_mode": "remote" if remote_inference else "local",
            "inference_service_url": settings.BGE_INFERENCE_SERVICE_URL,
            "embedding_dimension": settings.BGE_EMBEDDING_DIMENSION,
            "candidate_count": settings.BGE_RETRIEVAL_CANDIDATES,
            "top_k": settings.BGE_RERANK_TOP_K,
            "bge_model_available": remote_inference or bge_model.exists(),
            "reranker_model_available": remote_inference or reranker_model.exists(),
            "ready": healthy,
            "checks": checks,
            "gpu": runtime_status(),
        },
    }


@app.get("/")
async def root():
    return {
        "message": "AI 个性化学习平台 API",
        "docs": "/docs",
        "health": "/health",
    }
