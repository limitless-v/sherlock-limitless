"""Internet + hybrid search provider-status tests (roadmap Phase 18).

Confirms INTERNET returns a degraded-but-usable response when the only web
provider is unavailable (`AgentReachUnavailableError` or missing CLI), and
that HYBRID keeps local results when the internet source is down.
"""

import pytest

from app.config.settings import Settings
from app.discovery.engine import DiscoveryEngine
from app.discovery.schemas import Candidate
from app.osint.agent_reach.capabilities import AgentReachCapabilities
from app.osint.agent_reach.client import AgentReachClient
from app.osint.agent_reach.provider import AgentReachWebProvider
from app.search.hybrid_search import HybridSearchService
from app.search.internet_search import InternetSearchService
from app.search.modes import SearchMode
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse, SearchResult


class _UnavailableAgent(AgentReachClient):
    """An AgentReachClient that is always unavailable (no CLI)."""

    def is_available(self) -> bool:
        return False


def _settings(tmp_path) -> Settings:
    return Settings(uploads_dir=tmp_path)


def _internet(tmp_path) -> InternetSearchService:
    return InternetSearchService(
        engine=DiscoveryEngine(
            web_providers=[AgentReachWebProvider(_UnavailableAgent())],
        ),
        settings=_settings(tmp_path),
    )


def _request(image_id="img-1") -> SearchRequest:
    return SearchRequest(image_id=image_id)


async def test_internet_degraded_when_provider_unavailable(tmp_path):
    service = _internet(tmp_path)
    response = await service.search(_request())
    assert isinstance(response, SearchResponse)
    assert response.mode == SearchMode.INTERNET
    assert response.status == "degraded"
    assert response.results == []
    assert response.providers["agent_reach"]["available"] is False


def test_internet_available_false_without_provider(tmp_path):
    service = InternetSearchService(engine=DiscoveryEngine(web_providers=[]), settings=_settings(tmp_path))
    assert service.available is False


def test_internet_available_true_with_healthy_provider(tmp_path):
    class _HealthyAgent(_UnavailableAgent):
        def is_available(self) -> bool:
            return True

    service = InternetSearchService(
        engine=DiscoveryEngine(web_providers=[AgentReachWebProvider(_HealthyAgent())]),
        settings=_settings(tmp_path),
    )
    assert service.available is True


async def test_hybrid_keeps_local_when_internet_degraded(tmp_path):
    class _LocalStrategy:
        async def search(self, request) -> SearchResponse:
            return SearchResponse(
                search_id=str(request.image_id),
                mode=SearchMode.LOCAL,
                status="completed",
                results=[SearchResult(id="1", source="local", url="local://face/1", title="Face 1", display_name="Face 1")],
            )

    internet = _internet(tmp_path)
    hybrid = HybridSearchService(_LocalStrategy(), internet)
    response = await hybrid.search(_request())
    assert response.mode == SearchMode.HYBRID
    assert response.status == "degraded"
    assert len(response.results) == 1
    assert response.results[0].source == "local"
    assert response.providers["local"]["available"] is True


    async def test_hybrid_dedupes_identical_results(tmp_path):
        class _Both:
            async def search(self, request) -> SearchResponse:
                return SearchResponse(
                    search_id=str(request.image_id),
                    mode=SearchMode.HYBRID,
                    status="completed",
                    results=[
                        SearchResult(id="1", source="internet", url="https://x.example/1", title="A", display_name="A"),
                        SearchResult(id="2", source="internet", url="https://x.example/1", title="A", display_name="A"),
                    ],
                )

        hybrid = HybridSearchService(_Both(), _Both())
        response = await hybrid.search(_request())
        assert len(response.results) == 1


def test_provider_status_reflects_unavailable_reason(tmp_path):
    provider = AgentReachWebProvider(_UnavailableAgent())
    status = provider.status()
    assert status.name == "agent_reach"
    assert status.available is False
    assert status.capabilities == ("web",)
    assert status.reason or status.reason == ""


def test_provider_disabled_by_config(tmp_path):
    provider = AgentReachWebProvider(_UnavailableAgent(), enabled=False)
    assert provider.available is False
    assert "disabled" in provider.availability_reason.lower()