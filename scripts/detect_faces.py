#!/usr/bin/env python3
"""Detect (and optionally embed) faces in an image.

Usage (from the repository root):
    python scripts/detect_faces.py <image_path>
    python scripts/detect_faces.py --embed <image_path>

Prints each detection's bounding box, score, and landmarks. With --embed,
run the Phase 4 -> Phase 5 chain and print the ArcFace embedding dimension,
norm, and a short digest per face. Downloads model packs on first run.
"""

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ai.embedding.generator import EmbeddingGenerator  # noqa: E402
from app.ai.face_detection.detector import FaceDetector  # noqa: E402
from app.ai.preprocessing.pipeline import align_face  # noqa: E402
from app.config.settings import get_settings  # noqa: E402


def _short_digest(embedding) -> str:
    digest = hashlib.sha256(embedding.tobytes()).hexdigest()
    return digest[:16]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="Path to the image to analyze")
    parser.add_argument("--embed", action="store_true", help="Also compute ArcFace embeddings")
    args = parser.parse_args()

    path = Path(args.image)
    if not path.is_file():
        print(f"Error: image not found: {path}")
        return 2

    settings = get_settings()
    detector = FaceDetector(settings)
    if not detector.model_ready_on_disk:
        print(f"Downloading detection model pack to {detector.model_pack_dir} ...")
    detections = detector.detect(path)
    print(f"Faces detected: {len(detections)}")

    generator = EmbeddingGenerator(settings) if args.embed else None
    if generator is not None and not generator.model_ready_on_disk:
        print(f"Embedding model not found: {generator.model_path.name} (run scripts/download_models.py)")

    import cv2

    img = cv2.imread(str(path))
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        line = (
            f"  [{det.index}] bbox=({x1:.1f}, {y1:.1f}) -> ({x2:.1f}, {y2:.1f}) "
            f"| landmarks={len(det.kpts)} | score={det.det_score:.3f}"
        )
        if generator is not None:
            crop = align_face(img, det.kpts)
            embedding = generator.embed(crop)
            norm = float(embedding.dot(embedding)) ** 0.5
            line += (
                f"\n      embedding: dim={embedding.shape[0]} norm={norm:.4f} "
                f"digest={_short_digest(embedding)}"
            )
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())