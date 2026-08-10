"""FastAPI dependency providers.

Wires the SearchOrchestrator (and its strategy components) via
Depends. The API layer stays thin — it only calls the orchestrator.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.matching.similarity import cosine_similarity
from app.ai.matching.similarity_engine import SimilarityEngine
from app.ai.embedding.face_embedder import FaceEmbedder, InsightFaceEmbedder
from app.ai.face_detection.detector import FaceDetector
from app.ai.embedding.generator import EmbeddingGenerator
from app.ai.vector_db.faiss_index import FaissIndex
from app.ai.vector_db.vector_store import VectorStore
from app.config.settings import Settings, get_settings
from app.database.session import get_db_session
from app.osint.agent_reach.client import AgentReachClient
from app.osint.crawler.images import CandidateCrawler
from app.repositories.faces import FaceRepository
from app.repositories.search_history import SearchHistoryRepository
from app.search.deduplication import ResultDeduplicator
from app.search.hybrid_search import HybridSearchService
from app.search.internet_search import InternetSearchService
from app.search.local_search import LocalSearchService
from app.search.modes import SearchMode
from app.search.orchestrator import SearchOrchestrator
from app.search.ranking import ResultRanker
from app.search.verification import CandidateVerifier
from app.services.face_indexing_service import FaceIndexingService
from app.services.search_service import SearchService
from app.services.upload_service import UploadService


async def get_settings_dep() -> Settings:
    return get_settings()


async def get_session(session: AsyncSession = Depends(get_db_session)) -> AsyncGenerator[AsyncSession, None]:
    yield session


def get_upload_service(
    settings: Settings = Depends(get_settings_dep),
    session: AsyncSession = Depends(get_session),
) -> UploadService:
    return UploadService(settings, SearchHistoryRepository(session))


def get_vector_store(settings: Settings = Depends(get_settings_dep)) -> VectorStore:
    """Configured FAISS vector store (lazy-loads embeddings/faiss.index)."""
    return FaissIndex(settings)


def get_face_detector(settings: Settings = Depends(get_settings_dep)) -> FaceDetector:
    """Lazy-singleton face detector (model downloads on first detection)."""
    return FaceDetector(settings)


def get_embedding_generator(settings: Settings = Depends(get_settings_dep)) -> EmbeddingGenerator:
    """Lazy-singleton ArcFace embedding generator."""
    return EmbeddingGenerator(settings)


def get_face_embedder(settings: Settings = Depends(get_settings_dep)) -> FaceEmbedder:
    """Face detect+align+embed pipeline (Phase 3-5, composed for Phases 8-9)."""
    return InsightFaceEmbedder(settings)


def get_similarity_engine(settings: Settings = Depends(get_settings_dep)) -> SimilarityEngine:
    return SimilarityEngine(
        threshold=settings.similarity_threshold,
        top_k=settings.faiss_top_k,
    )


def get_face_repository(session: AsyncSession = Depends(get_session)) -> FaceRepository:
    return FaceRepository(session)


def get_agent_reach_client() -> AgentReachClient:
    return AgentReachClient()


def get_candidate_crawler() -> CandidateCrawler:
    return CandidateCrawler()


def get_local_search_service(
    vector_store: VectorStore = Depends(get_vector_store),
    similarity_engine: SimilarityEngine = Depends(get_similarity_engine),
    face_repository: FaceRepository = Depends(get_face_repository),
    embedder: FaceEmbedder = Depends(get_face_embedder),
    settings: Settings = Depends(get_settings_dep),
) -> LocalSearchService:
    return LocalSearchService(
        vector_store=vector_store,
        similarity_engine=similarity_engine,
        face_repository=face_repository,
        embedder=embedder,
        settings=settings,
    )


def get_face_indexing_service(
    settings: Settings = Depends(get_settings_dep),
    session: AsyncSession = Depends(get_session),
    embedder: FaceEmbedder = Depends(get_face_embedder),
    vector_store: VectorStore = Depends(get_vector_store),
    face_repo: FaceRepository = Depends(get_face_repository),
) -> FaceIndexingService:
    return FaceIndexingService(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
        face_repo=face_repo,
        search_repo=SearchHistoryRepository(session),
    )


def get_internet_search_service(
    client: AgentReachClient = Depends(get_agent_reach_client),
    crawler: CandidateCrawler = Depends(get_candidate_crawler),
) -> InternetSearchService:
    return InternetSearchService(client, crawler)


def get_hybrid_search_service(
    local_search: LocalSearchService = Depends(get_local_search_service),
    internet_search: InternetSearchService = Depends(get_internet_search_service),
) -> HybridSearchService:
    return HybridSearchService(local_search, internet_search)


def get_candidate_verifier() -> CandidateVerifier:
    return CandidateVerifier(cosine_similarity)


def get_result_deduplicator() -> ResultDeduplicator:
    return ResultDeduplicator()


def get_result_ranker() -> ResultRanker:
    return ResultRanker()


def get_search_orchestrator(
    local_search: LocalSearchService = Depends(get_local_search_service),
    internet_search: InternetSearchService = Depends(get_internet_search_service),
    hybrid_search: HybridSearchService = Depends(get_hybrid_search_service),
    deduplicator: ResultDeduplicator = Depends(get_result_deduplicator),
    verifier: CandidateVerifier = Depends(get_candidate_verifier),
    ranker: ResultRanker = Depends(get_result_ranker),
    settings: Settings = Depends(get_settings_dep),
) -> SearchOrchestrator:
    return SearchOrchestrator(
        local_search=local_search,
        internet_search=internet_search,
        hybrid_search=hybrid_search,
        deduplicator=deduplicator,
        verifier=verifier,
        ranker=ranker,
        default_mode=SearchMode(settings.search_default_mode),
    )


def get_search_service(
    orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
) -> SearchService:
    return SearchService(orchestrator=orchestrator)
