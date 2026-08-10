# Installation Guide

## Prerequisites

- **Python 3.12+** (3.12 or 3.13 recommended; some wheels e.g. `asyncpg` may not build on 3.14 yet)
- Node.js 20+ (frontend)
- Optional: Docker Desktop, CUDA toolkit for GPU

## Backend

```bash
cd d:\PYTHON\Sherlock
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts\init_storage.py
```

Run API from the repository root (the launcher pre-installs the Windows
Selector event loop that async psycopg requires):

```bash
cd d:\PYTHON\Sherlock
python scripts\run_api.py          # --port 8000 --no-reload to customize
```

Or raw uvicorn from `backend` (no DB access — health checks only):

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify: [http://localhost:8000/health](http://localhost:8000/health)

## Database migrations

When ORM is wired to Alembic `env.py`:

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

Development uses SQLite at `./data/app.db` by default.

For PostgreSQL in production/Docker:

```bash
pip install -r requirements-prod.txt
```

## AI models

InsightFace (SCRFD/RetinaFace + ArcFace) now installs on Windows/Python 3.12
via a binary wheel:

```bash
pip install insightface      # or: pip install -r requirements-ai.txt
```

The `buffalo_l` model pack downloads automatically to `models/models/buffalo_l/`
on first detection. To fetch it explicitly:

```bash
python scripts/download_models.py
```

Verify detection on any photo:

```bash
python scripts/detect_faces.py <image_path>
```

Place standalone ONNX exports under `ai/models/` if using raw ONNX Runtime graphs.
Build the FAISS index into `embeddings/faiss.index` in a later phase.

## Frontend

```bash
cd frontend
npm install
set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## shadcn/ui

```bash
cd frontend
npx shadcn@latest add button card input table
```

## Pre-commit

```bash
pip install pre-commit
pre-commit install
```
