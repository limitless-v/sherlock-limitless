"""Similarity engine — roadmap Phase 7.

Wraps cosine similarity plus threshold matching and confidence bands.
Local search (Phase 9) filters FAISS hits by SIMILARITY_THRESHOLD and maps
the remaining scores to high / medium / low confidence for the normalized
SearchResult.consumers.
"""

import numpy as np

from app.ai.matching.similarity import cosine_similarity

DEFAULT_HIGH_THRESHOLD = 0.75


class SimilarityEngine:
    """Evaluate and label face-embedding similarity scores."""

    def __init__(self, threshold: float, high_threshold: float = DEFAULT_HIGH_THRESHOLD, top_k: int = 20) -> None:
        if not 0.0 <= threshold <= 1.0 or not 0.0 <= high_threshold <= 1.0:
            raise ValueError("Similarity thresholds must be within [0, 1]")
        if high_threshold < threshold:
            raise ValueError("high_threshold must be >= threshold")
        self._threshold = threshold
        self._high_threshold = high_threshold
        self._top_k = top_k

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def high_threshold(self) -> float:
        return self._high_threshold

    @property
    def top_k(self) -> int:
        return self._top_k

    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        return cosine_similarity(a, b)

    def keep(self, score: float) -> bool:
        """True when a score meets the match threshold."""
        return score >= self._threshold

    def confidence(self, score: float) -> str:
        """Map a score to a confidence label: high / medium / low."""
        if score >= self._high_threshold:
            return "high"
        if score >= self._threshold:
            return "medium"
        return "low"

    def filter_results(self, results: list[tuple[int, float]]) -> list[tuple[int, float]]:
        """Drop (entity_id, score) pairs below the match threshold."""
        return [(entity_id, score) for entity_id, score in results if self.keep(score)]