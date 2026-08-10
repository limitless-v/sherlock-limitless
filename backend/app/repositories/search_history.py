"""Search history repository (scaffold)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import SearchHistory
from app.repositories.base import BaseRepository


class SearchHistoryRepository(BaseRepository[SearchHistory]):
    """Persistence for search jobs."""

    async def create(self, uploaded_image: str, user_id: int | None = None) -> SearchHistory:
        """Persist a new search job for an uploaded image."""
        entry = SearchHistory(user_id=user_id, uploaded_image=uploaded_image)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def delete(self, entity_id: int, user_id: int | None = None) -> bool:
        """Delete a search record owned by (or orphaned from) a user."""
        entry = await self.get_by_id(entity_id)
        if entry is None or (user_id is not None and entry.user_id != user_id):
            return False
        await self._session.delete(entry)
        await self._session.flush()
        return True

    async def get_by_id(self, entity_id: int) -> SearchHistory | None:
        result = await self.session.execute(
            select(SearchHistory).where(SearchHistory.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int, limit: int = 50) -> list[SearchHistory]:
        result = await self.session.execute(
            select(SearchHistory)
            .where(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
