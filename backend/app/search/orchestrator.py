"""Search orchestrator (roadmap section 7, Phase 10).

Responsibilities (all mode routing and orchestration lives here, never in
the API layer):
- validate the search mode
- check available capabilities
- select the search strategy
- execute the search
- normalize / finalize the result pipeline

The finalize pipeline (merge, face verification, deduplication, ranking)
is intentionally wired to later phases; today it only normalizes what the
executed strategy already returns. INTERNET / HYBRID strategies degrade
gracefully (202 + `status: "degraded"`) when Agent Reach is unavailable.
"""

from app.search.deduplication import ResultDeduplicator
from app.search.hybrid_search import HybridSearchService
from app.search.internet_search import InternetSearchService
from app.search.local_search import LocalSearchService
from app.search.modes import SearchMode
from app.search.ranking import ResultRanker
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse
from app.search.verification import CandidateVerifier

_STRATEGY_TYPES = (LocalSearchService, InternetSearchService, HybridSearchService)


class SearchOrchestrator:
    """Routes a SearchRequest to the correct strategy and normalizes results."""

    def __init__(
        self,
        local_search: LocalSearchService,
        internet_search: InternetSearchService,
        hybrid_search: HybridSearchService,
        deduplicator: ResultDeduplicator,
        verifier: CandidateVerifier,
        ranker: ResultRanker,
        default_mode: SearchMode = SearchMode.INTERNET,
    ) -> None:
        self._local_search = local_search
        self._internet_search = internet_search
        self._hybrid_search = hybrid_search
        self._deduplicator = deduplicator
        self._verifier = verifier
        self._ranker = ranker
        self._default_mode = default_mode

    # --- mode handling ----------------------------------------------------

    @staticmethod
    def validate_mode(mode: SearchMode | str | None) -> SearchMode | None:
        """Coerce a mode value to SearchMode; None stays None.

        Raises ValueError for unknown mode strings (invalid modes are not
        silently mapped to a default strategy).
        """
        if mode is None:
            return None
        if isinstance(mode, SearchMode):
            return mode
        return SearchMode(mode)

    def resolve_mode(self, request: SearchRequest) -> SearchMode:
        """Return the effective mode, applying the configured default when absent."""
        mode = self.validate_mode(request.mode)
        return mode if mode is not None else self._default_mode

    # --- strategy selection ------------------------------------------------

    def _resolve_strategy(self, mode: SearchMode):
        """Return the search service for the requested mode."""
        mode = self.validate_mode(mode)
        if mode is SearchMode.LOCAL:
            return self._local_search
        if mode is SearchMode.INTERNET:
            return self._internet_search
        if mode is SearchMode.HYBRID:
            return self._hybrid_search
        raise ValueError(f"Unknown search mode: {mode}")

    # --- capabilities ------------------------------------------------------

    def mode_available(self, mode: SearchMode | str | None) -> bool:
        """True when a strategy for the mode can execute.

        A strategy that is not yet implemented (raises NotImplementedError
        from its availability probe) is reported as unavailable — the
        orchestrator must not fall back to another mode silently.
        """
        try:
            strategy = self._resolve_strategy(mode)
        except ValueError:
            return False
        try:
            probe = getattr(strategy, "available", None)
            if probe is not None:
                return bool(probe)
        except NotImplementedError:
            return False
        # strategies without an availability probe are treated as available
        return isinstance(strategy, _STRATEGY_TYPES)

    def capabilities(self) -> dict[str, bool]:
        """Map every SearchMode to its availability (for UI / capability checks)."""
        return {mode.value: self.mode_available(mode) for mode in SearchMode}

    # --- execution ----------------------------------------------------------

    async def execute(self, request: SearchRequest) -> SearchResponse:
        """Validate, route, execute, and return a normalized response."""
        mode = self.resolve_mode(request)
        strategy = self._resolve_strategy(mode)
        response = await strategy.search(request)
        return self._finalize(mode, response)

    def _finalize(self, mode: SearchMode, response: SearchResponse) -> SearchResponse:
        """Final result pipeline hook.

        Currently passes the strategy output through; later phases slot
        verification, deduplication, and ranking here.
        """
        return response