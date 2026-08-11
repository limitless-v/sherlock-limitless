"""Image correlation (roadmap Phase 25).

Compares discovered candidate images against the uploaded image using:
- Perceptual hashing (pHash) for near-duplicate detection
- Face embeddings for facial similarity
- Classifies: exact_duplicate, near_duplicate, similar, unrelated
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from app.ai.embedding.face_embedder import FaceEmbedder, FaceEmbedding
from app.ai.matching.similarity import cosine_similarity
from app.discovery.fingerprinting import FingerprintService, ImageFingerprint, hamming_distance


@dataclass
class ImageCorrelation:
    """Result of correlating a candidate image with the uploaded image."""

    candidate_image_path: Path
    fingerprint: ImageFingerprint
    classification: str  # exact_duplicate, near_duplicate, similar, unrelated
    hamming_distance: int
    face_similarity: float | None = None
    correlation_confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "candidate_image_path": str(self.candidate_image_path),
            "sha256": self.fingerprint.sha256,
            "p_hash": self.fingerprint.p_hash,
            "classification": self.classification,
            "hamming_distance": self.hamming_distance,
            "face_similarity": self.face_similarity,
            "correlation_confidence": self.correlation_confidence,
        }


class ImageCorrelator:
    """Correlate candidate images with the uploaded reference image."""

    def __init__(
        self,
        fingerprint_service: FingerprintService,
        face_embedder: FaceEmbedder,
        p_hash_threshold_exact: int = 0,
        p_hash_threshold_near: int = 10,
        p_hash_threshold_similar: int = 20,
        face_similarity_threshold: float = 0.75,
    ) -> None:
        self._fingerprints = fingerprint_service
        self._face_embedder = face_embedder
        self._p_hash_threshold_exact = p_hash_threshold_exact
        self._p_hash_threshold_near = p_hash_threshold_near
        self._p_hash_threshold_similar = p_hash_threshold_similar
        self._face_similarity_threshold = face_similarity_threshold

    def correlate(
        self,
        uploaded_fingerprint: ImageFingerprint,
        uploaded_embeddings: list[np.ndarray] | None,
        candidate_images: list[Path],
    ) -> list[ImageCorrelation]:
        """Correlate multiple candidate images against the uploaded image.

        Args:
            uploaded_fingerprint: Fingerprint of the uploaded reference image
            uploaded_embeddings: Face embeddings from the uploaded image (optional)
            candidate_images: List of paths to candidate images to correlate

        Returns:
            List of ImageCorrelation results
        """
        results = []
        for candidate_path in candidate_images:
            if not candidate_path.exists():
                continue

            try:
                correlation = self._correlate_single(
                    uploaded_fingerprint, uploaded_embeddings, candidate_path
                )
                results.append(correlation)
            except Exception:
                # Skip images that can't be processed
                continue

        return results

    def _correlate_single(
        self,
        uploaded_fp: ImageFingerprint,
        uploaded_embeddings: list[np.ndarray] | None,
        candidate_path: Path,
    ) -> ImageCorrelation:
        """Correlate a single candidate image."""
        # Compute candidate fingerprint
        cand_fp = self._fingerprints.fingerprint(candidate_path)

        # Check exact duplicate (SHA256)
        if self._fingerprints.exact_match(uploaded_fp, cand_fp):
            classification = "exact_duplicate"
            hamming_dist = 0
            confidence = 1.0
        # Check near duplicate (pHash <= threshold)
        elif self._fingerprints.near_duplicate(uploaded_fp, cand_fp, self._p_hash_threshold_near):
            classification = "near_duplicate"
            hamming_dist = hamming_distance(uploaded_fp.p_hash, cand_fp.p_hash)
            confidence = 1.0 - (hamming_dist / 64.0) * 0.5  # Scale confidence
        # Check similar (pHash <= similar threshold)
        elif hamming_distance(uploaded_fp.p_hash, cand_fp.p_hash) <= self._p_hash_threshold_similar:
            classification = "similar"
            hamming_dist = hamming_distance(uploaded_fp.p_hash, cand_fp.p_hash)
            confidence = 0.5 * (1.0 - hamming_dist / 64.0)
        else:
            classification = "unrelated"
            hamming_dist = hamming_distance(uploaded_fp.p_hash, cand_fp.p_hash)
            confidence = 0.1

        # Face embedding correlation if available
        face_similarity = None
        if uploaded_embeddings and len(uploaded_embeddings) > 0:
            face_similarity = self._compare_faces(uploaded_embeddings, candidate_path)
            # Boost confidence if face similarity is high
            if face_similarity is not None and face_similarity >= self._face_similarity_threshold:
                confidence = max(confidence, 0.8)
                if classification == "unrelated":
                    classification = "similar"  # Face match upgrades classification

        return ImageCorrelation(
            candidate_image_path=candidate_path,
            fingerprint=cand_fp,
            classification=classification,
            hamming_distance=hamming_dist,
            face_similarity=face_similarity,
            correlation_confidence=round(confidence, 3),
        )

    def _compare_faces(
        self,
        uploaded_embeddings: list[np.ndarray],
        candidate_path: Path,
    ) -> float | None:
        """Compare faces between uploaded image and candidate image."""
        try:
            # Use FaceEmbedder to get face embeddings from candidate image
            face_embeddings: list[FaceEmbedding] = self._face_embedder.embed_image(candidate_path)
            if not face_embeddings:
                return None

            candidate_embeddings = [fe.embedding for fe in face_embeddings]
            if not candidate_embeddings:
                return None

            # Compute max similarity between any uploaded face and any candidate face
            max_similarity = 0.0
            for up_emb in uploaded_embeddings:
                for cand_emb in candidate_embeddings:
                    sim = cosine_similarity(up_emb, cand_emb)
                    max_similarity = max(max_similarity, sim)

            return max_similarity if max_similarity > 0 else None

        except Exception:
            return None