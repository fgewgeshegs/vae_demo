from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from inference_service.batcher import DynamicBatcher
from inference_service.engines import (
    HybridOnnxEngine,
    OnnxEmbeddingEngine,
    TorchBGEEngine,
    runtime_capabilities,
)

MODEL_PATH = os.getenv("BGE_MODEL_PATH", r"D:\jay_demo\models\bge-m3")
RERANKER_PATH = os.getenv("BGE_RERANKER_PATH", r"D:\jay_demo\models\bge-reranker-v2-m3")
DEVICE = os.getenv("BGE_DEVICE", "cuda")
RUNTIME = os.getenv("BGE_INFERENCE_RUNTIME", "torch")
MAX_BATCH_SIZE = int(os.getenv("BGE_DYNAMIC_BATCH_SIZE", "32"))
MAX_WAIT_MS = int(os.getenv("BGE_DYNAMIC_BATCH_WAIT_MS", "10"))

engine = None
embed_batcher = None
rerank_batcher = None


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=128)


class RerankRequest(BaseModel):
    query: str
    documents: list[str] = Field(min_length=1, max_length=128)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, embed_batcher, rerank_batcher
    if RUNTIME == "onnx":
        onnx_engine = OnnxEmbeddingEngine(str(os.path.join(MODEL_PATH, "onnx")))
        torch_engine = TorchBGEEngine(MODEL_PATH, RERANKER_PATH, DEVICE)
        engine = HybridOnnxEngine(onnx_engine, torch_engine)
    elif RUNTIME == "tensorrt":
        raise RuntimeError(
            "TensorRT runtime requires an exported engine and tensorrt package; "
            "neither is bundled with this workspace"
        )
    else:
        engine = TorchBGEEngine(MODEL_PATH, RERANKER_PATH, DEVICE)

    embed_batcher = DynamicBatcher(engine.embed, MAX_BATCH_SIZE, MAX_WAIT_MS)
    rerank_batcher = DynamicBatcher(engine.score, MAX_BATCH_SIZE, MAX_WAIT_MS)
    await embed_batcher.start()
    await rerank_batcher.start()
    yield
    await embed_batcher.close()
    await rerank_batcher.close()


app = FastAPI(title="BGE Inference Service", lifespan=lifespan)


@app.post("/embed")
async def embed(request: EmbedRequest):
    return {"embeddings": await embed_batcher.submit(request.texts)}


@app.post("/rerank")
async def rerank(request: RerankRequest):
    pairs = [(request.query, document) for document in request.documents]
    return {"scores": await rerank_batcher.submit(pairs)}


@app.get("/health")
async def health():
    return {
        "status": "healthy" if engine is not None else "starting",
        "runtime": RUNTIME,
        "device": DEVICE,
        "dynamic_batch": {"max_size": MAX_BATCH_SIZE, "max_wait_ms": MAX_WAIT_MS},
        "capabilities": runtime_capabilities(),
    }
