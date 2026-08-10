"""Image upload endpoint (roadmap Phase 2 — Image Upload)."""

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.dependencies.container import get_upload_service
from app.schemas.upload import UploadResponse
from app.services.upload_service import UploadService

router = APIRouter(prefix="/upload")


@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_image(
    file: UploadFile = File(...),
    upload_service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    """
    Upload a source image for face detection.

    Validates MIME/size/dimensions, stores the file under uploads/,
    and creates a search job. The returned image_id is used by
    POST /api/v1/search.
    """
    return await upload_service.store_and_create(file)