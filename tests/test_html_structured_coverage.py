"""Coverage-focused tests for LLM HTML structured extraction and the structured pipeline."""

from __future__ import annotations

import sys
import types

import pytest

from biblicus import html_structured as html_structured_module
from biblicus import html_structured_pipeline as pipeline_module
from biblicus.html_heuristics import HtmlHeuristicDocument
from biblicus.html_structured import (
    HTML_STRUCTURED_ENABLE_ENV,
    HTML_STRUCTURED_MAX_ARTICLE_CHARS,
    enrich_web_extraction_with_llm_structured,
    extract_html_structured_metadata,
    html_llm_structured_enabled,
)
from biblicus.html_structured_pipeline import (
    HTML_HEURISTICS_ENABLE_ENV,
    enrich_web_extraction_structured,
    html_heuristics_enabled,
)

WEAK_REFERENCE_BODY = "<article><h2>References</h2><ol><li>Brief</li></ol></article>"


def _build_turn_resolver(authors_payload, date_payload, citations_payload, recorded_calls=None):
    payloads_by_turn = [authors_payload, date_payload, citations_payload]
    calls = recorded_calls if recorded_calls is not None else []

    def resolve_turn(*, model, messages):
        calls.append({"model": model, "messages": list(messages)})
        return payloads_by_turn[len(calls) - 1]

    return resolve_turn


def _empty_turn_resolver():
    return _build_turn_resolver({}, {}, {})


def _html_page(head_markup: str = "", body_markup: str = "") -> str:
    return f"<html><head>{head_markup}</head><body>{body_markup}</body></html>"


def test_html_llm_structured_enabled_respects_disable_values(monkeypatch):
    """Disable tokens turn LLM extraction off; anything else leaves it on."""
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, " Off ")
    assert html_llm_structured_enabled() is False
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "yes")
    assert html_llm_structured_enabled() is True
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV)
    assert html_llm_structured_enabled() is True


def test_html_heuristics_enabled_respects_disable_values(monkeypatch):
    """Disable tokens turn heuristics off; unset leaves them on."""
    monkeypatch.setenv(HTML_HEURISTICS_ENABLE_ENV, "false")
    assert html_heuristics_enabled() is False
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV)
    assert html_heuristics_enabled() is True


def test_enrich_llm_returns_converted_unchanged_when_disabled(monkeypatch):
    """A disabled LLM layer returns the conversion payload untouched."""
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "0")
    converted = {"text": "body"}
    assert enrich_web_extraction_with_llm_structured(converted, source_uri="u") is converted


def test_enrich_llm_returns_converted_when_no_article_content(monkeypatch):
    """No HTML, markdown, or text means there is nothing to send."""
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)
    converted = {"text": "   ", "markdown": ""}
    result = enrich_web_extraction_with_llm_structured(
        converted,
        source_uri="u",
        completion_resolver=_empty_turn_resolver(),
    )
    assert result is converted


def test_enrich_llm_uses_markdown_when_html_absent_and_returns_converted_on_empty_results(
    monkeypatch,
):
    """Markdown is used as article content, and empty LLM answers leave the payload unchanged."""
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)
    recorded_calls: list = []
    converted = {"markdown": "# Heading\n\nBody text", "title": "Heading"}
    result = enrich_web_extraction_with_llm_structured(
        converted,
        source_uri="https://example.test/a",
        completion_resolver=_build_turn_resolver({}, {}, {}, recorded_calls),
    )
    assert result is converted
    initial_prompt = recorded_calls[0]["messages"][1]["content"]
    assert "Content kind: markdown" in initial_prompt
    assert "Page title: Heading" in initial_prompt


def test_enrich_llm_attaches_structured_payload_from_text_fallback(monkeypatch):
    """Text content is used when markdown is missing and results are attached."""
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)
    result = enrich_web_extraction_with_llm_structured(
        {"text": "plain body"},
        source_uri="https://example.test/b",
        completion_resolver=_build_turn_resolver({}, {"publication_date": "2020"}, {}),
    )
    assert result["method"] == "llm-html"
    assert result["structured"]["publication_date"] == "2020-01-01"
    assert result["llm_structured"]["content_kind"] == "markdown"


