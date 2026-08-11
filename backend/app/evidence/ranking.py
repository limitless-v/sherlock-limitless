"""Evidence ranking (roadmap Phase 27).

Ranks evidence by strength, separates observation from inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.evidence.schemas import EvidenceNodeData, EvidenceEdgeData


class EvidenceStrength(str, Enum):
    """Evidence strength levels."""
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class EvidenceType(str, Enum):
    """Evidence type classification."""
    OBSERVED = "observed"
    INFERENCE = "inference"
    UNCERTAIN = "uncertain"


@dataclass
class RankedEvidence:
    """Ranked evidence item with strength and type classification."""

    node_id: int
    edge_id: int | None
    evidence_strength: EvidenceStrength
    evidence_type: EvidenceType
    signals: list[str]
    confidence_score: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "edge_id": self.edge_id,
            "evidence_strength": self.evidence_strength.value,
            "evidence_type": self.evidence_type.value,
            "signals": self.signals,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
        }


class EvidenceRanker:
    """Rank evidence by strength and classify as observed/inference/uncertain."""

    def __init__(
        self,
        strong_threshold: float = 0.8,
        medium_threshold: float = 0.5,
        face_similarity_threshold: float = 0.75,
    ) -> None:
        self._strong_threshold = strong_threshold
        self._medium_threshold = medium_threshold
        self._face_similarity_threshold = face_similarity_threshold

    def rank_evidence(
        self,
        nodes: list[EvidenceNodeData],
        edges: list[EvidenceEdgeData],
        uploaded_image_node_id: int | None = None,
    ) -> list[RankedEvidence]:
        """Rank all evidence in the graph.

        Args:
            nodes: All evidence nodes
            edges: All evidence edges
            uploaded_image_node_id: ID of the uploaded image node (for correlation context)

        Returns:
            List of ranked evidence items
        """
        # Build adjacency for quick lookup
        node_map = {i: node for i, node in enumerate(nodes)}
        
        ranked: list[RankedEvidence] = []

        for i, edge in enumerate(edges):
            ranked_item = self._rank_edge(edge, node_map, i, uploaded_image_node_id)
            ranked.append(ranked_item)

        # Sort by confidence score descending
        ranked.sort(key=lambda x: x.confidence_score, reverse=True)
        return ranked

    def _rank_edge(
        self,
        edge: EvidenceEdgeData,
        node_map: dict[int, EvidenceNodeData],
        edge_index: int,
        uploaded_image_node_id: int | None,
    ) -> RankedEvidence:
        """Rank a single edge based on its type and metadata."""
        source_node = node_map.get(edge.source_node_id)
        target_node = node_map.get(edge.target_node_id)

        signals: list[str] = []
        confidence = 0.0

        # Base confidence from edge metadata
        if edge.confidence is not None:
            confidence = edge.confidence
            signals.append(f"correlation_confidence:{edge.confidence:.2f}")

        # Rank based on edge type
        if edge.edge_type == "same_image":
            # Image correlation - very strong evidence
            metadata = edge.metadata or {}
            classification = metadata.get("classification", "unknown")
            hamming = metadata.get("hamming_distance")
            face_sim = metadata.get("face_similarity")

            if classification == "exact_duplicate":
                confidence = max(confidence, 1.0)
                signals.append("exact_image_match_sha256")
            elif classification == "near_duplicate":
                confidence = max(confidence, 0.9)
                signals.append(f"near_duplicate_phash_hamming:{hamming}")
            elif classification == "similar":
                confidence = max(confidence, 0.7)
                signals.append(f"similar_phash_hamming:{hamming}")

            if face_sim is not None:
                signals.append(f"face_similarity:{face_sim:.2f}")
                if face_sim >= self._face_similarity_threshold:
                    confidence = max(confidence, 0.85)
                    signals.append("high_face_similarity")

            evidence_type = EvidenceType.OBSERVED
            if confidence >= self._strong_threshold:
                strength = EvidenceStrength.STRONG
            elif confidence >= self._medium_threshold:
                strength = EvidenceStrength.MEDIUM
            else:
                strength = EvidenceStrength.WEAK

        elif edge.edge_type == "image_found_on":
            # Image found on a page
            confidence = max(confidence, 0.8)
            signals.append("image_found_on_page")
            evidence_type = EvidenceType.OBSERVED
            if confidence >= self._strong_threshold:
                strength = EvidenceStrength.STRONG
            else:
                strength = EvidenceStrength.MEDIUM

        elif edge.edge_type == "same_public_identifier":
            # Same username/handle across sources
            confidence = max(confidence, 0.85)
            signals.append("same_public_identifier")
            evidence_type = EvidenceType.OBSERVED
            if confidence >= self._strong_threshold:
                strength = EvidenceStrength.STRONG
            else:
                strength = EvidenceStrength.MEDIUM

        elif edge.edge_type == "links_to":
            # URL links to another URL
            confidence = max(confidence, 0.4)
            signals.append("hyperlink")
            evidence_type = EvidenceType.INFERENCE
            strength = EvidenceStrength.WEAK

        elif edge.edge_type == "mentions":
            # Username mentioned on page
            confidence = max(confidence, 0.3)
            signals.append("username_mention")
            evidence_type = EvidenceType.INFERENCE
            strength = EvidenceStrength.WEAK

        elif edge.edge_type == "located_at":
            # Location associated
            confidence = max(confidence, 0.3)
            signals.append("location_association")
            evidence_type = EvidenceType.INFERENCE
            strength = EvidenceStrength.WEAK

        elif edge.edge_type == "published_at":
            # Timestamp association
            confidence = max(confidence, 0.3)
            signals.append("timestamp_association")
            evidence_type = EvidenceType.INFERENCE
            strength = EvidenceStrength.WEAK

        else:
            # Unknown edge type
            confidence = max(confidence, 0.1)
            signals.append("unknown_edge_type")
            evidence_type = EvidenceType.UNCERTAIN
            strength = EvidenceStrength.WEAK

        # Adjust for generic names/locations (weaken)
        if source_node and target_node:
            if source_node.node_type == "username" and target_node.node_type == "url":
                # Could be generic username
                pass  # Keep as is for now

        # Build metadata
        metadata = {
            "source_node_type": source_node.node_type if source_node else "unknown",
            "target_node_type": target_node.node_type if target_node else "unknown",
            "source_node_value": source_node.entity_value if source_node else "unknown",
            "target_node_value": target_node.entity_value if target_node else "unknown",
            "edge_metadata": edge.metadata,
        }

        return RankedEvidence(
            node_id=edge.target_node_id,
            edge_id=edge_index,
            evidence_strength=strength,
            evidence_type=evidence_type,
            signals=signals,
            confidence_score=round(confidence, 3),
            metadata=metadata,
        )