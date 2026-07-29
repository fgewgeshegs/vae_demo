from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import numpy as np


class TorchBGEEngine:
    def __init__(self, model_path: str, reranker_path: str, device: str):
        from FlagEmbedding import FlagReranker
        from sentence_transformers import SentenceTransformer

        self.embedding_model = SentenceTransformer(
            model_path,
            device=device,
            local_files_only=True,
            model_kwargs={"low_cpu_mem_usage": False},
        )
        self.reranker = FlagReranker(
            reranker_path,
            use_fp16=device.startswith("cuda"),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def run():
            return self.embedding_model.encode(
                texts,
                batch_size=len(texts),
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

        return await asyncio.to_thread(run)

    async def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        def run():
            values = self.reranker.compute_score([list(pair) for pair in pairs], normalize=True)
            if isinstance(values, float):
                return [values]
            return [float(value) for value in values]

        return await asyncio.to_thread(run)


class OnnxEmbeddingEngine:
    def __init__(self, onnx_dir: str):
        if importlib.util.find_spec("onnxruntime") is None:
            raise RuntimeError("onnxruntime-gpu is not installed")
        import onnxruntime as ort
        from transformers import AutoTokenizer

        path = Path(onnx_dir)
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        self.session = ort.InferenceSession(str(path / "model.onnx"), providers=providers)
        self.input_names = {item.name for item in self.session.get_inputs()}

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def run():
            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="np",
            )
            inputs = {key: value for key, value in encoded.items() if key in self.input_names}
            output = self.session.run(None, inputs)[0]
            if output.ndim == 3:
                mask = encoded["attention_mask"][..., None]
                output = (output * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
            output = output / np.maximum(np.linalg.norm(output, axis=1, keepdims=True), 1e-12)
            return output.astype("float32").tolist()

        return await asyncio.to_thread(run)


class HybridOnnxEngine:
    """Use ONNX for embeddings while retaining the PyTorch reranker."""

    def __init__(self, embedding_engine: OnnxEmbeddingEngine, torch_engine: TorchBGEEngine):
        self.embedding_engine = embedding_engine
        self.torch_engine = torch_engine

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self.embedding_engine.embed(texts)

    async def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        return await self.torch_engine.score(pairs)


def runtime_capabilities() -> dict:
    return {
        "onnxruntime": importlib.util.find_spec("onnxruntime") is not None,
        "tensorrt": importlib.util.find_spec("tensorrt") is not None,
    }
