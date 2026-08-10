"""Vector store port — infrastructure boundary for local search.

ai.vector_db implements vector search (FAISS today); search/local_search
depends on this interface, not on a concrete implementation (roadmap
section 2, 8).
"""

from abc import ABC, abstractmethod
from pathlib import Path


class VectorStore(ABC):
    """Abstract nearest-neighbor search over face embeddings."""

    @abstractmethod
    def load(self, index_path: Path, dim: int) -> None:
        """Load or initialize the index file."""

    @abstractmethod
    def search(self, vector: list[float], top_k: int) -> list[tuple[int, float]]:
        """Return (id, score) pairs for the most similar vectors.

        Returns [] when the index contains no vectors.
        """

    @abstractmethod
    def add(self, vector: list[float], entity_id: int) -> None:
        """Add an embedding to the index."""

    @abstractmethod
    def save(self) -> None:
        """Persist the current index to disk."""

    @property
    @abstractmethod
    def count(self) -> int:
        """Number of indexed vectors."""