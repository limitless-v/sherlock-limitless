"""Image fingerprinting (roadmap Phase 13).

Generates SHA256, aHash, dHash, and pHash fingerprints for an image using
only Pillow + NumPy (pHash uses a direct DCT-II, no SciPy dependency).

Purpose: exact/near-duplicate detection and image clustering. Hashes are
the evidence backbone for later image-correlation phases.
"""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageFingerprint:
    """Fingerprints computed for one image."""

    sha256: str
    a_hash: str
    d_hash: str
    p_hash: str


def _bits_to_hex(bits: np.ndarray) -> str:
    """Pack 64 (8x8 or 9x8) bits into 16 hex characters."""
    n = bits.size
    if n % 4:
        raise ValueError(f"cannot pack {n} bits into hex")
    out = []
    for i in range(0, n, 4):
        nibble = int("".join(str(int(b)) for b in bits[i : i + 4]), 2)
        out.append(f"{nibble:x}")
    return "".join(out)


def _ahash_bits(gray: Image.Image) -> np.ndarray:
    small = gray.resize((8, 8), Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.float64)
    return (arr > arr.mean()).astype(bool).flatten()


def _dhash_bits(gray: Image.Image) -> np.ndarray:
    small = gray.resize((9, 8), Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.float64)
    return (arr[:, :-1] > arr[:, 1:]).astype(bool).flatten()


def _dct2(matrix: np.ndarray) -> np.ndarray:
    """Orthonormal 2D DCT-II via a precomputed basis matrix."""
    n = matrix.shape[0]
    rows = np.arange(n)
    basis = np.zeros((n, n), dtype=np.float64)
    basis[0, :] = np.sqrt(1.0 / n)
    for k in range(1, n):
        basis[k, :] = np.sqrt(2.0 / n) * np.cos((np.pi * k * (2 * rows + 1)) / (2 * n))
    return basis @ matrix @ basis.T


def _phash_bits(gray: Image.Image) -> np.ndarray:
    small = gray.resize((32, 32), Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.float64)
    low = _dct2(arr)[:8, :8]
    return (low > np.median(low)).astype(bool).flatten()


def hamming_distance(a: str, b: str) -> int:
    """Number of differing bits between two hex-encoded hashes."""
    return sum((int(x, 16) ^ int(y, 16)).bit_count() for x, y in zip(a, b))


def fingerprint_image(image_path: Path | str) -> ImageFingerprint:
    """Compute all fingerprints for an image file."""
    path = Path(image_path)
    data = path.read_bytes()
    digest = sha256(data).hexdigest()
    with Image.open(path) as image:
        gray = image.convert("L")
        return ImageFingerprint(
            sha256=digest,
            a_hash=_bits_to_hex(_ahash_bits(gray)),
            d_hash=_bits_to_hex(_dhash_bits(gray)),
            p_hash=_bits_to_hex(_phash_bits(gray)),
        )


class FingerprintService:
    """Fingerprint generation and similarity helpers used by later phases."""

    @staticmethod
    def sha256_of(data: bytes) -> str:
        return sha256(data).hexdigest()

    @staticmethod
    def hamming(a: str, b: str) -> int:
        return hamming_distance(a, b)

    def fingerprint(self, image_path: Path | str) -> ImageFingerprint:
        """Fingerprint an image on disk."""
        return fingerprint_image(image_path)

    def exact_match(self, a: ImageFingerprint, b: ImageFingerprint) -> bool:
        """Same byte content (SHA256 equality)."""
        return a.sha256 == b.sha256

    def near_duplicate(
        self,
        a: ImageFingerprint,
        b: ImageFingerprint,
        p_hash_threshold: int = 10,
    ) -> bool:
        """Perceptual near-duplicate via pHash Hamming distance (default <= 10)."""
        return hamming_distance(a.p_hash, b.p_hash) <= p_hash_threshold