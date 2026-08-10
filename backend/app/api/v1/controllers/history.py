"""Search history endpoints (scaffold)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.container import get_search_service
from app.schemas.search import SearchHistoryItem
from app.services.search_service import SearchService

router = APIRouter(prefix="/history")


@router.get("", response_model=list[SearchHistoryItem])
async def list_history(
    search_service: SearchService = Depends(get_search_service),
) -> list[SearchHistoryItem]:
    """List past searches for the authenticated user."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="History not implemented",
    )


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(
    search_id: int,
    search_service: SearchService = Depends(get_search_service),
) -> None:
    """Delete a search record and associated artifacts."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete history not implemented",
    )
