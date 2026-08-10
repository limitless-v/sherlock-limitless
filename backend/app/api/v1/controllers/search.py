"""Search job endpoints (thin HTTP adapters).

No search-routing logic here — routing lives in the SearchOrchestrator
(roadmap section 5, 7).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.container import get_search_service
from app.schemas.search import SearchCreateRequest, SearchResponseRead, SearchDetailRead
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
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Search retrieval not implemented",
    )
