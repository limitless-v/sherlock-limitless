"""Local search service (roadmap section 8, Phase 9).

Searches the locally indexed face database through the VectorStore
interface: embed the query image, run FAISS search, apply the similarity
threshold, then look up matching DetectedFace metadata for the hits.

When the index is empty or the query image has no face, it returns an
empty response instead of raising — the app must never assume a local
dataset exists. INTERNET / HYBRID modes are handled elsewhere.
"""

from pathlib import Path

from app.ai.embedding.face_embedder import FaceEmbedder
from app.ai.matching.similarity_engine import SimilarityEngine
from app.ai.vector_db.vector_store import VectorStore
from app.config.settings import Settings
from app.repositories.faces import FaceRepository
from app.search.modes import SearchMode
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse, SearchResult


class LocalSearchService:
    """FAISS-backed search against the local face index."""

    def __init__(
        self,
        vector_store: VectorStore,
        similarity_engine: SimilarityEngine,
        face_repository: FaceRepository,
        embedder: FaceEmbedder,
        settings: Settings,
    ) -> None:
        self._vector_store = vector_store
        self._similarity_engine = similarity_engine
        self._face_repository = face_repository
        self._embedder = embedder
        self._settings = settings

    @staticmethod
    def _empty_response(request: SearchRequest) -> SearchResponse:
        return SearchResponse(
            search_id=str(request.image_id),
            mode=SearchMode.LOCAL,
            status="completed",
        )

    def _resolve_upload(self, request: SearchRequest) -> Path | None:
        """Locate the stored upload for an image_id (filename encodes the UUID)."""
        uploads_dir = self._settings.uploads_dir
        try:
            candidates = sorted(uploads_dir.glob(f"{request.image_id}.*"))
        except OSError:
            return None
        return candidates[0] if candidates else None

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Return local candidates or an empty response for empty indexes."""
        if self._vector_store.count == 0:
            return self._empty_response(request)

        upload = self._resolve_upload(request)
        if upload is None or not upload.is_file():
            return self._empty_response(request)

        faces = self._embedder.embed_image(upload)
        if not faces:
            return self._empty_response(request)

        query_vec = faces[0].embedding
        top_k = min(request.max_results or self._settings.search_max_results, self._similarity_engine.top_k)
        raw_hits = self._vector_store.search(list(query_vec), top_k)
        kept = self._similarity_engine.filter_results(raw_hits)

        results: list[SearchResult] = []
        if kept:
            rows = await self._face_repository.get_many([entity_id for entity_id, _ in kept])
            by_id = {row.id: row for row in rows}
            for entity_id, score in kept:
                row = by_id.get(entity_id)
                results.append(
                    SearchResult(
                        id=str(entity_id),
                        source="local",
                        url=f"local://faces/{entity_id}",
                        title=f"Local face #{entity_id}",
                        display_name=f"Local face #{entity_id}",
                        face_similarity=round(score, 4),
                        confidence=self._similarity_engine.confidence(score),
                        discovery_method="faiss",
                        metadata={
                            "face_image": row.face_image if row else None,
                            "embedding_path": row.embedding_path if row else None,
                            "search_id": row.search_id if row else None,
                        },
                    )
                )

        return SearchResponse(
            search_id=str(request.image_id),
            mode=SearchMode.LOCAL,
            status="completed",
            results=results,
        )