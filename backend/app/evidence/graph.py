"""Evidence Graph (roadmap Phase 24).

Custom adjacency-list implementation for the evidence graph.
Nodes: image, url, domain, profile, username, website, organization, location
Edges: image_found_on, links_to, same_public_identifier, same_image, mentions, published_at, located_at
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.evidence.schemas import EvidenceEdgeData, EvidenceGraphData, EvidenceNodeData


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Node:
    """Internal node representation."""
    id: int
    data: EvidenceNodeData


@dataclass
class _Edge:
    """Internal edge representation."""
    id: int
    source_id: int
    target_id: int
    data: EvidenceEdgeData


class EvidenceGraph:
    """In-memory evidence graph with custom adjacency-list implementation.

    Provides methods for building, querying, and serializing the graph.
    All data is serializable and PostgreSQL-friendly.
    """

    # Valid node types
    NODE_TYPES = frozenset({
        "image", "url", "domain", "profile", "username",
        "website", "organization", "location",
    })

    # Valid edge types
    EDGE_TYPES = frozenset({
        "image_found_on", "links_to", "same_public_identifier",
        "same_image", "mentions", "published_at", "located_at",
    })

    def __init__(self, search_id: int) -> None:
        self._search_id = search_id
        self._nodes: dict[int, _Node] = {}
        self._edges: dict[int, _Edge] = {}
        self._adjacency: dict[int, list[int]] = defaultdict(list)  # source_id -> [target_ids]
        self._reverse_adjacency: dict[int, list[int]] = defaultdict(list)  # target_id -> [source_ids]
        self._node_lookup: dict[tuple[str, str], int] = {}  # (node_type, entity_id) -> node_id
        self._edge_lookup: dict[tuple[int, int, str], int] = {}  # (source_id, target_id, edge_type) -> edge_id
        self._next_node_id = 1
        self._next_edge_id = 1

    @property
    def search_id(self) -> int:
        return self._search_id

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    # --- Node operations ---

    def add_node(
        self,
        node_type: str,
        entity_id: str,
        entity_value: str,
        attributes: dict | None = None,
        source_url: str | None = None,
        source_evidence_id: int | None = None,
    ) -> int:
        """Add a node to the graph. Returns the node ID.

        If a node with the same (node_type, entity_id) already exists,
        returns the existing node ID (deduplication).
        """
        if node_type not in self.NODE_TYPES:
            raise ValueError(f"Invalid node_type: {node_type}. Must be one of {self.NODE_TYPES}")

        key = (node_type, entity_id)
        if key in self._node_lookup:
            return self._node_lookup[key]

        node_id = self._next_node_id
        self._next_node_id += 1

        data = EvidenceNodeData(
            node_type=node_type,
            entity_id=entity_id,
            entity_value=entity_value,
            attributes=attributes or {},
            source_url=source_url,
            source_evidence_id=source_evidence_id,
        )
        node = _Node(id=node_id, data=data)
        self._nodes[node_id] = node
        self._node_lookup[key] = node_id
        return node_id

    def get_node(self, node_id: int) -> EvidenceNodeData | None:
        """Get node data by ID."""
        node = self._nodes.get(node_id)
        return node.data if node else None

    def get_node_by_entity(self, node_type: str, entity_id: str) -> int | None:
        """Get node ID by type and entity ID."""
        return self._node_lookup.get((node_type, entity_id))

    def get_nodes_by_type(self, node_type: str) -> list[EvidenceNodeData]:
        """Get all nodes of a specific type."""
        return [
            node.data for node in self._nodes.values()
            if node.data.node_type == node_type
        ]

    # --- Edge operations ---

    def add_edge(
        self,
        source_node_id: int,
        target_node_id: int,
        edge_type: str,
        source_url: str,
        source_evidence_id: int | None = None,
        confidence: float | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Add an edge to the graph. Returns the edge ID.

        If an edge with the same (source, target, edge_type) already exists,
        returns the existing edge ID (deduplication).
        """
        if edge_type not in self.EDGE_TYPES:
            raise ValueError(f"Invalid edge_type: {edge_type}. Must be one of {self.EDGE_TYPES}")

        if source_node_id not in self._nodes:
            raise ValueError(f"Source node {source_node_id} does not exist")
        if target_node_id not in self._nodes:
            raise ValueError(f"Target node {target_node_id} does not exist")

        key = (source_node_id, target_node_id, edge_type)
        if key in self._edge_lookup:
            return self._edge_lookup[key]

        edge_id = self._next_edge_id
        self._next_edge_id += 1

        data = EvidenceEdgeData(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            source_url=source_url,
            source_evidence_id=source_evidence_id,
            confidence=confidence,
            metadata=metadata or {},
        )
        edge = _Edge(id=edge_id, source_id=source_node_id, target_id=target_node_id, data=data)
        self._edges[edge_id] = edge
        self._edge_lookup[key] = edge_id
        self._adjacency[source_node_id].append(target_node_id)
        self._reverse_adjacency[target_node_id].append(source_node_id)
        return edge_id

    def get_edge(self, edge_id: int) -> EvidenceEdgeData | None:
        """Get edge data by ID."""
        edge = self._edges.get(edge_id)
        return edge.data if edge else None

    def get_edges_by_type(self, edge_type: str) -> list[EvidenceEdgeData]:
        """Get all edges of a specific type."""
        return [
            edge.data for edge in self._edges.values()
            if edge.data.edge_type == edge_type
        ]

    # --- Graph traversal ---

    def get_outgoing_edges(self, node_id: int) -> list[EvidenceEdgeData]:
        """Get all outgoing edges from a node."""
        if node_id not in self._nodes:
            return []
        return [
            self._edges[eid].data
            for eid in self._edge_lookup.values()
            if self._edges[eid].source_id == node_id
        ]

    def get_incoming_edges(self, node_id: int) -> list[EvidenceEdgeData]:
        """Get all incoming edges to a node."""
        if node_id not in self._nodes:
            return []
        return [
            self._edges[eid].data
            for eid in self._edge_lookup.values()
            if self._edges[eid].target_id == node_id
        ]

    def get_neighbors(self, node_id: int, direction: str = "out") -> list[int]:
        """Get neighbor node IDs (outgoing or incoming)."""
        if direction == "out":
            return self._adjacency.get(node_id, [])
        elif direction == "in":
            return self._reverse_adjacency.get(node_id, [])
        else:
            return list(set(self._adjacency.get(node_id, []) + self._reverse_adjacency.get(node_id, [])))

    def get_subgraph(self, node_id: int, depth: int = 2) -> "EvidenceGraph":
        """Get a subgraph centered on a node up to specified depth."""
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} does not exist")

        subgraph = EvidenceGraph(self._search_id)
        visited: set[int] = set()
        current_level: set[int] = {node_id}

        for _ in range(depth + 1):
            next_level: set[int] = set()
            for nid in current_level:
                if nid in visited:
                    continue
                visited.add(nid)

                # Copy node
                node = self._nodes[nid]
                subgraph._nodes[nid] = _Node(id=nid, data=node.data)
                subgraph._node_lookup[(node.data.node_type, node.data.entity_id)] = nid

                # Copy outgoing edges
                for target_id in self._adjacency.get(nid, []):
                    edge_key = (nid, target_id, None)  # We need to find all edge types
                    for eid, edge in self._edges.items():
                        if edge.source_id == nid and edge.target_id == target_id:
                            subgraph._edges[eid] = _Edge(
                                id=eid,
                                source_id=edge.source_id,
                                target_id=edge.target_id,
                                data=edge.data,
                            )
                            subgraph._edge_lookup[(edge.source_id, edge.target_id, edge.data.edge_type)] = eid
                            subgraph._adjacency[edge.source_id].append(edge.target_id)
                            subgraph._reverse_adjacency[edge.target_id].append(edge.source_id)
                            next_level.add(target_id)

                # Copy incoming edges
                for source_id in self._reverse_adjacency.get(nid, []):
                    for eid, edge in self._edges.items():
                        if edge.source_id == source_id and edge.target_id == nid:
                            if eid not in subgraph._edges:
                                subgraph._edges[eid] = _Edge(
                                    id=eid,
                                    source_id=edge.source_id,
                                    target_id=edge.target_id,
                                    data=edge.data,
                                )
                                subgraph._edge_lookup[(edge.source_id, edge.target_id, edge.data.edge_type)] = eid
                                subgraph._adjacency[edge.source_id].append(edge.target_id)
                                subgraph._reverse_adjacency[edge.target_id].append(edge.source_id)
                                next_level.add(source_id)

            current_level = next_level

        # Update next IDs
        if subgraph._nodes:
            subgraph._next_node_id = max(subgraph._nodes.keys()) + 1
        if subgraph._edges:
            subgraph._next_edge_id = max(subgraph._edges.keys()) + 1

        return subgraph

    # --- Serialization ---

    def serialize(self) -> EvidenceGraphData:
        """Serialize the graph for API response."""
        nodes = []
        for node in self._nodes.values():
            node_dict = node.data.to_dict()
            node_dict["id"] = node.id
            nodes.append(node_dict)

        edges = []
        for edge in self._edges.values():
            edge_dict = edge.data.to_dict()
            edge_dict["id"] = edge.id
            edges.append(edge_dict)

        return EvidenceGraphData(nodes=nodes, edges=edges)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.serialize().to_dict()

    # --- Persistence helpers ---

    def get_nodes_for_persistence(self) -> list[dict[str, Any]]:
        """Get nodes formatted for database insertion."""
        result = []
        for node in self._nodes.values():
            result.append({
                "id": node.id,
                "search_id": self._search_id,
                "node_type": node.data.node_type,
                "entity_id": node.data.entity_id,
                "entity_value": node.data.entity_value,
                "attributes": node.data.attributes,
                "source_url": node.data.source_url,
                "source_evidence_id": node.data.source_evidence_id,
            })
        return result

    def get_edges_for_persistence(self) -> list[dict[str, Any]]:
        """Get edges formatted for database insertion."""
        result = []
        for edge in self._edges.values():
            result.append({
                "id": edge.id,
                "search_id": self._search_id,
                "source_node_id": edge.source_id,
                "target_node_id": edge.target_id,
                "edge_type": edge.data.edge_type,
                "source_url": edge.data.source_url,
                "source_evidence_id": edge.data.source_evidence_id,
                "confidence": edge.data.confidence,
                "metadata": edge.data.metadata,
            })
        return result

    @classmethod
    def from_database(cls, search_id: int, nodes: list[dict], edges: list[dict]) -> "EvidenceGraph":
        """Reconstruct graph from database records."""
        graph = cls(search_id)
        graph._next_node_id = 1
        graph._next_edge_id = 1

        # Load nodes
        for node_data in nodes:
            node_id = node_data["id"]
            data = EvidenceNodeData(
                node_type=node_data["node_type"],
                entity_id=node_data["entity_id"],
                entity_value=node_data["entity_value"],
                attributes=node_data.get("attributes"),
                source_url=node_data.get("source_url"),
                source_evidence_id=node_data.get("source_evidence_id"),
            )
            graph._nodes[node_id] = _Node(id=node_id, data=data)
            graph._node_lookup[(data.node_type, data.entity_id)] = node_id
            graph._next_node_id = max(graph._next_node_id, node_id + 1)

        # Load edges
        for edge_data in edges:
            edge_id = edge_data["id"]
            data = EvidenceEdgeData(
                source_node_id=edge_data["source_node_id"],
                target_node_id=edge_data["target_node_id"],
                edge_type=edge_data["edge_type"],
                source_url=edge_data["source_url"],
                source_evidence_id=edge_data.get("source_evidence_id"),
                confidence=edge_data.get("confidence"),
                metadata=edge_data.get("metadata"),
            )
            graph._edges[edge_id] = _Edge(id=edge_id, source_id=edge_data["source_node_id"], target_id=edge_data["target_node_id"], data=data)
            graph._edge_lookup[(edge_data["source_node_id"], edge_data["target_node_id"], edge_data["edge_type"])] = edge_id
            graph._adjacency[edge_data["source_node_id"]].append(edge_data["target_node_id"])
            graph._reverse_adjacency[edge_data["target_node_id"]].append(edge_data["source_node_id"])
            graph._next_edge_id = max(graph._next_edge_id, edge_id + 1)

        return graph