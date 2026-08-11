"""Correlation service (roadmap Phase 25).

Service layer for image correlation and evidence graph integration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding.face_embedder import FaceEmbedder
from app.discovery.fingerprinting import FingerprintService
from app.evidence.correlation import ImageCorrelator, ImageCorrelation
from app.evidence.graph import EvidenceGraph
from app.models.entities import CandidateExtractedImage
from app.repositories.candidates import CandidateRepository


class CorrelationService:
    """Service for image correlation and evidence graph updates."""

    def __init__(
        self,
        session: AsyncSession,
        fingerprint_service: FingerprintService,
        face_embedder: FaceEmbedder,
        p_hash_threshold_exact: int = 0,
        p_hash_threshold_near: int = 10,
        p_hash_threshold_similar: int = 20,
        face_similarity_threshold: float = 0.75,
    ) -> None:
        self._repo = CandidateRepository(session)
        self._correlator = ImageCorrelator(
            fingerprint_service=fingerprint_service,
            face_embedder=face_embedder,
            p_hash_threshold_exact=p_hash_threshold_exact,
            p_hash_threshold_near=p_hash_threshold_near,
            p_hash_threshold_similar=p_hash_threshold_similar,
            face_similarity_threshold=face_similarity_threshold,
        )

    async def correlate_candidate_images(
        self,
        candidate_id: int,
        uploaded_fingerprint: Any,
        uploaded_embeddings: list[Any] | None,
    ) -> list[ImageCorrelation]:
        """Correlate all images for a candidate against the uploaded image."""
        # Get candidate with images
        candidate = await self._repo.get_candidate_by_id(candidate_id)
        if not candidate:
            return []

        # Collect local paths of downloaded images
        candidate_paths = []
        for img in candidate.images:
            if img.local_path and Path(img.local_path).exists():
                candidate_paths.append(Path(img.local_path))

        if not candidate_paths:
            return []

        # Run correlation
        correlations = self._correlator.correlate(
            uploaded_fingerprint=uploaded_fingerprint,
            uploaded_embeddings=uploaded_embeddings,
            candidate_images=candidate_paths,
        )

        # Update database with correlation results (match by local_path)
        for corr in correlations:
            await self._repo.update_candidate_correlation_by_path(
                candidate_id=candidate_id,
                local_path=str(corr.candidate_image_path),
                classification=corr.classification,
                hamming_distance=corr.hamming_distance,
                face_similarity=corr.face_similarity,
                correlation_confidence=corr.correlation_confidence,
            )

        return correlations

    async def add_correlation_to_evidence_graph(
        self,
        graph: EvidenceGraph,
        candidate_id: int,
        correlations: list[ImageCorrelation],
        uploaded_image_node_id: int,
    ) -> None:
        """Add correlation results as same_image edges to the evidence graph."""
        for corr in correlations:
            if corr.classification in ("exact_duplicate", "near_duplicate", "similar"):
                # Find or create candidate image node
                cand_image_node_id = graph.add_node(
                    node_type="image",
                    entity_id=str(corr.candidate_image_path),
                    entity_value=corr.fingerprint.sha256[:16],
                    attributes={
                        "classification": corr.classification,
                        "hamming_distance": corr.hamming_distance,
                        "face_similarity": corr.face_similarity,
                        "correlation_confidence": corr.correlation_confidence,
                    },
                )
                # Add same_image edge between uploaded image and candidate image
                graph.add_edge(
                    source_node_id=uploaded_image_node_id,
                    target_node_id=cand_image_node_id,
                    edge_type="same_image",
                    source_url="correlation",
                    confidence=corr.correlation_confidence,
                    metadata={
                        "classification": corr.classification,
                        "hamming_distance": corr.hamming_distance,
                        "face_similarity": corr.face_similarity,
                    },
                )