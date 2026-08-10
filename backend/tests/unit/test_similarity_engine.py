"""Similarity engine unit tests (roadmap Phase 7)."""

import numpy as np
import pytest

from app.ai.matching.similarity_engine import SimilarityEngine


@pytest.fixture
def engine() -> SimilarityEngine:
    return SimilarityEngine(threshold=0.6, high_threshold=0.75, top_k=20)


def test_cosine_returns_one_for_identical(engine: SimilarityEngine):
    vec = np.asarray([1.0, 0.0, 0.0], dtype=np.float32)
    assert engine.cosine(vec, vec) == pytest.approx(1.0)


def test_cosine_zero_for_orthogonal(engine: SimilarityEngine):
    a = np.asarray([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.asarray([0.0, 1.0, 0.0], dtype=np.float32)
    assert engine.cosine(a, b) == pytest.approx(0.0)


def test_cosine_handles_zero_vector(engine: SimilarityEngine):
    zero = np.zeros(3, dtype=np.float32)
    vec = np.asarray([1.0, 0.0, 0.0], dtype=np.float32)
    assert engine.cosine(zero, vec) == 0.0


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.8, "high"),
        (0.75, "high"),
        (0.6, "medium"),
        (0.65, "medium"),
        (0.59, "low"),
        (0.0, "low"),
    ],
)
def test_confidence_bands(engine: SimilarityEngine, score: float, expected: str):
    assert engine.confidence(score) == expected


def test_keep_honors_threshold(engine: SimilarityEngine):
    assert engine.keep(0.6)
    assert not engine.keep(0.599)


def test_filter_results_drops_below_threshold(engine: SimilarityEngine):
    hits = [(1, 0.9), (2, 0.5), (3, 0.61)]
    assert engine.filter_results(hits) == [(1, 0.9), (3, 0.61)]


def test_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        SimilarityEngine(threshold=1.5)
    with pytest.raises(ValueError):
        SimilarityEngine(threshold=0.8, high_threshold=0.6)


def test_top_k_surfaces(engine: SimilarityEngine):
    assert engine.top_k == 20