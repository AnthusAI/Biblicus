from __future__ import annotations

import json

from biblicus import cli
from biblicus import url_text as url_text_module


def test_extract_url_text_web_markdown_first_success(monkeypatch):
    call_steps = []

    def fake_fetch_url_bytes(**kwargs):
        call_steps.append(kwargs["step"])
        return {
            "ok": True,
            "body": b"# markdown body",
            "content_type": "text/markdown",
            "final_url": kwargs["uri"],
            "attempts": [{"step": kwargs["step"], "result": "ok"}],
            "error": None,
        }

    monkeypatch.setattr(url_text_module, "_fetch_url_bytes", fake_fetch_url_bytes)
    monkeypatch.setattr(
        url_text_module,
        "_convert_bytes_with_markitdown",
        lambda **kwargs: {
            "text": "Extracted markdown text",
            "markdown": "# Extracted markdown text",
            "title": "Markdown title",
            "content_type": kwargs.get("content_type"),
        },
    )
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("direct should not run")),
    )

    result = url_text_module.extract_url_text(source_uri="https://example.test/article")

    assert result["status"] == "ok"
    assert result["source_kind"] == "web"
    assert result["text"] == "Extracted markdown text"
    assert call_steps == ["web_markdown_fetch"]


def test_extract_url_text_web_falls_back_to_html(monkeypatch):
    call_steps = []

    def fake_fetch_url_bytes(**kwargs):
        call_steps.append(kwargs["step"])
        if kwargs["step"] == "web_markdown_fetch":
            return {
                "ok": False,
                "body": b"",
                "content_type": None,
                "final_url": kwargs["uri"],
                "attempts": [{"step": kwargs["step"], "result": "failed"}],
                "error": {"code": "manual_fetch_failed", "message": "no markdown"},
            }
        return {
            "ok": True,
            "body": b"<html><body>html fallback</body></html>",
            "content_type": "text/html",
            "final_url": kwargs["uri"],
            "attempts": [{"step": kwargs["step"], "result": "ok"}],
            "error": None,
        }

    monkeypatch.setattr(url_text_module, "_fetch_url_bytes", fake_fetch_url_bytes)
    monkeypatch.setattr(
        url_text_module,
        "_convert_bytes_with_markitdown",
        lambda **kwargs: {
            "text": "Extracted from html",
            "markdown": "Extracted from html",
            "title": None,
            "content_type": kwargs.get("content_type"),
        },
    )
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("direct should not run")),
    )

    result = url_text_module.extract_url_text(source_uri="https://example.test/article")

    assert result["status"] == "ok"
    assert result["text"] == "Extracted from html"
    assert call_steps == ["web_markdown_fetch", "web_html_fetch"]


def test_extract_url_text_pdf_uses_grobid_only(monkeypatch):
    call_steps = []

    def fake_fetch_url_bytes(**kwargs):
        call_steps.append(kwargs["step"])
        return {
            "ok": True,
            "body": b"%PDF-fake",
            "content_type": "application/pdf",
            "final_url": kwargs["uri"],
            "attempts": [{"step": kwargs["step"], "result": "ok"}],
            "error": None,
        }

    monkeypatch.setattr(url_text_module, "_fetch_url_bytes", fake_fetch_url_bytes)
    monkeypatch.setattr(
        url_text_module,
        "_convert_pdf_with_grobid",
        lambda **kwargs: {
            "text": "Extracted PDF text",
            "markdown": "Extracted PDF text",
            "title": "PDF title",
            "content_type": kwargs.get("content_type"),
            "structured": {
                "authors": [{"name": "Ada Lovelace", "normalized_name": "ada lovelace"}],
                "citations": [{"title": "Prior work"}],
                "summary": {"authors_count": 1, "citations_count": 1, "citations_with_identifiers": 0},
                "warnings": [],
            },
        },
    )
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("direct should not run")),
    )
    result = url_text_module.extract_url_text(source_uri="https://example.test/report.pdf")

    assert result["status"] == "ok"
    assert result["source_kind"] == "pdf"
    assert result["text"] == "Extracted PDF text"
    assert result["structured"]["summary"]["citations_count"] == 1
    assert call_steps == ["pdf_fetch"]


