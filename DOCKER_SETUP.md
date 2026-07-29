# Docker team setup

The application code and Python dependencies run in Docker. BGE model files
stay outside the image and are mounted read-only, so rebuilding the application
does not repeatedly copy several gigabytes of model weights.

## Required directory layout

Place the repositories and models like this:

```text
jay_demo/
├── models/
│   ├── bge-m3/
│   └── bge-reranker-v2-m3/
├── knowledge-base/
└── vae_demo/
    └── docker-compose.yml
```

Both model directories must contain `config.json` and their model weight files.
The `knowledge-base` directory must contain `embeddings/metadata.json` and
`db/faiss.index`.

## Start

From the `vae_demo` directory:

```powershell
.\start-docker.ps1
```

The script checks that both BGE models and the prepared knowledge-base index
exist before it runs `docker compose up --build`.

Open:

- Frontend: http://localhost:8080
- Backend API docs: http://localhost:8000/docs
- Backend health and model-path check: http://localhost:8000/health

The first build downloads Python, PyTorch, Node, and other dependencies, so it
can take 20-60 minutes. Later starts reuse the Docker image and model files.

## Stop

```powershell
docker compose down
```

To preserve team data, do not add `-v` unless the PostgreSQL and Redis volumes
should also be deleted.

## Optional GPU mode

The default is CPU mode because it works on teammates' computers without an
NVIDIA setup. GPU passthrough additionally requires NVIDIA Container Toolkit
and a CUDA-compatible PyTorch image, so it is intentionally not enabled in the
shared default configuration.
