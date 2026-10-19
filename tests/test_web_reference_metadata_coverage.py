"""Coverage tests for web reference metadata extraction helpers."""

from __future__ import annotations

import pytest

from biblicus import url_text, web_reference_metadata
from biblicus.html_heuristics import HtmlHeuristicDocument
from biblicus.web_reference_metadata import (
    LOCAL_HTML_SOURCE_URI,
    WEB_REFERENCE_METADATA_VERSION,
    _document_to_payload,
    _fetch_html,
    _subtitle_from_document,
    _subtitle_from_structured,
    extract_web_reference_metadata_from_html,
    extract_web_reference_metadata_from_url,
    extraction_metadata_from_web_payload,
    title_subtitle_resolution_from_web_metadata,
)

SIMPLE_ARTICLE_HTML = (
    "<html><head><title>Plain Article</title></head>"
    "<body><article><p>Body paragraph for the plain article.</p></article></body></html>"
)
UNTITLED_ARTICLE_HTML = "<html><body><p>Only a paragraph with no title at all.</p></body></html>"


def test_extraction_metadata_from_web_payload_omits_empty_optional_fields():
    """Verify that extraction metadata from web payload omits empty optional fields."""
    metadata = extraction_metadata_from_web_payload(
        {"method": "  ", "structured": "not a dict", "title": "", "authors": [], "layers": []}
    )
    assert metadata == {"method": "html-heuristics", "structured": {}}


def test_extraction_metadata_from_web_payload_ignores_non_list_authors_and_layers():
    """Verify that extraction metadata from web payload ignores non list authors and layers."""
    metadata = extraction_metadata_from_web_payload(
        {
            "authors": "Alex Example",
            "layers": "json_ld",
            "publicationDate": "2024-01-02",
        }
    )
    assert metadata == {
        "method": "html-heuristics",
        "structured": {},
        "publicationDate": "2024-01-02",
    }


def test_extract_web_reference_metadata_from_html_returns_empty_payload_for_blank_html():
    """Verify that extract web reference metadata from html returns empty payload for blank html."""
    payload = extract_web_reference_metadata_from_html("   ")
    assert payload["method"] == "empty_html"
    assert payload["sourceUri"] == LOCAL_HTML_SOURCE_URI
    assert payload["schemaVersion"] == WEB_REFERENCE_METADATA_VERSION
    assert payload["warnings"] == []
    assert payload["structured"] == {"authors": [], "citations": [], "warnings": []}


def test_extract_web_reference_metadata_from_html_reports_disabled_heuristics(monkeypatch):
    """Verify that extract web reference metadata from html reports disabled heuristics."""
    monkeypatch.setattr(web_reference_metadata, "html_heuristics_enabled", lambda: False)
    payload = extract_web_reference_metadata_from_html(
        SIMPLE_ARTICLE_HTML, source_uri="https://fixture.test/a"
    )
    assert payload["method"] == "html_heuristics_disabled"
    assert payload["sourceUri"] == "https://fixture.test/a"
    assert payload["warnings"][0]["code"] == "html_heuristics_disabled"
    assert payload["structured"]["warnings"][0]["code"] == "html_heuristics_disabled"


def test_extract_web_reference_metadata_from_html_reports_unavailable_heuristics(monkeypatch):
    """Verify that extract web reference metadata from html reports unavailable heuristics."""

    def raise_missing_parser(_html, *, source_uri):
        raise ValueError(f"BeautifulSoup is not installed for {source_uri}")

    monkeypatch.setattr(web_reference_metadata, "extract_html_heuristics", raise_missing_parser)
    payload = extract_web_reference_metadata_from_html(
        SIMPLE_ARTICLE_HTML, source_uri="https://fixture.test/b"
    )
    assert payload["method"] == "html_heuristics_unavailable"
    assert payload["warnings"] == [
        {
            "code": "html_heuristics_unavailable",
            "message": "BeautifulSoup is not installed for https://fixture.test/b",
        }
    ]