def test_enrich_llm_records_warning_when_resolver_raises(monkeypatch):
    """Resolver failures become llm_structured_warnings, replacing a non-list value."""
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)

    def failing_resolver(*, model, messages):
        raise RuntimeError("resolver exploded")

    result = enrich_web_extraction_with_llm_structured(
        {"text": "body", "llm_structured_warnings": "not-a-list"},
        source_uri="u",
        html_content="<p>body</p>",
        completion_resolver=failing_resolver,
    )
    assert result["llm_structured_warnings"] == [
        {"code": "llm_structured_failed", "message": "resolver exploded"}
    ]


def test_extract_metadata_truncates_long_articles_and_warns():
    """Articles beyond the character budget are clipped and flagged."""
    recorded_calls: list = []
    long_article = "x" * (HTML_STRUCTURED_MAX_ARTICLE_CHARS + 10) + "\x00"
    structured, llm_meta = extract_html_structured_metadata(
        article_content=long_article,
        content_kind="html",
        source_uri="u",
        completion_resolver=_build_turn_resolver({}, {}, {}, recorded_calls),
    )
    assert llm_meta["article_chars_sent"] == HTML_STRUCTURED_MAX_ARTICLE_CHARS
    assert structured["warnings"][-1]["code"] == "article_truncated"
    initial_prompt = recorded_calls[0]["messages"][1]["content"]
    assert "Page title: (unknown)" in initial_prompt
    assert "Reference title hint: (none)" in initial_prompt


def test_extract_metadata_normalizes_authors_dates_and_citations():
    """Author, date, and citation payloads are normalized and deduplicated."""
    authors_payload = {
        "authors": [
            "  Grace   Hopper ",
            {"normalized_name": "grace hopper"},
            {"name": ""},
            42,
            {"name": "Plato"},
        ]
    }
    date_payload = {"publication_date": "", "raw": "2021/07"}
    citations_payload = {
        "citations": [
            "not-a-dict",
            {"title": "", "raw": ""},
            {
                "title": "Paper With Identifiers",
                "authors": ["Alan Turing", "  "],
                "year": "circa 1950",
                "doi": "https://doi.org/10.1000/xyz.",
                "arxivId": "arXiv:1234.5678",
                "isbn": "978-0",
                "venue": "Mind",
                "citingContext": "Used as foundation.",
            },
            {
                "raw": "Raw citation line",
                "authors": "not-a-list",
                "year": 99999,
                "doi": "doi:",
                "arxiv_id": "https://arxiv.org/abs/",
            },
            {"url": "https://example.test/ref", "year": 1999, "doi": "10.5/abc"},
        ]
    }
    structured, _ = extract_html_structured_metadata(
        article_content="<p>a</p>",
        content_kind="html",
        source_uri="u",
        page_title="Title",
        reference_title="Hint",
        completion_resolver=_build_turn_resolver(authors_payload, date_payload, citations_payload),
    )
    assert structured["authors"] == [
        {"name": "Grace Hopper", "normalized_name": "hopper grace"},
        {"name": "Plato", "normalized_name": "plato"},
    ]
    assert structured["publication_date"] == "2021-07-01"
    assert structured["publication_date_raw"] == "2021/07"
    citations = structured["citations"]
    assert len(citations) == 3
    assert citations[0]["doi"] == "10.1000/xyz"
    assert citations[0]["arxiv_id"] == "1234.5678"
    assert citations[0]["year"] == 1950
    assert citations[0]["authors"] == ["Alan Turing"]
    assert citations[0]["citing_context"] == "Used as foundation."
    assert citations[1]["title"] is None
    assert citations[1]["authors"] == []
    assert citations[1]["year"] is None
    assert citations[1]["doi"] is None
    assert citations[1]["arxiv_id"] is None
    assert citations[2]["year"] == 1999
    assert structured["summary"]["citations_with_identifiers"] == 2
    assert structured["warnings"][0]["code"] == "citation_unusable"


