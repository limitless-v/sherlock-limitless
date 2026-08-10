#!/usr/bin/env python3
"""Phase 6 endpoint demo: build a FAISS gallery and query it.

Usage (from the repository root):
    python scripts/face_index_demo.py --gallery <dir> --query <image> [--top-k 5]
    python scripts/face_index_demo.py --gallery <dir> --build-only

For each image in <dir> (sorted), the first detected face is aligned and
embedded; the embedding is added to the FAISS index under an entity id
matching its file index + 1. Non-face images are embedded as-is (resized
112x112) so a gallery can mix people and distractors.

The index is persisted to embeddings/faiss.index, reloaded on the query,
proving the save/load roundtrip works.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import cv2  # noqa: E402

from app.ai.embedding.generator import EmbeddingGenerator  # noqa: E402
from app.ai.face_detection.detector import FaceDetector  # noqa: E402
from app.ai.preprocessing.pipeline import align_face  # noqa: E402
from app.ai.vector_db.faiss_index import FaissIndex  # noqa: E402
from app.config.settings import get_settings  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _embed_image(img_path: Path, detector: FaceDetector, generator: EmbeddingGenerator):
    img = cv2.imread(str(img_path))
    if img is None:
        raise ValueError(f"Could not read image: {img_path}")
    faces = detector.detect(img)
    if faces:
        return generator.embed(align_face(img, faces[0].kpts))
    return generator.embed(img)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and query a local FAISS face gallery")
    parser.add_argument("--gallery", required=True, help="Directory of gallery images")
    parser.add_argument("--query", help="Query image to search for")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to print")
    parser.add_argument("--build-only", action="store_true", help="Build/save the index only")
    args = parser.parse_args()

    gallery = Path(args.gallery)
    if not gallery.is_dir():
        print(f"Error: gallery not found: {gallery}")
        return 2

    settings = get_settings()
    detector = FaceDetector(settings)
    generator = EmbeddingGenerator(settings)
    store = FaissIndex(settings)

    images = sorted(p for p in gallery.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        print(f"Error: no images in gallery: {gallery}")
        return 2
    if not detector.model_ready_on_disk or not generator.model_ready_on_disk:
        print("Model packs missing; run `python scripts/download_models.py` first")
        return 3

    print(f"Indexing {len(images)} gallery images -> {settings.faiss_index_abs}")
    for entity_id, img_path in enumerate(images, start=1):
        vec = _embed_image(img_path, detector, generator)
        store.add(vec, entity_id)
        print(f"  [{entity_id}] {img_path.name} (norm={float(vec.dot(vec)) ** 0.5:.4f})")
    print(f"Indexed vectors: {store.count}")
    store.save()
    print(f"Saved index to {settings.faiss_index_abs}")

    if args.build_only:
        return 0
    if args.query is None:
        print("Tip: pass --query <image> to search, or --build-only to skip query.")
        return 0

    query_path = Path(args.query)
    if not query_path.is_file():
        print(f"Error: query image not found: {query_path}")
        return 2

    reloaded = FaissIndex(settings)
    reloaded.load(settings.faiss_index_abs, settings.embedding_dim)
    print(f"Reloaded index from disk: {reloaded.count} vectors")

    query_vec = _embed_image(query_path, detector, generator)
    print(f"Query: {query_path.name}")
    for entity_id, score in reloaded.search(list(query_vec), args.top_k):
        source = images[entity_id - 1].name if 0 < entity_id <= len(images) else f"id={entity_id}"
        print(f"  id={entity_id} ({source}) score={score:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())