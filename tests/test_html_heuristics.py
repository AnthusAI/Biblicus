"""Unit tests for HTML heuristic extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from biblicus.html_heuristics import (
    extract_html_heuristics,
    heuristic_document_to_structured,
    structured_metadata_is_sufficient,
)
from biblicus.html_structured_pipeline import enrich_web_extraction_structured

_FIXTURES = Path(__file__).parent / "fixtures" / "html_heuristics"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_json_ld_blog_fixture_authors_and_references():
    doc = extract_html_heuristics(_read("synthetic_blog_json_ld.html"))
    structured = heuristic_document_to_structured(doc)
    assert doc.title == "Understanding Sequence Models"
    assert len(doc.authors) >= 2
    assert doc.publication_date == "2021-03-15"
    assert len(structured["citations"]) >= 2
    assert structured_metadata_is_sufficient(structured)


def test_open_graph_news_fixture():
    doc = extract_html_heuristics(_read("synthetic_news_open_graph.html"))
    assert doc.title == "Corpus Audit Checklist"
    assert doc.publication_date == "2024-11-02"
    assert any(author["name"] == "Casey Reviewer" for author in doc.authors)


def test_footer_links_require_external_hosts():
    doc = extract_html_heuristics(
        _read("synthetic_footer_links.html"),
        source_uri="https://fixture.test/articles/footer",
    )
    urls = {row.get("url") for row in doc.citations}
    assert "https://example.test/external/paper-a" in urls
    assert all("/internal/" not in (url or "") for url in urls)


def test_pipeline_skips_llm_when_heuristics_sufficient(monkeypatch):
    monkeypatch.setenv("BIBLICUS_HTML_LLM_STRUCTURED", "0")
    enriched = enrich_web_extraction_structured(
        {"text": "body", "markdown": "body"},
        source_uri="https://fixture.test/blog",
        html_content=_read("synthetic_blog_json_ld.html"),
    )
    assert enriched["method"] == "html-heuristics"
    assert len(enriched["structured"]["authors"]) >= 2


def test_pipeline_llm_fallback_when_sparse(monkeypatch):
    monkeypatch.setenv("BIBLICUS_HTML_LLM_STRUCTURED", "1")

    def resolver(*, model: str, messages: list[dict[str, str]]) -> dict:
        turn = sum(1 for row in messages if row.get("role") == "assistant")
        if turn == 0:
            return {"authors": [{"name": "Fallback Author", "normalized_name": "author fallback"}]}
        if turn == 1:
            return {"publication_date": None, "raw": None}
        return {"citations": [{"title": "Fallback Citation", "authors": ["A. Reader"], "year": 2021}]}

    enriched = enrich_web_extraction_structured(
        {"text": "body"},
        source_uri="https://fixture.test/sparse",
        html_content=_read("synthetic_sparse.html"),
        completion_resolver=resolver,
    )
    assert enriched["method"] == "llm-html"
    assert enriched["structured"]["authors"][0]["name"] == "Fallback Author"
