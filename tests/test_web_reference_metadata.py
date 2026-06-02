"""Tests for shared web reference metadata extraction."""

from __future__ import annotations

from pathlib import Path

from biblicus.web_reference_metadata import (
    extract_web_reference_metadata_from_html,
    extraction_metadata_from_web_payload,
    title_subtitle_resolution_from_web_metadata,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "html_heuristics"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_extraction_metadata_from_web_payload_fixture():
    payload = extract_web_reference_metadata_from_html(
        _read("synthetic_blog_json_ld.html"),
        source_uri="https://fixture.test/blog/post",
    )
    metadata = extraction_metadata_from_web_payload(payload)
    assert metadata["method"] == "html-heuristics"
    assert metadata["structured"].get("authors")


def test_web_metadata_from_json_ld_fixture():
    payload = extract_web_reference_metadata_from_html(
        _read("synthetic_blog_json_ld.html"),
        source_uri="https://fixture.test/blog/post",
    )
    assert payload["title"] == "Understanding Sequence Models"
    assert "json_ld" in payload["layers"]
    assert len(payload["authors"]) >= 2
    assert payload["citationCount"] >= 2
    resolution = title_subtitle_resolution_from_web_metadata(payload)
    assert resolution["title"] == payload["title"]
    assert resolution["titleMode"] == "original_web_metadata"


def test_web_metadata_from_open_graph_fixture():
    payload = extract_web_reference_metadata_from_html(
        _read("synthetic_news_open_graph.html"),
        source_uri="https://fixture.test/news/story",
    )
    assert payload["title"] == "Corpus Audit Checklist"
    assert payload["publicationDate"] == "2024-11-02"
    assert any(name == "Casey Reviewer" for name in payload["authors"])
