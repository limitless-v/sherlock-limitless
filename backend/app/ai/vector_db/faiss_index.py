"""FAISS vector index — concrete VectorStore implementation (roadmap Phase 6).

Wraps a FAISS IndexIDMap2(IndexFlatIP). Embeddings are L2-normalized by the
Phase 5 generator, so inner product == cosine similarity: higher is better.

* vector ids == entity ids (e.g. DetectedFace ids) for later DB joins
* add() is an upsert — re-adding an existing id replaces its vector; FAISS
  itself reports the duplicate, so no client-side id bookkeeping is needed
* the index persists to disk via faiss.write_index and reloads automatically
* when constructed with Settings it self-configures lazily on first use
"""

import threading
from pathlib import Path

import numpy as np

from app.ai.vector_db.vector_store import VectorStore
from app.config.settings import Settings


class FaissIndex(VectorStore):
    """Local approximate nearest neighbor search via FAISS."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._index = None
        self._dim: int | None = None
        self._index_path: Path | None = None
        self._ids: set[int] = set()
        self._lock = threading.Lock()

        if settings is not None:
            self._dim = settings.embedding_dim
            self._index_path = settings.faiss_index_abs

    def _labels_path(self) -> Path | None:
        if self._index_path is None:
            return None
        return self._index_path.with_name(self._index_path.name + ".labels.npy")

    def load(self, index_path: Path, dim: int) -> None:
        """Load the index and its entity ids from disk, or start empty."""
        with self._lock:
            self._dim = dim
            self._index_path = Path(index_path)
            if self._index_path.is_file():
                import faiss

                self._index = faiss.read_index(str(self._index_path.resolve()))
                labels_path = self._labels_path()
                if labels_path is not None and labels_path.is_file():
                    self._ids = {int(v) for v in np.load(labels_path).tolist()}
                else:
                    self._ids = set()
            else:
                self._index = self._new_index(dim)
                self._ids = set()

    @staticmethod
    def _new_index(dim: int):
        import faiss

        return faiss.IndexIDMap2(faiss.IndexFlatIP(dim))

    def _ensure_loaded(self) -> None:
        if self._index is None:
            if self._index_path is None:
                raise RuntimeError("FaissIndex is not configured; call load(index_path, dim) first")
            self.load(self._index_path, self._dim)

    def search(self, vector, top_k: int) -> list[tuple[int, float]]:
        """Return (entity_id, cosine_score) pairs for the closest vectors."""
        self._ensure_loaded()
        if self.count == 0 or vector is None or len(vector) == 0:
            return []
        query = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        k = min(top_k, self.count)
        with self._lock:
            scores, labels = self._index.search(query, k)
        return [(int(labels[0, i]), float(scores[0, i])) for i in range(k)]

    def add(self, vector, entity_id: int) -> None:
        """Upsert a single embedding under the given entity id."""
        self._ensure_loaded()
        arr = np.asarray(vector, dtype=np.float32)
        if arr.size == 0:
            raise ValueError("Cannot add an empty embedding")
        arr = arr.reshape(1, -1)
        ids = np.asarray([entity_id], dtype=np.int64)
        with self._lock:
            if entity_id in self._ids:
                self._index.remove_ids(ids)
                self._ids.discard(entity_id)
            self._index.add_with_ids(arr, ids)
            self._ids.add(entity_id)

    def save(self) -> None:
        """Persist the index and its entity ids to disk."""
        self._ensure_loaded()
        if self._index_path is None:
            raise RuntimeError("No index path configured; call save to a path first")
        import faiss

        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            faiss.write_index(self._index, str(self._index_path.resolve()))
            labels_path = self._labels_path()
            if labels_path is not None:
                np.save(labels_path, np.asarray(sorted(self._ids), dtype=np.int64))

    @property
    def count(self) -> int:
        """Number of indexed vectors (lazily loads a configured index)."""
        if self._index is None:
            if self._index_path is None:
                return 0
            self.load(self._index_path, self._dim)
            if self._index is None:
                return 0
        return int(self._index.ntotal)