"""Face detection via InsightFace (SCRFD / RetinaFace) — roadmap Phase 3.

Wraps insightface.app.FaceAnalysis behind a narrow, config-driven API.
Model files (buffalo_l pack) are stored under the configured models
directory and downloaded lazily on first model load.
"""

import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.config.settings import Settings


@dataclass(slots=True)
class FaceDetection:
    """One detected face."""

    index: int
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 (pixels)
    kpts: list[list[float]]  # 5 landmarks (e.g. eyes, nose, mouth corners)
    det_score: float


class FaceDetector:
    """Detect faces in an image using the configured InsightFace model."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model_name = settings.insightface_model
        self._det_thresh = settings.face_det_confidence
        self._det_size = (640, 640)
        self._use_gpu = settings.ai_use_gpu or settings.ai_device == "cuda"
        self._models_dir = settings.models_dir
        self._app = None
        self._error: Exception | None = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        """True when the detection model can be loaded (may download it)."""
        if self._app is not None:
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
    def model_pack_dir(self) -> Path:
        """Directory containing the downloaded InsightFace model pack.

        FaceAnalysis stores packs under <root>/models/<name>; our models
        storage dir is passed as root.
        """
        return self._settings.face_model_pack_dir

    @property
    def model_ready_on_disk(self) -> bool:
        """True when the model pack has already been downloaded."""
        pack = self.model_pack_dir
        return pack.is_dir() and any(pack.glob("*.onnx"))

    def _providers(self) -> list[str]:
        if self._use_gpu:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def load(self) -> None:
        """Load the detection model once (lazy; downloads on first use)."""
        if self._app is not None:
            return
        with self._lock:
            if self._app is not None:
                return
            try:
                from insightface.app import FaceAnalysis

                self._models_dir.mkdir(parents=True, exist_ok=True)
                app = FaceAnalysis(
                    name=self._model_name,
                    root=str(self._models_dir.resolve()),
                    providers=self._providers(),
                )
                app.prepare(
                    ctx_id=0 if self._use_gpu else -1,
                    det_size=self._det_size,
                    det_thresh=self._det_thresh,
                )
                self._app = app
            except Exception as exc:
                self._error = exc
                raise

    def detect(self, image: str | Path | np.ndarray) -> list[FaceDetection]:
        """Return all faces detected in the image (empty list when none)."""
        self.load()
        img = self._read_image(image)
        with self._lock:
            faces = self._app.get(img)
        return [
            FaceDetection(
                index=idx,
                bbox=tuple(float(v) for v in face.bbox),
                kpts=[[float(v) for v in pt] for pt in face.kps],
                det_score=float(face.det_score),
            )
            for idx, face in enumerate(faces)
        ]

    @staticmethod
    def _read_image(image: str | Path | np.ndarray) -> np.ndarray:
        if isinstance(image, (str, Path)):
            img = cv2.imread(str(image))
            if img is None:
                raise ValueError(f"Could not read image: {image}")
            return img
        if isinstance(image, np.ndarray):
            return image
        raise TypeError(f"Unsupported image input: {type(image)!r}")