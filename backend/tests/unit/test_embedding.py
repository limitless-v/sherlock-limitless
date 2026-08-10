"""Face embedding unit tests (roadmap Phase 5).

These need the ArcFace ONNX model (w600k_r50.onnx from the buffalo_l pack).
If it has not been downloaded yet (offline / fresh clone), the tests are
skipped instead of failing; run `python scripts/download_models.py` once.
"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.ai.embedding.generator import EmbeddingGenerator, EMBEDDING_MODEL_FILENAME
from app.ai.face_detection.detector import FaceDetector
from app.ai.matching.similarity import cosine_similarity
from app.ai.preprocessing.pipeline import align_face
from app.config.settings import get_settings

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_face.jpg"


@pytest.fixture(scope="module")
def generator() -> EmbeddingGenerator:
    gen = EmbeddingGenerator(get_settings())
    if not gen.model_ready_on_disk:
        pytest.skip(
            "ArcFace model not on disk; run `python scripts/download_models.py` first"
        )
    gen.load()
    return gen


def test_model_ready_flag_is_boolean():
    assert isinstance(EmbeddingGenerator(get_settings()).model_ready_on_disk, bool)


def test_dim_matches_settings(generator: EmbeddingGenerator):
    assert generator.dim == get_settings().embedding_dim == 512


def test_embed_returns_normalized_vector(generator: EmbeddingGenerator):
    crop = _aligned_face_crop()
    embedding = generator.embed(crop)
    assert embedding.shape == (512,)
    assert embedding.dtype == np.float32
    assert np.isfinite(embedding).all()
    assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-4)


def test_embed_is_deterministic(generator: EmbeddingGenerator):
    crop = _aligned_face_crop()
    assert np.array_equal(generator.embed(crop), generator.embed(crop))


def test_embed_self_similarity_high(generator: EmbeddingGenerator):
    crop = _aligned_face_crop()
    assert cosine_similarity(generator.embed(crop), generator.embed(crop)) > 0.999


def test_embed_differs_from_non_face(generator: EmbeddingGenerator):
    face_vec = generator.embed(_aligned_face_crop())
    non_face = np.full((112, 112, 3), 128, dtype=np.uint8)
    non_face_vec = generator.embed(non_face)
    self_cos = cosine_similarity(face_vec, face_vec)
    blank_cos = cosine_similarity(face_vec, non_face_vec)
    assert self_cos - blank_cos > 0.5


def test_embed_batch_matches_single(generator: EmbeddingGenerator):
    crop = _aligned_face_crop()
    single = generator.embed(crop)
    batch = generator.embed_batch([crop])[0]
    assert np.allclose(single, batch, atol=1e-5)


def _aligned_face_crop() -> np.ndarray:
    settings = get_settings()
    detector = FaceDetector(settings)
    detector.load()
    img = cv2.imread(str(FIXTURE))
    faces = detector.detect(img)
    assert faces, f"No face detected in fixture: {FIXTURE}"
    return align_face(img, faces[0].kpts)