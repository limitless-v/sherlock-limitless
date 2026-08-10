"""Image fingerprinting unit tests (roadmap Phase 13)."""

from pathlib import Path

import numpy as np

from app.discovery.fingerprinting import (
    FingerprintService,
    ImageFingerprint,
    fingerprint_image,
    hamming_distance,
)


def _write_image(path: Path, pixels: np.ndarray) -> None:
    from PIL import Image

    Image.fromarray(pixels.astype("uint8")).save(path)


def _gradient_pixels() -> np.ndarray:
    rows = np.arange(64, dtype=np.float64)
    column = (rows[:, None] * 255 / 63).astype(np.uint8)  # vertical gradient
    return np.repeat(column[..., None], 3, axis=2)


def _checker_pixels() -> np.ndarray:
    base = np.indices((64, 64)).sum(axis=0) // 8 % 2
    return np.repeat((base * 255)[..., None], 3, axis=2).astype(np.uint8)


def test_fingerprint_sha256_matches_file_bytes(tmp_path: Path):
    path = tmp_path / "a.png"
    pixels = _gradient_pixels()
    _write_image(path, pixels)
    fp = fingerprint_image(path)
    assert fp.sha256 == FingerprintService.sha256_of(path.read_bytes())
    assert len(fp.sha256) == 64
    for h in (fp.a_hash, fp.d_hash, fp.p_hash):
        assert len(h) == 16


def test_near_duplicate_detected(tmp_path: Path):
    path_a = tmp_path / "a.png"
    path_b = tmp_path / "b.png"
    a = _gradient_pixels()
    b = np.clip(a.astype(np.int16) + 10, 0, 255).astype(np.uint8)  # +10 brightness: near duplicate
    _write_image(path_a, a)
    _write_image(path_b, b)

    fp_a = fingerprint_image(path_a)
    fp_b = fingerprint_image(path_b)
    service = FingerprintService()

    assert service.exact_match(fp_a, fp_b) is False  # bytes differ
    assert service.near_duplicate(fp_a, fp_b) is True
    assert hamming_distance(fp_a.p_hash, fp_b.p_hash) <= 10


def test_distinct_images_not_near_duplicates(tmp_path: Path):
    _write_image(tmp_path / "g.png", _gradient_pixels())
    _write_image(tmp_path / "c.png", _checker_pixels())
    fp_g = fingerprint_image(tmp_path / "g.png")
    fp_c = fingerprint_image(tmp_path / "c.png")
    assert hamming_distance(fp_g.p_hash, fp_c.p_hash) > 10
    assert FingerprintService().near_duplicate(fp_g, fp_c) is False


def test_hamming_identical_zero_and_service_match():
    fp = ImageFingerprint(a_hash="1234567890abcdef", d_hash="1234567890abcdef", p_hash="1234567890abcdef", sha256="x")
    assert hamming_distance(fp.p_hash, fp.p_hash) == 0
    assert FingerprintService().hamming("00ff", "01ff") == 1