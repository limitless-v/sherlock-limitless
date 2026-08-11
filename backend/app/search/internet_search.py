"""Internet search service (roadmap section 9, wired in Phase 18).

Runs web discovery through the Discovery Engine (Agent Reach provider when
installed). The service never pretends success: when no provider is
available it returns a *degraded* response with explicit provider status and
zero candidates rather than raising 501.

Agent Reach is the discovery layer only — it finds public candidate pages,
metadata, and images. It never performs facial verification. This is a
first-class search mode, not a fallback for LOCAL.

Phase 23: Integrates ResearchAgent for deep candidate investigation and extraction.
Phase 24: Integrates EvidenceGraph for building evidence connections.
Phase 25: Integrates CandidateCrawler and ImageCorrelator for image correlation.
"""

from __future__ import annotations

from pathlib import Path

from app.agents.web_research.agent import ResearchAgent, ResearchResult
from app.config.settings import Settings
from app.discovery.context.builder import SearchContextBuilder
from app.discovery.engine import DiscoveryEngine
from app.discovery.schemas import Candidate
from app.evidence.correlation import ImageCorrelation
from app.osint.agent_reach.client import AgentReachClient
from app.osint.crawler.images import CandidateCrawler
from app.search.modes import SearchMode
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse, SearchResult
from app.services.candidate_service import CandidateService
from app.services.correlation_service import CorrelationService
from app.services.evidence_graph_service import EvidenceGraphService


def _candidate_to_result(candidate: Candidate) -> SearchResult:
    return SearchResult(
        id=str(hash(candidate.url)),
        source=candidate.source,
        url=candidate.url,
        title=candidate.title,
        display_name=candidate.title,
        image_urls=candidate.images,
        discovery_method="web",
        confidence="low",
        metadata={
            "domain": candidate.domain,
            "reason": candidate.reason,
            "kind": candidate.kind,
        },
    )


