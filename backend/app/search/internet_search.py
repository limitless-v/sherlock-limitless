"""Internet search service (roadmap section 9, wired in Phase 18).

Runs web discovery through the Discovery Engine (Agent Reach provider when
installed). The service never pretends success: when no provider is
available it returns a *degraded* response with explicit provider status and
zero candidates rather than raising 501.

Agent Reach is the discovery layer only — it finds public candidate pages,
metadata, and images. It never performs facial verification. This is a
first-class search mode, not a fallback for LOCAL.
"""

from __future__ import annotations

from pathlib import Path

from app.config.settings import Settings
from app.discovery.context.builder import SearchContextBuilder
from app.discovery.engine import DiscoveryEngine
from app.discovery.schemas import Candidate
from app.osint.agent_reach.client import AgentReachClient
from app.search.modes import SearchMode
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse, SearchResult


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

        available_any = any(status.available for status in statuses)
        status = "completed" if results or (statuses and available_any) else "degraded"

        return SearchResponse(
            search_id=str(request.image_id),
            mode=SearchMode.INTERNET,
            status=status,
            results=results,
            providers=providers,
        )

    @staticmethod
    def _empty_context(request: SearchRequest):
        from app.discovery.context.models import SearchContext

        return SearchContext(user_filters={"sources": request.sources})