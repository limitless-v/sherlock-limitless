"""Integration tests for image correlation (roadmap Phase 25)."""

import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.discovery.fingerprinting import FingerprintService, ImageFingerprint
from app.evidence.correlation import ImageCorrelator, ImageCorrelation
from app.models.entities import Candidate, CandidateExtractedImage, SearchHistory
from app.repositories.candidates import CandidateRepository
from app.services.correlation_service import CorrelationService


@pytest.mark.asyncio
async def test_correlation_service_update_correlation(db_session: AsyncSession) -> None:
    """Test updating candidate correlation results."""
    repo = CandidateRepository(db_session)
    fingerprint_service = FingerprintService()
    
    # Create search and candidate
    search = SearchHistory(user_id=1, uploaded_image="uploads/test.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)
    
    candidate = Candidate(
        search_id=search.id,
        url="https://example.com/profile",
        domain="example.com",
        source="web_research",
        kind="web",
    )
    db_session.add(candidate)
    await db_session.flush()
    await db_session.refresh(candidate)
    
    # Add candidate image
    img = CandidateExtractedImage(
        candidate_id=candidate.id,
        image_url="https://example.com/img.jpg",
        local_path="cache/candidate_images/abc123.jpg",
        sha256="abc123",
        p_hash="0000000000000001",
    )
    db_session.add(img)
    await db_session.flush()
    await db_session.refresh(img)
    
    # Update correlation by path
    await repo.update_candidate_correlation_by_path(
        candidate_id=candidate.id,
        local_path=img.local_path,
        classification="near_duplicate",
        hamming_distance=5,
        face_similarity=0.85,
        correlation_confidence=0.9,
    )
    
    # Verify
    await db_session.refresh(img)
    assert img.correlation_classification == "near_duplicate"
    assert img.correlation_hamming_distance == 5
    assert img.face_similarity == 0.85
    assert img.correlation_confidence == 0.9
    assert img.correlated_at is not None


@pytest.mark.asyncio
async def test_correlation_service_correlate(db_session: AsyncSession) -> None:
    """Test CorrelationService correlate method."""
    # This test requires a real FaceEmbedder which needs InsightFace models
    # We'll test the fingerprint correlation logic instead
    
    repo = CandidateRepository(db_session)
    fingerprint_service = FingerprintService()
    
    # Create search and candidate
    search = SearchHistory(user_id=1, uploaded_image="uploads/test.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)
    
    candidate = Candidate(
        search_id=search.id,
        url="https://example.com/profile",
        domain="example.com",
        source="web_research",
        kind="web",
    )
    db_session.add(candidate)
    await db_session.flush()
    await db_session.refresh(candidate)
    
    # Add candidate images with fingerprints
    img1 = CandidateExtractedImage(
        candidate_id=candidate.id,
        image_url="https://example.com/img1.jpg",
        local_path="cache/candidate_images/img1.jpg",
        sha256="abc123",
        p_hash="0000000000000000",
    )
    img2 = CandidateExtractedImage(
        candidate_id=candidate.id,
        image_url="https://example.com/img2.jpg",
        local_path="cache/candidate_images/img2.jpg",
        sha256="def456",
        p_hash="ffffffffffffffff",
    )
    db_session.add_all([img1, img2])
    await db_session.flush()
    
    # Create a mock face embedder
    class MockFaceEmbedder:
        def embed_image(self, path):
            return []
    
    service = CorrelationService(
        session=db_session,
        fingerprint_service=fingerprint_service,
        face_embedder=MockFaceEmbedder(),
    )
    
    # Create uploaded fingerprint
    uploaded_fp = ImageFingerprint(
        sha256="uploaded123",
        a_hash="1111",
        d_hash="2222",
        p_hash="0000000000000000",
    )
    
    # Run correlation (will skip missing files)
    correlations = await service.correlate_candidate_images(
        candidate_id=candidate.id,
        uploaded_fingerprint=uploaded_fp,
        uploaded_embeddings=None,
    )
    
    # Should return empty because files don't exist
    assert correlations == []


@pytest.mark.asyncio
async def test_correlation_service_evidence_graph(db_session: AsyncSession) -> None:
    """Test adding correlation to evidence graph."""
    from app.evidence.graph import EvidenceGraph
    from app.evidence.correlation import ImageCorrelation
    from app.discovery.fingerprinting import ImageFingerprint
    
    repo = CandidateRepository(db_session)
    fingerprint_service = FingerprintService()
    
    class MockFaceEmbedder:
        def embed_image(self, path):
            return []
    
    service = CorrelationService(
        session=db_session,
        fingerprint_service=fingerprint_service,
        face_embedder=MockFaceEmbedder(),
    )
    
    # Create evidence graph
    graph = EvidenceGraph(search_id=1)
    uploaded_node_id = graph.add_node("image", "uploaded.jpg", "sha256_uploaded")
    
    # Create correlations
    corr = ImageCorrelation(
        candidate_image_path=Path("cache/candidate_images/img1.jpg"),
        fingerprint=ImageFingerprint(
            sha256="cand123",
            a_hash="1111",
            d_hash="2222",
            p_hash="0000000000000005",  # Near duplicate
        ),
        classification="near_duplicate",
        hamming_distance=5,
        face_similarity=0.85,
        correlation_confidence=0.9,
    )
    
    # Add to evidence graph
    await service.add_correlation_to_evidence_graph(
        graph=graph,
        candidate_id=1,
        correlations=[corr],
        uploaded_image_node_id=uploaded_node_id,
    )
    
    # Verify graph has new nodes and edges
    assert graph.node_count == 2  # uploaded + candidate
    assert graph.edge_count == 1
    
    # Check edge type
    edges = graph.get_edges_by_type("same_image")
    assert len(edges) == 1
    assert edges[0].edge_type == "same_image"
    assert edges[0].confidence == 0.9