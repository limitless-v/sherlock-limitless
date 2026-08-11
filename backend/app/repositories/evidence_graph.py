"""Evidence graph repository (roadmap Phase 24).

Persistence layer for evidence graph nodes and edges.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import EvidenceNode, EvidenceEdge, SearchHistory


class EvidenceGraphRepository:
    """Repository for evidence graph persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_nodes_bulk(
        self,
        search_id: int,
        nodes: list[dict[str, Any]],
    ) -> list[EvidenceNode]:
        """Create multiple nodes efficiently."""
        created_nodes: list[EvidenceNode] = []
        for node_data in nodes:
            node = EvidenceNode(
                search_id=search_id,
                node_type=node_data["node_type"],
                entity_id=node_data["entity_id"],
                entity_value=node_data["entity_value"],
                attributes=node_data.get("attributes"),
                source_url=node_data.get("source_url"),
                source_evidence_id=node_data.get("source_evidence_id"),
            )
            self._session.add(node)
            created_nodes.append(node)

        await self._session.flush()
        for node in created_nodes:
            await self._session.refresh(node)
        return created_nodes

    async def create_edges_bulk(
        self,
        search_id: int,
        edges: list[dict[str, Any]],
    ) -> list[EvidenceEdge]:
        """Create multiple edges efficiently."""
        created_edges: list[EvidenceEdge] = []
        for edge_data in edges:
            edge = EvidenceEdge(
                search_id=search_id,
                source_node_id=edge_data["source_node_id"],
                target_node_id=edge_data["target_node_id"],
                edge_type=edge_data["edge_type"],
                source_url=edge_data["source_url"],
                source_evidence_id=edge_data.get("source_evidence_id"),
                confidence=edge_data.get("confidence"),
                edge_metadata=edge_data.get("metadata"),
            )
            self._session.add(edge)
            created_edges.append(edge)

        await self._session.flush()
        for edge in created_edges:
            await self._session.refresh(edge)
        return created_edges

    async def persist_graph(self, graph: "EvidenceGraph") -> None:
        """Persist an entire EvidenceGraph to database."""
        # Persist nodes
        nodes_data = graph.get_nodes_for_persistence()
        if nodes_data:
            await self.create_nodes_bulk(graph.search_id, nodes_data)

        # Persist edges
        edges_data = graph.get_edges_for_persistence()
        if edges_data:
            await self.create_edges_bulk(graph.search_id, edges_data)

    async def get_nodes_by_search(
        self,
        search_id: int,
        node_type: str | None = None,
    ) -> Sequence[EvidenceNode]:
        """Get all nodes for a search, optionally filtered by type."""
        stmt = select(EvidenceNode).where(EvidenceNode.search_id == search_id)
        if node_type:
            stmt = stmt.where(EvidenceNode.node_type == node_type)
        stmt = stmt.order_by(EvidenceNode.created_at)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_edges_by_search(
        self,
        search_id: int,
        edge_type: str | None = None,
    ) -> Sequence[EvidenceEdge]:
        """Get all edges for a search, optionally filtered by type."""
        stmt = select(EvidenceEdge).where(EvidenceEdge.search_id == search_id)
        if edge_type:
            stmt = stmt.where(EvidenceEdge.edge_type == edge_type)
        stmt = stmt.order_by(EvidenceEdge.created_at)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_graph_for_search(self, search_id: int) -> tuple[list[dict], list[dict]]:
        """Get full graph data for a search (nodes + edges)."""
        nodes = await self.get_nodes_by_search(search_id)
        edges = await self.get_edges_by_search(search_id)

        node_dicts = [
            {
                "id": n.id,
                "search_id": n.search_id,
                "node_type": n.node_type,
                "entity_id": n.entity_id,
                "entity_value": n.entity_value,
                "attributes": n.attributes,
                "source_url": n.source_url,
                "source_evidence_id": n.source_evidence_id,
            }
            for n in nodes
        ]

        edge_dicts = [
            {
                "id": e.id,
                "search_id": e.search_id,
                "source_node_id": e.source_node_id,
                "target_node_id": e.target_node_id,
                "edge_type": e.edge_type,
                "source_url": e.source_url,
                "source_evidence_id": e.source_evidence_id,
                "confidence": e.confidence,
                "metadata": e.edge_metadata,
            }
            for e in edges
        ]

        return node_dicts, edge_dicts

    async def get_node_count_by_search(self, search_id: int) -> int:
        """Get total node count for a search."""
        stmt = select(func.count(EvidenceNode.id)).where(EvidenceNode.search_id == search_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_edge_count_by_search(self, search_id: int) -> int:
        """Get total edge count for a search."""
        stmt = select(func.count(EvidenceEdge.id)).where(EvidenceEdge.search_id == search_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_node_by_entity(
        self,
        search_id: int,
        node_type: str,
        entity_id: str,
    ) -> EvidenceNode | None:
        """Get a node by type and entity ID."""
        stmt = select(EvidenceNode).where(
            EvidenceNode.search_id == search_id,
            EvidenceNode.node_type == node_type,
            EvidenceNode.entity_id == entity_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_edges_by_node(
        self,
        node_id: int,
        direction: str = "out",  # "out", "in", or "both"
    ) -> Sequence[EvidenceEdge]:
        """Get edges connected to a node."""
        if direction == "out":
            stmt = select(EvidenceEdge).where(EvidenceEdge.source_node_id == node_id)
        elif direction == "in":
            stmt = select(EvidenceEdge).where(EvidenceEdge.target_node_id == node_id)
        else:
            from sqlalchemy import or_
            stmt = select(EvidenceEdge).where(
                or_(
                    EvidenceEdge.source_node_id == node_id,
                    EvidenceEdge.target_node_id == node_id,
                )
            )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete_graph_by_search(self, search_id: int) -> tuple[int, int]:
        """Delete all nodes and edges for a search. Returns (node_count, edge_count)."""
        # Delete edges first (FK constraint)
        edge_result = await self._session.execute(
            delete(EvidenceEdge).where(EvidenceEdge.search_id == search_id)
        )
        edge_count = edge_result.rowcount

        node_result = await self._session.execute(
            delete(EvidenceNode).where(EvidenceNode.search_id == search_id)
        )
        node_count = node_result.rowcount

        return node_count, edge_count