def test_extract_web_reference_metadata_from_html_uses_llm_structured_enrichment(monkeypatch):
    """Verify that extract web reference metadata from html uses llm structured enrichment."""
    enrichment_calls = []

    def fake_enrichment(extraction, **keyword_arguments):
        enrichment_calls.append((extraction, keyword_arguments))
        return {
            "method": "llm-structured",
            "title": "  LLM Resolved Title  ",
            "structured": {
                "citations": [{"title": "Cited Paper"}],
                "raw_metadata": {"heuristic": {"open_graph": {"og:description": "LLM subtitle"}}},
            },
        }

    monkeypatch.setattr(web_reference_metadata, "enrich_web_extraction_structured", fake_enrichment)
    payload = extract_web_reference_metadata_from_html(
        UNTITLED_ARTICLE_HTML,
        source_uri="https://fixture.test/c",
        reference_title="Hint Title",
        use_llm_fallback=True,
        model="test-model",
        completion_resolver="resolver-sentinel",
    )
    assert payload["title"] == "LLM Resolved Title"
    assert payload["subtitle"] == "LLM subtitle"
    assert payload["method"] == "llm-structured"
    assert payload["citationCount"] == 1
    extraction, keyword_arguments = enrichment_calls[0]
    assert extraction["title"] is None
    assert keyword_arguments["source_uri"] == "https://fixture.test/c"
    assert keyword_arguments["html_content"] == UNTITLED_ARTICLE_HTML
    assert keyword_arguments["reference_title"] == "Hint Title"
    assert keyword_arguments["model"] == "test-model"
    assert keyword_arguments["completion_resolver"] == "resolver-sentinel"


def test_extract_web_reference_metadata_from_html_keeps_heuristics_when_llm_returns_nothing(
    monkeypatch,
):
    """Verify that extract web reference metadata from html keeps heuristics when llm returns nothing."""
    monkeypatch.setattr(
        web_reference_metadata,
        "enrich_web_extraction_structured",
        lambda _extraction, **_keyword_arguments: {"structured": None, "title": "   "},
    )
    payload = extract_web_reference_metadata_from_html(
        UNTITLED_ARTICLE_HTML, source_uri="https://fixture.test/d", use_llm_fallback=True
    )
    assert payload["method"] == "html-heuristics"
    assert not payload["title"]
    assert payload["subtitle"] is None


def test_extract_web_reference_metadata_from_html_llm_uses_default_method_and_keeps_titles(
    monkeypatch,
):
    """Verify that extract web reference metadata from html llm uses default method and keeps titles."""
    html_with_title_and_description = (
        "<html><head><title>Titled Page</title>"
        '<meta property="og:title" content="Titled Page">'
        '<meta property="og:description" content="Heuristic subtitle"></head>'
        "<body><p>Body.</p></body></html>"
    )
    monkeypatch.setattr(
        web_reference_metadata,
        "enrich_web_extraction_structured",
        lambda _extraction, **_keyword_arguments: {
            "title": "Ignored LLM Title",
            "structured": {"citations": []},
        },
    )
    payload = extract_web_reference_metadata_from_html(
        html_with_title_and_description,
        source_uri="https://fixture.test/e",
        use_llm_fallback=True,
    )
    assert payload["title"] == "Titled Page"
    assert payload["subtitle"] == "Heuristic subtitle"
    assert payload["method"] == "html-heuristics"
    assert payload["structured"] == {"citations": []}


def test_extract_web_reference_metadata_from_url_rejects_non_http_uri():
    """Verify that extract web reference metadata from url rejects non http uri."""
    payload = extract_web_reference_metadata_from_url(" ftp://fixture.test/file ")
    assert payload["method"] == "unsupported_uri"
    assert payload["sourceUri"] == "ftp://fixture.test/file"
    assert payload["warnings"][0]["code"] == "unsupported_uri"


def test_extract_web_reference_metadata_from_url_merges_fetch_warnings(monkeypatch):
    """Verify that extract web reference metadata from url merges fetch warnings."""
    fetch_calls = []

    def fake_fetch_html(source_uri, *, timeout_seconds):
        fetch_calls.append((source_uri, timeout_seconds))
        return SIMPLE_ARTICLE_HTML, [{"code": "http_error", "message": "first fetch failed"}]

    monkeypatch.setattr(web_reference_metadata, "_fetch_html", fake_fetch_html)
    payload = extract_web_reference_metadata_from_url(
        "HTTPS://fixture.test/article", timeout_seconds=3.5
    )
    assert fetch_calls == [("HTTPS://fixture.test/article", 3.5)]
    assert payload["title"] == "Plain Article"
    assert payload["warnings"][-1] == {"code": "http_error", "message": "first fetch failed"}


