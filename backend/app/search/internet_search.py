"""Internet search service (roadmap section 9).

Agent Reach is the discovery layer only — it finds public candidate
pages, metadata, and images. It never performs facial verification.
This is a first-class search mode, not a fallback for LOCAL.
"""

from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse


class InternetSearchService:
    """Agent Reach-backed public profile discovery."""

    def __init__(self, agent_reach_client, crawler=None) -> None:
        self._agent_reach_client = agent_reach_client
        self._crawler = crawler

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Discover public candidates via Agent Reach."""
        raise NotImplementedError("Internet search not implemented in scaffold.")

    @property
    def available(self) -> bool:
        """Agent Reach capability detection (roadmap section 12)."""
        raise NotImplementedError("Capability detection not implemented in scaffold.")
