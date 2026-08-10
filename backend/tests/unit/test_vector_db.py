"""FAISS vector store unit tests (roadmap Phase 6).

faiss-cpu is a plain dependency of Phase 6, so these run unconditionally.
They use tmp_path to avoid touching the development index.
"""

import numpy as np
import pytest

from app.ai.vector_db.faiss_index import FaissIndex

DIM = 512


@pytest.fixture
def store(tmp_path) -> FaissIndex:
    s = FaissIndex()
    s.load(tmp_path / "faiss.bin", DIM)
    return s


def _embed(seed: float) -> list[float]:
    rng = np.random.default_rng(int(seed))
    raw = rng.standard_normal(DIM).astype(np.float32)
    v = raw / np.linalg.norm(raw)
    return [float(x) for x in v]


def test_empty_index_search_returns_nothing(store: FaissIndex):
    assert store.count == 0
    assert store.search(_embed(0), 5) == []


def test_add_increases_count(store: FaissIndex):
    store.add(_embed(1), 1)
    store.add(_embed(2), 2)
    assert store.count == 2


def test_search_returns_best_match_first(store: FaissIndex):
    store.add(_embed(1), 1)
    store.add(_embed(2), 2)
    results = store.search(_embed(2), 3)
    assert results[0][0] == 2
    assert results[0][1] > 0.99
    assert len(results) == 2
    assert results[0][1] >= results[1][1]


def test_top_k_limits_results(store: FaissIndex):
    for i in range(1, 6):
        store.add(_embed(i), i)
    results = store.search(_embed(1), 3)
    assert len(results) == 3


def test_upsert_replaces_existing_id(store: FaissIndex):
    store.add(_embed(1), 7)
    store.add(_embed(2), 8)
    store.add(_embed(3), 7)
    assert store.count == 2
    results = store.search(_embed(3), 1)
    assert results[0][0] == 7
    assert results[0][1] > 0.99


def test_save_and_reload_roundtrip(store: FaissIndex, tmp_path):
    store.add(_embed(1), 1)
    store.add(_embed(2), 2)
    store.save()

    reloaded = FaissIndex()
    reloaded.load(tmp_path / "faiss.bin", DIM)
    assert reloaded.count == 2
    results = reloaded.search(_embed(2), 1)
    assert results[0][0] == 2
    assert results[0][1] > 0.99


def test_load_missing_file_initializes_empty(store: FaissIndex):
    assert store.count == 0
    store.add(_embed(1), 1)
    assert store.count == 1