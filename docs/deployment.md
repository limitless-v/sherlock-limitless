# Deployment Guide

## Environment

| Variable | Production notes |
|----------|------------------|
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `SECRET_KEY` | Cryptographically random |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `CORS_ORIGINS` | Your frontend origin(s) |
| `OSINT_ENABLED` | Enable only with legal/compliance review |

## Docker Compose (recommended)

```bash
cp .env.example .env
# Set DATABASE_URL to postgres service
docker compose up -d --build
docker compose --profile production up -d nginx
```

Volumes persist uploads, embeddings, models, and Postgres data.

## Manual deployment

1. Install system deps: `libgl1`, `libglib2.0-0` (OpenCV headless).
2. Gunicorn/Uvicorn workers: `--workers` ≈ `2 * CPU + 1` for I/O bound; keep AI in Celery workers for CPU isolation.
3. Alembic migrate against PostgreSQL.
4. Nginx terminates TLS and proxies `/api` → backend, `/` → Next.js.

## Celery workers

```bash
docker compose --profile workers up -d worker
```

Configure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` to Redis.

## Observability

- Structured logs via Loguru (`LOG_JSON=true` in prod).
- Request IDs in `X-Request-ID` response header.
- Extend with Prometheus/OpenTelemetry in implementation phase.

## Backups

- PostgreSQL: standard pg_dump schedule.
- `embeddings/` and `models/`: versioned object storage snapshots.
