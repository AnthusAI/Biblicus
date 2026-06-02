"""Behave steps for HTML heuristic structured extraction."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from behave import given, then, when

from biblicus.html_heuristics import (
    _normalize_reference_candidates,
    extract_html_heuristics,
    heuristic_document_to_structured,
    structured_metadata_is_sufficient,
)
from biblicus.html_structured_pipeline import enrich_web_extraction_structured

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "html_heuristics"


def _fixture_path(name: str) -> Path:
    return _FIXTURES_DIR / name


def _load_fixture(context, filename: str, *, source_uri: str = "https://fixture.test/") -> None:
    html = _fixture_path(filename).read_text(encoding="utf-8")
    context._last_fixture_html = html
    context.current_fixture_name = filename
    context.heuristic_document = extract_html_heuristics(html, source_uri=source_uri)
    context.heuristic_structured = heuristic_document_to_structured(context.heuristic_document)


@given("HTML heuristic fixtures are available")
def step_fixtures_available(context) -> None:
    assert _FIXTURES_DIR.is_dir(), f"Missing fixtures directory: {_FIXTURES_DIR}"


@given("HTML LLM structured extraction is disabled")
def step_disable_llm(context) -> None:
    os.environ["BIBLICUS_HTML_LLM_STRUCTURED"] = "0"
    context.html_llm_resolver = None


@given("HTML LLM structured extraction is enabled")
def step_enable_llm(context) -> None:
    os.environ["BIBLICUS_HTML_LLM_STRUCTURED"] = "1"


@given("a fake HTML LLM resolver returns authors and citations for sparse pages")
def step_fake_llm_sparse(context) -> None:
    def resolver(*, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        turn = sum(1 for row in messages if row.get("role") == "assistant")
        if turn == 0:
            return {"authors": [{"name": "LLM Author", "normalized_name": "author llm"}]}
        if turn == 1:
            return {"publication_date": "2024-01-01", "raw": "2024-01-01"}
        return {
            "citations": [
                {
                    "title": "LLM discovered citation",
                    "authors": ["Pat Example"],
                    "year": 2022,
                    "doi": "10.1000/llm.test",
                    "citing_context": "Fixture LLM citation context for sparse pages.",
                }
            ]
        }

    context.html_llm_resolver = resolver


@given("a fake HTML LLM resolver returns only publication date")
def step_fake_llm_date_only(context) -> None:
    def resolver(*, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        turn = sum(1 for row in messages if row.get("role") == "assistant")
        if turn == 0:
            return {"authors": []}
        if turn == 1:
            return {"publication_date": "2024-01-01", "raw": "2024-01-01"}
        return {"citations": []}

    context.html_llm_resolver = resolver


@given('I parse the HTML heuristic fixture "{filename}"')
def step_parse_fixture(context, filename: str) -> None:
    _load_fixture(context, filename)


@given('the heuristic fixture source uri is "{source_uri}"')
def step_set_fixture_source_uri(context, source_uri: str) -> None:
    filename = getattr(context, "current_fixture_name", None)
    assert filename, "Parse a fixture before setting source uri"
    _load_fixture(context, filename, source_uri=source_uri)


@given('I prepare a web extraction payload with text "{text}"')
def step_prepare_web_payload(context, text: str) -> None:
    html = str(getattr(context, "_last_fixture_html", "") or "")
    context.web_payload = {
        "text": text,
        "markdown": text,
        "title": None,
        "html_content": html,
    }


@given('the HTML heuristic fixture "{filename}" is served for uri "{uri}"')
def step_serve_fixture(context, filename: str, uri: str) -> None:
    context.served_html = {
        "uri": uri,
        "body": _fixture_path(filename).read_text(encoding="utf-8"),
        "content_type": "text/html",
    }


@when('I enrich the web extraction payload with source uri "{source_uri}"')
def step_enrich_payload(context, source_uri: str) -> None:
    payload = dict(context.web_payload)
    html = str(payload.pop("html_content", "") or "")
    context.enriched_payload = enrich_web_extraction_structured(
        payload,
        source_uri=source_uri,
        html_content=html,
        completion_resolver=getattr(context, "html_llm_resolver", None),
    )


@when("I extract URL text from {uri}")
def step_extract_url_text(context, uri: str) -> None:
    import biblicus.url_text as url_text_module

    served = getattr(context, "served_html", None)
    uri = uri.strip('"')

    def fake_fetch(**kwargs):
        if served and kwargs.get("uri") == served["uri"]:
            return {
                "ok": True,
                "body": served["body"].encode("utf-8"),
                "content_type": served["content_type"],
                "final_url": served["uri"],
                "attempts": [],
                "error": None,
            }
        return {
            "ok": False,
            "body": b"",
            "content_type": None,
            "final_url": kwargs.get("uri"),
            "attempts": [],
            "error": {"code": "not_found", "message": "fixture not served"},
        }

    def fake_markitdown(**_kwargs):
        return {
            "text": "Fixture body from markitdown",
            "markdown": "Fixture body from markitdown",
            "title": "Fixture title",
        }

    original_fetch = url_text_module._fetch_url_bytes
    original_markitdown = url_text_module._convert_bytes_with_markitdown
    url_text_module._fetch_url_bytes = fake_fetch
    url_text_module._convert_bytes_with_markitdown = fake_markitdown
    try:
        context.url_text_result = url_text_module.extract_url_text(source_uri=uri)
    finally:
        url_text_module._fetch_url_bytes = original_fetch
        url_text_module._convert_bytes_with_markitdown = original_markitdown


@given('a heuristic reference candidate with raw line "{raw}"')
def step_reference_candidate(context, raw: str) -> None:
    context.reference_candidates = [{"source": "test", "raw": raw, "title": raw}]


@when("I normalize heuristic reference candidates")
def step_normalize_candidates(context) -> None:
    context.normalized_citations = _normalize_reference_candidates(context.reference_candidates)


@then('the heuristic document title is "{title}"')
def step_doc_title(context, title: str) -> None:
    assert context.heuristic_document.title == title


def _author_name_from_step(name: str) -> str:
    return str(name or "").strip().strip('"')


@then("the heuristic document has exactly {count:d} authors including {name}")
def step_doc_authors(context, count: int, name: str) -> None:
    expected_name = _author_name_from_step(name)
    names = [row.get("name") for row in context.heuristic_document.authors]
    assert len(names) == count, f"expected {count} authors, got {names}"
    assert expected_name in names, f"{expected_name!r} not in {names!r}"


@then("the heuristic document has at least {count:d} authors including {name}")
def step_doc_authors_at_least(context, count: int, name: str) -> None:
    expected_name = _author_name_from_step(name)
    names = [row.get("name") for row in context.heuristic_document.authors]
    assert len(names) >= count, f"expected >={count} authors, got {names!r}"
    assert expected_name in names, f"{expected_name!r} not in {names!r}"


@then('the heuristic document publication date is "{value}"')
def step_doc_pubdate(context, value: str) -> None:
    assert context.heuristic_document.publication_date == value


@then('the heuristic extraction layers include "{layer}"')
def step_layers_include(context, layer: str) -> None:
    assert layer in context.heuristic_document.layers


@then("the heuristic structured payload has at least {count:d} citations")
def step_structured_citations(context, count: int) -> None:
    citations = context.heuristic_structured.get("citations") or []
    assert len(citations) >= count


@then("heuristic citation {index:d} title contains {text}")
def step_citation_title_contains(context, index: int, text: str) -> None:
    needle = _author_name_from_step(text)
    citation = context.heuristic_structured["citations"][index - 1]
    title = str(citation.get("title") or "")
    assert needle in title, f"expected {needle!r} in citation title {title!r}"


@then('heuristic citation {index:d} has url "{url}"')
def step_citation_url(context, index: int, url: str) -> None:
    citation = context.heuristic_structured["citations"][index - 1]
    assert citation.get("url") == url


@then("the heuristic document has at least {count:d} reference candidates")
def step_ref_candidates(context, count: int) -> None:
    assert len(context.heuristic_document.reference_candidates) >= count


@then("structured metadata sufficiency is false")
def step_not_sufficient(context) -> None:
    assert structured_metadata_is_sufficient(context.heuristic_structured) is False


@then('the heuristic structured warnings include code "{code}"')
def step_warning_code(context, code: str) -> None:
    warnings = context.heuristic_structured.get("warnings") or []
    assert any(str(row.get("code") or "") == code for row in warnings)


@then('the enriched web extraction method is "{method}"')
def step_enriched_method(context, method: str) -> None:
    assert context.enriched_payload.get("method") == method


@then("the enriched structured payload has at least {count:d} citations")
def step_enriched_citations(context, count: int) -> None:
    structured = context.enriched_payload.get("structured") or {}
    assert len(structured.get("citations") or []) >= count


@then("the enriched structured payload has at least {count:d} authors")
def step_enriched_authors(context, count: int) -> None:
    structured = context.enriched_payload.get("structured") or {}
    assert len(structured.get("authors") or []) >= count


@then('the enriched structured publication date is "{value}"')
def step_enriched_pubdate(context, value: str) -> None:
    structured = context.enriched_payload.get("structured") or {}
    assert structured.get("publication_date") == value


@then("normalized citation {index:d} year is {year}")
def step_norm_year(context, index: int, year: str) -> None:
    citation = context.normalized_citations[index - 1]
    if not year.strip():
        assert citation.get("year") is None
    else:
        assert citation.get("year") == int(year)


@then("normalized citation {index:d} doi equals {doi}")
def step_norm_doi(context, index: int, doi: str) -> None:
    citation = context.normalized_citations[index - 1]
    expected = doi.strip()
    if not expected or expected.lower() == "none":
        assert not citation.get("doi")
    else:
        assert citation.get("doi") == expected


@then('the URL text extraction status is "{status}"')
def step_url_status(context, status: str) -> None:
    assert context.url_text_result.get("status") == status


@then('the URL text extraction method is "{method}"')
def step_url_method(context, method: str) -> None:
    assert context.url_text_result.get("method") == method


@then("the URL text structured authors count is at least {count:d}")
def step_url_authors(context, count: int) -> None:
    structured = context.url_text_result.get("structured") or {}
    assert len(structured.get("authors") or []) >= count
