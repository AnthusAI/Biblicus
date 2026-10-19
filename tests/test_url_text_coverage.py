from __future__ import annotations

import io
import sys
import types
from urllib.error import HTTPError, URLError

import pytest

from biblicus import grobid_client as grobid_client_module
from biblicus import grobid_runtime as grobid_runtime_module
from biblicus import url_text as url_text_module
from biblicus.url_text import UrlTextExtractionError

TEI_NAMESPACE_URI = "http://www.tei-c.org/ns/1.0"


class FakeUrlopenResponse:
    """Provide a fake urlopen response test double."""

    def __init__(self, *, body, content_type, status=None, final_url="", getcode_value=200):
        self._body = body
        self.headers = {"Content-Type": content_type}
        if status is not None:
            self.status = status
        self.url = final_url
        self._getcode_value = getcode_value

    def read(self):
        """Return the fake response body."""
        return self._body

    def getcode(self):
        """Return the fake HTTP status code."""
        return self._getcode_value

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeResponseWithoutStatusAttribute:
    """Provide a fake response without status attribute test double."""

    def __init__(self, *, body, content_type):
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        """Return the fake response body."""
        return self._body

    def getcode(self):
        """Return the fake HTTP status code."""
        return 201

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeMarkItDownResult:
    """Provide a fake mark it down result test double."""

    def __init__(self, *, text_content="", markdown="", title=""):
        self.text_content = text_content
        self.markdown = markdown
        self.title = title


class RecordingFakeMarkItDownConverter:
    """Provide a recording fake mark it down converter test double."""

    def __init__(self, *, result=None, error=None):
        self.result = result
        self.error = error
        self.convert_calls = []

    def convert(self, *args, **kwargs):
        """Record the conversion call and return or raise the configured outcome."""
        self.convert_calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
        return self.result


def build_sequential_urlopen_fake(outcomes):
    """Support tests with the build sequential urlopen fake helper."""
    remaining_outcomes = list(outcomes)
    recorded_requests = []

    def fake_urlopen(request, timeout):
        recorded_requests.append((request, timeout))
        outcome = remaining_outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return fake_urlopen, recorded_requests


def build_http_error(status_code):
    """Support tests with the build http error helper."""
    return HTTPError("https://example.test/doc", status_code, "failure", {}, io.BytesIO(b""))


def build_fetch_result(*, ok, body=b"", content_type=None, final_url="", step="step"):
    """Support tests with the build fetch result helper."""
    return {
        "ok": ok,
        "body": body,
        "content_type": content_type,
        "final_url": final_url,
        "attempts": [{"step": step, "result": "ok" if ok else "failed"}],
        "error": None if ok else {"code": "manual_fetch_failed", "message": "failed"},
    }


def wrap_tei_document(inner_markup):
    """Support tests with the wrap tei document helper."""
    return f'<TEI xmlns="{TEI_NAMESPACE_URI}">{inner_markup}</TEI>'


def test_url_text_extraction_error_to_dict_omits_empty_details():
    """Verify url text extraction error to dict omits empty details."""
    error = UrlTextExtractionError(code="some_code", message="some message")
    assert error.to_dict() == {"code": "some_code", "message": "some message"}


def test_load_url_text_input_json_reads_standard_input_for_dash(monkeypatch):
    """Verify load url text input json reads standard input for dash."""
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"source_uri": "https://example.test"}'))
    assert url_text_module.load_url_text_input_json("-") == {"source_uri": "https://example.test"}


def test_load_url_text_input_json_treats_blank_argument_as_standard_input(monkeypatch):
    """Verify load url text input json treats blank argument as standard input."""
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"key": 1}'))
    assert url_text_module.load_url_text_input_json("  ") == {"key": 1}


def test_load_url_text_input_json_reads_file_path(tmp_path):
    """Verify load url text input json reads file path."""
    input_path = tmp_path / "input.json"
    input_path.write_text('{"source_uri": "https://example.test/file"}', encoding="utf-8")
    assert url_text_module.load_url_text_input_json(str(input_path)) == {
        "source_uri": "https://example.test/file"
    }


def test_load_url_text_input_json_rejects_invalid_json(tmp_path):
    """Verify load url text input json rejects invalid json."""
    input_path = tmp_path / "input.json"
    input_path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid input JSON"):
        url_text_module.load_url_text_input_json(str(input_path))


def test_load_url_text_input_json_rejects_non_object_json(tmp_path):
    """Verify load url text input json rejects non object json."""
    input_path = tmp_path / "input.json"
    input_path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        url_text_module.load_url_text_input_json(str(input_path))


def test_extract_url_text_raises_when_source_uri_is_blank():
    """Verify extract url text raises when source uri is blank."""
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module.extract_url_text(source_uri="   ")
    assert captured.value.code == "missing_source_uri"


def test_extract_url_text_reports_empty_text_when_conversion_yields_whitespace(monkeypatch):
    """Verify extract url text reports empty text when conversion yields whitespace."""
    monkeypatch.setattr(
        url_text_module,
        "_extract_web",
        lambda **kwargs: {"text": "   ", "content_type": "text/html"},
    )
    result = url_text_module.extract_url_text(source_uri="https://example.test/page")
    assert result["status"] == "failed"
    assert result["error"]["code"] == "empty_text"
    assert result["content_type"] == "text/html"


def test_extract_url_text_reports_empty_text_with_missing_content_type(monkeypatch):
    """Verify extract url text reports empty text with missing content type."""
    monkeypatch.setattr(url_text_module, "_extract_web", lambda **kwargs: {"text": ""})
    result = url_text_module.extract_url_text(source_uri="https://example.test/page")
    assert result["content_type"] is None


def test_extract_url_text_enriches_web_result_without_structured_payload(monkeypatch):
    """Verify extract url text enriches web result without structured payload."""
    enrichment_calls = []

    def fake_enrich_web_extraction_structured(
        converted, *, source_uri, html_content, reference_title
    ):
        enrichment_calls.append((source_uri, html_content, reference_title))
        return {
            "text": "Enriched text",
            "markdown": "# Enriched",
            "title": "Enriched title",
            "structured": {"sections": []},
            "method": converted["method"],
        }

    monkeypatch.setattr(
        url_text_module,
        "_extract_web",
        lambda **kwargs: {
            "text": "Raw text",
            "markdown": "Raw markdown",
            "title": "Raw title",
            "content_type": "text/html",
            "html_content": "<p>Raw</p>",
            "method": "markitdown",
        },
    )
    monkeypatch.setattr(
        url_text_module, "enrich_web_extraction_structured", fake_enrich_web_extraction_structured
    )
    result = url_text_module.extract_url_text(
        source_uri="https://example.test/page", reference_title="Reference"
    )
    assert enrichment_calls == [("https://example.test/page", "<p>Raw</p>", "Reference")]
    assert result["status"] == "ok"
    assert result["text"] == "Enriched text"
    assert result["markdown"] == "# Enriched"
    assert result["title"] == "Enriched title"
    assert result["structured"] == {"sections": []}
    assert result["method"] == "markitdown"
    assert result["grobid"] is None


