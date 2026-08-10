"""Detected face repository (roadmap Phase 8 — Local Face Database).

Each indexed gallery/uploaded face becomes a DetectedFace row whose primary
key is reused as the FAISS entity id, so local search can join hits back to
their on-disk crop and embedding via Metadata Lookup.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import DetectedFace
from app.repositories.base import BaseRepository


class FaceRepository(BaseRepository[DetectedFace]):
    """Persistence for locally indexed faces."""

    async def create(
        self,
        search_id: int,
        face_image: str,
        embedding_path: str | None = None,
    ) -> DetectedFace:
        """Persist a detected face linked to a search job."""
        entry = DetectedFace(
            search_id=search_id,
            face_image=face_image,
            embedding_path=embedding_path,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_by_id(self, entity_id: int) -> DetectedFace | None:
        result = await self.session.execute(
            select(DetectedFace).where(DetectedFace.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_many(self, entity_ids: list[int]) -> list[DetectedFace]:
        """Fetch rows for a set of ids (metadata lookup for search hits)."""
        if not entity_ids:
            return []
        result = await self.session.execute(
            select(DetectedFace).where(DetectedFace.id.in_(entity_ids))
        )
        return list(result.scalars().all())

    async def list_for_search(self, search_id: int) -> list[DetectedFace]:
        result = await self.session.execute(
            select(DetectedFace)
            .where(DetectedFace.search_id == search_id)
            .order_by(DetectedFace.id)
        )
        return list(result.scalars().all())