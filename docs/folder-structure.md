# Folder Structure

## Root runtime directories

| Path | Purpose |
|------|---------|
| `uploads/` | Raw user uploads |
| `cache/` | HTTP/OSINT and inference cache |
| `embeddings/` | Serialized vectors + FAISS index |
| `results/` | JSON/artifact exports per search |
| `logs/` | Rotating application logs |
| `models/` | Downloaded ONNX / InsightFace bundles |
| `data/` | SQLite file (dev) |

## `backend/app/`

| Path | Responsibility |
|------|----------------|
| `main.py` | FastAPI factory, middleware, routers |
| `api/v1/controllers/` | Route handlers (upload, search, history, profile, auth) |
| `search/` | Search orchestration: `modes.py` (SearchMode), `orchestrator.py`, `request_models.py`, `result_models.py`, `local_search.py`, `internet_search.py`, `hybrid_search.py`, `verification.py`, `deduplication.py`, `ranking.py` |
| `ai/` | Face AI backbone: detection, preprocessing, embedding, matching/similarity, FAISS (`vector_db/`) |
| `osint/` | Internet OSINT: Agent Reach adapter + capabilities, platform parsers, candidate crawler |
| `llm/` | Optional Ollama: `ollama_client.py`, `summarizer.py` (off by default) |
| `services/` | Business logic / thin adapters (upload, search delegation) |
| `repositories/` | SQLAlchemy data access |
| `models/entities.py` | ORM tables |
| `schemas/` | Pydantic DTOs |
| `database/` | Engine, session, Base |
| `middleware/` | Logging, rate limit (stub) |
| `core/` | Security, logging |
| `config/settings.py` | Pydantic settings |
| `dependencies/` | DI providers |
| `workers/` | Celery app (optional) |

## `frontend/src/`

| Path | Responsibility |
|------|----------------|
| `app/` | Next.js routes (`/`, `/dashboard`) |
| `components/` | UI + layouts + shadcn/ui |
| `services/` | Axios API client |
| `types/` | Shared TS types |
| `hooks/` | TanStack Query hooks (future) |
| `store/` | Client state (future) |

## `ai/` (assets)

Mirror of model directories for documentation and offline packaging; runtime code remains under `backend/app/ai/`.

## `configs/`

Nginx, logging YAML, future feature flags.

## `scripts/`

`init_storage.py`, `download_models.py`, `detect_faces.py`, future index rebuild scripts.

## `docs/`

Architecture, API, installation, deployment, testing, scalability.
