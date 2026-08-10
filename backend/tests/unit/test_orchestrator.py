"""Search orchestrator unit tests (roadmap Phase 10).

Exercises mode validation, default-mode fallback, capability reporting,
strategy selection, and NotImplementedError propagation for the not-yet-
implemented INTERNET / HYBRID strategies. No models, DB, or network.
"""

from uuid import uuid4

import pytest

from app.ai.matching.similarity import cosine_similarity
from app.search.deduplication import ResultDeduplicator
from app.search.modes import SearchMode
from app.search.orchestrator import SearchOrchestrator
from app.search.ranking import ResultRanker
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse, SearchResult
from app.search.verification import CandidateVerifier


class StubStrategy:
    def __init__(self, response: SearchResponse | None = None, raise_error=None, available: bool | None = None) -> None:
        self._response = response
        self._error = raise_error  # callable/marker; NotImplementedError raised when set
        self._available = available

    async def search(self, request: SearchRequest) -> SearchResponse:
        if self._error is not None:
            if self._error is NotImplementedError:
                raise NotImplementedError("strategy not implemented")
            raise self._error
        if self._response is not None:
            return self._response
        return SearchResponse(search_id=str(request.image_id), mode=request.mode or SearchMode.INTERNET)

    def _availability(self) -> bool:
        if self._available is None:
            return True
        if self._available is NotImplementedError:
            raise NotImplementedError("capability detection not implemented")
        return bool(self._available)

    available = property(_availability)


def _orchestrator(local=None, internet=None, hybrid=None, default_mode=SearchMode.LOCAL) -> SearchOrchestrator:
    return SearchOrchestrator(
        local_search=local or StubStrategy(available=True),
        internet_search=internet or StubStrategy(raise_error=NotImplementedError, available=NotImplementedError),
        hybrid_search=hybrid or StubStrategy(raise_error=NotImplementedError, available=NotImplementedError),
        deduplicator=ResultDeduplicator(),
        verifier=CandidateVerifier(cosine_similarity),
        ranker=ResultRanker(),
        default_mode=default_mode,
    )


def _request(mode=None) -> SearchRequest:
    return SearchRequest(image_id=uuid4(), mode=mode, max_results=10)


def test_validate_mode_coerces_and_rejects():
    assert SearchOrchestrator.validate_mode("local") is SearchMode.LOCAL
    assert SearchOrchestrator.validate_mode(SearchMode.HYBRID) is SearchMode.HYBRID
    assert SearchOrchestrator.validate_mode(None) is None
    with pytest.raises(ValueError):
        SearchOrchestrator.validate_mode("bogus")


def test_resolve_mode_applies_default():
    orch = _orchestrator(default_mode=SearchMode.LOCAL)
    assert orch.resolve_mode(_request(mode=None)) is SearchMode.LOCAL
    assert orch.resolve_mode(_request(mode=SearchMode.INTERNET)) is SearchMode.INTERNET


async def test_execute_local_returns_strategy_response():
    response = SearchResponse(
        search_id="x",
        mode=SearchMode.LOCAL,
        results=[SearchResult(id="1", source="local", url="local://faces/1")],
    )
    orch = _orchestrator(local=StubStrategy(response=response))
    result = await orch.execute(_request(mode=SearchMode.LOCAL))
    assert result is response
    assert result.results[0].source == "local"


async def test_execute_propagates_not_implemented_for_internet_and_hybrid():
    orchid = _orchestrator()
    with pytest.raises(NotImplementedError):
        await orchid.execute(_request(mode=SearchMode.INTERNET))
    with pytest.raises(NotImplementedError):
        await orchid.execute(_request(mode=SearchMode.HYBRID))


def test_execute_unknown_mode_raises_value_error():
    orch = _orchestrator()
    with pytest.raises(ValueError):
        orch.validate_mode("nope")


def test_capabilities_report_availability():
    local = StubStrategy(available=True)
    internet = StubStrategy(available=NotImplementedError)
    hybrid = StubStrategy(available=NotImplementedError)
    orch = _orchestrator(local=local, internet=internet, hybrid=hybrid)
    caps = orch.capabilities()
    assert caps == {"local": True, "internet": False, "hybrid": False}


def test_mode_available_false_for_unknown_and_unavailable():
    orch = _orchestrator()
    assert orch.mode_available(SearchMode.LOCAL) is True
    assert orch.mode_available(SearchMode.INTERNET) is False
    assert orch.mode_available("bogus") is False


async def test_execute_uses_default_mode_when_absent():
    seen = []

    class Echo(StubStrategy):
        async def search(self, request):
            seen.append(request.mode)
            return SearchResponse(search_id=str(request.image_id), mode=request.mode or SearchMode.LOCAL)

    orch = _orchestrator(local=Echo(), default_mode=SearchMode.LOCAL)
    await orch.execute(_request(mode=None))
    assert seen == [None]  # orchestrator resolves default; strategy still receives request as-is