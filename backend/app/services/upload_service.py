"""Upload service (roadmap Phase 2 — Image Upload).

Validates MIME type, size, and dimensions, persists the file under the
uploads storage directory, and records a search job so the image can be
referenced by POST /api/v1/search via its image_id.
"""

from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config.settings import Settings
from app.repositories.search_history import SearchHistoryRepository
from app.schemas.upload import UploadResponse

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class UploadService:
    """Validate and store uploaded images."""

    def __init__(self, settings: Settings, search_repo: SearchHistoryRepository) -> None:
        self._settings = settings
        self._search_repo = search_repo

    async def validate_image(self, file: UploadFile) -> None:
        """Raise HTTPException when the file fails validation rules."""
        if file.content_type not in self._settings.allowed_mime_types_list:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type: {file.content_type}",
            )

        data = await file.read()
        await file.seek(0)

        if len(data) > self._settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds maximum upload size",
            )

        if not _is_valid_image_dimensions(data, self._settings.max_image_dimension):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image exceeds maximum dimension of {self._settings.max_image_dimension}px",
            )

    async def store_and_create(self, file: UploadFile) -> UploadResponse:
        """Validate, persist the image, and create a search job."""
        await self.validate_image(file)

        image_id = uuid4()
        extension = EXTENSIONS.get(file.content_type or "", ".jpg")
        uploads_dir = self._settings.uploads_dir
        uploads_dir.mkdir(parents=True, exist_ok=True)
        relative_path = Path(f"{image_id}{extension}")
        dest = uploads_dir / relative_path

        data = await file.read()
        async with aiofiles.open(dest, "wb") as handle:
            await handle.write(data)

        search = await self._search_repo.create(str(relative_path))
        await self._search_repo.session.commit()
        return UploadResponse(
            image_id=image_id,
            search_id=search.id,
            filename=file.filename or relative_path.name,
        )


def _is_valid_image_dimensions(data: bytes, max_dimension: int) -> bool:
    """Return True when the image opens and respects the dimension limit."""
    try:
        with Image.open(__import__("io").BytesIO(data)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError):
        return False
    return width <= max_dimension and height <= max_dimension