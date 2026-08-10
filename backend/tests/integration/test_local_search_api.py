"""Local Search API integration test (roadmap Phase 9).

Overrides the search-service dependency so the real controller +
orchestrator run against canned strategies — no models, DB, or FAISS needed.
Confirms LOCAL returns results (202 -> response body) while INTERNET and
HYBRID remain 501 until their later phases.
"""

from uuid import uuid4

import httpx
import pytest

from app.ai.matching.similarity import cosine_similarity
from app.dependencies.container import get_search_service
from app.main import app
from app.osint.agent_reach.client import AgentReachClient
from app.search.deduplication import ResultDeduplicator
from app.search.hybrid_search import HybridSearchService
from app.search.internet_search import InternetSearchService
from app.search.modes import SearchMode
from app.search.orchestrator import SearchOrchestrator
from app.search.ranking import ResultRanker
from app.search.result_models import SearchResponse, SearchResult
from app.search.verification import CandidateVerifier
from app.services.search_service import SearchService

STUB_RESULT = SearchResult(
    id="1",
    source="local",
    url="local://faces/1",
    title="Local face #1",
    display_name="Local face #1",
    face_similarity=0.9,
    confidence="high",
    discovery_method="faiss",
)


class _StubStrategy:
    def __init__(self, factory) -> None:
        self._factory = factory

    async def search(self, request) -> SearchResponse:
        return self._factory(request)


def _local_response(request) -> SearchResponse:
    return SearchResponse(
        search_id=str(request.image_id),
        mode=SearchMode.LOCAL,
        status="completed",
        results=[STUB_RESULT],
    )


@pytest.fixture
def override_search_service():
    internet = InternetSearchService(AgentReachClient())
    local = _StubStrategy(_local_response)
    hybrid = HybridSearchService(local, internet)  # type: ignore[arg-type]
    orchestrator = SearchOrchestrator(
        local_search=local,  # type: ignore[arg-type]
        internet_search=internet,
        hybrid_search=hybrid,
        deduplicator=ResultDeduplicator(),
        verifier=CandidateVerifier(cosine_similarity),
        ranker=ResultRanker(),
        default_mode=SearchMode.INTERNET,
    )
    app.dependency_overrides[get_search_service] = lambda: SearchService(orchestrator=orchestrator)
    yield
    app.dependency_overrides.pop(get_search_service, None)


async def test_local_mode_returns_results(override_search_service):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/search",
            json={"image_id": str(uuid4()), "mode": "local"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["mode"] == "local"
    assert body["status"] == "completed"
    assert len(body["results"]) == 1
    assert body["results"][0]["source"] == "local"


async def test_internet_mode_still_501(override_search_service):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/search",
            json={"image_id": str(uuid4()), "mode": "internet"},
        )
    assert response.status_code == 501


async def test_hybrid_mode_still_501(override_search_service):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/search",
            json={"image_id": str(uuid4()), "mode": "hybrid"},
        )
    assert response.status_code == 501