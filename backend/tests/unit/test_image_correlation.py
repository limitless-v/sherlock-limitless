"""Unit tests for image correlation (roadmap Phase 25)."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from app.discovery.fingerprinting import FingerprintService, ImageFingerprint, hamming_distance
from app.evidence.correlation import ImageCorrelator, ImageCorrelation
from app.agents.web_research.policies import UrlGuard


def test_image_correlator_exact_duplicate() -> None:
    """Test exact duplicate detection via SHA256."""
    fingerprint_service = FingerprintService()
    
    # Create two identical fingerprints
    fp1 = ImageFingerprint(
        sha256="abc123",
        a_hash="1111",
        d_hash="2222",
        p_hash="3333",
    )
    fp2 = ImageFingerprint(
        sha256="abc123",  # Same SHA256
        a_hash="4444",
        d_hash="5555",
        p_hash="6666",
    )
    
    # Mock face embedder
    class MockFaceEmbedder:
        def embed_image(self, path):
            return []
    
    correlator = ImageCorrelator(
        fingerprint_service=fingerprint_service,
        face_embedder=MockFaceEmbedder(),
    )
    
    # Test exact match
    assert fingerprint_service.exact_match(fp1, fp2) is True


def test_image_correlator_near_duplicate() -> None:
    """Test near duplicate detection via pHash."""
    fingerprint_service = FingerprintService()
    
    # pHash with small hamming distance
    fp1 = ImageFingerprint(
        sha256="abc123",
        a_hash="1111",
        d_hash="2222",
        p_hash="0000000000000000",
    )
    fp2 = ImageFingerprint(
        sha256="def456",
        a_hash="3333",
        d_hash="4444",
        p_hash="0000000000000001",  # 1 bit difference
    )
    
    assert fingerprint_service.near_duplicate(fp1, fp2, p_hash_threshold=10) is True
    assert fingerprint_service.near_duplicate(fp1, fp2, p_hash_threshold=0) is False


def test_image_correlator_similar() -> None:
    """Test similar detection via pHash."""
    fingerprint_service = FingerprintService()
    
    fp1 = ImageFingerprint(
        sha256="abc123",
        a_hash="1111",
        d_hash="2222",
        p_hash="0000000000000000",
    )
    fp2 = ImageFingerprint(
        sha256="def456",
        a_hash="3333",
        d_hash="4444",
        p_hash="000000000000ffff",  # ~16 bits different
    )
    
    hd = hamming_distance(fp1.p_hash, fp2.p_hash)
    assert hd <= 20  # Similar threshold
    assert hd > 10   # But not near duplicate


def test_image_correlator_unrelated() -> None:
    """Test unrelated images have high hamming distance."""
    fingerprint_service = FingerprintService()
    
    fp1 = ImageFingerprint(
        sha256="abc123",
        a_hash="1111",
        d_hash="2222",
        p_hash="0000000000000000",
    )
    fp2 = ImageFingerprint(
        sha256="def456",
        a_hash="3333",
        d_hash="4444",
        p_hash="ffffffffffffffff",  # Completely different
    )
    
    hd = hamming_distance(fp1.p_hash, fp2.p_hash)
    assert hd > 20  # Unrelated


def test_image_correlation_classification() -> None:
    """Test ImageCorrelation dataclass."""
    fp = ImageFingerprint(
        sha256="abc123",
        a_hash="1111",
        d_hash="2222",
        p_hash="3333",
    )
    
    corr = ImageCorrelation(
        candidate_image_path=Path("/tmp/test.jpg"),
        fingerprint=fp,
        classification="near_duplicate",
        hamming_distance=5,
        face_similarity=0.85,
        correlation_confidence=0.9,
    )
    
    assert corr.classification == "near_duplicate"
    assert corr.hamming_distance == 5
    assert corr.face_similarity == 0.85
    assert corr.correlation_confidence == 0.9
    
    data = corr.to_dict()
    assert data["classification"] == "near_duplicate"
    assert data["hamming_distance"] == 5
    assert data["face_similarity"] == 0.85


def test_fingerprint_service_hamming() -> None:
    """Test hamming distance calculation."""
    fingerprint_service = FingerprintService()
    
    # Identical
    assert fingerprint_service.hamming("0000", "0000") == 0
    
    # One hex char different (4 bits)
    assert fingerprint_service.hamming("0", "1") == 1
    
    # All 4 bits different
    assert fingerprint_service.hamming("0", "f") == 4
    
    # Full 16-char hash
    assert fingerprint_service.hamming("0" * 16, "f" * 16) == 64


@pytest.mark.asyncio
async def test_candidate_crawler_validation() -> None:
    """Test CandidateCrawler URL validation."""
    from app.osint.crawler.images import CandidateCrawler
    from app.config.settings import Settings
    from app.agents.web_research.policies import UrlGuard
    
    settings = Settings()
    # Use empty allow_domains to test default blocked hosts
    url_guard = UrlGuard(allow_domains=())
    crawler = CandidateCrawler(settings=settings, url_guard=url_guard)
    
    # Valid URL
    allowed, reason = crawler._validate_url("https://example.com/image.jpg")
    assert allowed is True
    assert reason == ""
    
    # SSRF - localhost (blocked by default blocked hosts)
    allowed, reason = crawler._validate_url("http://localhost/image.jpg")
    assert allowed is False
    assert "blocked" in reason.lower()
    
    # SSRF - private IP
    allowed, reason = crawler._validate_url("http://192.168.1.1/image.jpg")
    assert allowed is False
    assert "blocked" in reason.lower()
    
    # Invalid scheme
    allowed, reason = crawler._validate_url("ftp://example.com/image.jpg")
    assert allowed is False
    assert "scheme" in reason.lower()