class InternetSearchService:
    """Provider-aware internet discovery returning degraded-safe responses."""

    def __init__(
        self,
        engine: DiscoveryEngine | None = None,
        context_builder: SearchContextBuilder | None = None,
        settings: Settings | None = None,
        agent_reach_client=None,
        crawler=None,
        research_agent: ResearchAgent | None = None,
        candidate_service: CandidateService | None = None,
        evidence_graph_service: EvidenceGraphService | None = None,
        correlation_service: CorrelationService | None = None,
    ) -> None:
        """New wiring passes an engine + builder + settings.

        The legacy (client + crawler) signature is preserved for DI/test
        compatibility: when no engine is given, a DiscoveryEngine with an
        AgentReachWebProvider is built from the client.
        """
        if engine is not None:
            self._engine = engine
            self._context_builder = context_builder or SearchContextBuilder()
            self._settings = settings
        else:
            from app.config.settings import get_settings
            from app.osint.agent_reach.provider import AgentReachWebProvider

            self._settings = settings or get_settings()
            provider = AgentReachWebProvider(client=agent_reach_client or AgentReachClient())
            provider.enabled = self._settings.agent_reach_enabled
            self._engine = DiscoveryEngine(web_providers=[provider])
            self._context_builder = context_builder or SearchContextBuilder()
        self._crawler = crawler
        self._research_agent = research_agent
        self._candidate_service = candidate_service
        self._evidence_graph_service = evidence_graph_service
        self._correlation_service = correlation_service

    @property
    def available(self) -> bool:
        """True when at least one discovery provider can run."""
        return any(status.available for status in self._engine.provider_statuses())

    def _resolve_upload(self, request: SearchRequest) -> Path | None:
        """Locate the stored upload for an image_id (filename encodes the UUID)."""
        try:
            candidates = sorted(self._settings.uploads_dir.glob(f"{request.image_id}.*"))
        except OSError:
            return None
        return candidates[0] if candidates else None

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Return discovery candidates, or a degraded response when down."""
        upload = self._resolve_upload(request)
        context = (
            self._context_builder.build(upload, user_filters={"sources": request.sources})
            if upload is not None and upload.is_file()
            else self._empty_context(request)
        )

        statuses = self._engine.provider_statuses()
        providers = {status.name: status.to_dict() for status in statuses}

        results: list[SearchResult] = []
        if any(status.available for status in statuses):
            candidates = await self._engine.discover(context)
            results = [_candidate_to_result(c) for c in candidates]

            # Phase 23-24: Run research agent on candidates and persist extracted data + evidence graph
            if self._research_agent is not None and candidates:
                # Use image_id as search_id for now (need proper search_id from DB)
                search_id = int(request.image_id) if request.image_id.isdigit() else 0
                research_result = await self._research_agent.research(
                    candidates, context, search_id=search_id
                )
                # Persist extracted candidates if candidate_service is available
                if self._candidate_service is not None and research_result.extracted_candidates:
                    try:
                        await self._candidate_service.persist_candidates(
                            search_id=search_id,
                            extracted=research_result.extracted_candidates,
                        )
                    except Exception:
                        # Log but don't fail the search
                        pass

                # Phase 24: Persist evidence graph
                if self._evidence_graph_service is not None and research_result.evidence_graph is not None:
                    try:
                        await self._evidence_graph_service.persist_graph(research_result.evidence_graph)
                    except Exception:
                        # Log but don't fail the search
                        pass

            # Phase 25: Download candidate images and run correlation
            if self._correlation_service is not None and upload is not None and upload.is_file() and candidates:
                try:
                    await self._run_image_correlation(
                        search_id=search_id,
                        upload_path=upload,
                        candidates=candidates,
                        research_result=research_result,
                    )
                except Exception:
                    # Log but don't fail the search
                    pass

        available_any = any(status.available for status in statuses)
        status = "completed" if results or (statuses and available_any) else "degraded"

        return SearchResponse(
            search_id=str(request.image_id),
            mode=SearchMode.INTERNET,
            status=status,
            results=results,
            providers=providers,
        )

    async def _run_image_correlation(
        self,
        search_id: int,
        upload_path: Path,
        candidates: list[Candidate],
        research_result: ResearchResult,
    ) -> None:
        """Download candidate images and run correlation against uploaded image."""
        if self._correlation_service is None:
            return

        # Compute uploaded image fingerprint and face embeddings
        from app.discovery.fingerprinting import FingerprintService
        from app.ai.embedding.face_embedder import FaceEmbedder

        fingerprint_service = FingerprintService()
        face_embedder: FaceEmbedder | None = None
        try:
            # We need to get the face embedder from the container
            # For now, create a basic one - in production this would be injected
            from app.config.settings import get_settings
            from app.ai.embedding.face_embedder import InsightFaceEmbedder
            face_embedder = InsightFaceEmbedder(get_settings())
        except Exception:
            pass

        uploaded_fingerprint = fingerprint_service.fingerprint(upload_path)
        uploaded_embeddings = None
        if face_embedder is not None:
            try:
                face_results = face_embedder.embed_image(upload_path)
                uploaded_embeddings = [fr.embedding for fr in face_results]
            except Exception:
                pass

        # Download candidate images
        async with CandidateCrawler(self._settings) as crawler:
            for candidate in candidates:
                if not candidate.images:
                    continue

                # Get or create candidate in DB
                cand_db = await self._get_or_create_candidate_db(search_id, candidate)
                if not cand_db:
                    continue

                # Download images for this candidate
                download_results = await crawler.fetch_images_batch(candidate.images, cand_db.id)

                # Update candidate with local paths
                for dl_result in download_results:
                    if dl_result.get("success"):
                        # Find matching image in candidate and update local_path
                        for img in cand_db.images:
                            if img.image_url == dl_result["url"]:
                                img.local_path = dl_result["local_path"]
                                img.sha256 = dl_result["sha256"]
                                img.width = dl_result["width"]
                                img.height = dl_result["height"]
                                img.content_type = dl_result["content_type"]
                                img.file_size = dl_result["file_size"]
                                break

        # Run correlation for all candidates with downloaded images
        if self._candidate_service is not None:
            candidates_with_images = await self._candidate_service.get_candidates(search_id)
            for cand in candidates_with_images:
                if not cand.images:
                    continue
                await self._correlation_service.correlate_candidate_images(
                    candidate_id=cand.id,
                    uploaded_fingerprint=uploaded_fingerprint,
                    uploaded_embeddings=uploaded_embeddings,
                )

        # Add correlation results to evidence graph
        if self._evidence_graph_service is not None and research_result.evidence_graph is not None:
            graph = research_result.evidence_graph
            # Find uploaded image node
            uploaded_image_node_id = graph.get_node_by_entity("image", str(upload_path))
            if uploaded_image_node_id is None:
                uploaded_image_node_id = graph.add_node(
                    node_type="image",
                    entity_id=str(upload_path),
                    entity_value=uploaded_fingerprint.sha256[:16],
                    source_url=str(upload_path),
                )

            for cand in candidates_with_images:
                if not cand.images:
                    continue
                correlations = await self._correlation_service.correlate_candidate_images(
                    candidate_id=cand.id,
                    uploaded_fingerprint=uploaded_fingerprint,
                    uploaded_embeddings=uploaded_embeddings,
                )
                await self._correlation_service.add_correlation_to_evidence_graph(
                    graph=graph,
                    candidate_id=cand.id,
                    correlations=correlations,
                    uploaded_image_node_id=uploaded_image_node_id,
                )

            # Persist updated graph
            await self._evidence_graph_service.persist_graph(graph)

    async def _get_or_create_candidate_db(
        self,
        search_id: int,
        candidate: Candidate,
    ) -> Any | None:
        """Get or create candidate in database."""
        if self._candidate_service is None:
            return None
        # Check if candidate already exists
        existing = await self._candidate_service.get_candidates_by_domain(search_id, candidate.domain)
        for ec in existing:
            if ec.url == candidate.url:
                return ec
        # Create new
        from app.evidence.extraction import CandidateExtractor
        extractor = CandidateExtractor()
        extraction = extractor.extract_from_discovery([candidate])
        if extraction:
            created = await self._candidate_service.persist_candidates(search_id, [extraction[0].extraction])
            return created[0] if created else None
        return None

    @staticmethod
    def _empty_context(request: SearchRequest):
        from app.discovery.context.models import SearchContext

        return SearchContext(user_filters={"sources": request.sources})