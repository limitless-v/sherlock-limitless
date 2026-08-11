"""Evidence graph service (roadmap Phase 24).

Service layer for building and managing the evidence graph.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.graph import EvidenceGraph
from app.repositories.evidence_graph import EvidenceGraphRepository


class EvidenceGraphService:
    """Service layer for evidence graph operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = EvidenceGraphRepository(session)

    def create_graph(self, search_id: int) -> EvidenceGraph:
        """Create a new empty evidence graph for a search."""
        return EvidenceGraph(search_id)

    async def persist_graph(self, graph: EvidenceGraph) -> None:
        """Persist an evidence graph to the database."""
        await self._repo.persist_graph(graph)

    async def load_graph(self, search_id: int) -> EvidenceGraph:
        """Load an evidence graph from the database."""
        nodes, edges = await self._repo.get_graph_for_search(search_id)
        return EvidenceGraph.from_database(search_id, nodes, edges)

    async def get_graph_data(self, search_id: int) -> dict[str, Any]:
        """Get serialized graph data for API response."""
        graph = await self.load_graph(search_id)
        return graph.to_dict()

    async def get_node_count(self, search_id: int) -> int:
        """Get total node count for a search."""
        return await self._repo.get_node_count_by_search(search_id)

    async def get_edge_count(self, search_id: int) -> int:
        """Get total edge count for a search."""
        return await self._repo.get_edge_count_by_search(search_id)

    async def delete_graph(self, search_id: int) -> tuple[int, int]:
        """Delete all graph data for a search."""
        return await self._repo.delete_graph_by_search(search_id)