def test_extract_url_text_enrichment_keeps_original_values_when_enrichment_is_empty(
    monkeypatch,
):
    """Verify extract url text enrichment keeps original values when enrichment is empty."""
    monkeypatch.setattr(
        url_text_module,
        "_extract_web",
        lambda **kwargs: {"text": "Raw text", "title": None},
    )
    monkeypatch.setattr(
        url_text_module,
        "enrich_web_extraction_structured",
        lambda converted, **kwargs: {"structured": "not a dict"},
    )
    result = url_text_module.extract_url_text(source_uri="https://example.test/page")
    assert result["text"] == "Raw text"
    assert result["markdown"] == "Raw text"
    assert result["title"] is None
    assert result["structured"] is None
    assert result["method"] is None


def test_extract_url_text_skips_enrichment_when_web_result_is_structured(monkeypatch):
    """Verify extract url text skips enrichment when web result is structured."""
    monkeypatch.setattr(
        url_text_module,
        "_extract_web",
        lambda **kwargs: {"text": "Raw text", "structured": {"already": True}},
    )
    monkeypatch.setattr(
        url_text_module,
        "enrich_web_extraction_structured",
        lambda *args, **kwargs: pytest.fail("enrichment should not run"),
    )
    result = url_text_module.extract_url_text(source_uri="https://example.test/page")
    assert result["structured"] == {"already": True}


def test_extract_url_text_pdf_reports_fetch_failure(monkeypatch):
    """Verify extract url text pdf reports fetch failure."""
    monkeypatch.setattr(
        url_text_module,
        "_fetch_url_bytes",
        lambda **kwargs: build_fetch_result(ok=False, step=kwargs["step"]),
    )
    result = url_text_module.extract_url_text(source_uri="https://example.test/paper.pdf")
    assert result["status"] == "failed"
    assert result["error"]["code"] == "pdf_fetch_failed"
    assert result["attempts"] == [{"step": "pdf_fetch", "result": "failed"}]


def test_extract_url_text_pdf_reports_grobid_empty_text(monkeypatch):
    """Verify extract url text pdf reports grobid empty text."""
    monkeypatch.setattr(
        url_text_module,
        "_fetch_url_bytes",
        lambda **kwargs: build_fetch_result(
            ok=True, body=b"%PDF", content_type="application/pdf", final_url=""
        ),
    )
    received_source_uris = []

    def fake_convert_pdf_with_grobid(*, data, source_uri, content_type):
        received_source_uris.append(source_uri)
        return {"text": "   "}

    monkeypatch.setattr(url_text_module, "_convert_pdf_with_grobid", fake_convert_pdf_with_grobid)
    result = url_text_module.extract_url_text(source_uri="https://example.test/paper.pdf")
    assert received_source_uris == ["https://example.test/paper.pdf"]
    assert result["error"]["code"] == "grobid_empty_text"
    assert result["attempts"][-1]["step"] == "pdf_convert_grobid"


def test_extract_web_records_empty_conversion_and_conversion_exception_then_goes_direct(
    monkeypatch,
):
    """Verify extract web records empty conversion and conversion exception then goes direct."""
    monkeypatch.setattr(
        url_text_module,
        "_fetch_url_bytes",
        lambda **kwargs: build_fetch_result(
            ok=True,
            body=b"<html>body</html>",
            content_type="text/html",
            final_url="",
            step=kwargs["step"],
        ),
    )
    conversion_outcomes = [{"text": ""}, RuntimeError("conversion exploded")]

    def fake_convert_bytes_with_markitdown(**kwargs):
        outcome = conversion_outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(
        url_text_module, "_convert_bytes_with_markitdown", fake_convert_bytes_with_markitdown
    )
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda uri: {"text": "direct text"},
    )
    attempts = []
    converted = url_text_module._extract_web(
        uri="https://example.test/page",
        source_kind="web",
        attempts=attempts,
        timeout_seconds=1.0,
        max_retries=0,
        backoff_seconds=0.0,
    )
    assert converted == {"text": "direct text"}
    failed_errors = [entry.get("error") for entry in attempts if entry.get("result") == "failed"]
    assert "conversion produced empty text" in failed_errors
    assert "conversion exploded" in failed_errors
    assert attempts[-1]["step"] == "direct_markitdown"


def test_extract_web_attaches_html_content_to_successful_conversion(monkeypatch):
    """Verify extract web attaches html content to successful conversion."""
    monkeypatch.setattr(
        url_text_module,
        "_fetch_url_bytes",
        lambda **kwargs: build_fetch_result(
            ok=True,
            body=b"<html>body</html>",
            content_type="text/html; charset=utf-8",
            final_url="https://example.test/final",
        ),
    )
    received_source_uris = []

    def fake_convert_bytes_with_markitdown(*, data, source_uri, content_type):
        received_source_uris.append(source_uri)
        return {"text": "converted"}

    monkeypatch.setattr(
        url_text_module, "_convert_bytes_with_markitdown", fake_convert_bytes_with_markitdown
    )
    converted = url_text_module._extract_web(
        uri="https://example.test/page",
        source_kind="web",
        attempts=[],
        timeout_seconds=1.0,
        max_retries=0,
        backoff_seconds=0.0,
    )
    assert converted["html_content"] == "<html>body</html>"
    assert received_source_uris == ["https://example.test/final"]


def test_attempt_direct_markitdown_appends_youtube_retry_attempt_dictionaries(monkeypatch):
    """Verify attempt direct markitdown appends youtube retry attempt dictionaries."""
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda uri: {
            "text": "video text",
            "youtube_transcript_retry": {
                "attempts": [{"step": "youtube_transcript", "attempt": 1}, "not a dict"]
            },
        },
    )
    attempts = []
    converted = url_text_module._attempt_direct_markitdown(
        uri="https://youtu.be/abc", source_kind="youtube", attempts=attempts
    )
    assert converted["text"] == "video text"
    assert attempts[1] == {"step": "youtube_transcript", "attempt": 1}
    assert len(attempts) == 2


def test_attempt_direct_markitdown_handles_youtube_retry_without_attempts(monkeypatch):
    """Verify attempt direct markitdown handles youtube retry without attempts."""
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda uri: {"text": "video text", "youtube_transcript_retry": {"attempts": None}},
    )
    attempts = []
    url_text_module._attempt_direct_markitdown(
        uri="https://youtu.be/abc", source_kind="youtube", attempts=attempts
    )
    assert len(attempts) == 1


def test_attempt_direct_markitdown_raises_when_direct_conversion_is_empty(monkeypatch):
    """Verify attempt direct markitdown raises when direct conversion is empty."""
    monkeypatch.setattr(url_text_module, "_convert_direct_with_markitdown", lambda uri: {})
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._attempt_direct_markitdown(
            uri="https://example.test", source_kind="web", attempts=[]
        )
    assert captured.value.code == "direct_conversion_empty"


def test_attempt_direct_markitdown_wraps_unexpected_exceptions(monkeypatch):
    """Verify attempt direct markitdown wraps unexpected exceptions."""

    def raise_runtime_error(uri):
        raise RuntimeError("network down")

    monkeypatch.setattr(url_text_module, "_convert_direct_with_markitdown", raise_runtime_error)
    attempts = []
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._attempt_direct_markitdown(
            uri="https://example.test", source_kind="web", attempts=attempts
        )
    assert captured.value.code == "direct_conversion_failed"
    assert captured.value.details["error"] == "network down"
    assert attempts[-1]["result"] == "failed"


