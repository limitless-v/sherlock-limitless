"""Search service (thin adapter).

Delegates search routing/execution to the SearchOrchestrator and keeps
persistence/history plumbing separate. No `if mode == ...` logic lives
here — that belongs in backend/app/search/ (roadmap section 5, 7).
"""

from app.search.orchestrator import SearchOrchestrator
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse
from app.schemas.search import SearchCreateResponse, SearchDetailRead, SearchHistoryItem


class SearchService:
    """Coordinates search execution and persistence."""

    def __init__(self, orchestrator: SearchOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def execute_search(self, request: SearchRequest) -> SearchResponse:
        """Delegate to the orchestrator, which routes by search mode."""
        return await self._orchestrator.execute(request)

    async def get_search(self, search_id: int) -> SearchDetailRead | None:
        raise NotImplementedError

    async def list_history(self, user_id: int) -> list[SearchHistoryItem]:
        raise NotImplementedError

    async def delete_history(self, search_id: int, user_id: int) -> bool:
        raise NotImplementedError