"""Language detection + keyword extraction unit tests (roadmap Phases 12/15)."""

import pytest

from app.discovery.context.keywords import extract_keywords
from app.discovery.context.language import detect_language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Kochi Marine Drive coffee shop", "en"),
        ("\u4f60\u597d\u4e16\u754c\uff0chello", "zh"),  # 你好世界，hello
        ("\u041f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440", "ru"),  # Привет мир
        (None, None),
        ("", None),
        ("12345 !!!", None),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_keywords_exclude_stopwords_and_rank_by_frequency():
    texts = ["The quick brown fox", "quick fox jumps"]
    assert extract_keywords(texts)[:2] == ["fox", "quick"]


def test_keywords_respect_max_and_drop_numbers():
    texts = ["alpha beta 1234 beta"]
    assert extract_keywords(texts, max_keywords=1) == ["beta"]
    assert "1234" not in extract_keywords(texts, max_keywords=10)