def test_fetch_url_bytes_returns_body_on_first_success(monkeypatch):
    """Verify fetch url bytes returns body on first success."""
    fake_urlopen, recorded_requests = build_sequential_urlopen_fake(
        [
            FakeUrlopenResponse(
                body=b"hello",
                content_type="Text/HTML; charset=utf-8",
                status=200,
                final_url="https://example.test/final",
            )
        ]
    )
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    result = url_text_module._fetch_url_bytes(
        uri="https://example.test/start",
        source_kind="web",
        step="web_html_fetch",
        accept="text/html",
        timeout_seconds=0.1,
        max_retries=2,
        backoff_seconds=0.5,
    )
    assert result["ok"] is True
    assert result["body"] == b"hello"
    assert result["content_type"] == "text/html"
    assert result["final_url"] == "https://example.test/final"
    assert result["attempts"][0]["http_status"] == 200
    assert recorded_requests[0][1] == 1.0
    assert recorded_requests[0][0].get_header("Accept") == "text/html"


def test_fetch_url_bytes_uses_getcode_and_source_uri_when_response_lacks_attributes(
    monkeypatch,
):
    """Verify fetch url bytes uses getcode and source uri when response lacks attributes."""
    fake_urlopen, _ = build_sequential_urlopen_fake(
        [FakeResponseWithoutStatusAttribute(body=b"x", content_type=None)]
    )
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    result = url_text_module._fetch_url_bytes(
        uri="https://example.test/start",
        source_kind="web",
        step="step",
        accept="*/*",
        timeout_seconds=5.0,
        max_retries=0,
        backoff_seconds=0.0,
    )
    assert result["attempts"][0]["http_status"] == 201
    assert result["final_url"] == "https://example.test/start"
    assert result["content_type"] is None


def test_fetch_url_bytes_retries_retryable_http_errors_and_url_errors_with_backoff(
    monkeypatch,
):
    """Verify fetch url bytes retries retryable http errors and url errors with backoff."""
    fake_urlopen, _ = build_sequential_urlopen_fake(
        [
            build_http_error(503),
            URLError("temporary dns failure"),
            FakeUrlopenResponse(body=b"ok", content_type="text/plain", status=200),
        ]
    )
    recorded_sleeps = []
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(url_text_module.time, "sleep", recorded_sleeps.append)
    result = url_text_module._fetch_url_bytes(
        uri="https://example.test/start",
        source_kind="web",
        step="step",
        accept="*/*",
        timeout_seconds=5.0,
        max_retries=2,
        backoff_seconds=0.5,
    )
    assert result["ok"] is True
    assert recorded_sleeps == [0.5, 1.0]
    assert [entry["result"] for entry in result["attempts"]] == ["failed", "failed", "ok"]
    assert result["attempts"][0]["http_status"] == 503


