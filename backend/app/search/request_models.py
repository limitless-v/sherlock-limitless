"""Search request domain models (roadmap section 11)."""

from dataclasses import dataclass, field
from uuid import UUID

from app.search.modes import SearchMode


@dataclass(slots=True)
class SearchRequest:
    """Normalized search request accepted by the orchestrator.

    The API layer converts its HTTP payload into this model; the
    orchestrator must not see framework-specific request types.
    """

    image_id: UUID
    mode: SearchMode = SearchMode.INTERNET
    max_results: int = 50
    sources: list[str] = field(default_factory=list)
