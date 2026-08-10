"""Visual context analysis unit tests (roadmap Phase 14)."""

from pathlib import Path

import pytest

from app.discovery.context.visual import HeuristicVisualAnalyzer, VisualContextAnalyzer


def _solid(path: Path, rgb: tuple[int, int, int]) -> None:
    from PIL import Image

    Image.new("RGB", (64, 64), rgb).save(path)


def test_analyzer_protocol_uninstantiable():
    with pytest.raises(TypeError):
        VisualContextAnalyzer()


def test_dominant_color_red(tmp_path: Path):
    path = tmp_path / "red.png"
    _solid(path, (255, 0, 0))
    ctx = HeuristicVisualAnalyzer().analyze(path)
    assert "red" in ctx.dominant_colors
    assert 0.0 < ctx.brightness < 1.0


def test_white_brightness_high(tmp_path: Path):
    path = tmp_path / "white.png"
    _solid(path, (255, 255, 255))
    ctx = HeuristicVisualAnalyzer().analyze(path)
    assert ctx.brightness == pytest.approx(1.0, abs=0.02)
    assert "white" in ctx.dominant_colors


def test_missing_file_returns_empty():
    ctx = HeuristicVisualAnalyzer().analyze(Path("does-not-exist.png"))
    assert ctx.dominant_colors == []
    assert ctx.scene_type is None


def test_deterministic():
    assert HeuristicVisualAnalyzer().analyze(Path("nope.png")) == HeuristicVisualAnalyzer().analyze(
        Path("nope.png")
    )