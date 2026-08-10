# Testing Strategy

## Backend

- **Framework**: pytest + pytest-asyncio
- **Integration**: `httpx.AsyncClient` + `ASGITransport` against `app.main:app`
- **Fixtures** (future): in-memory SQLite, temp upload dirs, mocked ONNX sessions

Run:

```bash
pytest backend/tests tests -v
```

## Frontend

- **Framework**: Vitest
- **Future**: React Testing Library for upload form and results table

Run:

```bash
cd frontend && npm test
```

## Coverage targets (implementation phase)

| Module | Priority |
|--------|----------|
| Upload validation | High |
| JWT auth | High |
| Similarity / ranking | High |
| FAISS index IO | Medium |
| OSINT client (mocked HTTP) | Medium |
| E2E upload → search | Medium |

## CI (recommended)

1. Lint: black, isort, flake8, mypy
2. pytest on PR
3. `npm run lint && npm test` for frontend
4. Optional: build Docker images on main