def test_extract_web_reference_metadata_from_url_reports_empty_fetch(monkeypatch):
    """Verify that extract web reference metadata from url reports empty fetch."""
    monkeypatch.setattr(
        web_reference_metadata,
        "_fetch_html",
        lambda _uri, *, timeout_seconds: ("", [{"code": "empty_html_body", "message": "none"}]),
    )
    payload = extract_web_reference_metadata_from_url("http://fixture.test/empty")
    assert payload["method"] == "empty_html"
    assert payload["warnings"] == [{"code": "empty_html_body", "message": "none"}]


def test_title_subtitle_resolution_returns_empty_mapping_without_title():
    """Verify that title subtitle resolution returns empty mapping without title."""
    assert title_subtitle_resolution_from_web_metadata({"title": "  ", "subtitle": "x"}) == {}


def test_title_subtitle_resolution_without_layers_subtitle_or_source():
    """Verify that title subtitle resolution without layers subtitle or source."""
    resolution = title_subtitle_resolution_from_web_metadata(
        {"title": "Only Title", "layers": "not-a-list"}
    )
    assert resolution == {
        "title": "Only Title",
        "subtitle": "",
        "titleMode": "original_web_metadata",
        "subtitleMode": "unresolved",
        "source": "html_heuristics",
        "sourceUrls": [],
        "rationale": "Resolved from structured HTML metadata (html_heuristics).",
    }


def test_title_subtitle_resolution_with_subtitle_layers_and_source():
    """Verify that title subtitle resolution with subtitle layers and source."""
    resolution = title_subtitle_resolution_from_web_metadata(
        {
            "title": "Full Title",
            "subtitle": "Full Subtitle",
            "sourceUri": "https://fixture.test/f",
            "method": "llm-structured",
            "layers": ["json_ld", "open_graph", "twitter_card", "meta", "dom"],
        }
    )
    assert resolution["subtitleMode"] == "original_web_metadata"
    assert resolution["source"] == "llm-structured"
    assert resolution["sourceUrls"] == ["https://fixture.test/f"]
    assert resolution["rationale"] == (
        "Resolved from structured HTML metadata (json_ld, open_graph, twitter_card, meta)."
    )


def test_document_to_payload_skips_non_dict_and_nameless_authors_and_non_dict_structured():
    """Verify that document to payload skips non dict and nameless authors and non dict structured."""
    heuristic_document = HtmlHeuristicDocument(source_uri="https://fixture.test/g")
    heuristic_document.authors = [{"name": " Named Author "}, {"name": ""}, "not-a-dict"]
    payload = _document_to_payload(
        heuristic_document, structured="not-a-dict", method="html-heuristics", subtitle=""
    )
    assert payload["authors"] == ["Named Author"]
    assert payload["citationCount"] == 0
    assert payload["subtitle"] is None


@pytest.mark.parametrize(
    ("raw_metadata", "title", "expected_subtitle"),
    [
        ("not-a-dict", "Title", ""),
        ({"open_graph": "not-a-dict", "twitter_card": "not-a-dict"}, "Title", ""),
        ({"open_graph": {"og:description": "Title", "description": "Meta"}}, "Title", "Meta"),
        ({"open_graph": {"og:description": "Same"}}, "Same", ""),
        ({"twitter_card": {"twitter:description": "Twitter text"}}, None, "Twitter text"),
        ({"twitter_card": {"twitter:description": "Title"}}, "Title", ""),
    ],
)
def test_subtitle_from_document_prefers_distinct_descriptions(
    raw_metadata, title, expected_subtitle
):
    """Verify that subtitle from document prefers distinct descriptions."""
    heuristic_document = HtmlHeuristicDocument(source_uri="https://fixture.test/h")
    heuristic_document.title = title
    heuristic_document.raw_metadata = raw_metadata
    assert _subtitle_from_document(heuristic_document) == expected_subtitle


