# API Reference (v1)

Base URL: `http://localhost:8000`  
Prefix: `/api/v1`

OpenAPI: `/docs`, `/openapi.json`

## Authentication

Planned: Bearer JWT from `POST /api/v1/auth/login`.

## Endpoints

### `POST /api/v1/upload`

Multipart form field `file` (JPEG/PNG/WebP).

**202 Accepted** — upload validated and queued.

```json
{ "message": "...", "filename": "photo.jpg" }
```

### `POST /api/v1/search`

Starts processing for the latest upload or body reference (TBD in implementation).

**202 Accepted**

```json
{ "search_id": 1, "status": "pending" }
```

### `GET /api/v1/search/{search_id}`

**200 OK** — `SearchDetailRead` with detected faces and nested matches.

### `GET /api/v1/history`

**200 OK** — list of `SearchHistoryItem` for authenticated user.

### `DELETE /api/v1/history/{search_id}`

**204 No Content** on success.

### `GET /api/v1/profile/{profile_id}`

**200 OK** — `ProfileDetailRead` with platform links and verification images.

### Auth

- `POST /api/v1/auth/register` — `UserCreate` → `UserRead`
- `POST /api/v1/auth/login` — `TokenResponse`

### Health

- `GET /health` — `{ "status": "ok", "env": "development" }`

## Error shape

FastAPI default:

```json
{ "detail": "Human-readable message" }
```

## CORS

Configured via `CORS_ORIGINS` in `.env`.
