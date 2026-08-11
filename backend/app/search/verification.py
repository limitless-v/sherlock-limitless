"""Candidate image verification (roadmap section 15, Phase 15).

Verifies candidate images against the query face using local face AI
(ai.matching.similarity). Internet/OSINT sources never verify faces.
"""

from app.search.result_models import SearchResult


class CandidateVerifier:
    """Local face verification of candidate images."""

    def __init__(self, similarity_engine) -> None:
        self._similarity_engine = similarity_engine

    def verify(self, results: list[SearchResult], query_embedding: list[float] | None = None) -> list[SearchResult]:
        """Attach face_similarity / confidence to candidate results.
        
        If query_embedding is not provided, returns results unchanged.
        """
        if query_embedding is None:
            return results
        # TODO: Implement actual face verification against query_embedding
        return results
