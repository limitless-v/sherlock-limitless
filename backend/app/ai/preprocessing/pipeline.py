"""Face preprocessing — roadmap Phase 4.

Aligns a detected face into a fixed 112x112 (ArcFace convention) crop so the
embedding model sees consistent geometry regardless of the source photo.
"""

import numpy as np

ALIGNMENT_SIZE = 112
LANDMARK_COUNT = 5

_face_align = None


def _norm_crop(image: np.ndarray, landmark: list[list[float]], image_size: int) -> np.ndarray:
    """Lazily import and call InsightFace's landmark-based alignment."""
    global _face_align
    if _face_align is None:
        from insightface.utils import face_align

        _face_align = face_align
    landmark_arr = np.asarray(landmark, dtype=np.float64).reshape(5, 2)
    return _face_align.norm_crop(image, landmark_arr, image_size=image_size, mode="arcface")


def validate_landmarks(kpts: list[list[float]]) -> list[list[float]]:
    """Ensure exactly LANDMARK_COUNT 2D landmarks are provided."""
    if kpts is None or len(kpts) != LANDMARK_COUNT:
        raise ValueError(
            f"Face alignment requires exactly {LANDMARK_COUNT} landmarks, got {len(kpts) if kpts is not None else None}"
        )
    return [[float(x), float(y)] for x, y in kpts]


def align_face(image: np.ndarray, kpts: list[list[float]], image_size: int = ALIGNMENT_SIZE) -> np.ndarray:
    """Align a detected face to a fixed-size crop using its 5 landmarks.

    Args:
        image: BGR image (H, W, 3) as loaded by cv2.
        kpts: 5 facial landmarks from face detection, e.g. [[x, y], ...].
        image_size: output crop side length (ArcFace default is 112).

    Returns:
        uint8 BGR crop of shape (image_size, image_size, 3).
    """
    if image is None or image.size == 0:
        raise ValueError("Cannot align an empty image")
    landmark = validate_landmarks(kpts)
    return _norm_crop(image, landmark, image_size)