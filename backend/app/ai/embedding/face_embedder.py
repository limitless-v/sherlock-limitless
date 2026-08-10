"""Face embedding port — detect + align + embed an image.

Isolates the heavy InsightFace work behind a small protocol so local search
and face indexing can be tested with stubs, and so provider-specific model
types never leak into the search layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.ai.embedding.generator import EmbeddingGenerator
from app.ai.face_detection.detector import FaceDetector
from app.ai.preprocessing.pipeline import align_face
from app.config.settings import Settings


@dataclass(slots=True)
class FaceEmbedding:
    """One detected face plus its embedding and aligned crop."""

    embedding: np.ndarray  # float32, L2-normalized (512,)
    face_index: int
    source_path: str | None = None
    crop: np.ndarray | None = None  # aligned uint8 BGR (112, 112, 3)


class FaceEmbedder(ABC):
    """Protocol for turning an image into face embeddings."""

    @abstractmethod
    def embed_image(self, path: str | Path) -> list[FaceEmbedding]:
        """Return one FaceEmbedding per detected face (empty when no face)."""


class InsightFaceEmbedder(FaceEmbedder):
    """Default embedder composing the Phase 3-5 components."""

    def __init__(self, settings: Settings) -> None:
        self._detector = FaceDetector(settings)
        self._generator = EmbeddingGenerator(settings)

    def embed_image(self, path: str | Path) -> list[FaceEmbedding]:
        source_path = Path(path)
        image_nd = self._detector._read_image(source_path)  # noqa: SLF001 - reuse validation
        detections = self._detector.detect(image_nd)
        results: list[FaceEmbedding] = []
        for detection in detections:
            crop = align_face(image_nd, detection.kpts)
            vec = self._generator.embed(crop)
            results.append(
                FaceEmbedding(
                    embedding=vec,
                    face_index=detection.index,
                    source_path=str(source_path),
                    crop=crop,
                )
            )
        return results