@pytest.mark.parametrize(
    ("date_payload", "expected_date", "expected_raw"),
    [
        ({}, None, None),
        ({"publication_date": "2020.01.02"}, "2020-01-02", "2020.01.02"),
        ({"publication_date": "Spring 2020", "raw": "Spring"}, None, "Spring"),
    ],
)
def test_extract_metadata_publication_date_variants(date_payload, expected_date, expected_raw):
    """Publication dates normalize to ISO days or None when unrecognized."""
    structured, _ = extract_html_structured_metadata(
        article_content="<p>a</p>",
        content_kind="html",
        source_uri="u",
        completion_resolver=_build_turn_resolver({"authors": "bad"}, date_payload, {}),
    )
    assert structured["publication_date"] == expected_date
    assert structured["publication_date_raw"] == expected_raw
    assert structured["authors"] == []
    assert structured["citations"] == []


def test_normalize_helpers_handle_edge_values():
    """Private normalization helpers cover their empty and edge inputs."""
    assert html_structured_module._normalize_person_name("   ") == ""
    assert html_structured_module._coerce_year(None) is None
    assert html_structured_module._coerce_year(2001) == 2001
    assert html_structured_module._coerce_year(12) is None
    assert html_structured_module._coerce_year("no year") is None
    assert html_structured_module._normalize_doi(None) is None
    assert html_structured_module._normalize_doi("10.1/a") == "10.1/a"
    assert html_structured_module._normalize_arxiv_id("") is None
    assert html_structured_module._normalize_arxiv_id("2101.00001") == "2101.00001"


def test_parse_json_object_accepts_fenced_and_double_encoded_json():
    """Fenced code blocks and JSON-encoded strings are unwrapped into objects."""
    assert html_structured_module._parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert html_structured_module._parse_json_object('"{\\"b\\": 2}"') == {"b": 2}


def test_parse_json_object_rejects_non_object_payloads():
    """A JSON array is rejected with a clear error."""
    with pytest.raises(ValueError, match="JSON object"):
        html_structured_module._parse_json_object("[1, 2]")


def _install_fake_openai_module(monkeypatch, response_text):
    recorded_requests: list = []

    class FakeCompletions:
        def create(self, *, model, messages):
            recorded_requests.append({"model": model, "messages": messages})
            message = types.SimpleNamespace(content=response_text)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    class FakeOpenAiClient:
        def __init__(self, *, api_key):
            recorded_requests.append({"api_key": api_key})
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    class FakeLlmClientConfig:
        def __init__(self, *, provider, model):
            self.provider = provider
            self.model = model

        def resolve_api_key(self):
            return "fake-key"

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAiClient))
    monkeypatch.setattr(html_structured_module, "LlmClientConfig", FakeLlmClientConfig)
    return recorded_requests


def test_openai_json_completion_parses_response_with_fake_client(monkeypatch):
    """The OpenAI completion helper parses the first choice into a JSON object."""
    recorded_requests = _install_fake_openai_module(monkeypatch, '```\n{"authors": []}\n```')
    payload = html_structured_module._openai_json_completion(
        model="test-model", messages=[{"role": "user", "content": "hi"}]
    )
    assert payload == {"authors": []}
    assert recorded_requests[0] == {"api_key": "fake-key"}
    assert recorded_requests[1]["model"] == "test-model"


def test_openai_json_completion_reports_missing_openai_package(monkeypatch):
    """A missing openai package yields a clear installation hint."""
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(ValueError, match="requires the openai package"):
        html_structured_module._openai_json_completion(model="m", messages=[])


def test_pipeline_returns_converted_when_heuristics_disabled_and_llm_disabled(monkeypatch):
    """With both layers disabled the conversion payload is returned unchanged."""
    monkeypatch.setenv(HTML_HEURISTICS_ENABLE_ENV, "off")
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "off")
    converted = {"text": "body"}
    result = enrich_web_extraction_structured(converted, source_uri="u", html_content="<p>body</p>")
    assert result is converted


