"""Unit tests for evidence ranking (roadmap Phase 27)."""

import pytest
from app.evidence.ranking import EvidenceRanker, EvidenceStrength, EvidenceType, RankedEvidence
from app.evidence.schemas import EvidenceNodeData, EvidenceEdgeData


def test_evidence_ranker_same_image_exact() -> None:
    """Test ranking for exact image match."""
    ranker = EvidenceRanker()
    
    nodes = [
        EvidenceNodeData(node_type="image", entity_id="uploaded.jpg", entity_value="sha256_uploaded"),
        EvidenceNodeData(node_type="image", entity_id="candidate.jpg", entity_value="sha256_candidate"),
    ]
    edges = [
        EvidenceEdgeData(
            source_node_id=0,
            target_node_id=1,
            edge_type="same_image",
            source_url="correlation",
            confidence=1.0,
            metadata={"classification": "exact_duplicate", "hamming_distance": 0},
        ),
    ]
    
    ranked = ranker.rank_evidence(nodes, edges, uploaded_image_node_id=0)
    
    assert len(ranked) == 1
    re = ranked[0]
    assert re.evidence_strength == EvidenceStrength.STRONG
    assert re.evidence_type == EvidenceType.OBSERVED
    assert "exact_image_match_sha256" in re.signals
    assert re.confidence_score == 1.0


def test_evidence_ranker_same_image_near_duplicate() -> None:
    """Test ranking for near duplicate image."""
    ranker = EvidenceRanker()
    
    nodes = [
        EvidenceNodeData(node_type="image", entity_id="uploaded.jpg", entity_value="sha256_uploaded"),
        EvidenceNodeData(node_type="image", entity_id="candidate.jpg", entity_value="sha256_candidate"),
    ]
    edges = [
        EvidenceEdgeData(
            source_node_id=0,
            target_node_id=1,
            edge_type="same_image",
            source_url="correlation",
            confidence=0.9,
            metadata={"classification": "near_duplicate", "hamming_distance": 5},
        ),
    ]
    
    ranked = ranker.rank_evidence(nodes, edges, uploaded_image_node_id=0)
    
    assert len(ranked) == 1
    re = ranked[0]
    assert re.evidence_strength == EvidenceStrength.STRONG
    assert re.evidence_type == EvidenceType.OBSERVED
    assert "near_duplicate_phash_hamming:5" in re.signals
    assert re.confidence_score >= 0.9


def test_evidence_ranker_same_public_identifier() -> None:
    """Test ranking for same username across sources."""
    ranker = EvidenceRanker()
    
    nodes = [
        EvidenceNodeData(node_type="username", entity_id="github:johndoe", entity_value="johndoe"),
        EvidenceNodeData(node_type="profile", entity_id="https://github.com/johndoe", entity_value="https://github.com/johndoe"),
    ]
    edges = [
        EvidenceEdgeData(
            source_node_id=0,
            target_node_id=1,
            edge_type="same_public_identifier",
            source_url="https://example.com/page",
        ),
    ]
    
    ranked = ranker.rank_evidence(nodes, edges)
    
    assert len(ranked) == 1
    re = ranked[0]
    assert re.evidence_strength == EvidenceStrength.STRONG
    assert re.evidence_type == EvidenceType.OBSERVED
    assert "same_public_identifier" in re.signals
    assert re.confidence_score >= 0.85


def test_evidence_ranker_links_to() -> None:
    """Test ranking for hyperlink edges."""
    ranker = EvidenceRanker()
    
    nodes = [
        EvidenceNodeData(node_type="url", entity_id="https://example.com", entity_value="https://example.com"),
        EvidenceNodeData(node_type="url", entity_id="https://other.com", entity_value="https://other.com"),
    ]
    edges = [
        EvidenceEdgeData(
            source_node_id=0,
            target_node_id=1,
            edge_type="links_to",
            source_url="https://example.com",
        ),
    ]
    
    ranked = ranker.rank_evidence(nodes, edges)
    
    assert len(ranked) == 1
    re = ranked[0]
    assert re.evidence_type == EvidenceType.INFERENCE
    assert re.evidence_strength == EvidenceStrength.WEAK
    assert "hyperlink" in re.signals
    assert re.confidence_score < 0.5


