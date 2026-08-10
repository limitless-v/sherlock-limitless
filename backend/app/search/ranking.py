"""Ranking engine (roadmap section 15, Phase 18).

Merges FAISS similarity, verification, and OSINT signals into a single
confidence score and sorts candidates.
"""

from dataclasses import dataclass

from app.search.result_models import SearchResult


@dataclass
class RankedMatch:
    """Internal ranked candidate representation."""

    result: SearchResult
    confidence: float


class ResultRanker:
    """Combine signals into one score and rank candidates."""

    def rank(self, candidates: list[RankedMatch]) -> list[RankedMatch]:
        return sorted(candidates, key=lambda c: c.confidence, reverse=True)
