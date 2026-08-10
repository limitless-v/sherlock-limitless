"""Repository layer."""

from app.repositories.faces import FaceRepository
from app.repositories.search_history import SearchHistoryRepository

__all__ = ["FaceRepository", "SearchHistoryRepository"]
