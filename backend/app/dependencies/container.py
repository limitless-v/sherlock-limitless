"""FastAPI dependency providers.

Wires the SearchOrchestrator (and its strategy components) via
Depends. The API layer stays thin — it only calls the orchestrator.
"""

from collections.abc import AsyncGenerator

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.matching.similarity import cosine_similarity
from app.ai.matching.similarity_engine import SimilarityEngine
from app.ai.embedding.face_embedder import FaceEmbedder, InsightFaceEmbedder
from app.ai.face_detection.detector import FaceDetector
from app.ai.embedding.generator import EmbeddingGenerator
from app.ai.vector_db.faiss_index import FaissIndex
from app.ai.vector_db.vector_store import VectorStore
from app.agents.web_research.agent import ResearchAgent
from app.agents.web_research.policies import CrawlPolicies
from app.agents.web_research.tools import WebToolbox
from app.config.settings import Settings, get_settings
from app.database.session import get_db_session
from app.discovery.context.exif import ExifExtractor
from app.discovery.context.ocr import TesseractOCREngine
from app.discovery.context.visual import HeuristicVisualAnalyzer
from app.discovery.context.builder import SearchContextBuilder
from app.discovery.engine import DiscoveryEngine
from app.discovery.fingerprinting import FingerprintService
from app.evidence.graph import EvidenceGraph
from app.evidence.ranking import EvidenceRanker
from app.osint.agent_reach.capabilities import AgentReachCapabilities
from app.osint.agent_reach.client import AgentReachClient
from app.osint.agent_reach.provider import AgentReachWebProvider
from app.osint.crawler.images import CandidateCrawler
from app.repositories.candidates import CandidateRepository
from app.repositories.evidence_graph import EvidenceGraphRepository
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
from app.services.candidate_service import CandidateService
from app.services.correlation_service import CorrelationService
from app.services.evidence_graph_service import EvidenceGraphService
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


def get_agent_reach_client(settings: Settings = Depends(get_settings_dep)) -> AgentReachClient:
    return AgentReachClient(
        cmd=settings.agent_reach_cmd or None,
        timeout_seconds=settings.agent_reach_timeout_seconds,
        search_channel=settings.agent_reach_search_channel,
    )


def get_agent_reach_capabilities(
    client: AgentReachClient = Depends(get_agent_reach_client),
) -> AgentReachCapabilities:
    capabilities = AgentReachCapabilities()
    capabilities.refresh(client)
    return capabilities


def get_agent_reach_web_provider(
    client: AgentReachClient = Depends(get_agent_reach_client),
    capabilities: AgentReachCapabilities = Depends(get_agent_reach_capabilities),
    settings: Settings = Depends(get_settings_dep),
) -> AgentReachWebProvider:
    return AgentReachWebProvider(client, capabilities, enabled=settings.agent_reach_enabled)


def get_candidate_crawler() -> CandidateCrawler:
    return CandidateCrawler()


def get_exif_extractor() -> ExifExtractor:
    return ExifExtractor()


def get_ocr_engine(settings: Settings = Depends(get_settings_dep)) -> TesseractOCREngine:
    return TesseractOCREngine(
        languages=tuple(lang.strip() for lang in settings.ocr_language.split(",") if lang.strip()),
        tesseract_cmd=settings.tesseract_path or None,
    )


def get_visual_analyzer() -> HeuristicVisualAnalyzer:
    return HeuristicVisualAnalyzer()


def get_fingerprint_service() -> FingerprintService:
    return FingerprintService()


def get_context_builder(
    exif: ExifExtractor = Depends(get_exif_extractor),
    ocr: TesseractOCREngine = Depends(get_ocr_engine),
    visual: HeuristicVisualAnalyzer = Depends(get_visual_analyzer),
    fingerprinter: FingerprintService = Depends(get_fingerprint_service),
) -> SearchContextBuilder:
    return SearchContextBuilder(
        exif_extractor=exif,
        ocr_engine=ocr,
        visual_analyzer=visual,
        fingerprint_service=fingerprinter,
    )


def get_discovery_engine(
    settings: Settings = Depends(get_settings_dep),
    agent_reach: AgentReachWebProvider = Depends(get_agent_reach_web_provider),
) -> DiscoveryEngine:
    return DiscoveryEngine(
        web_providers=[agent_reach],
        max_candidates=settings.discovery_max_candidates,
    )


