"""Face embedding generation via ArcFace — roadmap Phase 5.

Runs the w600k_r50 ArcFace ONNX model (shipped in the buffalo_l pack) through
a dedicated ONNX Runtime session. Input is an aligned 112x112 BGR crop from
the Phase 4 preprocessing module; output is a 512-d L2-normalized embedding.

The normalization mirrors InsightFace exactly ((BGR - 127.5) / 127.5), so
embeddings are comparable with InsightFace's own reference output.
"""

import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.config.settings import Settings
from app.ai.preprocessing.pipeline import ALIGNMENT_SIZE

EMBEDDING_MODEL_FILENAME = "w600k_r50.onnx"


@dataclass(slots=True)
class EmbeddingResult:
    """One face embedding."""

    embedding: np.ndarray  # float32, L2-normalized (dim,)
    dim: int


class EmbeddingGenerator:
    """Produce L2-normalized ArcFace embeddings from aligned face crops."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model_path = settings.face_model_pack_dir / EMBEDDING_MODEL_FILENAME
        self._use_gpu = settings.ai_use_gpu or settings.ai_device == "cuda"
        self._session = None
        self._error: Exception | None = None
        self._lock = threading.Lock()
        self._dim = settings.embedding_dim

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_path(self) -> Path:
        """Path to the ArcFace ONNX file."""
        return self._model_path

    @property
    def available(self) -> bool:
        """True when the embedding model can be loaded."""
        if self._session is not None:
            return True
        try:
            self.load()
            return True
        except Exception as exc:  # noqa: BLE001 - availability probe
            self._error = exc
            return False

    @property
    def last_error(self) -> Exception | None:
        return self._error

    @property
    def model_ready_on_disk(self) -> bool:
        """True when the ArcFace ONNX file has been downloaded."""
        return self._model_path.is_file()

    def _providers(self) -> list[str]:
        if self._use_gpu:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def load(self) -> None:
        """Load the ArcFace model once (lazy)."""
        if self._session is not None:
            return
        with self._lock:
            if self._session is not None:
                return
            try:
                if not self._model_path.is_file():
                    raise FileNotFoundError(
                        f"Embedding model not found: {self._model_path} "
                        "(run scripts/download_models.py to fetch the buffalo_l pack)"
                    )
                import onnxruntime as ort

                self._session = ort.InferenceSession(
                    str(self._model_path.resolve()),
                    providers=self._providers(),
                )
                output = self._session.get_outputs()[0]
                output_dim = output.shape[-1] if output.shape else self._dim
                if output_dim != self._dim:
                    raise ValueError(
                        f"Model output dim {output_dim} does not match EMBEDDING_DIM={self._dim}"
                    )
            except Exception as exc:
                self._error = exc
                raise

    def _prepare(self, aligned_face: np.ndarray) -> np.ndarray:
        """Normalize an aligned BGR crop into the model's NCHW input."""
        if aligned_face is None or aligned_face.size == 0:
            raise ValueError("Cannot embed an empty face crop")
        img = aligned_face
        if img.shape[0] != ALIGNMENT_SIZE or img.shape[1] != ALIGNMENT_SIZE:
            img = cv2.resize(img, (ALIGNMENT_SIZE, ALIGNMENT_SIZE), interpolation=cv2.INTER_AREA)
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        if img.dtype != np.uint8:
            img = np.clip(img, 0, 255).astype(np.uint8)
        normed = img.astype(np.float32)
        normed = (normed - 127.5) / 127.5
        return normed.transpose(2, 0, 1)[None, ...]

    def embed(self, aligned_face: np.ndarray) -> np.ndarray:
        """Return the L2-normalized 512-d embedding of an aligned face crop."""
        self.load()
        with self._lock:
            prepared = self._prepare(aligned_face)
            output = self._session.run(None, {"input.1": prepared})[0]
        vector = output[0].astype(np.float32)
        norm = float(np.linalg.norm(vector))
        if norm == 0:
            raise ValueError("Embedding model returned a zero vector")
        return vector / norm

    def embed_batch(self, crops: list[np.ndarray]) -> list[np.ndarray]:
        """Embed several aligned crops in one ONNX call."""
        self.load()
        with self._lock:
            prepared = self._prepare_batch(crops)
            outputs = self._session.run(None, {"input.1": prepared})[0]
        results: list[np.ndarray] = []
        for row in outputs:
            vector = np.asarray(row).reshape(-1).astype(np.float32)
            norm = float(np.linalg.norm(vector))
            if norm == 0:
                raise ValueError("Embedding model returned a zero vector")
            results.append(vector / norm)
        return results

    def _prepare_batch(self, crops: list[np.ndarray]) -> np.ndarray:
        return np.stack([self._prepare(crop)[0] for crop in crops])