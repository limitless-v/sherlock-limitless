"""Repository interfaces and base (scaffold)."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract repository for persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> T | None:
        """Fetch entity by primary key."""
