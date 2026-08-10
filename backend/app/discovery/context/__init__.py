"""Search context subpackage (roadmap Phases 11-15)."""

from app.discovery.context.builder import SearchContextBuilder
from app.discovery.context.exif import ExifExtractor, ExifMetadata, GpsInfo
from app.discovery.context.keywords import extract_keywords
from app.discovery.context.language import detect_language
from app.discovery.context.models import SearchContext
from app.discovery.context.ocr import (
    OCREngine,
    OCRError,
    OCRExtraction,
    OCRTextBlock,
    OCRUnavailableError,
    TesseractOCREngine,
    extract_structured,
)
from app.discovery.context.visual import HeuristicVisualAnalyzer, VisualContext, VisualContextAnalyzer

__all__ = [
    "ExifExtractor",
    "ExifMetadata",
    "GpsInfo",
    "HeuristicVisualAnalyzer",
    "OCREngine",
    "OCRError",
    "OCRExtraction",
    "OCRTextBlock",
    "OCRUnavailableError",
    "SearchContext",
    "SearchContextBuilder",
    "TesseractOCREngine",
    "VisualContext",
    "VisualContextAnalyzer",
    "detect_language",
    "extract_keywords",
    "extract_structured",
]