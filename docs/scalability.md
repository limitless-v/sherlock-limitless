# Scalability Recommendations

## Application tier

- Stateless FastAPI instances behind a load balancer.
- JWT avoids server-side session affinity.
- Move long searches to Celery; API returns `202` + poll `GET /search/{id}`.

## AI inference

- Dedicated worker pool with constrained concurrency to avoid CPU thrashing.
- Optional GPU nodes for embedding batch jobs only.
- Quantized ONNX models for CPU throughput.

## Vector search

- Start with single-process FAISS `IndexIVFPQ` for large galleries.
- Split indexes by tenant or geography if multi-tenant.
- Consider Milvus/Qdrant when you need distributed replication and filtering.

## Storage

- S3-compatible object store for uploads and embedding blobs.
- CDN for public result thumbnails (if any).

## Caching

- Redis: rate limits, OSINT HTTP cache keys, hot search status.
- CDN not required for private dashboards.

## Data tier

- PostgreSQL read replicas for history/analytics.
- Partition `search_history` by `created_at` at high volume.

## Observability at scale

- Trace ID propagation (`X-Request-ID` → OpenTelemetry).
- Separate metrics for inference latency vs OSINT latency.

## Compliance

- OSINT features should be feature-flagged per deployment region.
- Audit log table (future) for search actions and data retention policies.