def test_fetch_url_bytes_stops_on_non_retryable_http_error(monkeypatch):
    """Verify fetch url bytes stops on non retryable http error."""
    fake_urlopen, recorded_requests = build_sequential_urlopen_fake([build_http_error(404)])
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    result = url_text_module._fetch_url_bytes(
        uri="https://example.test/missing",
        source_kind="web",
        step="step",
        accept="*/*",
        timeout_seconds=5.0,
        max_retries=3,
        backoff_seconds=0.0,
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "manual_fetch_failed"
    assert result["body"] == b""
    assert len(recorded_requests) == 1


def test_fetch_url_bytes_stops_after_retry_budget_for_retryable_http_error(monkeypatch):
    """Verify fetch url bytes stops after retry budget for retryable http error."""
    fake_urlopen, recorded_requests = build_sequential_urlopen_fake(
        [build_http_error(500), build_http_error(500)]
    )
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    result = url_text_module._fetch_url_bytes(
        uri="https://example.test/flaky",
        source_kind="web",
        step="step",
        accept="*/*",
        timeout_seconds=5.0,
        max_retries=1,
        backoff_seconds=0.0,
    )
    assert result["ok"] is False
    assert len(recorded_requests) == 2


def test_fetch_url_bytes_stops_after_retry_budget_for_url_errors(monkeypatch):
    """Verify fetch url bytes stops after retry budget for url errors."""
    fake_urlopen, recorded_requests = build_sequential_urlopen_fake(
        [URLError("refused"), URLError("refused")]
    )
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    result = url_text_module._fetch_url_bytes(
        uri="https://example.test/down",
        source_kind="web",
        step="step",
        accept="*/*",
        timeout_seconds=5.0,
        max_retries=1,
        backoff_seconds=0.0,
    )
    assert result["ok"] is False
    assert len(recorded_requests) == 2
    assert all("http_status" not in entry for entry in result["attempts"])


def test_convert_bytes_with_markitdown_infers_extension_and_builds_payload(monkeypatch):
    """Verify convert bytes with markitdown infers extension and builds payload."""
    converter = RecordingFakeMarkItDownConverter(
        result=FakeMarkItDownResult(text_content="body", markdown="# body", title=" Title ")
    )
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    payload = url_text_module._convert_bytes_with_markitdown(
        data=b"body", source_uri="https://example.test/doc.md", content_type=None
    )
    assert payload == {
        "text": "body",
        "markdown": "# body",
        "title": "Title",
        "content_type": None,
    }
    call_args, call_kwargs = converter.convert_calls[0]
    assert call_args[0].read() == b"body"
    assert call_kwargs == {"file_extension": ".md", "url": "https://example.test/doc.md"}


def test_convert_bytes_with_markitdown_prefers_explicit_file_extension(monkeypatch):
    """Verify convert bytes with markitdown prefers explicit file extension."""
    converter = RecordingFakeMarkItDownConverter(result=FakeMarkItDownResult(text_content="t"))
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    payload = url_text_module._convert_bytes_with_markitdown(
        data=b"t",
        source_uri="https://example.test/doc",
        content_type="text/plain",
        file_extension=".rst",
    )
    assert converter.convert_calls[0][1]["file_extension"] == ".rst"
    assert payload["markdown"] == "t"
    assert payload["title"] is None


def test_convert_direct_with_markitdown_routes_youtube_to_youtube_converter(monkeypatch):
    """Verify convert direct with markitdown routes youtube to youtube converter."""
    monkeypatch.setattr(
        url_text_module, "_convert_youtube_markdown", lambda uri: {"text": f"youtube:{uri}"}
    )
    payload = url_text_module._convert_direct_with_markitdown("https://youtu.be/abc")
    assert payload == {"text": "youtube:https://youtu.be/abc"}


def test_convert_direct_with_markitdown_converts_non_youtube_uri(monkeypatch):
    """Verify convert direct with markitdown converts non youtube uri."""
    converter = RecordingFakeMarkItDownConverter(
        result=FakeMarkItDownResult(text_content="page text")
    )
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    payload = url_text_module._convert_direct_with_markitdown("https://example.test/page")
    assert payload["text"] == "page text"
    assert payload["content_type"] is None
    assert converter.convert_calls[0][0] == ("https://example.test/page",)


@pytest.mark.parametrize(
    ("source_uri", "expected_canonical_uri"),
    [
        ("https://www.youtube.com/channel/xyz", "https://www.youtube.com/channel/xyz"),
        ("https://youtu.be/", "https://youtu.be/"),
        ("  https://example.test/video  ", "https://example.test/video"),
        ("https://www.youtube.com/shorts/short123", "https://www.youtube.com/watch?v=short123"),
    ],
)
def test_canonicalize_youtube_watch_url_handles_hosts_without_video_ids(
    source_uri, expected_canonical_uri
):
    """Verify canonicalize youtube watch url handles hosts without video ids."""
    assert url_text_module._canonicalize_youtube_watch_url(source_uri) == expected_canonical_uri


@pytest.mark.parametrize(
    ("source_uri", "expected_video_id"),
    [
        ("https://youtu.be/abc123/extra", "abc123"),
        ("https://www.youtube.com/watch?v=watch123", "watch123"),
        ("https://www.youtube.com/shorts/short123/more", "short123"),
        ("https://www.youtube.com/embed/embed123", "embed123"),
        ("https://www.youtube.com/channel/xyz", ""),
        ("https://example.test/watch?v=nope", ""),
    ],
)
def test_youtube_video_id_from_uri_supports_link_shapes(source_uri, expected_video_id):
    """Verify youtube video id from uri supports link shapes."""
    assert url_text_module._youtube_video_id_from_uri(source_uri) == expected_video_id


@pytest.mark.parametrize(
    ("markdown_text", "expected_low_quality"),
    [
        ("", True),
        ("   ", True),
        ("Intro\n### Transcript\nwords", False),
        ("# YouTube\n\n### Description\nabout", False),
        ("Menu [About](https://www.youtube.com/about) more", True),
        ("Some page © 2024 Google", True),
        ("A genuine page body without footer markers", False),
    ],
)
def test_is_low_quality_youtube_markdown_classifies_markdown(markdown_text, expected_low_quality):
    """Verify is low quality youtube markdown classifies markdown."""
    assert url_text_module._is_low_quality_youtube_markdown(markdown_text) is expected_low_quality


def test_youtube_transcript_retry_settings_uses_defaults_without_environment(monkeypatch):
    """Verify youtube transcript retry settings uses defaults without environment."""
    monkeypatch.delenv(url_text_module.YOUTUBE_TRANSCRIPT_MAX_WAIT_ENV, raising=False)
    monkeypatch.delenv(url_text_module.YOUTUBE_TRANSCRIPT_INITIAL_BACKOFF_ENV, raising=False)
    monkeypatch.delenv(url_text_module.YOUTUBE_TRANSCRIPT_MAX_BACKOFF_ENV, raising=False)
    assert url_text_module._youtube_transcript_retry_settings() == {
        "max_wait_seconds": url_text_module.YOUTUBE_TRANSCRIPT_DEFAULT_MAX_WAIT_SECONDS,
        "initial_backoff_seconds": (
            url_text_module.YOUTUBE_TRANSCRIPT_DEFAULT_INITIAL_BACKOFF_SECONDS
        ),
        "max_backoff_seconds": url_text_module.YOUTUBE_TRANSCRIPT_DEFAULT_MAX_BACKOFF_SECONDS,
    }


@pytest.mark.parametrize(
    ("raw_environment_value", "expected_value"),
    [("2.5", 2.5), ("not-a-number", 7.0), ("-3", 7.0), ("0", 7.0), ("", 7.0)],
)
def test_positive_env_float_parses_or_returns_default(
    monkeypatch, raw_environment_value, expected_value
):
    """Verify positive env float parses or returns default."""
    monkeypatch.setenv("BIBLICUS_TEST_POSITIVE_FLOAT", raw_environment_value)
    assert url_text_module._positive_env_float("BIBLICUS_TEST_POSITIVE_FLOAT", 7.0) == (
        expected_value
    )


@pytest.mark.parametrize(
    "retryable_code",
    ["youtube_transcript_unavailable", "direct_conversion_empty", "direct_conversion_failed"],
)
def test_is_retryable_youtube_transcript_error_accepts_known_codes(retryable_code):
    """Verify is retryable youtube transcript error accepts known codes."""
    error = UrlTextExtractionError(code=retryable_code, message="m")
    assert url_text_module._is_retryable_youtube_transcript_error(error) is True


def test_is_retryable_youtube_transcript_error_accepts_rate_limited_nested_error():
    """Verify is retryable youtube transcript error accepts rate limited nested error."""
    error = UrlTextExtractionError(
        code="other", message="m", details={"error": "HTTP 429 Too Many Requests"}
    )
    assert url_text_module._is_retryable_youtube_transcript_error(error) is True


def test_is_retryable_youtube_transcript_error_rejects_permanent_structured_errors():
    """Verify is retryable youtube transcript error rejects permanent structured errors."""
    error = UrlTextExtractionError(code="other", message="m")
    error.details = None
    assert url_text_module._is_retryable_youtube_transcript_error(error) is False


@pytest.mark.parametrize(
    ("exception_message", "expected_retryable"),
    [
        ("HTTP Error 503: Service Unavailable", True),
        ("no element found: line 1", True),
        ("completely unrelated failure", False),
    ],
)
def test_is_retryable_youtube_transcript_error_matches_plain_exception_markers(
    exception_message, expected_retryable
):
    """Verify is retryable youtube transcript error matches plain exception markers."""
    assert (
        url_text_module._is_retryable_youtube_transcript_error(ValueError(exception_message))
        is expected_retryable
    )


def install_fake_youtube_transcript_api_module(monkeypatch, *, fetch_behavior):
    """Support tests with the install fake youtube transcript api module helper."""
    fetch_calls = []

    class FakeYouTubeTranscriptApi:
        def fetch(self, video_id, languages):
            fetch_calls.append((video_id, languages))
            return fetch_behavior(video_id, languages)

    fake_module = types.ModuleType("youtube_transcript_api")
    fake_module.YouTubeTranscriptApi = FakeYouTubeTranscriptApi
    monkeypatch.setitem(sys.modules, "youtube_transcript_api", fake_module)
    return fetch_calls


def test_fetch_youtube_transcript_text_returns_empty_without_video_id():
    """Verify fetch youtube transcript text returns empty without video id."""
    assert url_text_module._fetch_youtube_transcript_text("") == ""


def test_fetch_youtube_transcript_text_returns_empty_when_dependency_is_missing(monkeypatch):
    """Verify fetch youtube transcript text returns empty when dependency is missing."""
    monkeypatch.setitem(sys.modules, "youtube_transcript_api", None)
    assert url_text_module._fetch_youtube_transcript_text("abc") == ""


def test_fetch_youtube_transcript_text_joins_snippets_and_defaults_languages(monkeypatch):
    """Verify fetch youtube transcript text joins snippets and defaults languages."""
    fetch_calls = install_fake_youtube_transcript_api_module(
        monkeypatch,
        fetch_behavior=lambda video_id, languages: [
            types.SimpleNamespace(text="hello"),
            types.SimpleNamespace(text="world"),
        ],
    )
    assert url_text_module._fetch_youtube_transcript_text("abc", languages=[" ", ""]) == (
        "hello world"
    )
    assert fetch_calls == [("abc", ["en"])]


def test_fetch_youtube_transcript_text_wraps_fetch_failures(monkeypatch):
    """Verify fetch youtube transcript text wraps fetch failures."""

    def raise_fetch_failure(video_id, languages):
        raise RuntimeError("captions disabled")

    install_fake_youtube_transcript_api_module(monkeypatch, fetch_behavior=raise_fetch_failure)
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._fetch_youtube_transcript_text("abc", languages=["fr"])
    assert captured.value.code == "youtube_transcript_unavailable"
    assert captured.value.details == {"video_id": "abc", "error": "captions disabled"}


def test_attempt_youtube_transcript_only_once_requires_video_id():
    """Verify attempt youtube transcript only once requires video id."""
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._attempt_youtube_transcript_only_once("https://www.youtube.com/feed")
    assert captured.value.code == "youtube_transcript_unavailable"


def test_attempt_youtube_transcript_only_once_builds_transcript_markdown(monkeypatch):
    """Verify attempt youtube transcript only once builds transcript markdown."""
    monkeypatch.setattr(
        url_text_module, "_fetch_youtube_transcript_text", lambda video_id: "spoken words"
    )
    payload = url_text_module._attempt_youtube_transcript_only_once("https://youtu.be/vid1")
    assert payload["method"] == "youtube-transcript-api"
    assert payload["title"] == "YouTube video vid1"
    assert "### Transcript\nspoken words" in payload["text"]


def test_attempt_youtube_markdown_once_delegates_to_transcript_api_when_preferred(monkeypatch):
    """Verify attempt youtube markdown once delegates to transcript api when preferred."""
    monkeypatch.setattr(
        url_text_module,
        "_attempt_youtube_transcript_only_once",
        lambda uri: {"text": "transcript only"},
    )
    payload = url_text_module._attempt_youtube_markdown_once(
        "https://youtu.be/vid1", prefer_transcript_api=True
    )
    assert payload == {"text": "transcript only"}


def test_attempt_youtube_markdown_once_returns_markitdown_transcript(monkeypatch):
    """Verify attempt youtube markdown once returns markitdown transcript."""
    converter = RecordingFakeMarkItDownConverter(
        result=FakeMarkItDownResult(
            text_content="# YouTube\n### Transcript\nwords",
            markdown="",
            title="Video title",
        )
    )
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    payload = url_text_module._attempt_youtube_markdown_once("https://youtu.be/vid1")
    assert payload["title"] == "Video title"
    assert payload["markdown"] == "# YouTube\n### Transcript\nwords"
    assert converter.convert_calls[0] == (
        ("https://www.youtube.com/watch?v=vid1",),
        {"youtube_transcript_languages": ["en"]},
    )


def test_attempt_youtube_markdown_once_appends_transcript_to_description_markdown(monkeypatch):
    """Verify attempt youtube markdown once appends transcript to description markdown."""
    converter = RecordingFakeMarkItDownConverter(
        result=FakeMarkItDownResult(text_content="# YouTube\n### Description\nabout  ")
    )
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    monkeypatch.setattr(url_text_module, "_fetch_youtube_transcript_text", lambda video_id: "words")
    payload = url_text_module._attempt_youtube_markdown_once("https://youtu.be/vid1")
    assert payload["text"] == "# YouTube\n### Description\nabout\n\n### Transcript\nwords\n"
    assert payload["markdown"] == payload["text"]


def test_attempt_youtube_markdown_once_keeps_description_when_transcript_is_empty(monkeypatch):
    """Verify attempt youtube markdown once keeps description when transcript is empty."""
    converter = RecordingFakeMarkItDownConverter(
        result=FakeMarkItDownResult(text_content="# YouTube\n### Description\nabout")
    )
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    monkeypatch.setattr(url_text_module, "_fetch_youtube_transcript_text", lambda video_id: "")
    payload = url_text_module._attempt_youtube_markdown_once("https://youtu.be/vid1")
    assert payload["text"] == "# YouTube\n### Description\nabout"


def test_attempt_youtube_markdown_once_skips_transcript_lookup_without_video_id(monkeypatch):
    """Verify attempt youtube markdown once skips transcript lookup without video id."""
    converter = RecordingFakeMarkItDownConverter(
        result=FakeMarkItDownResult(text_content="A real channel page body")
    )
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    monkeypatch.setattr(
        url_text_module,
        "_fetch_youtube_transcript_text",
        lambda video_id: pytest.fail("transcript lookup should not run"),
    )
    payload = url_text_module._attempt_youtube_markdown_once("https://www.youtube.com/@channel")
    assert payload["text"] == "A real channel page body"


def test_attempt_youtube_markdown_once_falls_back_to_transcript_after_retryable_failure(
    monkeypatch,
):
    """Verify attempt youtube markdown once falls back to transcript after retryable failure."""
    converter = RecordingFakeMarkItDownConverter(error=RuntimeError("HTTP 429 from youtube"))
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    monkeypatch.setattr(url_text_module, "_fetch_youtube_transcript_text", lambda video_id: "words")
    payload = url_text_module._attempt_youtube_markdown_once("https://youtu.be/vid1")
    assert payload["text"] == "# YouTube\n\n## YouTube video vid1\n\n### Transcript\nwords\n"
    assert payload["title"] is None


def test_attempt_youtube_markdown_once_uses_markitdown_title_for_low_quality_fallback(
    monkeypatch,
):
    """Verify attempt youtube markdown once uses markitdown title for low quality fallback."""
    converter = RecordingFakeMarkItDownConverter(
        result=FakeMarkItDownResult(text_content="How YouTube works", title="Real title")
    )
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    monkeypatch.setattr(url_text_module, "_fetch_youtube_transcript_text", lambda video_id: "words")
    payload = url_text_module._attempt_youtube_markdown_once("https://youtu.be/vid1")
    assert "## Real title" in payload["text"]
    assert payload["title"] == "Real title"


def test_attempt_youtube_markdown_once_wraps_non_retryable_markitdown_failure(monkeypatch):
    """Verify attempt youtube markdown once wraps non retryable markitdown failure."""
    converter = RecordingFakeMarkItDownConverter(error=ValueError("bad argument"))
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._attempt_youtube_markdown_once("https://youtu.be/vid1")
    assert captured.value.code == "direct_conversion_failed"
    assert captured.value.details["video_id"] == "vid1"


def test_attempt_youtube_markdown_once_raises_when_no_transcript_is_available(monkeypatch):
    """Verify attempt youtube markdown once raises when no transcript is available."""
    converter = RecordingFakeMarkItDownConverter(result=FakeMarkItDownResult(text_content=""))
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    monkeypatch.setattr(url_text_module, "_fetch_youtube_transcript_text", lambda video_id: "")
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._attempt_youtube_markdown_once("https://youtu.be/vid1")
    assert captured.value.code == "youtube_transcript_unavailable"


def test_attempt_youtube_markdown_once_raises_for_low_quality_page_without_video_id(monkeypatch):
    """Verify attempt youtube markdown once raises for low quality page without video id."""
    converter = RecordingFakeMarkItDownConverter(result=FakeMarkItDownResult(text_content=""))
    monkeypatch.setattr(url_text_module, "_build_markitdown_converter", lambda: converter)
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._attempt_youtube_markdown_once("https://www.youtube.com/@channel")
    assert captured.value.details["video_id"] is None


def configure_fast_youtube_retry_environment(monkeypatch, *, max_wait_seconds):
    """Support tests with the configure fast youtube retry environment helper."""
    monkeypatch.setenv(url_text_module.YOUTUBE_TRANSCRIPT_MAX_WAIT_ENV, str(max_wait_seconds))
    monkeypatch.setenv(url_text_module.YOUTUBE_TRANSCRIPT_INITIAL_BACKOFF_ENV, "1")
    monkeypatch.setenv(url_text_module.YOUTUBE_TRANSCRIPT_MAX_BACKOFF_ENV, "3")
    monkeypatch.setattr(url_text_module.random, "random", lambda: 0.5)


def test_convert_youtube_markdown_records_markitdown_method_on_first_success(monkeypatch):
    """Verify convert youtube markdown records markitdown method on first success."""
    configure_fast_youtube_retry_environment(monkeypatch, max_wait_seconds=10)
    monkeypatch.setattr(
        url_text_module,
        "_attempt_youtube_markdown_once",
        lambda uri, prefer_transcript_api: {"text": "video"},
    )
    payload = url_text_module._convert_youtube_markdown("https://youtu.be/vid1")
    retry = payload["youtube_transcript_retry"]
    assert retry["attempt_count"] == 1
    assert retry["attempts"][0]["method"] == "markitdown"
    assert retry["max_wait_seconds"] == 10.0


def test_convert_youtube_markdown_caps_backoff_and_switches_to_transcript_api(monkeypatch):
    """Verify convert youtube markdown caps backoff and switches to transcript api."""
    configure_fast_youtube_retry_environment(monkeypatch, max_wait_seconds=1000)
    outcomes = [
        UrlTextExtractionError(code="direct_conversion_empty", message="empty"),
        UrlTextExtractionError(code="youtube_transcript_unavailable", message="nope"),
        UrlTextExtractionError(code="youtube_transcript_unavailable", message="nope"),
        {"text": "video"},
    ]
    prefer_flags = []

    def fake_attempt_youtube_markdown_once(uri, prefer_transcript_api):
        prefer_flags.append(prefer_transcript_api)
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    recorded_sleeps = []
    monkeypatch.setattr(
        url_text_module, "_attempt_youtube_markdown_once", fake_attempt_youtube_markdown_once
    )
    monkeypatch.setattr(url_text_module.time, "sleep", recorded_sleeps.append)
    payload = url_text_module._convert_youtube_markdown("https://youtu.be/vid1")
    assert prefer_flags == [False, True, True, True]
    assert recorded_sleeps == [1.0, 2.0, 3.0]
    assert payload["youtube_transcript_retry"]["attempts"][-1]["method"] == (
        "youtube-transcript-api"
    )
    assert payload["youtube_transcript_retry"]["attempts"][0]["sleep_seconds"] == 1.0


def test_convert_youtube_markdown_raises_after_retry_budget_is_exhausted(monkeypatch):
    """Verify convert youtube markdown raises after retry budget is exhausted."""
    configure_fast_youtube_retry_environment(monkeypatch, max_wait_seconds=5)
    monotonic_values = iter([100.0, 100.0, 100.0, 100.0, 200.0, 200.0, 200.0])
    monkeypatch.setattr(url_text_module.time, "monotonic", lambda: next(monotonic_values))

    def raise_unavailable(uri, prefer_transcript_api):
        raise UrlTextExtractionError(
            code="youtube_transcript_unavailable",
            message="no captions",
            details={"video_id": "vid1"},
        )

    monkeypatch.setattr(url_text_module, "_attempt_youtube_markdown_once", raise_unavailable)
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._convert_youtube_markdown("https://youtu.be/vid1")
    assert captured.value.code == "youtube_transcript_unavailable"
    assert "exhausted YouTube retry budget after 100.0s" in captured.value.message
    assert captured.value.details["video_id"] == "vid1"
    assert captured.value.details["youtube_transcript_retry"]["attempt_count"] == 1


def install_fake_grobid_dependencies(monkeypatch, *, ensure_behavior=None):
    """Support tests with the install fake grobid dependencies helper."""

    def default_ensure_grobid_running(base_url):
        return base_url

    monkeypatch.setattr(
        grobid_runtime_module, "resolve_grobid_base_url", lambda: "http://grobid.test:8070"
    )
    monkeypatch.setattr(
        grobid_runtime_module,
        "ensure_grobid_running",
        ensure_behavior or default_ensure_grobid_running,
    )
    monkeypatch.setattr(
        grobid_client_module, "call_grobid_with_limits", lambda operation: operation()
    )


def test_convert_pdf_with_grobid_reports_unreachable_runtime(monkeypatch):
    """Verify convert pdf with grobid reports unreachable runtime."""

    def raise_runtime_error(base_url):
        raise RuntimeError("docker unavailable")

    install_fake_grobid_dependencies(monkeypatch, ensure_behavior=raise_runtime_error)
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._convert_pdf_with_grobid(
            data=b"%PDF", source_uri="https://example.test/a.pdf", content_type=None
        )
    assert captured.value.code == "grobid_unreachable"
    assert captured.value.message == "docker unavailable"


def test_convert_pdf_with_grobid_posts_multipart_and_parses_tei(monkeypatch):
    """Verify convert pdf with grobid posts multipart and parses tei."""
    install_fake_grobid_dependencies(monkeypatch)
    tei_document = wrap_tei_document(
        "<teiHeader><fileDesc><titleStmt><title>Paper</title></titleStmt></fileDesc></teiHeader>"
        "<text><body><div><head>Intro</head><p>Body text.</p></div></body></text>"
    )
    fake_urlopen, recorded_requests = build_sequential_urlopen_fake(
        [FakeUrlopenResponse(body=tei_document.encode("utf-8"), content_type="application/xml")]
    )
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    payload = url_text_module._convert_pdf_with_grobid(
        data=b"%PDF-bytes", source_uri="https://example.test/a.pdf", content_type=None
    )
    assert payload["text"] == "# Paper\n\n## Intro\n\nBody text."
    assert payload["title"] == "Paper"
    assert payload["content_type"] == "application/pdf"
    assert payload["method"] == "grobid"
    assert payload["grobid"] == {
        "base_url": "http://grobid.test:8070",
        "endpoint": "http://grobid.test:8070/api/processFulltextDocument",
    }
    sent_request, sent_timeout = recorded_requests[0]
    assert sent_timeout == url_text_module.URL_TEXT_GROBID_TIMEOUT_SECONDS
    assert sent_request.get_method() == "POST"
    assert b"%PDF-bytes" in sent_request.data
    assert b'name="consolidateHeader"' in sent_request.data


def test_convert_pdf_with_grobid_preserves_supplied_content_type(monkeypatch):
    """Verify convert pdf with grobid preserves supplied content type."""
    install_fake_grobid_dependencies(monkeypatch)
    fake_urlopen, _ = build_sequential_urlopen_fake(
        [FakeUrlopenResponse(body=b"", content_type="application/xml")]
    )
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    payload = url_text_module._convert_pdf_with_grobid(
        data=b"%PDF", source_uri="https://example.test/a.pdf", content_type="application/x-pdf"
    )
    assert payload["content_type"] == "application/x-pdf"
    assert payload["structured"]["warnings"][0]["code"] == "empty_tei_xml"


@pytest.mark.parametrize(
    ("raised_exception", "expected_code"),
    [
        (build_http_error(503), "grobid_http_error"),
        (OSError("socket closed"), "grobid_request_failed"),
        (UrlTextExtractionError(code="custom_grobid", message="custom"), "custom_grobid"),
    ],
)
def test_convert_pdf_with_grobid_maps_request_failures(
    monkeypatch, raised_exception, expected_code
):
    """Verify convert pdf with grobid maps request failures."""
    install_fake_grobid_dependencies(monkeypatch)
    fake_urlopen, _ = build_sequential_urlopen_fake([raised_exception])
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._convert_pdf_with_grobid(
            data=b"%PDF", source_uri="https://example.test/a.pdf", content_type=None
        )
    assert captured.value.code == expected_code


def test_convert_pdf_with_grobid_includes_http_status_in_error_details(monkeypatch):
    """Verify convert pdf with grobid includes http status in error details."""
    install_fake_grobid_dependencies(monkeypatch)
    fake_urlopen, _ = build_sequential_urlopen_fake([build_http_error(500)])
    monkeypatch.setattr(url_text_module, "urlopen", fake_urlopen)
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._convert_pdf_with_grobid(
            data=b"%PDF", source_uri="https://example.test/a.pdf", content_type=None
        )
    assert captured.value.details == {
        "source_uri": "https://example.test/a.pdf",
        "http_status": 500,
    }


def test_tei_to_structured_text_reports_empty_tei_xml():
    """Verify tei to structured text reports empty tei xml."""
    text, title, structured = url_text_module._tei_to_structured_text("   ")
    assert text == ""
    assert title is None
    assert structured["warnings"] == [
        {"code": "empty_tei_xml", "message": "GROBID returned empty TEI XML."}
    ]


def test_tei_to_structured_text_assembles_full_document_with_authors_and_citations():
    """Verify tei to structured text assembles full document with authors and citations."""
    tei_document = wrap_tei_document(
        "<teiHeader>"
        "<fileDesc>"
        "<titleStmt><title>  Deep   Paper </title></titleStmt>"
        "<sourceDesc><biblStruct><analytic>"
        "<author><persName><forename>Ada</forename> <surname>Lovelace</surname></persName>"
        '<idno type="ORCID">https://orcid.org/0000-0002-1825-009x</idno>'
        "<email>ada@example.test</email>"
        "<affiliation><orgName>Analytical Society</orgName></affiliation>"
        "<affiliation><orgName>analytical society</orgName></affiliation>"
        "<affiliation> </affiliation>"
        "</author>"
        "<author><persName><forename>Ada</forename> <surname>Lovelace</surname></persName>"
        '<idno type="ORCID">0000-0002-1825-009X</idno>'
        "</author>"
        "<author>1 Charles Babbage</author>"
        "<author> </author>"
        "<author><persName> </persName>,;</author>"
        "</analytic></biblStruct></sourceDesc>"
        "</fileDesc>"
        "<profileDesc><abstract>An abstract.</abstract></profileDesc>"
        "</teiHeader>"
        "<text><body>"
        "<div><head>Introduction</head><p>First paragraph.</p><p> </p></div>"
        "<div><head>Results</head></div>"
        "<div><head>Notes</head>Inline note text</div>"
        "<div>Loose text only</div>"
        "</body>"
        "<back><listBibl>"
        "<biblStruct>"
        "<analytic><title>Cited Work</title>"
        "<author><persName>Grace Hopper</persName></author>"
        "<author><persName>grace hopper</persName></author>"
        "<author> </author>"
        "<author>Alan Turing</author>"
        "</analytic>"
        '<monogr><title>Journal of Tests</title><imprint><date when="2019-03-01"/></imprint>'
        "</monogr>"
        '<idno type="DOI">doi:10.1234/abc.def</idno>'
        '<idno type="arXiv">arXiv:2101.12345v2</idno>'
        '<idno type="ISBN">978-3-16-148410-0</idno>'
        '<ptr target="https://example.test/cited"/>'
        "</biblStruct>"
        "<biblStruct>"
        "<monogr><title>Book Only</title><imprint><date>circa 1998</date></imprint></monogr>"
        "<idno>10.5555/fallback</idno>"
        '<ptr target="ftp://ignored"/>'
        '<ref target="http://example.test/ref-target">link</ref>'
        "</biblStruct>"
        "<biblStruct>"
        "<series><title>Series Title</title></series>"
        '<ref target="mailto:x">https://example.test/ref-text</ref>'
        "<date>undated</date>"
        "</biblStruct>"
        "<biblStruct>"
        '<ref target="none">plain text reference</ref>'
        "</biblStruct>"
        "<biblStruct></biblStruct>"
        "</listBibl></back>"
        "</text>"
    )
    text, title, structured = url_text_module._tei_to_structured_text(tei_document)
    assert title == "Deep Paper"
    assert text.split("\n\n") == [
        "# Deep Paper",
        "## Abstract",
        "An abstract.",
        "## Introduction",
        "First paragraph.",
        "## Results",
        "## Notes",
        "NotesInline note text",
        "Loose text only",
    ]
    authors = structured["authors"]
    assert [author["name"] for author in authors] == ["Ada Lovelace", "Charles Babbage"]
    assert authors[0]["orcid"] == "0000-0002-1825-009X"
    assert authors[0]["email"] == "ada@example.test"
    assert authors[0]["affiliation"] == "Analytical Society"
    assert authors[1]["orcid"] is None
    assert authors[1]["email"] is None
    assert authors[1]["affiliation"] is None
    assert [warning["code"] for warning in structured["warnings"]] == [
        "author_name_missing",
        "author_name_missing",
        "citation_unusable",
    ]
    citations = structured["citations"]
    assert len(citations) == 4
    assert citations[0] == {
        "title": "Cited Work",
        "authors": ["Grace Hopper", "Alan Turing"],
        "year": 2019,
        "venue": "Journal of Tests",
        "doi": "10.1234/abc.def",
        "arxiv_id": "2101.12345v2",
        "isbn": "978-3-16-148410-0",
        "url": "https://example.test/cited",
        "raw": citations[0]["raw"],
    }
    assert citations[1]["title"] == "Book Only"
    assert citations[1]["year"] == 1998
    assert citations[1]["doi"] == "10.5555/fallback"
    assert citations[1]["url"] == "http://example.test/ref-target"
    assert citations[2]["title"] is None
    assert citations[2]["venue"] == "Series Title"
    assert citations[2]["url"] == "https://example.test/ref-text"
    assert citations[2]["year"] is None
    assert citations[3]["url"] is None
    assert citations[3]["raw"] == "plain text reference"
    assert structured["summary"] == {
        "authors_count": 2,
        "citations_count": 4,
        "citations_with_identifiers": 2,
    }


def test_tei_to_structured_text_uses_title_statement_authors_and_reports_missing_citations():
    """Verify tei to structured text uses title statement authors and reports missing citations."""
    tei_document = wrap_tei_document(
        "<teiHeader><fileDesc><titleStmt>"
        "<author>Solo Author</author>"
        "</titleStmt></fileDesc></teiHeader>"
    )
    text, title, structured = url_text_module._tei_to_structured_text(tei_document)
    assert text == ""
    assert title is None
    assert [author["name"] for author in structured["authors"]] == ["Solo Author"]
    assert structured["warnings"] == [
        {
            "code": "citations_missing",
            "message": "No TEI bibliography entries were present in the GROBID output.",
        }
    ]


def test_first_non_empty_prefers_typed_values_then_falls_back_then_returns_empty():
    """Verify first non empty prefers typed values then falls back then returns empty."""
    preferred_node = url_text_module.ET.fromstring('<idno type="DOI">preferred</idno>')
    fallback_node = url_text_module.ET.fromstring('<idno type="other">fallback</idno>')
    empty_node = url_text_module.ET.fromstring('<idno type="DOI"> </idno>')
    assert url_text_module._first_non_empty([fallback_node, preferred_node], {"DOI"}) == "preferred"
    assert url_text_module._first_non_empty([empty_node, fallback_node], {"DOI"}) == "fallback"
    assert url_text_module._first_non_empty([empty_node], {"DOI"}) == ""


def test_identifier_normalizers_handle_empty_unmatched_and_matched_values():
    """Verify identifier normalizers handle empty unmatched and matched values."""
    assert url_text_module._normalize_orcid("") == ""
    assert url_text_module._normalize_orcid("not an orcid") == "not an orcid"
    assert url_text_module._normalize_doi("") == ""
    assert url_text_module._normalize_doi("no doi here") == ""
    assert url_text_module._normalize_arxiv_id("") == ""
    assert url_text_module._normalize_arxiv_id("no arxiv here") == ""
    assert url_text_module._normalize_arxiv_id("arXiv:1706.03762") == "1706.03762"
    assert url_text_module._normalize_person_name("   ") == ""
    assert url_text_module._normalize_person_name("12 Jane Doe ,;") == "Jane Doe"


def test_dedupe_author_rows_drops_rows_without_identity_and_duplicates():
    """Verify dedupe author rows drops rows without identity and duplicates."""
    rows = [
        {"orcid": None, "normalized_name": ""},
        {"orcid": "0000-0000-0000-0001", "normalized_name": "a"},
        {"orcid": "0000-0000-0000-0001", "normalized_name": "b"},
        {"orcid": None, "normalized_name": "c"},
    ]
    assert url_text_module._dedupe_author_rows(rows) == [rows[1], rows[3]]


def test_multipart_form_data_encodes_fields_and_files():
    """Verify multipart form data encodes fields and files."""
    body = url_text_module._multipart_form_data(
        fields={"alpha": "1"},
        files={"input": ("doc.pdf", b"PDFDATA", "application/pdf")},
        boundary="BOUNDARY",
    )
    assert body == (
        b"--BOUNDARY\r\n"
        b'Content-Disposition: form-data; name="alpha"\r\n\r\n'
        b"1\r\n"
        b"--BOUNDARY\r\n"
        b'Content-Disposition: form-data; name="input"; filename="doc.pdf"\r\n'
        b"Content-Type: application/pdf\r\n\r\n"
        b"PDFDATA\r\n"
        b"--BOUNDARY--\r\n"
    )


def test_build_markitdown_converter_reports_missing_dependency(monkeypatch):
    """Verify build markitdown converter reports missing dependency."""
    monkeypatch.setitem(sys.modules, "markitdown", None)
    with pytest.raises(UrlTextExtractionError) as captured:
        url_text_module._build_markitdown_converter()
    assert captured.value.code == "missing_markitdown_dependency"


def test_build_markitdown_converter_enables_plugins(monkeypatch):
    """Verify build markitdown converter enables plugins."""
    constructor_calls = []

    class FakeMarkItDown:
        def __init__(self, **kwargs):
            constructor_calls.append(kwargs)

    fake_module = types.ModuleType("markitdown")
    fake_module.MarkItDown = FakeMarkItDown
    monkeypatch.setitem(sys.modules, "markitdown", fake_module)
    converter = url_text_module._build_markitdown_converter()
    assert isinstance(converter, FakeMarkItDown)
    assert constructor_calls == [{"enable_plugins": True}]


@pytest.mark.parametrize(
    ("fetch_result", "expected_html"),
    [
        ({"content_type": "text/plain", "body": b"plain"}, ""),
        ({"content_type": "text/html", "body": "not bytes"}, ""),
        ({"content_type": "application/xhtml+xml", "body": bytearray(b"<p>x</p>")}, "<p>x</p>"),
        ({"content_type": "text/html", "body": b"caf\xe9"}, "café"),
    ],
)
def test_html_body_from_fetch_decodes_only_html_bytes(fetch_result, expected_html):
    """Verify html body from fetch decodes only html bytes."""
    assert url_text_module._html_body_from_fetch(fetch_result) == expected_html


@pytest.mark.parametrize(
    ("raw_content_type", "expected_content_type"),
    [(None, None), ("  ", None), (";charset=utf-8", None), ("TEXT/HTML; x=1", "text/html")],
)
def test_normalize_content_type_lowercases_and_strips_parameters(
    raw_content_type, expected_content_type
):
    """Verify normalize content type lowercases and strips parameters."""
    assert url_text_module._normalize_content_type(raw_content_type) == expected_content_type


@pytest.mark.parametrize(
    ("source_uri", "content_type", "expected_extension"),
    [
        ("https://example.test/a", "application/pdf", ".pdf"),
        ("https://example.test/a", "text/markdown", ".md"),
        ("https://example.test/a", "text/x-markdown", ".md"),
        ("https://example.test/a", "text/plain", ".txt"),
        ("https://example.test/a", "application/xhtml+xml", ".html"),
        ("https://example.test/a.PDF", None, ".pdf"),
        ("https://example.test/a.md", "application/octet-stream", ".md"),
        ("https://example.test/a.markdown", None, ".md"),
        ("https://example.test/a.txt", None, ".txt"),
        ("https://example.test/a", None, ".html"),
    ],
)
def test_infer_file_extension_uses_content_type_then_path(
    source_uri, content_type, expected_extension
):
    """Verify infer file extension uses content type then path."""
    assert (
        url_text_module._infer_file_extension(source_uri=source_uri, content_type=content_type)
        == expected_extension
    )


@pytest.mark.parametrize(
    ("status_code", "expected_retryable"),
    [(408, True), (429, True), (503, True), (404, False), (400, False)],
)
def test_is_retryable_http_status_matches_transient_codes(status_code, expected_retryable):
    """Verify is retryable http status matches transient codes."""
    assert url_text_module._is_retryable_http_status(status_code) is expected_retryable
