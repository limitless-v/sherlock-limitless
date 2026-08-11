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

Phase 27: Integrates EvidenceRanker for evidence-based result ranking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.search.deduplication import ResultDeduplicator
from app.search.modes import SearchMode
from app.search.ranking import ResultRanker
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse
from app.search.verification import CandidateVerifier

if TYPE_CHECKING:
    from app.evidence.ranking import EvidenceRanker, RankedEvidence, EvidenceStrength, EvidenceType
    from app.evidence.graph import EvidenceGraph
    from app.search.hybrid_search import HybridSearchService
    from app.search.internet_search import InternetSearchService
    from app.search.local_search import LocalSearchService

_STRATEGY_TYPES: tuple[type, ...] = ()


class SearchOrchestrator:
    """Routes a SearchRequest to the correct strategy and normalizes results."""

    def __init__(
        self,
        local_search: "LocalSearchService",
        internet_search: "InternetSearchService",
        hybrid_search: "HybridSearchService",
        deduplicator: ResultDeduplicator,
        verifier: CandidateVerifier,
        ranker: ResultRanker,
        evidence_ranker: "EvidenceRanker | None" = None,
        default_mode: SearchMode = SearchMode.INTERNET,
    ) -> None:
        self._local_search = local_search
        self._internet_search = internet_search
        self._hybrid_search = hybrid_search
        self._deduplicator = deduplicator
        self._verifier = verifier
        self._ranker = ranker
        self._evidence_ranker = evidence_ranker
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
        return isinstance(strategy, (_STRATEGY_TYPES if _STRATEGY_TYPES else (object,)))

    def capabilities(self) -> dict[str, bool]:
        """Map every SearchMode to its availability (for UI / capability checks)."""
        return {mode.value: self.mode_available(mode) for mode in SearchMode}

    # --- execution ----------------------------------------------------------

    async def execute(self, request: SearchRequest) -> SearchResponse:
        """Validate, route, execute, and return a normalized response."""
        mode = self.resolve_mode(request)
        strategy = self._resolve_strategy(mode)
        response = await strategy.search(request)
        return self._finalize(mode, response, request.image_id)

    def _finalize(
        self,
        mode: SearchMode,
        response: SearchResponse,
        image_id: str,
    ) -> SearchResponse:
        """Final result pipeline hook.

        Phase 27: Apply evidence ranking if evidence graph is available.
        """
        # Apply deduplication
        if response.results:
            response.results = self._deduplicator.deduplicate(response.results)

        # Apply verification (face matching)
        if response.results:
            response.results = self._verifier.verify(response.results, query_embedding=None)

        # Apply ranking
        if response.results:
            response.results = self._ranker.rank(response.results)

        # Phase 27: Apply evidence-based ranking if evidence graph is available
        if self._evidence_ranker is not None and hasattr(response, "evidence_graph") and response.evidence_graph:
            try:
                ranked_evidence = self._evidence_ranker.rank_evidence(
                    nodes=response.evidence_graph.nodes,
                    edges=response.evidence_graph.edges,
                    uploaded_image_node_id=response.evidence_graph.uploaded_image_node_id,
                )
                # Attach ranked evidence to response
                response.ranked_evidence = [re.to_dict() for re in ranked_evidence]
                
                # Boost result confidence based on evidence strength
                self._boost_results_from_evidence(response.results, ranked_evidence)
            except Exception:
                # Log but don't fail
                pass

        return response

    def _boost_results_from_evidence(
        self,
        results: list,
        ranked_evidence: list,
    ) -> None:
        """Boost result confidence based on evidence ranking."""
        # Map entity values to evidence strength
        evidence_map = {}
        for re in ranked_evidence:
            target_value = re.metadata.get("target_node_value")
            if target_value:
                evidence_map[target_value] = re.evidence_strength

        for result in results:
            # Check if result URL or domain has strong evidence
            if result.url in evidence_map:
                strength = evidence_map[result.url]
                if strength == "strong":
                    result.confidence = "high"
                elif strength == "medium":
                    result.confidence = "medium"
            if result.metadata and "domain" in result.metadata:
                domain = result.metadata["domain"]
                if domain in evidence_map:
                    strength = evidence_map[domain]
                    if strength == "strong" and result.confidence == "low":
                        result.confidence = "medium"