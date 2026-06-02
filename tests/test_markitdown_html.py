"""Tests that MarkItDown runs on HTML corpus items (not skipped as generic text/*)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from biblicus.extractors import markitdown_text as md_mod
from biblicus.extractors.markitdown_text import MarkItDownExtractor

_FIXTURE = Path(__file__).parent / "fixtures" / "html_heuristics" / "synthetic_blog_json_ld.html"


def test_text_html_is_not_in_markitdown_skip_list():
    assert "text/html" not in md_mod._MARKITDOWN_SKIP_MEDIA_TYPES
    media_type = "text/html"
    assert not (
        media_type.startswith("text/")
        and media_type not in {"text/html", "application/xhtml+xml"}
    )


def test_text_plain_is_skipped_by_markitdown(tmp_path):
    plain_path = tmp_path / "note.txt"
    plain_path.write_text("hello", encoding="utf-8")
    extractor = MarkItDownExtractor()
    result = extractor.extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=SimpleNamespace(relpath="note.txt", media_type="text/plain"),
        config={},
        previous_extractions=[],
    )
    assert result is None


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("markitdown"),
    reason="markitdown optional dependency not installed",
)
def test_markitdown_converts_text_html_file(tmp_path, monkeypatch):
    html_path = tmp_path / "page.html"
    html_path.write_text(_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    mock_converter = MagicMock()
    mock_converter.convert.return_value = SimpleNamespace(text_content="# Converted markdown")
    monkeypatch.setattr("markitdown.MarkItDown", lambda **kwargs: mock_converter)

    extractor = MarkItDownExtractor()
    result = extractor.extract_text(
        corpus=SimpleNamespace(root=tmp_path),
        item=SimpleNamespace(relpath="page.html", media_type="text/html"),
        config={},
        previous_extractions=[],
    )
    assert result is not None
    assert "Converted" in result.text
    mock_converter.convert.assert_called_once()