def test_pipeline_without_html_returns_converted_when_llm_disabled(monkeypatch):
    """Without HTML, heuristics are skipped and a disabled LLM returns the payload."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "0")
    converted = {"text": "body"}
    assert enrich_web_extraction_structured(converted, source_uri="u") is converted


def test_pipeline_records_heuristic_warning_when_beautifulsoup_unavailable(monkeypatch):
    """A ValueError from heuristics becomes an html_heuristic_warnings entry."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "0")

    def raise_missing_dependency(html, *, source_uri):
        raise ValueError("beautifulsoup4 missing")

    monkeypatch.setattr(pipeline_module, "extract_html_heuristics", raise_missing_dependency)
    result = enrich_web_extraction_structured(
        {"text": "body", "html_heuristic_warnings": "not-a-list"},
        source_uri="u",
        html_content="<p>body</p>",
    )
    assert result["html_heuristic_warnings"] == [
        {"code": "html_heuristics_unavailable", "message": "beautifulsoup4 missing"}
    ]
    assert "structured" not in result


def test_pipeline_appends_heuristic_warning_to_existing_warning_list(monkeypatch):
    """An existing html_heuristic_warnings list is extended rather than replaced."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "0")

    def raise_missing_dependency(html, *, source_uri):
        raise ValueError("second failure")

    monkeypatch.setattr(pipeline_module, "extract_html_heuristics", raise_missing_dependency)
    existing_warning = {"code": "earlier", "message": "earlier warning"}
    result = enrich_web_extraction_structured(
        {"text": "body", "html_heuristic_warnings": [existing_warning]},
        source_uri="u",
        html_content="<p>body</p>",
    )
    assert [warning["code"] for warning in result["html_heuristic_warnings"]] == [
        "earlier",
        "html_heuristics_unavailable",
    ]


def test_pipeline_keeps_existing_title_and_returns_partial_when_llm_disabled(monkeypatch):
    """Weak heuristic citations are returned as partial results when the LLM is disabled."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "0")
    result = enrich_web_extraction_structured(
        {"text": "body", "title": "Converted Title"},
        source_uri="https://site.test/a",
        html_content=_html_page("<title>Html Title</title>", WEAK_REFERENCE_BODY),
    )
    assert result["method"] == "html-heuristics-partial"
    assert result["title"] == "Converted Title"
    assert result["structured"]["citations"][0]["title"] == "Brief"


def test_pipeline_returns_converted_when_heuristics_empty_and_llm_disabled(monkeypatch):
    """Empty heuristic results with a disabled LLM return the payload unchanged."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "0")
    converted = {"text": "body"}
    result = enrich_web_extraction_structured(
        converted, source_uri="u", html_content=_html_page(body_markup="<p>x</p>")
    )
    assert result is converted


def test_pipeline_returns_heuristic_partial_when_llm_finds_nothing(monkeypatch):
    """When the LLM adds nothing, partial heuristic results are kept."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)
    result = enrich_web_extraction_structured(
        {"text": "body"},
        source_uri="u",
        html_content=_html_page(body_markup=WEAK_REFERENCE_BODY),
        completion_resolver=_empty_turn_resolver(),
    )
    assert result["method"] == "html-heuristics-partial"
    assert "llm" not in result["html_structured"]


def test_pipeline_returns_llm_payload_when_no_html_and_llm_finds_nothing(monkeypatch):
    """Without HTML or LLM results the LLM layer's payload is returned."""
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)
    converted = {"text": "body"}
    result = enrich_web_extraction_structured(
        converted, source_uri="u", completion_resolver=_empty_turn_resolver()
    )
    assert result is converted


