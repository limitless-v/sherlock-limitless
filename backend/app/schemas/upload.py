"""Upload DTOs."""

from uuid import UUID

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response for POST /api/v1/upload.

    image_id is the identifier referenced by POST /api/v1/search.
    """

    image_id: UUID
    search_id: int
    filename: str
    status: str = "ready"