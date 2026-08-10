"""Normalized search result model (roadmap section 12-13).

Every provider (FAISS or Agent Reach) must return this common internal
structure so provider-specific data never spreads through the app.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.search.modes import SearchMode


@dataclass(slots=True)
class SearchResult:
    """One candidate profile/match normalized across all sources."""

    id: str
    source: str
    url: str
    title: str = ""
    username: str = ""
    display_name: str = ""
    image_urls: list[str] = field(default_factory=list)
    text: str = ""
    discovery_method: str = ""
    face_similarity: float = 0.0
    confidence: str = "low"
    discovered_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class SearchResponse:
    """Normalized orchestrator response for all search modes."""

    search_id: str
    mode: SearchMode
    status: str = "completed"
    results: list[SearchResult] = field(default_factory=list)
