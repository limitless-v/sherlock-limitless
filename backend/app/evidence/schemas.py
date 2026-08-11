"""Candidate extraction schemas (roadmap Phase 23).

Normalized data structures for extracted candidate information.

Evidence Graph schemas (roadmap Phase 24).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CandidateImageData:
    """Image found on a candidate page."""

    image_url: str
    local_path: str | None = None
    sha256: str | None = None
    a_hash: str | None = None
    d_hash: str | None = None
    p_hash: str | None = None
    width: int | None = None
    height: int | None = None
    content_type: str | None = None
    file_size: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_url": self.image_url,
            "local_path": self.local_path,
            "sha256": self.sha256,
            "a_hash": self.a_hash,
            "d_hash": self.d_hash,
            "p_hash": self.p_hash,
            "width": self.width,
            "height": self.height,
            "content_type": self.content_type,
            "file_size": self.file_size,
        }


@dataclass
class CandidateProfileData:
    """Public profile link found on a candidate page."""

    profile_url: str
    platform: str
    username: str | None = None
    display_name: str | None = None
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_url": self.profile_url,
            "platform": self.platform,
            "username": self.username,
            "display_name": self.display_name,
            "source_url": self.source_url,
        }


@dataclass
class CandidateLocationData:
    """Location extracted from a candidate page."""

    location: str
    location_type: str | None = None
    source_text: str | None = None
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "location_type": self.location_type,
            "source_text": self.source_text,
            "confidence": self.confidence,
        }


@dataclass
class CandidateDateData:
    """Date/timestamp extracted from a candidate page."""

    date_value: datetime
    date_type: str | None = None
    source_text: str | None = None
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "date_value": self.date_value.isoformat() if self.date_value else None,
            "date_type": self.date_type,
            "source_text": self.source_text,
            "confidence": self.confidence,
        }


@dataclass
class CandidateExtraction:
    """Complete extracted candidate from a researched page.

    Matches the roadmap Phase 23 JSON structure:
    {
      "url": "",
      "domain": "",
      "title": "",
      "images": [],
      "links": [],
      "public_identifiers": [],
      "public_profile_links": [],
      "locations": [],
      "dates": []
    }
    """

    url: str
    domain: str
    title: str = ""
    source: str = "unknown"
    kind: str = "web"
    reason: str = ""
    metadata: dict = field(default_factory=dict)
    images: list[CandidateImageData] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    public_identifiers: list[str] = field(default_factory=list)  # usernames, handles
    public_profile_links: list[CandidateProfileData] = field(default_factory=list)
    locations: list[CandidateLocationData] = field(default_factory=list)
    dates: list[CandidateDateData] = field(default_factory=list)
    discovered_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "domain": self.domain,
            "title": self.title,
            "source": self.source,
            "kind": self.kind,
            "reason": self.reason,
            "metadata": self.metadata,
            "images": [img.to_dict() for img in self.images],
            "links": self.links,
            "public_identifiers": self.public_identifiers,
            "public_profile_links": [p.to_dict() for p in self.public_profile_links],
            "locations": [loc.to_dict() for loc in self.locations],
            "dates": [d.to_dict() for d in self.dates],
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
        }

    @classmethod
    def from_candidate(cls, candidate: "Candidate") -> "CandidateExtraction":
        """Create from ORM Candidate (imported locally to avoid circular)."""
        from app.models.entities import Candidate as ORMCandidate
        from app.models.entities import CandidateExtractedImage, CandidateProfile, CandidateLocation, CandidateDate

        if not isinstance(candidate, ORMCandidate):
            raise TypeError("Expected ORM Candidate")

        return cls(
            url=candidate.url,
            domain=candidate.domain,
            title=candidate.title or "",
            source=candidate.source,
            kind=candidate.kind,
            reason=candidate.reason or "",
            metadata=candidate.metadata or {},
            images=[
                CandidateImageData(
                    image_url=img.image_url,
                    local_path=img.local_path,
                    sha256=img.sha256,
                    a_hash=img.a_hash,
                    d_hash=img.d_hash,
                    p_hash=img.p_hash,
                    width=img.width,
                    height=img.height,
                    content_type=img.content_type,
                    file_size=img.file_size,
                )
                for img in candidate.images
            ],
            links=[],  # Links not stored separately in this schema
            public_identifiers=[],  # Usernames from profiles
            public_profile_links=[
                CandidateProfileData(
                    profile_url=p.profile_url,
                    platform=p.platform,
                    username=p.username,
                    display_name=p.display_name,
                    source_url=p.source_url,
                )
                for p in candidate.profiles
            ],
            locations=[
                CandidateLocationData(
                    location=loc.location,
                    location_type=loc.location_type,
                    source_text=loc.source_text,
                    confidence=loc.confidence,
                )
                for loc in candidate.locations
            ],
            dates=[
                CandidateDateData(
                    date_value=d.date_value,
                    date_type=d.date_type,
                    source_text=d.source_text,
                    confidence=d.confidence,
                )
                for d in candidate.dates
            ],
            discovered_at=candidate.discovered_at,
        )


# --- Evidence Graph (Phase 24) ---


@dataclass
class EvidenceNodeData:
    """Node data for evidence graph."""

    node_type: str  # image, url, domain, profile, username, website, organization, location
    entity_id: str  # unique identifier for the entity (e.g., URL, username, domain)
    entity_value: str  # human-readable value
    attributes: dict | None = None
    source_url: str | None = None
    source_evidence_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_type": self.node_type,
            "entity_id": self.entity_id,
            "entity_value": self.entity_value,
            "attributes": self.attributes,
            "source_url": self.source_url,
            "source_evidence_id": self.source_evidence_id,
        }


@dataclass
class EvidenceEdgeData:
    """Edge data for evidence graph."""

    source_node_id: int
    target_node_id: int
    edge_type: str  # image_found_on, links_to, same_public_identifier, same_image, mentions, published_at, located_at
    source_url: str
    source_evidence_id: int | None = None
    confidence: float | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "source_url": self.source_url,
            "source_evidence_id": self.source_evidence_id,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class EvidenceGraphData:
    """Serialized evidence graph for API response."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
        }