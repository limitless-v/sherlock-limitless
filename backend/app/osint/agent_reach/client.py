"""Agent Reach adapter — scaffold.

Wraps the Agent Reach discovery layer behind a narrow interface.
Returned data must be normalized into app.search.result_models.SearchResult
by callers; Agent Reach-specific structures stay inside this package.
"""


class AgentReachClient:
    """Discover public candidate pages for a query image or profile."""

    async def discover(self, query_image_path: str, sources: list[str] | None = None) -> list[dict]:
        raise NotImplementedError

    async def is_available(self) -> bool:
        """Return True when Agent Reach is reachable and usable."""
        raise NotImplementedError
