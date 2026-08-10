"""Search context builder unit tests (roadmap Phase 15)."""

from datetime import datetime
from pathlib import Path

import numpy as np

from app.discovery.context.builder import SearchContextBuilder
from app.discovery.context.exif import ExifMetadata, GpsInfo
from app.discovery.context.ocr import OCRExtraction
from app.discovery.context.visual import VisualContext
from app.discovery.fingerprinting import FingerprintService


class StubExif:
    def extract(self, _path):
        return ExifMetadata(
            camera_make="Canon",
            taken_at=datetime(2023, 4, 5, 10, 0, 0),
            gps=GpsInfo(9.58, 76.25),
        )


class StubOCR:
    available = True

    def extract(self, _path):
        return OCRExtraction(
            engine_name="stub",
            text="Kochi Marine Drive\nThe Coffee Shop",
            blocks=[],
            urls=["https://example.com/img"],
            usernames=["alice"],
            hashtags=["kochi"],
        )


class StubVisual:
    def analyze(self, _path):
        return VisualContext(dominant_colors=["red"], brightness=0.5)


def _write_image(path: Path) -> None:
    from PIL import Image

    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(path)


def test_builder_assembles_context(tmp_path: Path):
    image = tmp_path / "photo.png"
    _write_image(image)

    builder = SearchContextBuilder(
        exif_extractor=StubExif(),
        ocr_engine=StubOCR(),
        visual_analyzer=StubVisual(),
        fingerprint_service=FingerprintService(),
    )
    ctx = builder.build(image, user_filters={"min_date": "2020-01-01"})

    assert ctx.image_hash is not None
    assert len(ctx.image_hash.sha256) == 64
    assert ctx.timestamp == datetime(2023, 4, 5, 10, 0, 0)
    assert ctx.location == "9.58, 76.25 (approx)"
    assert ctx.urls == ["https://example.com/img"]
    assert ctx.usernames == ["alice"]
    assert ctx.hashtags == ["kochi"]
    assert "kochi" in ctx.keywords
    assert "the" not in ctx.keywords
    assert ctx.language == "en"
    assert ctx.user_filters == {"min_date": "2020-01-01"}
    assert {"exif", "ocr", "visual", "fingerprint", "user_filters"} <= ctx.sources


def test_builder_without_ocr_and_without_filters(tmp_path: Path):
    image = tmp_path / "plain.png"
    _write_image(image)
    builder = SearchContextBuilder(
        exif_extractor=StubExif(),
        ocr_engine=None,
        visual_analyzer=StubVisual(),
        fingerprint_service=FingerprintService(),
    )
    ctx = builder.build(image)
    assert ctx.text == []
    assert ctx.urls == []
    assert ctx.keywords == []
    assert "ocr" not in ctx.sources
    assert "user_filters" not in ctx.sources


def test_builder_missing_image_raises(tmp_path: Path):
    import pytest

    builder = SearchContextBuilder(exif_extractor=StubExif(), ocr_engine=StubOCR(), visual_analyzer=StubVisual())
    with pytest.raises(FileNotFoundError):
        builder.build(tmp_path / "nope.png")