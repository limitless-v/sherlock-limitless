"""Agent Reach capability detection (roadmap section 12).

Dynamically detects which sources/operations Agent Reach supports so the
internet search service can adapt at runtime instead of assuming a fixed
capability set.
"""


class AgentReachCapabilities:
    """Runtime capability snapshot for the Agent Reach client."""

    def __init__(self) -> None:
        self.available: bool = False
        self.sources: list[str] = []

    async def refresh(self, client) -> None:
        """Query the client and populate this capability snapshot."""
        raise NotImplementedError("Capability detection not implemented in scaffold.")

    def supports(self, source: str) -> bool:
        return source in self.sources
