# BGE Inference Service

The standalone service owns BGE embedding and reranker model memory and exposes:

- `POST /embed`
- `POST /rerank`
- `GET /health`

Start the default PyTorch/CUDA service with `start_inference_service.cmd`, then set
`BGE_INFERENCE_SERVICE_URL=http://127.0.0.1:8100` for the main backend.

Dynamic batching is controlled by:

- `BGE_DYNAMIC_BATCH_SIZE` (default `32`)
- `BGE_DYNAMIC_BATCH_WAIT_MS` (default `10`)

## Optional runtimes

Set `BGE_INFERENCE_RUNTIME=onnx` after installing
`requirements-inference-onnx.txt`. The existing BGE-M3 ONNX export is used for
embedding; reranking remains on PyTorch because no reranker ONNX export exists.

`BGE_INFERENCE_RUNTIME=tensorrt` intentionally fails fast until a TensorRT
runtime and model-specific serialized engine are supplied. TensorRT engines are
GPU-architecture and version specific, so this repository does not generate or
bundle one automatically.
