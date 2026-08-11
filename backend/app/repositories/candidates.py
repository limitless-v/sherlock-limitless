"""Candidate repository (roadmap Phase 23).

Persistence layer for extracted candidates and related entities.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    Candidate,
    CandidateExtractedImage,
    CandidateProfile,
    CandidateLocation,
    CandidateDate,
    SearchHistory,
)
from app.evidence.schemas import CandidateExtraction, CandidateImageData, CandidateProfileData, CandidateLocationData, CandidateDateData


class CandidateRepository:
    """Repository for candidate persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_candidate(
        self,
        search_id: int,
        extraction: CandidateExtraction,
    ) -> Candidate:
        """Create a new candidate with all related entities."""
        candidate = Candidate(
            search_id=search_id,
            url=extraction.url,
            domain=extraction.domain,
            title=extraction.title,
            source=extraction.source,
            kind=extraction.kind,
            reason=extraction.reason,
            candidate_metadata=extraction.metadata,
            discovered_at=extraction.discovered_at,
        )
        self._session.add(candidate)
        await self._session.flush()

        # Add images
        for img_data in extraction.images:
            img = CandidateExtractedImage(
                candidate_id=candidate.id,
                image_url=img_data.image_url,
                local_path=img_data.local_path,
                sha256=img_data.sha256,
                a_hash=img_data.a_hash,
                d_hash=img_data.d_hash,
                p_hash=img_data.p_hash,
                width=img_data.width,
                height=img_data.height,
                content_type=img_data.content_type,
                file_size=img_data.file_size,
            )
            self._session.add(img)

        # Add profiles
        for profile_data in extraction.public_profile_links:
            profile = CandidateProfile(
                candidate_id=candidate.id,
                profile_url=profile_data.profile_url,
                platform=profile_data.platform,
                username=profile_data.username,
                display_name=profile_data.display_name,
                source_url=profile_data.source_url,
            )
            self._session.add(profile)

        # Add locations
        for loc_data in extraction.locations:
            loc = CandidateLocation(
                candidate_id=candidate.id,
                location=loc_data.location,
                location_type=loc_data.location_type,
                source_text=loc_data.source_text,
                confidence=loc_data.confidence,
            )
            self._session.add(loc)

        # Add dates
        for date_data in extraction.dates:
            date_obj = CandidateDate(
                candidate_id=candidate.id,
                date_value=date_data.date_value,
                date_type=date_data.date_type,
                source_text=date_data.source_text,
                confidence=date_data.confidence,
            )
            self._session.add(date_obj)

        await self._session.flush()
        await self._session.refresh(candidate)
        return candidate

    async def create_candidates_bulk(
        self,
        search_id: int,
        extractions: list[CandidateExtraction],
    ) -> list[Candidate]:
        """Create multiple candidates efficiently."""
        candidates: list[Candidate] = []
        for extraction in extractions:
            candidate = await self.create_candidate(search_id, extraction)
            candidates.append(candidate)
        return candidates

    async def get_candidates_by_search(
        self,
        search_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Candidate]:
        """Get all candidates for a search."""
        stmt = (
            select(Candidate)
            .where(Candidate.search_id == search_id)
            .options(
                selectinload(Candidate.images),
                selectinload(Candidate.profiles),
                selectinload(Candidate.locations),
                selectinload(Candidate.dates),
            )
            .order_by(Candidate.discovered_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_candidate_count_by_search(self, search_id: int) -> int:
        """Get total candidate count for a search."""
        stmt = select(func.count(Candidate.id)).where(Candidate.search_id == search_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_candidate_by_id(self, candidate_id: int) -> Candidate | None:
        """Get a candidate by ID with all relations."""
        stmt = (
            select(Candidate)
            .where(Candidate.id == candidate_id)
            .options(
                selectinload(Candidate.images),
                selectinload(Candidate.profiles),
                selectinload(Candidate.locations),
                selectinload(Candidate.dates),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_candidate_images(
        self,
        candidate_id: int,
        images: list[CandidateImageData],
    ) -> None:
        """Update images for a candidate (after download/correlation)."""
        # Delete existing images
        await self._session.execute(
            delete(CandidateExtractedImage).where(CandidateExtractedImage.candidate_id == candidate_id)
        )

        # Add new images
        for img_data in images:
            img = CandidateExtractedImage(
                candidate_id=candidate_id,
                image_url=img_data.image_url,
                local_path=img_data.local_path,
                sha256=img_data.sha256,
                a_hash=img_data.a_hash,
                d_hash=img_data.d_hash,
                p_hash=img_data.p_hash,
                width=img_data.width,
                height=img_data.height,
                content_type=img_data.content_type,
                file_size=img_data.file_size,
            )
            self._session.add(img)

        await self._session.flush()

    async def update_candidate_correlation(
        self,
        candidate_id: int,
        image_url: str,
        classification: str,
        hamming_distance: int | None,
        face_similarity: float | None,
    ) -> None:
        """Update correlation results for a candidate image (by image_url)."""
        stmt = select(CandidateExtractedImage).where(
            CandidateExtractedImage.candidate_id == candidate_id,
            CandidateExtractedImage.image_url == image_url,
        )
        result = await self._session.execute(stmt)
        img = result.scalar_one_or_none()
        if img:
            img.correlation_classification = classification
            img.correlation_hamming_distance = hamming_distance
            img.face_similarity = face_similarity

    async def update_candidate_correlation_by_path(
        self,
        candidate_id: int,
        local_path: str,
        classification: str,
        hamming_distance: int | None,
        face_similarity: float | None,
        correlation_confidence: float | None = None,
    ) -> None:
        """Update correlation results for a candidate image (by local_path)."""
        stmt = select(CandidateExtractedImage).where(
            CandidateExtractedImage.candidate_id == candidate_id,
            CandidateExtractedImage.local_path == local_path,
        )
        result = await self._session.execute(stmt)
        img = result.scalar_one_or_none()
        if img:
            img.correlation_classification = classification
            img.correlation_hamming_distance = hamming_distance
            img.face_similarity = face_similarity
            if correlation_confidence is not None:
                img.correlation_confidence = correlation_confidence
            from datetime import datetime, timezone
            img.correlated_at = datetime.now(timezone.utc)

        await self._session.flush()

    async def get_candidates_by_domain(
        self,
        search_id: int,
        domain: str,
    ) -> Sequence[Candidate]:
        """Get candidates for a search filtered by domain."""
        stmt = (
            select(Candidate)
            .where(Candidate.search_id == search_id, Candidate.domain == domain)
            .options(selectinload(Candidate.images))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_all_domains_for_search(self, search_id: int) -> list[str]:
        """Get unique domains for a search."""
        stmt = select(Candidate.domain).where(Candidate.search_id == search_id).distinct()
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def delete_candidates_by_search(self, search_id: int) -> int:
        """Delete all candidates for a search (cascades to related entities)."""
        stmt = delete(Candidate).where(Candidate.search_id == search_id)
        result = await self._session.execute(stmt)
        return result.rowcount