def test_extract_url_text_pdf_returns_structured_error_when_grobid_fails(monkeypatch):
    monkeypatch.setattr(
        url_text_module,
        "_fetch_url_bytes",
        lambda **kwargs: {
            "ok": True,
            "body": b"%PDF-fake",
            "content_type": "application/pdf",
            "final_url": kwargs["uri"],
            "attempts": [{"step": kwargs["step"], "result": "ok"}],
            "error": None,
        },
    )
    monkeypatch.setattr(
        url_text_module,
        "_convert_pdf_with_grobid",
        lambda **_kwargs: (_ for _ in ()).throw(url_text_module.UrlTextExtractionError(code="grobid_unreachable", message="down")),
    )

    result = url_text_module.extract_url_text(source_uri="https://example.test/report.pdf")

    assert result["status"] == "failed"
    assert result["error"]["code"] == "grobid_unreachable"


def test_tei_to_structured_text_extracts_authors_and_citations():
    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <teiHeader>
        <fileDesc>
          <titleStmt><title>Example Paper</title></titleStmt>
          <sourceDesc>
            <biblStruct>
              <analytic>
                <author>
                  <persName><forename>Ada</forename><surname>Lovelace</surname></persName>
                  <idno type="ORCID">0000-0001-2345-6789</idno>
                  <email>ada@example.org</email>
                </author>
              </analytic>
            </biblStruct>
          </sourceDesc>
        </fileDesc>
      </teiHeader>
      <text>
        <body>
          <div><head>Introduction</head><p>Hello world.</p></div>
        </body>
        <back>
          <listBibl>
            <biblStruct>
              <analytic>
                <title>Prior Citation</title>
                <author><persName><forename>Alan</forename><surname>Turing</surname></persName></author>
              </analytic>
              <monogr>
                <title>Journal X</title>
                <imprint><date when="2024"/></imprint>
              </monogr>
              <idno type="DOI">10.1000/xyz123</idno>
            </biblStruct>
          </listBibl>
        </back>
      </text>
    </TEI>
    """
    text, title, structured = url_text_module._tei_to_structured_text(tei)
    assert title == "Example Paper"
    assert "Hello world." in text
    assert structured["summary"]["authors_count"] == 1
    assert structured["summary"]["citations_count"] == 1
    assert structured["authors"][0]["orcid"] == "0000-0001-2345-6789"
    assert structured["citations"][0]["doi"] == "10.1000/xyz123"


def test_tei_to_structured_text_handles_malformed_xml_with_bounded_warning():
    text, title, structured = url_text_module._tei_to_structured_text("<TEI><broken")
    assert text == ""
    assert title is None
    assert isinstance(structured["warnings"], list)
    assert structured["warnings"][0]["code"] == "tei_parse_failed"


def test_canonicalize_youtube_watch_url_supports_short_links():
    assert (
        url_text_module._canonicalize_youtube_watch_url("https://youtu.be/jGwO_UgTS7I")
        == "https://www.youtube.com/watch?v=jGwO_UgTS7I"
    )


def test_canonicalize_youtube_watch_url_strips_timestamp_query():
    assert (
        url_text_module._canonicalize_youtube_watch_url(
            "https://www.youtube.com/watch?v=wE1ZgJdt4uM&t=1935s"
        )
        == "https://www.youtube.com/watch?v=wE1ZgJdt4uM"
    )


def test_convert_youtube_markdown_falls_back_to_transcript_api(monkeypatch):
    monkeypatch.setattr(
        url_text_module,
        "_attempt_youtube_markdown_once",
        lambda _uri, **_kwargs: {
            "text": "# YouTube\n\n## Title\n\n### Transcript\nfallback transcript text\n",
            "markdown": "# YouTube\n\n## Title\n\n### Transcript\nfallback transcript text\n",
            "title": "Title",
            "content_type": None,
        },
    )

    payload = url_text_module._convert_youtube_markdown("https://youtu.be/abc123")

    assert "fallback transcript text" in payload["text"]
    assert "### Transcript" in payload["markdown"]


def test_convert_youtube_markdown_retries_with_backoff(monkeypatch):
    calls = {"count": 0}

    def fake_once(_uri: str, **_kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise url_text_module.UrlTextExtractionError(
                code="youtube_transcript_unavailable",
                message="429 Too Many Requests",
                details={"error": "429"},
            )
        return {
            "text": "# YouTube\n\n## Title\n\n### Transcript\nhello after retry\n",
            "markdown": "# YouTube\n\n## Title\n\n### Transcript\nhello after retry\n",
            "title": "Title",
            "content_type": None,
        }

    sleeps: list[float] = []
    monkeypatch.setattr(url_text_module, "_attempt_youtube_markdown_once", fake_once)
    monkeypatch.setattr(
        url_text_module,
        "_youtube_transcript_retry_settings",
        lambda: {
            "max_wait_seconds": 300.0,
            "initial_backoff_seconds": 0.01,
            "max_backoff_seconds": 0.05,
        },
    )
    monkeypatch.setattr(url_text_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    payload = url_text_module._convert_youtube_markdown("https://www.youtube.com/watch?v=abc123")

    assert calls["count"] == 3
    assert len(sleeps) == 2
    assert "hello after retry" in payload["text"]
    assert payload["youtube_transcript_retry"]["attempt_count"] == 3


def test_extract_url_text_youtube_uses_direct_only(monkeypatch):
    monkeypatch.setattr(
        url_text_module,
        "_fetch_url_bytes",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("manual fetch should not run for youtube")),
    )
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda *_args, **_kwargs: {
            "text": "YouTube transcript",
            "markdown": "YouTube transcript",
            "title": "Video title",
            "content_type": None,
        },
    )

    result = url_text_module.extract_url_text(source_uri="https://www.youtube.com/watch?v=abc")

    assert result["status"] == "ok"
    assert result["source_kind"] == "youtube"
    assert result["text"] == "YouTube transcript"


def test_extract_url_text_returns_structured_error_when_all_paths_fail(monkeypatch):
    def fake_fetch_url_bytes(**kwargs):
        return {
            "ok": False,
            "body": b"",
            "content_type": None,
            "final_url": kwargs["uri"],
            "attempts": [{"step": kwargs["step"], "result": "failed"}],
            "error": {"code": "manual_fetch_failed", "message": "blocked"},
        }

    monkeypatch.setattr(url_text_module, "_fetch_url_bytes", fake_fetch_url_bytes)
    monkeypatch.setattr(
        url_text_module,
        "_convert_direct_with_markitdown",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("direct blocked")),
    )

    result = url_text_module.extract_url_text(source_uri="https://example.test/article")

    assert result["status"] == "failed"
    assert result["error"]["code"] == "direct_conversion_failed"
    assert isinstance(result["attempts"], list)
    assert result["attempts"]


def test_cli_extract_url_text_outputs_json_contract(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"source_uri": "https://example.test/article"}), encoding="utf-8")

    captured = {}

    def fake_extract_url_text(**kwargs):
        captured.update(kwargs)
        return {
            "status": "ok",
            "source_kind": "web",
            "strategy": "markdown-then-html-then-direct",
            "text": "Extracted text",
            "markdown": "Extracted text",
            "title": "Example",
            "content_type": "text/html",
            "prompt_version": "url-text-v1",
            "attempts": [{"step": "web_markdown_fetch", "result": "ok"}],
            "error": None,
        }

    monkeypatch.setattr(url_text_module, "extract_url_text", fake_extract_url_text)

    exit_code = cli.main([
        "extract",
        "url-text",
        "--input-json",
        str(input_path),
        "--format",
        "json",
    ])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert captured["source_uri"] == "https://example.test/article"


def test_cli_extract_url_text_rejects_missing_source_uri(tmp_path, capsys):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"reference_title": "Missing URI"}), encoding="utf-8")

    exit_code = cli.main([
        "extract",
        "url-text",
        "--input-json",
        str(input_path),
        "--format",
        "json",
    ])

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "missing_source_uri"


def test_cli_extract_url_text_rejects_malformed_json(tmp_path, capsys):
    input_path = tmp_path / "bad.json"
    input_path.write_text("{not-json", encoding="utf-8")

    exit_code = cli.main([
        "extract",
        "url-text",
        "--input-json",
        str(input_path),
        "--format",
        "json",
    ])

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "invalid_input_json"
