"""Search job endpoints (thin HTTP adapters).

No search-routing logic here — routing lives in the SearchOrchestrator
(roadmap section 5, 7).
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.dependencies.container import get_search_service
from app.schemas.search import (
    SearchCreateRequest,
    SearchResponseRead,
    SearchDetailRead,
    SearchHistoryItem,
    SearchHistoryRead,
)
from app.search.request_models import SearchRequest
from app.services.search_service import SearchService

router = APIRouter(prefix="/search")


@router.post("", response_model=SearchResponseRead, status_code=status.HTTP_202_ACCEPTED)
async def start_search(
    payload: SearchCreateRequest,
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponseRead:
    """Start a search for the requested mode (local / internet / hybrid)."""
    request = SearchRequest(
        image_id=payload.image_id,
        mode=payload.mode,
        max_results=payload.max_results,
        sources=payload.sources,
        user_id=payload.user_id,
    )
    try:
        response = await search_service.execute_search(request)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Search pipeline not implemented",
        ) from exc
    return SearchResponseRead.model_validate(response)


@router.get("/{search_id}", response_model=SearchDetailRead)
async def get_search(
    search_id: int,
    search_service: SearchService = Depends(get_search_service),
) -> SearchDetailRead:
    """Retrieve search status and ranked results."""
    search = await search_service.get_search(search_id)
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )
    return search


@router.get("/{search_id}/results")
async def get_search_results(
    search_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search_service: SearchService = Depends(get_search_service),
) -> dict[str, Any]:
    """Get paginated search results."""
    search = await search_service.get_search(search_id)
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )
    
    # For now return basic structure - would be populated from SearchResponse
    return {
        "search_id": search_id,
        "page": page,
        "page_size": page_size,
        "total": 0,
        "results": [],
    }


@router.get("/{search_id}/evidence")
async def get_search_evidence(
    search_id: int,
    search_service: SearchService = Depends(get_search_service),
) -> dict[str, Any]:
    """Get full evidence graph for a search."""
    search = await search_service.get_search(search_id)
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )
    
    return {
        "search_id": search_id,
        "nodes": [],
        "edges": [],
    }


@router.get("/{search_id}/events")
async def get_search_events(
    search_id: int,
    after: int | None = Query(None, description="Sequence number to replay from"),
    search_service: SearchService = Depends(get_search_service),
) -> StreamingResponse:
    """SSE endpoint for live search progress."""
    
    # Verify search exists
    search = await search_service.get_search(search_id)
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )
    
    async def event_generator():
        """Generate SSE events from search_events table."""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.database.session import AsyncSessionLocal
        from app.models.entities import SearchEvent
        
        # This is a simplified version - in production you'd use a pub/sub mechanism
        # For now, we'll just yield existing events from the database
        last_sequence = after or 0
        
        while True:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(SearchEvent)
                    .where(
                        SearchEvent.search_id == search_id,
                        SearchEvent.sequence > last_sequence,
                    )
                    .order_by(SearchEvent.sequence)
                )
                result = await session.execute(stmt)
                events = result.scalars().all()
                
                for event in events:
                    yield f"id: {event.sequence}\nevent: {event.event_type}\ndata: {event.payload or {}}\n\n"
                    last_sequence = event.sequence
                
                # Check if search is completed
                from app.models.entities import Search
                search_stmt = select(Search).where(Search.id == search_id)
                search_result = await session.execute(search_stmt)
                search_obj = search_result.scalar_one_or_none()
                
                if search_obj and search_obj.status in ("completed", "degraded", "failed"):
                    # Send final event
                    yield f"event: search_completed\ndata: {{\"status\": \"{search_obj.status}\"}}\n\n"
                    break
            
            # Wait before polling again
            import asyncio
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )