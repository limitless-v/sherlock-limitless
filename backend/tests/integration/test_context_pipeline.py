"""End-to-end local search-context pipeline (roadmap Phases 11-15).

Builds a real SearchContext from a fixture image using the actual
Extractors (Tesseract absent in CI -> OCR degrades to None). No network.
"""

from pathlib import Path

from app.discovery.context.builder import SearchContextBuilder
from app.discovery.context.exif import ExifExtractor
from app.discovery.context.ocr import TesseractOCREngine
from app.discovery.context.visual import HeuristicVisualAnalyzer
from app.discovery.fingerprinting import FingerprintService

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_face.jpg"


def test_context_built_from_real_image():
    assert FIXTURE.is_file()
    builder = SearchContextBuilder(
        exif_extractor=ExifExtractor(),
        ocr_engine=TesseractOCREngine(),
        visual_analyzer=HeuristicVisualAnalyzer(),
        fingerprint_service=FingerprintService(),
    )
    ctx = builder.build(FIXTURE)

    assert ctx.image_hash is not None
    assert len(ctx.image_hash.sha256) == 64
    assert len(ctx.image_hash.p_hash) == 16
    assert "fingerprint" in ctx.sources
    assert "visual" in ctx.sources
    assert isinstance(ctx.language, (str, type(None)))