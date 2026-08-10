#!/usr/bin/env python3
"""Phase 8 tool: ingest a gallery folder into the local face database.

Usage (from the repository root):
    python scripts/ingest_gallery.py --gallery <dir>

For every image in <dir> (sorted), detects faces, persists aligned crops +
embeddings to disk (cache/faces, embeddings/faces), records DetectedFace
rows in the database, and adds embeddings to the FAISS index under the row
ids. Run `python scripts/face_index_demo.py --query <photo.jpg>` or use
POST /api/v1/search {"mode": "local"} to search the result.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ai.embedding.face_embedder import InsightFaceEmbedder  # noqa: E402
from app.ai.vector_db.faiss_index import FaissIndex  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.database.session import AsyncSessionLocal  # noqa: E402
from app.repositories.faces import FaceRepository  # noqa: E402
from app.repositories.search_history import SearchHistoryRepository  # noqa: E402
from app.services.face_indexing_service import FaceIndexingService  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


async def run(gallery: Path) -> int:
    settings = get_settings()
    if not settings.face_model_pack_dir.is_dir():
        print("Model pack missing; run `python scripts/download_models.py` first")
        return 3

    images = sorted(p for p in gallery.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        print(f"Error: no images in gallery: {gallery}")
        return 2

    async with AsyncSessionLocal() as session:
        service = FaceIndexingService(
            settings=settings,
            embedder=InsightFaceEmbedder(settings),
            vector_store=FaissIndex(settings),
            face_repo=FaceRepository(session),
            search_repo=SearchHistoryRepository(session),
        )
        total = 0
        for i, img_path in enumerate(images, start=1):
            count = await service.index_image(img_path)
            total += count
            print(f"[{i:03d}] {img_path.name}: {count} face(s) indexed")
        print(f"Done: {total} faces indexed from {len(images)} images")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a gallery into the local face database")
    parser.add_argument("--gallery", required=True, help="Directory of gallery images")
    args = parser.parse_args()
    gallery = Path(args.gallery)
    if not gallery.is_dir():
        print(f"Error: gallery not found: {gallery}")
        return 2
    return asyncio.run(run(gallery))


if __name__ == "__main__":
    sys.exit(main())