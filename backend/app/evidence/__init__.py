"""Evidence package (roadmap Phases 23-27).

Candidate extraction, evidence graph, image correlation, and ranking.
"""

from app.evidence.correlation import ImageCorrelator, ImageCorrelation
from app.evidence.extraction import CandidateExtractor, ExtractedCandidate
from app.evidence.graph import EvidenceGraph
from app.evidence.ranking import EvidenceRanker, RankedEvidence, EvidenceStrength, EvidenceType
from app.evidence.schemas import (
    CandidateExtraction,
    CandidateImageData,
    CandidateProfileData,
    CandidateLocationData,
    CandidateDateData,
    EvidenceNodeData,
    EvidenceEdgeData,
    EvidenceGraphData,
)

__all__ = [
    "CandidateExtractor",
    "ExtractedCandidate",
    "CandidateExtraction",
    "CandidateImageData",
    "CandidateProfileData",
    "CandidateLocationData",
    "CandidateDateData",
    "EvidenceGraph",
    "EvidenceNodeData",
    "EvidenceEdgeData",
    "EvidenceGraphData",
    "ImageCorrelator",
    "ImageCorrelation",
    "EvidenceRanker",
    "RankedEvidence",
    "EvidenceStrength",
    "EvidenceType",
]