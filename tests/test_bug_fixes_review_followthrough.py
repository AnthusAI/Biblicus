"""Regression tests for the review follow-through bug fixes."""

from __future__ import annotations

from biblicus.corpus import Corpus
from biblicus.html_heuristics import extract_html_heuristics
from biblicus.html_structured import _normalize_citations


def test_normalize_citations_ignores_authors_that_are_not_a_list():
    """Verify that a citation with non-list authors is kept with an empty author list."""
    rows, warnings = _normalize_citations([{"title": "Paper", "authors": 5}])
    assert rows[0]["authors"] == []
    assert warnings == []


def test_corpus_init_returns_corpus_with_loaded_config(tmp_path):
    """Verify that the corpus returned by init carries its configuration."""
    corpus = Corpus.init(tmp_path / "corpus")
    assert corpus.config is not None
    assert corpus.raw_dir.exists()


def test_json_ld_layer_is_listed_once():
    """Verify that the json_ld layer appears once in the heuristic layers."""
    html = (
        '<html><head><script type="application/ld+json">'
        '{"@type": "Article", "headline": "T", "author": {"name": "Ada Lovelace"},'
        ' "datePublished": "2024-01-02"}</script></head><body></body></html>'
    )
    document = extract_html_heuristics(html, source_uri="https://example.com/a")
    assert document.layers.count("json_ld") == 1
