"""Face preprocessing unit tests (roadmap Phase 4).

Alignment is a pure OpenCV/InsightFace-util operation and needs no model
on disk, so these tests always run.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.ai.preprocessing.pipeline import ALIGNMENT_SIZE, align_face, validate_landmarks

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_face.jpg"


@pytest.fixture(scope="module")
def image() -> np.ndarray:
    img = cv2.imread(str(FIXTURE))
    assert img is not None, f"Fixture missing: {FIXTURE}"
    return img


def _synthetic_landmarks(h: int, w: int) -> list[list[float]]:
    # Rough 5-point face template (ArcFace order) scaled to the image.
    return [
        [0.40 * w, 0.40 * h],  # right eye
        [0.60 * w, 0.40 * h],  # left eye
        [0.50 * w, 0.50 * h],  # nose
        [0.42 * w, 0.62 * h],  # right mouth corner
        [0.58 * w, 0.62 * h],  # left mouth corner
    ]


def test_align_face_returns_crop_shape(image: np.ndarray):
    crop = align_face(image, _synthetic_landmarks(*image.shape[:2]))
    assert crop.shape == (ALIGNMENT_SIZE, ALIGNMENT_SIZE, 3)
    assert crop.dtype == np.uint8
    assert np.isfinite(crop).all()


def test_align_face_is_deterministic(image: np.ndarray):
    kpts = _synthetic_landmarks(*image.shape[:2])
    first = align_face(image, kpts)
    second = align_face(image, kpts)
    assert np.array_equal(first, second)


def test_validate_landmarks_rejects_wrong_count():
    with pytest.raises(ValueError, match="exactly 5 landmarks"):
        validate_landmarks([[0, 0], [1, 1]])


def test_align_face_rejects_wrong_landmark_count(image: np.ndarray):
    with pytest.raises(ValueError, match="exactly 5 landmarks"):
        align_face(image, [[0, 0]] * 4)


def test_align_face_rejects_empty_image():
    empty = np.zeros((0, 0, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="empty image"):
        align_face(empty, _synthetic_landmarks(10, 10))