"""Candidate service (roadmap Phase 23).

Coordinates candidate extraction and persistence.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.web_research.schemas import ResearchOutput
from app.discovery.schemas import Candidate as DiscoveryCandidate
from app.evidence.extraction import CandidateExtractor, ExtractedCandidate
from app.repositories.candidates import CandidateRepository


class CandidateService:
    """Service layer for candidate extraction and persistence."""

    def __init__(
        self,
        session: AsyncSession,
        max_images_per_candidate: int = 5,
        max_profiles_per_candidate: int = 10,
    ) -> None:
        self._repo = CandidateRepository(session)
        self._extractor = CandidateExtractor(
            max_images_per_candidate=max_images_per_candidate,
            max_profiles_per_candidate=max_profiles_per_candidate,
        )

    def extract_from_research(self, research_output: ResearchOutput) -> list[ExtractedCandidate]:
        """Extract candidates from research output."""
        return self._extractor.extract_from_research(research_output)

    def extract_from_discovery(self, candidates: list[DiscoveryCandidate]) -> list[ExtractedCandidate]:
        """Extract candidates from discovery engine output."""
        return self._extractor.extract_from_discovery(candidates)

    async def persist_candidates(
        self,
        search_id: int,
        extracted: list[ExtractedCandidate],
    ) -> list[Any]:
        """Persist extracted candidates to database."""
        extractions = [ec.extraction for ec in extracted]
        return await self._repo.create_candidates_bulk(search_id, extractions)

    async def get_candidates(
        self,
        search_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Any]:
        """Get candidates for a search."""
        return list(await self._repo.get_candidates_by_search(search_id, limit, offset))

    async def get_candidate_count(self, search_id: int) -> int:
        """Get total candidate count for a search."""
        return await self._repo.get_candidate_count_by_search(search_id)

    async def update_candidate_images(
        self,
        candidate_id: int,
        images: list[Any],
    ) -> None:
        """Update candidate images after download/correlation."""
        await self._repo.update_candidate_images(candidate_id, images)

    async def update_candidate_correlation(
        self,
        candidate_id: int,
        image_url: str,
        classification: str,
        hamming_distance: int | None,
        face_similarity: float | None,
    ) -> None:
        """Update correlation results."""
        await self._repo.update_candidate_correlation(
            candidate_id, image_url, classification, hamming_distance, face_similarity
        )

    async def get_candidates_by_domain(
        self,
        search_id: int,
        domain: str,
    ) -> list[Any]:
        """Get candidates filtered by domain."""
        return list(await self._repo.get_candidates_by_domain(search_id, domain))

    async def get_domains(self, search_id: int) -> list[str]:
        """Get unique domains for a search."""
        return await self._repo.get_all_domains_for_search(search_id)