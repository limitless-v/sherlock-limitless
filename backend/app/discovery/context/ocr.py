"""Local OCR (roadmap Phase 12).

Engine-agnostic extraction: an `OCREngine` protocol (Tesseract provider
included, lazily imported) plus engine-independent structured post
processing that pulls URLs, usernames, and hashtags out of recognized text.
OCR is optional — an unavailable engine surfaces as `OCRUnavailableError`
at call time and an empty context upstream.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


class OCRUnavailableError(RuntimeError):
    """Raised when no OCR engine is installed/configured."""


class OCRError(RuntimeError):
    """Raised when the OCR engine fails."""


@dataclass
class OCRTextBlock:
    text: str
    confidence: float = 0.0
    bbox: tuple[int, int, int, int] | None = None


@dataclass
class OCRExtraction:
    """Structured OCR output for one image."""

    engine_name: str
    text: str
    blocks: list[OCRTextBlock] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    usernames: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)

    @property
    def lines(self) -> list[str]:
        return [line for line in self.text.splitlines() if line.strip()]


class OCREngine(ABC):
    """Protocol for OCR engines."""

    engine_name: str = "ocr"

    @property
    @abstractmethod
    def available(self) -> bool:
        """True when the underlying engine can be invoked right now."""

    @abstractmethod
    def extract(self, image_path: Path | str) -> OCRExtraction:
        """Run OCR on an image file and return structured output."""


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def extract_structured(text: str) -> tuple[list[str], list[str], list[str]]:
    """Engine-agnostic extraction of URLs, usernames, and hashtags."""
    urls = []
    for raw in re.findall(r"https?://[^\s<>\"']+", text):
        clean = raw.rstrip(".,;:!?)]}>\"'")
        if clean and clean not in urls:
            urls.append(clean)
    usernames = _dedupe(re.findall(r"(?<![\w@])@([A-Za-z0-9_.]{2,30})\b", text))
    hashtags = _dedupe(re.findall(r"(?<![\w#])#([\w]{1,50})\b", text))
    return urls, usernames, hashtags


class TesseractOCREngine(OCREngine):
    """Tesseract-backed OCR provider (pytesseract lazy-imported).

    Adds no hard dependency: `pytesseract` must be installed and the
    Tesseract binary reachable before `extract` can run.
    """

    engine_name = "tesseract"

    def __init__(self, languages=("eng",), tesseract_cmd: str | None = None) -> None:
        self._languages = tuple(languages) or ("eng",)
        self._tesseract_cmd = tesseract_cmd

    @property
    def available(self) -> bool:
        try:
            import pytesseract  # noqa: F401

            if self._tesseract_cmd:
                import pytesseract as pt

                pt.pytesseract.tesseract_cmd = self._tesseract_cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract(self, image_path: Path | str) -> OCRExtraction:
        if not self.available:
            raise OCRUnavailableError("Tesseract OCR is not available (install pytesseract + tesseract binary).")
        try:
            import pytesseract
            from pytesseract import Output
        except ImportError as exc:  # pragma: no cover - guarded by available
            raise OCRUnavailableError(str(exc)) from exc

        lang = "+".join(self._languages)
        try:
            data = pytesseract.image_to_data(str(image_path), output_type=Output.DICT, lang=lang)
            full = pytesseract.image_to_string(str(image_path), lang=lang)
        except Exception as exc:
            raise OCRError(f"Tesseract failure: {exc}") from exc

        blocks: list[OCRTextBlock] = []
        grouped: dict[int, list[int]] = {}
        for idx, block_num in enumerate(data.get("block_num", [])):
            grouped.setdefault(int(block_num), []).append(idx)
        for indices in grouped.values():
            words = " ".join(
                data["text"][i] for i in indices if str(data["text"][i]).strip()
            ).strip()
            if not words:
                continue
            confs = [
                float(data["conf"][i])
                for i in indices
                if i < len(data["conf"]) and str(data["conf"][i]).strip() not in {"", "-1"}
            ]
            left, top = data["left"][indices[0]], data["top"][indices[0]]
            width = data["left"][indices[-1]] + data["width"][indices[-1]] - left
            height = max(data["top"][i] + data["height"][i] for i in indices) - top
            blocks.append(
                OCRTextBlock(
                    text=words,
                    confidence=round(sum(confs) / len(confs), 2) if confs else 0.0,
                    bbox=(int(left), int(top), int(width), int(height)),
                )
            )

        urls, usernames, hashtags = extract_structured(full)
        return OCRExtraction(
            engine_name=self.engine_name,
            text=full.strip(),
            blocks=blocks,
            urls=urls,
            usernames=usernames,
            hashtags=hashtags,
            languages=list(self._languages),
        )