"""Coverage tests for the web extraction command-line interface commands."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace

import pytest

from biblicus import cli, url_text, web_reference_metadata
from biblicus.models import ExtractionSnapshotReference


def _write_input_json(tmp_path, payload):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    return str(input_path)


def _read_json_stream(stream_text):
    return json.loads(stream_text)


def _url_text_payload(status):
    return {
        "status": status,
        "source_kind": "web",
        "strategy": "markdown-then-html-then-direct",
        "text": "page text",
        "markdown": "page text",
        "title": None,
        "content_type": None,
        "prompt_version": "url-text-v1",
        "attempts": [],
        "error": None,
    }


def _metadata_payload(title, warnings=None):
    payload = web_reference_metadata._empty_payload(
        source_uri="https://fixture.test/page", method="html-heuristics"
    )
    payload["title"] = title
    payload["warnings"] = warnings or []
    return payload


def test_extract_url_text_reports_invalid_input_json(tmp_path, capsys):
    """Verify that extract url text reports invalid input json."""
    input_path = tmp_path / "broken.json"
    input_path.write_text("{not json", encoding="utf-8")
    exit_code = cli.main(["extract", "url-text", "--input-json", str(input_path)])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert _read_json_stream(captured.err)["error"]["code"] == "invalid_input_json"


def test_extract_url_text_requires_source_uri(tmp_path, capsys):
    """Verify that extract url text requires source uri."""
    exit_code = cli.main(
        ["extract", "url-text", "--input-json", _write_input_json(tmp_path, {"source_uri": " "})]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert _read_json_stream(captured.err)["error"] == {
        "code": "missing_source_uri",
        "message": "source_uri is required",
    }


@pytest.mark.parametrize(("status", "expected_exit_code"), [("ok", 0), ("failed", 1)])
def test_extract_url_text_prints_output_and_maps_status_to_exit_code(
    monkeypatch, tmp_path, capsys, status, expected_exit_code
):
    """Verify that extract url text prints output and maps status to exit code."""
    recorded_calls = []

    def fake_extract_url_text(**keyword_arguments):
        recorded_calls.append(keyword_arguments)
        return _url_text_payload(status)

    monkeypatch.setattr(url_text, "extract_url_text", fake_extract_url_text)
    exit_code = cli.main(
        [
            "extract",
            "url-text",
            "--input-json",
            _write_input_json(
                tmp_path,
                {
                    "source_uri": " https://fixture.test/page ",
                    "reference_title": "Reference",
                    "timeout_seconds": 7,
                },
            ),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == expected_exit_code
    assert _read_json_stream(captured.out) == _url_text_payload(status)
    assert recorded_calls == [
        {
            "source_uri": "https://fixture.test/page",
            "reference_title": "Reference",
            "timeout_seconds": 7.0,
        }
    ]


def test_extract_url_text_uses_default_timeout_and_reports_extraction_error(
    monkeypatch, tmp_path, capsys
):
    """Verify that extract url text uses default timeout and reports extraction error."""
    recorded_calls = []

    def failing_extract_url_text(**keyword_arguments):
        recorded_calls.append(keyword_arguments)
        raise url_text.UrlTextExtractionError(code="fetch_failed", message="unreachable")

    monkeypatch.setattr(url_text, "extract_url_text", failing_extract_url_text)
    exit_code = cli.main(
        [
            "extract",
            "url-text",
            "--input-json",
            _write_input_json(tmp_path, {"source_uri": "https://fixture.test/page"}),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    error_payload = _read_json_stream(captured.err)
    assert error_payload["status"] == "failed"
    assert error_payload["error"]["code"] == "fetch_failed"
    assert recorded_calls[0]["reference_title"] == ""
    assert recorded_calls[0]["timeout_seconds"] == url_text.URL_TEXT_DEFAULT_TIMEOUT_SECONDS


def test_extract_web_metadata_reports_invalid_input_json_from_standard_input(monkeypatch, capsys):
    """Verify that extract web metadata reports invalid input json from standard input."""
    monkeypatch.setattr("sys.stdin", io.StringIO("[1, 2, 3]"))
    exit_code = cli.main(["extract", "web-metadata"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert _read_json_stream(captured.err) == {
        "status": "failed",
        "error": {"code": "invalid_input_json", "message": "Input JSON must be an object"},
    }


def test_extract_web_metadata_requires_source_uri_or_html(tmp_path, capsys):
    """Verify that extract web metadata requires source uri or html."""
    exit_code = cli.main(
        ["extract", "web-metadata", "--input-json", _write_input_json(tmp_path, {})]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert _read_json_stream(captured.err)["error"]["code"] == "missing_input"


def test_extract_web_metadata_from_html_content_uses_local_source_uri(
    monkeypatch, tmp_path, capsys
):
    """Verify that extract web metadata from html content uses local source uri."""
    recorded_calls = []

    def fake_extract_from_html(html, **keyword_arguments):
        recorded_calls.append((html, keyword_arguments))
        return _metadata_payload("From HTML")

    monkeypatch.setattr(
        web_reference_metadata, "extract_web_reference_metadata_from_html", fake_extract_from_html
    )
    exit_code = cli.main(
        [
            "extract",
            "web-metadata",
            "--input-json",
            _write_input_json(
                tmp_path,
                {
                    "html": "<html><title>From HTML</title></html>",
                    "use_llm_fallback": True,
                    "reference_title": "Hint",
                    "model": "test-model",
                },
            ),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert _read_json_stream(captured.out) == {**_metadata_payload("From HTML"), "status": "ok"}
    html, keyword_arguments = recorded_calls[0]
    assert html == "<html><title>From HTML</title></html>"
    assert keyword_arguments == {
        "source_uri": web_reference_metadata.LOCAL_HTML_SOURCE_URI,
        "reference_title": "Hint",
        "use_llm_fallback": True,
        "model": "test-model",
    }


def test_extract_web_metadata_from_html_content_keeps_explicit_source_uri(
    monkeypatch, tmp_path, capsys
):
    """Verify that extract web metadata from html content keeps explicit source uri."""
    recorded_source_uris = []

    def fake_extract_from_html(_html, **keyword_arguments):
        recorded_source_uris.append(keyword_arguments["source_uri"])
        return _metadata_payload("Explicit")

    monkeypatch.setattr(
        web_reference_metadata, "extract_web_reference_metadata_from_html", fake_extract_from_html
    )
    exit_code = cli.main(
        [
            "extract",
            "web-metadata",
            "--input-json",
            _write_input_json(
                tmp_path,
                {"source_uri": "https://fixture.test/x", "html_content": "<p>Body</p>"},
            ),
        ]
    )
    capsys.readouterr()
    assert exit_code == 0
    assert recorded_source_uris == ["https://fixture.test/x"]


@pytest.mark.parametrize(
    ("timeout_value", "expected_timeout_seconds"),
    [(None, url_text.URL_TEXT_DEFAULT_TIMEOUT_SECONDS), (5, 5.0)],
)
def test_extract_web_metadata_from_source_uri_fetches_page(
    monkeypatch, tmp_path, capsys, timeout_value, expected_timeout_seconds
):
    """Verify that extract web metadata from source uri fetches page."""
    recorded_calls = []

    def fake_extract_from_url(source_uri, **keyword_arguments):
        recorded_calls.append((source_uri, keyword_arguments))
        return _metadata_payload("From URL")

    monkeypatch.setattr(
        web_reference_metadata, "extract_web_reference_metadata_from_url", fake_extract_from_url
    )
    payload = {"source_uri": "https://fixture.test/page"}
    if timeout_value is not None:
        payload["timeout_seconds"] = timeout_value
    exit_code = cli.main(
        [
            "extract",
            "web-metadata",
            "--use-llm-fallback",
            "--input-json",
            _write_input_json(tmp_path, payload),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert _read_json_stream(captured.out) == {**_metadata_payload("From URL"), "status": "ok"}
    source_uri, keyword_arguments = recorded_calls[0]
    assert source_uri == "https://fixture.test/page"
    assert keyword_arguments == {
        "reference_title": "",
        "use_llm_fallback": False,
        "model": "",
        "timeout_seconds": expected_timeout_seconds,
    }


def test_extract_web_metadata_reports_extraction_value_error(monkeypatch, tmp_path, capsys):
    """Verify that extract web metadata reports extraction value error."""

    def failing_extract_from_url(_source_uri, **_keyword_arguments):
        raise ValueError("metadata extraction exploded")

    monkeypatch.setattr(
        web_reference_metadata,
        "extract_web_reference_metadata_from_url",
        failing_extract_from_url,
    )
    exit_code = cli.main(
        [
            "extract",
            "web-metadata",
            "--input-json",
            _write_input_json(tmp_path, {"source_uri": "https://fixture.test/page"}),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert _read_json_stream(captured.err) == {
        "status": "failed",
        "error": {"code": "web_metadata_failed", "message": "metadata extraction exploded"},
    }


class _FakeCorpusForSnapshotReuse:
    def __init__(self, *, latest_reference=None):
        self.latest_reference = latest_reference
        self.recorded_extract_calls = []

    def latest_extraction_snapshot_reference(self, *, extractor_id):
        assert extractor_id == "pipeline"
        return self.latest_reference

    def extract(self, *, extractor_id, config, label):
        self.recorded_extract_calls.append(
            {"extractor_id": extractor_id, "config": config, "label": label}
        )
        return SimpleNamespace(snapshot_id="built-snapshot")


def test_get_or_build_extraction_snapshot_builds_pipeline_without_recipe(tmp_path):
    """Verify that get or build extraction snapshot builds pipeline without recipe."""
    fake_corpus = _FakeCorpusForSnapshotReuse()
    reference = cli._get_or_build_extraction_snapshot(
        corpus=fake_corpus, recipe_path=tmp_path / "missing.json", analysis_label="analysis"
    )
    assert reference == ExtractionSnapshotReference(
        extractor_id="pipeline", snapshot_id="built-snapshot"
    )
    assert fake_corpus.recorded_extract_calls == [
        {"extractor_id": "pipeline", "config": {}, "label": "analysis"}
    ]


def test_get_or_build_extraction_snapshot_reads_recipe_json(tmp_path):
    """Verify that get or build extraction snapshot reads recipe json."""
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text(
        json.dumps({"extractor_id": "pass-through-text", "config": {"option": 1}}),
        encoding="utf-8",
    )
    fake_corpus = _FakeCorpusForSnapshotReuse()
    reference = cli._get_or_build_extraction_snapshot(
        corpus=fake_corpus, recipe_path=recipe_path, analysis_label="analysis"
    )
    assert reference.extractor_id == "pass-through-text"
    assert fake_corpus.recorded_extract_calls[0]["config"] == {"option": 1}


def test_get_or_build_extraction_snapshot_ignores_invalid_recipe_json(tmp_path):
    """Verify that get or build extraction snapshot ignores invalid recipe json."""
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text("{invalid", encoding="utf-8")
    fake_corpus = _FakeCorpusForSnapshotReuse()
    reference = cli._get_or_build_extraction_snapshot(
        corpus=fake_corpus, recipe_path=recipe_path, analysis_label="analysis"
    )
    assert reference.extractor_id == "pipeline"
    assert fake_corpus.recorded_extract_calls[0]["config"] == {}
