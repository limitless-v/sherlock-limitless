"""Hybrid search service (roadmap section 10, wired in Phase 18).

Runs LOCAL and INTERNET searches independently and tolerates partial
failure: one unavailable source (e.g. Agent Reach not installed) yields a
degraded-but-usable response instead of a failure. Local results always
survive.
"""

from __future__ import annotations

from app.search.local_search import LocalSearchService
from app.search.internet_search import InternetSearchService
from app.search.modes import SearchMode
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse


class HybridSearchService:
    """Combines local and internet search with independent execution."""

    def __init__(
        self,
        local_search: LocalSearchService,
        internet_search: InternetSearchService,
    ) -> None:
        self._local_search = local_search
        self._internet_search = internet_search

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Merge local and internet results; one failing source is non-fatal."""
        local = await self._local_search.search(request)
        internet = await self._internet_search.search(request)

        seen: set[str] = set()
        merged = []
        for result in (*local.results, *internet.results):
            key = f"{result.url}|{result.source}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(result)

        status = "degraded" if internet.status == "degraded" else "completed"

        return SearchResponse(
            search_id=str(request.image_id),
            mode=SearchMode.HYBRID,
            status=status,
            results=merged,
            providers={"local": local.providers or {"available": True}, **internet.providers},
        )