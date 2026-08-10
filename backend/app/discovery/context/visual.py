"""Visual context analysis (roadmap Phase 14).

Local, offline visual hints: brightness, saturation, dominant colors, and
placeholder lists for landmarks/buildings/venues/objects/scene type. All
predictions are *search hints, not verified facts* — no model claims a
landmark without evidence. A model-backed analyzer can be swapped in behind
the same protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class VisualHint:
    """One soft visual prediction (never asserted as verified fact)."""

    category: str  # scene_type | landmark | building | venue | object | signage
    label: str
    confidence: float = 0.0


@dataclass
class VisualContext:
    """Local visual hints for one image."""

    scene_type: str | None = None
    objects: list[str] = field(default_factory=list)
    landmarks: list[str] = field(default_factory=list)
    buildings: list[str] = field(default_factory=list)
    venues: list[str] = field(default_factory=list)
    signage: list[str] = field(default_factory=list)
    hints: list[VisualHint] = field(default_factory=list)
    brightness: float = 0.0
    saturation: float = 0.0
    dominant_colors: list[str] = field(default_factory=list)


_COLOR_NAMES = [
    ("black", (0, 0, 0)),
    ("white", (255, 255, 255)),
    ("gray", (128, 128, 128)),
    ("red", (255, 0, 0)),
    ("green", (0, 128, 0)),
    ("blue", (0, 0, 255)),
    ("yellow", (255, 255, 0)),
    ("cyan", (0, 255, 255)),
    ("magenta", (255, 0, 255)),
    ("orange", (255, 165, 0)),
]


def _closest_color_name(rgb: tuple[int, int, int]) -> str:
    return min(
        _COLOR_NAMES,
        key=lambda name_rgb: sum((int(a) - int(b)) ** 2 for a, b in zip(rgb, name_rgb[1])),
    )[0]


class VisualContextAnalyzer(ABC):
    """Protocol for local visual-context analyzers."""

    @abstractmethod
    def analyze(self, image_path: Path | str) -> VisualContext:
        """Produce soft visual hints for an image."""


class HeuristicVisualAnalyzer(VisualContextAnalyzer):
    """Offline heuristic hints (dominant colors, brightness, saturation).

    Does not identify landmarks/buildings/objects without a detector; those
    lists stay empty so downstream code never treats absence as a fact.
    """

    def analyze(self, image_path: Path | str) -> VisualContext:
        try:
            with Image.open(image_path) as image:
                small = image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
        except (OSError, ValueError):
            return VisualContext()

        arr = np.asarray(small, dtype=np.float64)
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        brightness = round(float(luma.mean()) / 255.0, 4)
        denom = np.maximum(arr.max(axis=2), 1.0)
        saturation = round(float(((arr.max(axis=2) - arr.min(axis=2)) / denom).mean()), 4)

        quantized = (arr // 64).astype(np.uint8) * 64 + 32
        counts = {}
        for pixel in quantized.reshape(-1, 3):
            name = _closest_color_name(tuple(pixel))
            counts[name] = counts.get(name, 0) + 1
        top_colors = [name for name, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)][:3]

        return VisualContext(
            brightness=brightness,
            saturation=saturation,
            dominant_colors=top_colors,
            hints=[
                VisualHint(category="scene_type", label="unknown", confidence=0.0),
                VisualHint(category="scene_type", label="brightness", confidence=brightness),
            ],
        )