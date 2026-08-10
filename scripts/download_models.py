#!/usr/bin/env python3
"""Download the InsightFace model pack (buffalo_l with SCRFD detection).

Run from the repository root:
    python scripts/download_models.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ai.face_detection.detector import FaceDetector  # noqa: E402
from app.config.settings import get_settings  # noqa: E402


def main() -> None:
    detector = FaceDetector(get_settings())
    pack = detector.model_pack_dir
    print(f"Model target: {pack.resolve()}")
    detector.load()
    files = list(pack.glob("*")) if pack.is_dir() else []
    print(f"Downloaded/verified {len(files)} file(s): {sorted(p.name for p in files)}")
    print("Face detection model ready.")


if __name__ == "__main__":
    main()