def test_evidence_ranker_mentions() -> None:
    """Test ranking for username mentions."""
    ranker = EvidenceRanker()
    
    nodes = [
        EvidenceNodeData(node_type="username", entity_id="extracted:johndoe", entity_value="johndoe"),
        EvidenceNodeData(node_type="url", entity_id="https://example.com", entity_value="https://example.com"),
    ]
    edges = [
        EvidenceEdgeData(
            source_node_id=0,
            target_node_id=1,
            edge_type="mentions",
            source_url="https://example.com",
        ),
    ]
    
    ranked = ranker.rank_evidence(nodes, edges)
    
    assert len(ranked) == 1
    re = ranked[0]
    assert re.evidence_type == EvidenceType.INFERENCE
    assert re.evidence_strength == EvidenceStrength.WEAK
    assert "username_mention" in re.signals


def test_evidence_ranker_sorting() -> None:
    """Test that ranked evidence is sorted by confidence score descending."""
    ranker = EvidenceRanker()
    
    nodes = [
        EvidenceNodeData(node_type="image", entity_id="img1", entity_value="sha1"),
        EvidenceNodeData(node_type="image", entity_id="img2", entity_value="sha2"),
        EvidenceNodeData(node_type="username", entity_id="user1", entity_value="user1"),
        EvidenceNodeData(node_type="profile", entity_id="prof1", entity_value="prof1"),
    ]
    edges = [
        EvidenceEdgeData(source_node_id=0, target_node_id=1, edge_type="same_image", source_url="corr", confidence=0.9, metadata={"classification": "near_duplicate"}),  # Strong
        EvidenceEdgeData(source_node_id=2, target_node_id=3, edge_type="same_public_identifier", source_url="page"),  # Strong
        EvidenceEdgeData(source_node_id=0, target_node_id=2, edge_type="mentions", source_url="page"),  # Weak
    ]
    
    ranked = ranker.rank_evidence(nodes, edges)
    
    # Should be sorted by confidence descending
    assert ranked[0].confidence_score >= ranked[1].confidence_score
    assert ranked[1].confidence_score >= ranked[2].confidence_score


def test_ranked_evidence_serialization() -> None:
    """Test RankedEvidence to_dict serialization."""
    re = RankedEvidence(
        node_id=1,
        edge_id=0,
        evidence_strength=EvidenceStrength.STRONG,
        evidence_type=EvidenceType.OBSERVED,
        signals=["exact_image_match_sha256", "high_face_similarity"],
        confidence_score=0.95,
        metadata={"source_node_type": "image", "target_node_type": "image"},
    )
    
    data = re.to_dict()
    assert data["node_id"] == 1
    assert data["edge_id"] == 0
    assert data["evidence_strength"] == "strong"
    assert data["evidence_type"] == "observed"
    assert data["signals"] == ["exact_image_match_sha256", "high_face_similarity"]
    assert data["confidence_score"] == 0.95


def test_evidence_ranker_thresholds() -> None:
    """Test custom thresholds."""
    ranker = EvidenceRanker(strong_threshold=0.9, medium_threshold=0.6)
    
    nodes = [
        EvidenceNodeData(node_type="image", entity_id="img1", entity_value="sha1"),
        EvidenceNodeData(node_type="image", entity_id="img2", entity_value="sha2"),
    ]
    edges = [
        EvidenceEdgeData(
            source_node_id=0, target_node_id=1, edge_type="same_image",
            source_url="corr", confidence=0.85, metadata={"classification": "similar"}
        ),
    ]
    
    ranked = ranker.rank_evidence(nodes, edges)
    
    # With strong_threshold=0.9, confidence 0.85 should be MEDIUM
    assert ranked[0].evidence_strength == EvidenceStrength.MEDIUM