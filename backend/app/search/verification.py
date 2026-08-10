"""Candidate image verification (roadmap section 15, Phase 15).

Verifies candidate images against the query face using local face AI
(ai.matching.similarity). Internet/OSINT sources never verify faces.
"""

from app.search.result_models import SearchResult


class CandidateVerifier:
    """Local face verification of candidate images."""

    def __init__(self, similarity_engine) -> None:
        self._similarity_engine = similarity_engine

    async def verify(self, result: SearchResult, query_embedding: list[float]) -> SearchResult:
        """Attach face_similarity / confidence to a candidate result."""
        raise NotImplementedError("Candidate verification not implemented in scaffold.")
