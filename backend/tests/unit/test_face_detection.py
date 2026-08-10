"""Face detection unit tests (roadmap Phase 3).

The detection test requires the InsightFace model pack on disk
(models/<insightface_model>/). If it has not been downloaded yet (e.g. a
fresh clone running offline), the test is skipped instead of failing;
run `python scripts/download_models.py` once to enable it.
"""

from pathlib import Path

import pytest

from app.ai.face_detection.detector import FaceDetector
from app.config.settings import get_settings

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_face.jpg"


@pytest.fixture(scope="module")
def detector() -> FaceDetector:
    det = FaceDetector(get_settings())
    if not det.model_ready_on_disk:
        pytest.skip(
            "InsightFace model pack not on disk; run `python scripts/download_models.py` first"
        )
    det.load()
    return det


def test_model_ready_flag_is_boolean():
    assert isinstance(FaceDetector(get_settings()).model_ready_on_disk, bool)


def test_detect_on_missing_file_raises(detector: FaceDetector):
    with pytest.raises(ValueError):
        detector.detect(FIXTURE.parent / "does_not_exist.jpg")


def test_detect_finds_known_face(detector: FaceDetector):
    faces = detector.detect(FIXTURE)
    assert len(faces) >= 1
    face = faces[0]
    x1, y1, x2, y2 = face.bbox
    assert face.det_score >= get_settings().face_det_confidence
    assert 0 <= x1 < x2 <= 512
    assert 0 <= y1 < y2 <= 512
    assert len(face.kpts) == 5


def test_detect_empty_array_returns_empty(detector: FaceDetector):
    detector.load()
    faces = detector.detect(_blank_image())
    assert faces == []


def _blank_image():
    import numpy as np

    return np.zeros((64, 64, 3), dtype=np.uint8)