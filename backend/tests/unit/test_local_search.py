"""Local search service unit tests (roadmap Phase 9).

Runs the real LocalSearchService with a stub vector store, a stub embedder
(no model needed), and an in-memory SQLite database. Settings are replaced
by a lightweight namespace so the development uploads folder is untouched.
"""

from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.ai.embedding.face_embedder import FaceEmbedder, FaceEmbedding
from app.ai.matching.similarity_engine import SimilarityEngine
from app.ai.vector_db.vector_store import VectorStore
from app.database.base import Base
from app.repositories.faces import FaceRepository
from app.repositories.search_history import SearchHistoryRepository
from app.search.local_search import LocalSearchService
from app.search.modes import SearchMode
from app.search.request_models import SearchRequest

DIM = 512


class StubVectorStore(VectorStore):
    def __init__(self, hits: list[tuple[int, float]]) -> None:
        self._hits = hits

    def load(self, index_path, dim):
        pass

    def search(self, vector, top_k):
        return self._hits[:top_k]

    def add(self, vector, entity_id):
        pass

    def save(self):
        pass

    @property
    def count(self) -> int:
        return len(self._hits)


class StubEmbedder(FaceEmbedder):
    def __init__(self, embeddings: list[np.ndarray]) -> None:
        self._embeddings = embeddings

    def embed_image(self, path):
        return [
            FaceEmbedding(embedding=vec, face_index=idx) for idx, vec in enumerate(self._embeddings)
        ]


async def _make_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
    return engine, session


def _make_request() -> SearchRequest:
    return SearchRequest(image_id=uuid4(), mode=SearchMode.LOCAL, max_results=10)


def _query_vec() -> list[float]:
    v = np.random.default_rng(7).standard_normal(DIM).astype(np.float32)
    v /= np.linalg.norm(v)
    return [float(x) for x in v]


def _make_service(session: AsyncSession, store: VectorStore, embedder: FaceEmbedder, uploads_dir) -> LocalSearchService:
    settings = SimpleNamespace(uploads_dir=uploads_dir, search_max_results=50)
    return LocalSearchService(
        vector_store=store,
        similarity_engine=SimilarityEngine(threshold=0.6, top_k=20),
        face_repository=FaceRepository(session),
        embedder=embedder,
        settings=settings,
    )


async def _create_face_row(session: AsyncSession) -> int:
    search = await SearchHistoryRepository(session).create(uploaded_image="gallery.jpg")
    face = await FaceRepository(session).create(search_id=search.id, face_image="1/1.jpg")
    return face.id


async def _write_upload(request: SearchRequest, uploads_dir) -> None:
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / f"{request.image_id}.jpg").write_bytes(b"fake")


async def _close_db(engine, session) -> None:
    await session.close()
    await engine.dispose()


async def test_empty_index_returns_empty(tmp_path):
    engine, session = await _make_db()
    try:
        service = _make_service(session, StubVectorStore([]), StubEmbedder([np.asarray(_query_vec(), dtype=np.float32)]), tmp_path)
        response = await service.search(_make_request())
        assert response.mode == SearchMode.LOCAL
        assert response.results == []
    finally:
        await _close_db(engine, session)


async def test_missing_upload_returns_empty(tmp_path):
    engine, session = await _make_db()
    try:
        hits = [(99, 0.9)]
        service = _make_service(session, StubVectorStore(hits), StubEmbedder([np.asarray(_query_vec(), dtype=np.float32)]), tmp_path)
        response = await service.search(_make_request())
        assert response.results == []
    finally:
        await _close_db(engine, session)


async def test_no_face_in_query_returns_empty(tmp_path):
    request = _make_request()
    await _write_upload(request, tmp_path)
    engine, session = await _make_db()
    try:
        service = _make_service(session, StubVectorStore([(1, 0.9)]), StubEmbedder([]), tmp_path)
        response = await service.search(request)
        assert response.results == []
    finally:
        await _close_db(engine, session)


async def test_match_looks_up_metadata(tmp_path):
    request = _make_request()
    await _write_upload(request, tmp_path)
    engine, session = await _make_db()
    try:
        face_id = await _create_face_row(session)
        await session.commit()
        service = _make_service(session, StubVectorStore([(face_id, 0.9)]), StubEmbedder([np.asarray(_query_vec(), dtype=np.float32)]), tmp_path)
        response = await service.search(request)
        assert len(response.results) == 1
        result = response.results[0]
        assert result.source == "local"
        assert result.url == f"local://faces/{face_id}"
        assert result.face_similarity == pytest.approx(0.9)
        assert result.confidence == "high"
        assert result.metadata["face_image"] == "1/1.jpg"
    finally:
        await _close_db(engine, session)


async def test_below_threshold_is_dropped(tmp_path):
    request = _make_request()
    await _write_upload(request, tmp_path)
    engine, session = await _make_db()
    try:
        face_id = await _create_face_row(session)
        await session.commit()
        service = _make_service(session, StubVectorStore([(face_id, 0.4)]), StubEmbedder([np.asarray(_query_vec(), dtype=np.float32)]), tmp_path)
        response = await service.search(request)
        assert response.results == []
    finally:
        await _close_db(engine, session)


async def test_medium_confidence(tmp_path):
    request = _make_request()
    await _write_upload(request, tmp_path)
    engine, session = await _make_db()
    try:
        face_id = await _create_face_row(session)
        await session.commit()
        service = _make_service(session, StubVectorStore([(face_id, 0.64)]), StubEmbedder([np.asarray(_query_vec(), dtype=np.float32)]), tmp_path)
        response = await service.search(request)
        assert response.results[0].confidence == "medium"
    finally:
        await _close_db(engine, session)