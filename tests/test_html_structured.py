"""Tests for LLM HTML structured metadata extraction."""

from __future__ import annotations

from biblicus.graph.grobid_dedup import (
    grobid_blocked_surface_forms,
    is_grobid_extraction_metadata,
    should_suppress_ner_entity,
)
from biblicus.html_structured import (
    HTML_STRUCTURED_DEFAULT_MODEL,
    enrich_web_extraction_with_llm_structured,
    extract_html_structured_metadata,
    html_llm_structured_enabled,
)
from biblicus import html_structured as html_structured_module
from biblicus import html_structured_pipeline as pipeline_module
from biblicus import url_text as url_text_module


def test_html_llm_structured_three_turn_conversation_order():
    calls: list[list[dict[str, str]]] = []

    def fake_resolver(*, model: str, messages: list[dict[str, str]]) -> dict:
        calls.append(list(messages))
        turn = len(calls)
        if turn == 1:
            return {"authors": [{"name": "Jane Doe", "normalized_name": "doe jane"}]}
        if turn == 2:
            return {"publication_date": "2024-06-15", "raw": "June 15, 2024"}
        return {
            "citations": [
                {
                    "title": "Prior Work on Transformers",
                    "authors": ["Alan Turing"],
                    "year": 2017,
                    "doi": "10.1000/xyz",
                    "citing_context": "They introduced the core attention mechanism we build on.",
                }
            ]
        }

    structured, meta = extract_html_structured_metadata(
        article_content="<html><body><p>Article</p></body></html>",
        content_kind="html",
        source_uri="https://example.test/paper",
        completion_resolver=fake_resolver,
    )
    assert meta["model"] == HTML_STRUCTURED_DEFAULT_MODEL
    assert len(calls) == 3
    assert len(calls[1]) > len(calls[0])
    assert len(calls[2]) > len(calls[1])
    assert structured["authors"][0]["name"] == "Jane Doe"
    assert structured["publication_date"] == "2024-06-15"
    assert structured["citations"][0]["citing_context"].startswith("They introduced")
    assert meta["turns"] == 3


def test_enrich_web_extraction_attaches_llm_html_method(monkeypatch):
    monkeypatch.setattr(html_structured_module, "html_llm_structured_enabled", lambda: True)

    def fake_enrich(converted, **kwargs):
        return {
            **converted,
            "method": "llm-html",
            "structured": {
                "authors": [{"name": "Ada Lovelace", "normalized_name": "lovelace ada"}],
                "citations": [],
                "publication_date": "1843-01-01",
                "summary": {"authors_count": 1, "citations_count": 0, "citations_with_identifiers": 0},
                "warnings": [],
            },
        }

    monkeypatch.setattr(url_text_module, "enrich_web_extraction_structured", fake_enrich)
    monkeypatch.setattr(
        url_text_module,
        "_fetch_url_bytes",
        lambda **kwargs: {
            "ok": True,
            "body": b"# Title\n\nBody",
            "content_type": "text/markdown",
            "final_url": kwargs["uri"],
            "attempts": [],
            "error": None,
        },
    )
    monkeypatch.setattr(
        url_text_module,
        "_convert_bytes_with_markitdown",
        lambda **kwargs: {"text": "Body", "markdown": "# Title\n\nBody", "title": "Title"},
    )
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("direct should not run")),
    )

    result = url_text_module.extract_url_text(source_uri="https://example.test/article")
    assert result["status"] == "ok"
    assert result["method"] == "llm-html"
    assert result["structured"]["authors"][0]["name"] == "Ada Lovelace"


def test_is_grobid_extraction_metadata_llm_html():
    assert is_grobid_extraction_metadata({"method": "llm-html"}) is True


def test_blocked_surface_forms_include_publication_date():
    blocked = grobid_blocked_surface_forms(
        {
            "authors": [{"name": "Jane Doe"}],
            "citations": [],
            "publication_date": "2024-06-15",
            "publication_date_raw": "June 15, 2024",
        }
    )
    assert "2024 06 15" in blocked
    assert should_suppress_ner_entity(
        label="June 15, 2024",
        entity_type="DATE",
        blocked_forms=blocked,
    )
