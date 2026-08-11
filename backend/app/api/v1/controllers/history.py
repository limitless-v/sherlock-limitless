"""Search history endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.container import get_search_service
from app.schemas.search import SearchHistoryItem, SearchHistoryRead
from app.services.search_service import SearchService

router = APIRouter(prefix="/history")


@router.get("", response_model=SearchHistoryRead)
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    mode: str | None = Query(None),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    user_id: int | None = Query(None),
    search_service: SearchService = Depends(get_search_service),
) -> SearchHistoryRead:
    """List past searches for the authenticated user with pagination and filters."""
    items, total = await search_service.list_history(
        user_id=user_id,
        page=page,
        page_size=page_size,
        status=status,
        mode=mode,
        created_from=created_from,
        created_to=created_to,
    )
    return SearchHistoryRead(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(
    search_id: int,
    user_id: int | None = Query(None),
    search_service: SearchService = Depends(get_search_service),
) -> None:
    """Delete a search record and associated artifacts."""
    deleted = await search_service.delete_history(search_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )