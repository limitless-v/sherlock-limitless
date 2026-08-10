"""Research agent schemas (roadmap Phase 19).

Output models for the research agent. Every `Evidence` carries its source
URL; confidence/strength is coarse and evidence-driven (no identity claims).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Evidence:
    """One traceable observation from a candidate page."""

    url: str
    kind: str  # page_text | link | image | profile_link | metadata
    text: str = ""
    metadata: dict = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "kind": self.kind,
            "text": self.text,
            "metadata": self.metadata,
            "discovered_at": self.discovered_at.isoformat(),
        }


@dataclass
class ResearchOutput:
    """Aggregated, traceable research results for a set of candidates."""

    candidates_seen: int = 0
    status: str = "completed"
    evidence: list[Evidence] = field(default_factory=list)
    profiles: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    source_metadata: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates_seen": self.candidates_seen,
            "status": self.status,
            "evidence": [e.to_dict() for e in self.evidence],
            "profiles": self.profiles,
            "images": self.images,
            "links": self.links,
            "source_metadata": self.source_metadata,
            "errors": self.errors,
        }