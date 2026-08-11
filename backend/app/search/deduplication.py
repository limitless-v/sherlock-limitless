"""Result deduplication (roadmap section 14).

Deduplicate candidates across sources by URL, normalized URL, username,
profile identifiers, or image hash. Never merge people solely on name.
"""

from app.search.result_models import SearchResult


class ResultDeduplicator:
    """Removes duplicate candidates discovered through multiple sources."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """Return a de-duplicated, order-preserving result list."""
        seen: set[str] = set()
        deduplicated: list[SearchResult] = []
        for result in results:
            # Use URL as primary deduplication key
            key = result.url
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(result)
        return deduplicated