def get_agent_policies(settings: Settings = Depends(get_settings_dep)) -> CrawlPolicies:
    allow = tuple(d.strip().lower() for d in settings.agent_allow_domains.split(",") if d.strip())
    return CrawlPolicies(
        max_pages=settings.agent_max_pages,
        max_depth=settings.agent_max_depth,
        max_images=settings.agent_max_images,
        max_runtime_seconds=settings.agent_max_runtime_seconds,
        max_requests_per_domain=settings.agent_max_requests_per_domain,
        per_domain_min_interval=settings.agent_per_domain_min_interval,
        timeout_seconds=settings.agent_http_timeout_seconds,
        respect_robots=settings.agent_respect_robots,
        user_agent=settings.http_user_agent,
        allow_domains=allow,
    )


def get_web_toolbox(
    policies: CrawlPolicies = Depends(get_agent_policies),
) -> WebToolbox:
    client = httpx.AsyncClient(
        timeout=policies.timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": policies.user_agent},
    )
    return WebToolbox(client, policies)


def get_candidate_repository(session: AsyncSession = Depends(get_session)) -> CandidateRepository:
    return CandidateRepository(session)


def get_evidence_graph_repository(session: AsyncSession = Depends(get_session)) -> EvidenceGraphRepository:
    return EvidenceGraphRepository(session)


def get_evidence_graph_service(
    session: AsyncSession = Depends(get_session),
) -> EvidenceGraphService:
    return EvidenceGraphService(session=session)


def get_correlation_service(
    session: AsyncSession = Depends(get_session),
    fingerprint_service: FingerprintService = Depends(get_fingerprint_service),
    face_embedder: FaceEmbedder = Depends(get_face_embedder),
    settings: Settings = Depends(get_settings_dep),
) -> CorrelationService:
    return CorrelationService(
        session=session,
        fingerprint_service=fingerprint_service,
        face_embedder=face_embedder,
        p_hash_threshold_exact=settings.crawler_p_hash_threshold_exact,
        p_hash_threshold_near=settings.crawler_p_hash_threshold_near,
        p_hash_threshold_similar=settings.crawler_p_hash_threshold_similar,
        face_similarity_threshold=settings.similarity_threshold,
    )


def get_candidate_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings_dep),
) -> CandidateService:
    return CandidateService(
        session=session,
        max_images_per_candidate=settings.candidate_max_images_per_page,
        max_profiles_per_candidate=settings.candidate_max_profiles_per_page,
    )


def get_research_agent(
    policies: CrawlPolicies = Depends(get_agent_policies),
    toolbox: WebToolbox = Depends(get_web_toolbox),
    candidate_service: CandidateService = Depends(get_candidate_service),
    evidence_graph_service: EvidenceGraphService = Depends(get_evidence_graph_service),
) -> ResearchAgent:
    return ResearchAgent(policies=policies, toolbox=toolbox, candidate_service=candidate_service, evidence_graph_service=evidence_graph_service)


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
    engine: DiscoveryEngine = Depends(get_discovery_engine),
    context_builder: SearchContextBuilder = Depends(get_context_builder),
    settings: Settings = Depends(get_settings_dep),
    research_agent: ResearchAgent = Depends(get_research_agent),
    candidate_service: CandidateService = Depends(get_candidate_service),
    evidence_graph_service: EvidenceGraphService = Depends(get_evidence_graph_service),
    correlation_service: CorrelationService = Depends(get_correlation_service),
) -> InternetSearchService:
    return InternetSearchService(engine, context_builder, settings, research_agent=research_agent, candidate_service=candidate_service, evidence_graph_service=evidence_graph_service, correlation_service=correlation_service)


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


def get_evidence_ranker(settings: Settings = Depends(get_settings_dep)) -> EvidenceRanker:
    return EvidenceRanker(
        strong_threshold=settings.ranking_strong_threshold,
        medium_threshold=settings.ranking_medium_threshold,
        face_similarity_threshold=settings.similarity_threshold,
    )


def get_search_orchestrator(
    local_search: LocalSearchService = Depends(get_local_search_service),
    internet_search: InternetSearchService = Depends(get_internet_search_service),
    hybrid_search: HybridSearchService = Depends(get_hybrid_search_service),
    deduplicator: ResultDeduplicator = Depends(get_result_deduplicator),
    verifier: CandidateVerifier = Depends(get_candidate_verifier),
    ranker: ResultRanker = Depends(get_result_ranker),
    evidence_ranker: EvidenceRanker = Depends(get_evidence_ranker),
    settings: Settings = Depends(get_settings_dep),
) -> SearchOrchestrator:
    return SearchOrchestrator(
        local_search=local_search,
        internet_search=internet_search,
        hybrid_search=hybrid_search,
        deduplicator=deduplicator,
        verifier=verifier,
        ranker=ranker,
        evidence_ranker=evidence_ranker,
        default_mode=SearchMode(settings.search_default_mode),
    )


def get_search_service(
    orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
    session: AsyncSession = Depends(get_session),
) -> SearchService:
    return SearchService(orchestrator=orchestrator, session=session)