@pytest.mark.parametrize(
    ("structured", "expected_subtitle"),
    [
        ("not-a-dict", ""),
        ({}, ""),
        ({"raw_metadata": "not-a-dict"}, ""),
        ({"raw_metadata": {"open_graph": {"og:description": " Direct "}}}, "Direct"),
        (
            {"raw_metadata": {"heuristic": {"open_graph": {"og:description": "Nested"}}}},
            "Nested",
        ),
        ({"raw_metadata": {"heuristic": {"open_graph": "not-a-dict"}}}, ""),
    ],
)
def test_subtitle_from_structured_reads_open_graph_description(structured, expected_subtitle):
    """Verify that subtitle from structured reads open graph description."""
    assert _subtitle_from_structured(structured) == expected_subtitle


def _install_fake_url_fetches(monkeypatch, fetch_results_by_step, html_bodies_by_step):
    recorded_fetch_requests = []

    def fake_fetch_url_bytes(**keyword_arguments):
        recorded_fetch_requests.append(keyword_arguments)
        result = dict(fetch_results_by_step[keyword_arguments["step"]])
        result["step"] = keyword_arguments["step"]
        return result

    def fake_html_body_from_fetch(fetch_result):
        return html_bodies_by_step[fetch_result["step"]]

    monkeypatch.setattr(url_text, "_fetch_url_bytes", fake_fetch_url_bytes)
    monkeypatch.setattr(url_text, "_html_body_from_fetch", fake_html_body_from_fetch)
    return recorded_fetch_requests


def test_fetch_html_returns_first_successful_html_body(monkeypatch):
    """Verify that fetch html returns first successful html body."""
    recorded_fetch_requests = _install_fake_url_fetches(
        monkeypatch,
        {"web_html_fetch": {"ok": True}},
        {"web_html_fetch": SIMPLE_ARTICLE_HTML},
    )
    html, warnings = _fetch_html("https://fixture.test/i", timeout_seconds=4.0)
    assert html == SIMPLE_ARTICLE_HTML
    assert warnings == []
    assert len(recorded_fetch_requests) == 1
    assert recorded_fetch_requests[0]["uri"] == "https://fixture.test/i"
    assert recorded_fetch_requests[0]["timeout_seconds"] == 4.0
    assert recorded_fetch_requests[0]["max_retries"] == url_text.URL_TEXT_DEFAULT_MAX_RETRIES


def test_fetch_html_falls_back_to_markdown_step_after_failed_html_fetch(monkeypatch):
    """Verify that fetch html falls back to markdown step after failed html fetch."""
    _install_fake_url_fetches(
        monkeypatch,
        {
            "web_html_fetch": {"ok": False, "error": {"code": "http_404", "message": "missing"}},
            "web_markdown_fetch": {"ok": True},
        },
        {"web_markdown_fetch": SIMPLE_ARTICLE_HTML},
    )
    html, warnings = _fetch_html("https://fixture.test/j", timeout_seconds=1.0)
    assert html == SIMPLE_ARTICLE_HTML
    assert warnings == [{"code": "http_404", "message": "missing"}]


def test_fetch_html_reports_default_failure_and_empty_body_warnings(monkeypatch):
    """Verify that fetch html reports default failure and empty body warnings."""
    _install_fake_url_fetches(
        monkeypatch,
        {
            "web_html_fetch": {"ok": False, "error": "not-a-dict"},
            "web_markdown_fetch": {"ok": True},
        },
        {"web_markdown_fetch": "   "},
    )
    html, warnings = _fetch_html("https://fixture.test/k", timeout_seconds=1.0)
    assert html == ""
    assert warnings == [
        {"code": "fetch_failed", "message": "Fetch failed during web_html_fetch."},
        {
            "code": "empty_html_body",
            "message": "No HTML body returned during web_markdown_fetch.",
        },
    ]


def test_extraction_metadata_from_web_payload_copies_populated_optional_fields():
    """Verify that extraction metadata from web payload copies populated optional fields."""
    metadata = extraction_metadata_from_web_payload(
        {
            "method": "llm-structured",
            "structured": {"citations": []},
            "title": " Populated ",
            "authors": ["Alex Example"],
            "layers": ["json_ld"],
        }
    )
    assert metadata == {
        "method": "llm-structured",
        "structured": {"citations": []},
        "title": "Populated",
        "authors": ["Alex Example"],
        "htmlHeuristicLayers": ["json_ld"],
    }
