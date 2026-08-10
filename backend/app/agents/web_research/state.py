"""Research state (roadmap Phase 21).

Tracks what the research agent has seen and prevents duplicate crawling.
All collections deduplicate; every evidence item keeps its source URL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.agents.web_research.schemas import Evidence


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ResearchState:
    """Mutable research session state."""

    seed_urls: list[str] = field(default_factory=list)
    visited_urls: set[str] = field(default_factory=set)
    discovered_urls: set[str] = field(default_factory=set)
    queries: list[str] = field(default_factory=list)
    images: set[str] = field(default_factory=set)
    profiles: set[str] = field(default_factory=set)
    evidence: list[Evidence] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tool_calls: int = 0
    started_at: datetime = field(default_factory=_utcnow)
    finished_at: datetime | None = None

    def add_visit(self, url: str) -> bool:
        """Register a visit; returns False when the URL was already visited."""
        if url in self.visited_urls:
            return False
        self.visited_urls.add(url)
        return True

    def add_discovered(self, url: str) -> bool:
        """Register a newly found URL; deduplicated."""
        if url in self.discovered_urls:
            return False
        self.discovered_urls.add(url)
        return True

    def record_evidence(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)

    def mark_finished(self) -> None:
        self.finished_at = _utcnow()

    def page_count(self) -> int:
        return len(self.visited_urls)

    def summary(self) -> dict:
        return {
            "seed_urls": len(self.seed_urls),
            "pages_visited": len(self.visited_urls),
            "pages_discovered": len(self.discovered_urls),
            "queries": len(self.queries),
            "images": len(self.images),
            "profiles": len(self.profiles),
            "evidence_items": len(self.evidence),
            "errors": len(self.errors),
            "tool_calls": self.tool_calls,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }