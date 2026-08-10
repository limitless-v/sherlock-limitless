"""OCR unit tests (roadmap Phase 12)."""

from pathlib import Path

import pytest

from app.discovery.context.ocr import (
    OCREngine,
    TesseractOCREngine,
    extract_structured,
    OCRUnavailableError,
)


def test_extract_structured_pulls_urls_usernames_hashtags():
    sample = (
        "Read more at https://example.com/a?b=1, plus https://x.io/abc. "
        "Follow @alice_doe and @bob. Tag it #kochi #MarineDrive."
    )
    urls, usernames, hashtags = extract_structured(sample)
    assert urls == ["https://example.com/a?b=1", "https://x.io/abc"]
    assert usernames == ["alice_doe", "bob"]
    assert hashtags == ["kochi", "MarineDrive"]


def test_extract_structured_deduplicates():
    _, usernames, hashtags = extract_structured("@alice @alice #kochi #kochi")
    assert usernames == ["alice"]
    assert hashtags == ["kochi"]


def test_engine_protocol_uninstantiable():
    with pytest.raises(TypeError):
        OCREngine()  # abstract


def test_tesseract_missing_raises_clean_unavailable():
    engine = TesseractOCREngine()
    if engine.available:
        pytest.skip("Tesseract is installed in this environment")
    with pytest.raises(OCRUnavailableError):
        engine.extract(Path("unused.png"))