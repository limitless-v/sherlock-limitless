"""Hybrid search service (roadmap section 10).

Runs LOCAL and INTERNET searches independently and tolerates partial
failure: if one source fails, the other's results are still returned.
"""

from app.search.local_search import LocalSearchService
from app.search.internet_search import InternetSearchService
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
        raise NotImplementedError("Hybrid search not implemented in scaffold.")
