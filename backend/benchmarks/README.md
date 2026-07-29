# Retrieval Benchmark

Run from `backend` after the database and inference backend are available:

```powershell
D:\jay_demo\bge_env\Scripts\python.exe -m benchmarks.retrieval_benchmark --top-k 10
```

The report compares forced exact scans with indexed vector search and reports
`recall@k`, plus whether an HNSW index is present. If multiple vector indexes
exist, PostgreSQL chooses the index. Hybrid retrieval uses reciprocal rank
fusion over indexed vector and keyword results. Its coverage metric is not a
relevance judgment; use a labeled query set before making ranking-quality
claims.
