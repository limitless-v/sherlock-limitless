"""Agent Reach web provider (roadmap Phase 18).

Implements the `WebSearchProvider` contract on top of Agent Reach. Agent
Reach is intentionally registered as a *web* provider only — it is not an
image/reverse-image-search provider unless its real capabilities expose such
an operation (added explicitly at that point).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.discovery.context.models import SearchContext
from app.discovery.providers.base import WebSearchProvider
from app.discovery.schemas import Candidate
from app.osint.agent_reach.capabilities import AgentReachCapabilities
from app.osint.agent_reach.client import AgentReachClient, AgentReachUnavailableError

_UNAVAILABLE_REASON = "agent-reach CLI not installed"


@dataclass
class AgentReachWebProvider(WebSearchProvider):
    """Agent Reach web discovery as a replaceable provider."""

    client: AgentReachClient
    _capabilities: AgentReachCapabilities = None  # type: ignore[assignment]
    enabled: bool = True

    name: str = "agent_reach"
    kind: str = "web"

    def __post_init__(self) -> None:
        if self._capabilities is None:
            self._capabilities = AgentReachCapabilities()
            try:
                self._capabilities.refresh(self.client)
            except Exception:
                self._capabilities.available = False
                self._capabilities.reason = _UNAVAILABLE_REASON

    @property
    def available(self) -> bool:
        return self.enabled and self.client.is_available()

    @property
    def availability_reason(self) -> str:
        if not self.enabled:
            return "Agent Reach disabled (AGENT_REACH_ENABLED=false)"
        if not self.client.is_available():
            return self._capabilities.reason or _UNAVAILABLE_REASON
        return self._capabilities.reason

    def capabilities(self) -> list[str]:
        """Web capability only — no image-search capability is claimed."""
        return ["web"]

    async def search(self, query: str, context: SearchContext) -> list[Candidate]:
        """Query Agent Reach and return normalized candidates ([] when down)."""
        if not self.available:
            return []
        try:
            return await asyncio.to_thread(self.client.discover, query)
        except AgentReachUnavailableError:
            return []