def test_pipeline_uses_llm_structured_alone_without_html(monkeypatch):
    """Without HTML, LLM structured metadata is used as-is with method llm-html."""
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)
    result = enrich_web_extraction_structured(
        {"text": "body"},
        source_uri="u",
        completion_resolver=_build_turn_resolver({"authors": ["Ada Lovelace"]}, {}, {}),
    )
    assert result["method"] == "llm-html"
    assert result["structured"]["authors"][0]["name"] == "Ada Lovelace"
    assert result["html_structured"]["llm"]["turns"] == 3


def test_pipeline_merges_heuristic_authors_and_citations_into_llm_date(monkeypatch):
    """Heuristic authors and citations fill gaps left by an LLM that found only a date."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)
    html = _html_page('<meta name="author" content="Barbara Liskov">', WEAK_REFERENCE_BODY)
    result = enrich_web_extraction_structured(
        {"text": "body"},
        source_uri="u",
        html_content=html,
        completion_resolver=_build_turn_resolver({}, {"publication_date": "2010-10-10"}, {}),
    )
    structured = result["structured"]
    assert result["method"] == "html-heuristics+llm-html"
    assert structured["authors"][0]["name"] == "Barbara Liskov"
    assert structured["publication_date"] == "2010-10-10"
    assert structured["citations"][0]["title"] == "Brief"
    assert structured["summary"]["authors_count"] == 1
    assert structured["summary"]["citations_count"] == 1
    assert "heuristic" in structured["raw_metadata"]


def test_pipeline_merges_heuristic_date_into_llm_authors(monkeypatch):
    """A heuristic publication date fills the gap when the LLM found only authors."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.delenv(HTML_STRUCTURED_ENABLE_ENV, raising=False)
    html = _html_page('<meta name="dc.date" content="2005-05-05">', WEAK_REFERENCE_BODY)
    result = enrich_web_extraction_structured(
        {"text": "body"},
        source_uri="u",
        html_content=html,
        completion_resolver=_build_turn_resolver({"authors": ["Ken Thompson"]}, {}, {}),
    )
    structured = result["structured"]
    assert result["method"] == "html-heuristics+llm-html"
    assert structured["publication_date"] == "2005-05-05"
    assert structured["publication_date_raw"] == "2005-05-05"
    assert structured["authors"][0]["name"] == "Ken Thompson"


def test_merge_structured_and_resolve_method_with_sparse_heuristics():
    """Sparse heuristics keep LLM values, and non-list fields are treated as empty."""
    llm_structured = {
        "authors": "not-a-list",
        "citations": [{"url": "https://x.test"}, "not-a-dict"],
        "summary": "not-a-dict",
        "warnings": "not-a-list",
    }
    heuristic_structured = {"warnings": "not-a-list", "raw_metadata": {}}
    merged = pipeline_module._merge_structured(heuristic_structured, llm_structured)
    assert merged["warnings"] == []
    assert "raw_metadata" not in merged
    assert merged["summary"] == {
        "authors_count": 0,
        "citations_count": 2,
        "citations_with_identifiers": 1,
    }
    assert pipeline_module._merge_structured(None, {"a": 1}) == {"a": 1}
    assert pipeline_module._resolve_method(heuristic_structured, llm_structured) == "llm-html"
    assert pipeline_module._resolve_method(None, llm_structured) == "llm-html"


def test_pipeline_does_not_overwrite_title_when_heuristics_find_none(monkeypatch):
    """A heuristic document without a title leaves the converted payload title absent."""
    monkeypatch.delenv(HTML_HEURISTICS_ENABLE_ENV, raising=False)
    monkeypatch.setenv(HTML_STRUCTURED_ENABLE_ENV, "0")
    monkeypatch.setattr(
        pipeline_module,
        "extract_html_heuristics",
        lambda html, *, source_uri: HtmlHeuristicDocument(
            authors=[{"name": "A", "normalized_name": "a"}]
        ),
    )
    result = enrich_web_extraction_structured(
        {"text": "body"}, source_uri="u", html_content="<p>x</p>"
    )
    assert result["method"] == "html-heuristics"
    assert "title" not in result
