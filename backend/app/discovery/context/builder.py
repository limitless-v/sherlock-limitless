"""Search context builder (roadmap Phase 15).

Combines EXIF, OCR, visual context, and image fingerprints (plus optional
user filters) into a single `SearchContext`. The user can still provide
only an image — every subsystem degrades gracefully.
"""

from __future__ import annotations

from pathlib import Path

from app.discovery.context.exif import ExifExtractor
from app.discovery.context.keywords import extract_keywords
from app.discovery.context.language import detect_language
from app.discovery.context.models import SearchContext
from app.discovery.context.ocr import OCREngine
from app.discovery.context.visual import VisualContext, VisualContextAnalyzer
from app.discovery.fingerprinting import FingerprintService


class SearchContextBuilder:
    """Assemble non-sensitive search context from one uploaded image."""

    def __init__(
        self,
        exif_extractor: ExifExtractor | None = None,
        ocr_engine: OCREngine | None = None,
        visual_analyzer: VisualContextAnalyzer | None = None,
        fingerprint_service: FingerprintService | None = None,
        max_keywords: int = 20,
    ) -> None:
        self._extractor = exif_extractor or ExifExtractor()
        self._ocr = ocr_engine
        self._visual = visual_analyzer
        self._fingerprints = fingerprint_service or FingerprintService()
        self._max_keywords = max_keywords

    def build(
        self,
        image_path: Path | str,
        user_filters: dict | None = None,
    ) -> SearchContext:
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"image not found: {path}")

        sources: set[str] = set()
        image_hash = self._fingerprints.fingerprint(path)
        sources.add("fingerprint")

        exif = self._extractor.extract(path)
        if not exif.is_empty():
            sources.add("exif")

        ocr = None
        if self._ocr is not None and self._ocr.available:
            ocr = self._ocr.extract(path)
            sources.add("ocr")

        visual = self._visual.analyze(path) if self._visual is not None else VisualContext()
        if visual.dominant_colors or visual.scene_type:
            sources.add("visual")

        text_lines = list(ocr.lines) if ocr else []
        urls, usernames, hashtags = [], [], []
        if ocr:
            urls, usernames, hashtags = ocr.urls, ocr.usernames, ocr.hashtags

        filters = dict(user_filters) if user_filters else {}
        if filters:
            sources.add("user_filters")

        return SearchContext(
            keywords=extract_keywords(text_lines, max_keywords=self._max_keywords),
            text=text_lines,
            urls=urls,
            usernames=usernames,
            hashtags=hashtags,
            location=exif.public_location(),
            timestamp=exif.taken_at,
            language=detect_language("\n".join(text_lines)),
            image_hash=image_hash,
            user_filters=filters,
            sources=sources,
        )