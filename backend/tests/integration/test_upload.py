"""Upload endpoint integration tests (roadmap Phase 2)."""

from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.config.settings import get_settings
from app.main import app


def _png_bytes(size: tuple[int, int] = (10, 10)) -> bytes:
    """Build a tiny valid PNG."""
    buffer = BytesIO()
    Image.new("RGB", size, (10, 10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def _cleanup(image_id: str) -> None:
    """Remove a stored upload artifact for test isolation."""
    settings = get_settings()
    Path(settings.uploads_dir, f"{image_id}.png").unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_upload_valid_image():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("face.png", _png_bytes(), "image/png")}
        response = await client.post("/api/v1/upload", files=files)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "ready"
    assert body["image_id"]
    assert body["search_id"] > 0
    _cleanup(body["image_id"])


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_mime():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("notes.txt", b"not an image", "text/plain")}
        response = await client.post("/api/v1/upload", files=files)

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_invalid_image_bytes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("fake.png", b"this is not a real image", "image/png")}
        response = await client.post("/api/v1/upload", files=files)

    assert response.status_code == 400