"""Offline executable contracts for the bounded web worker."""

import contextlib
import io
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from behave import given, then, when

from biblicus.cli import main
from biblicus.web_transform import TransformFailureDetails
from biblicus.command_failure import INVALID_INPUT_FAILURE_CODES, CommandFailure
from features.steps.api_schema_support import assert_matches_published_schema


@given('a disposable web transformation gateway for "{case}"')
def given_gateway(context, case):
    """Start a disposable gateway for the observable contract case."""
    context.web_case = case
    context.web_requests = []
    context.web_payload = {
        "extracted_text": "Navigation\n\nArticle body.\n\nMore evidence.",
        "source_uri": "https://example.org/article",
        "reference_title": "Reference",
        "original_title": "Original",
        "original_subtitle": "Subtitle",
    }
    context.web_task = case if case in {"title", "subtitle", "summary"} else "article"
    if case in {"blank_value", "denied_reduce", "blank_reduce", "metadata_wrong_model"}:
        context.web_task = "summary"
    if case in {"historical_title", "missing_title_year", "archive_without_date"}:
        context.web_task = "title"
    if case in {"complementary_subtitle", "duplicate_subtitle"}:
        context.web_task = "subtitle"
    if case.startswith("quality_") or case in {
        "historical_title",
        "missing_title_year",
        "complementary_subtitle",
        "duplicate_subtitle",
        "invalid_source_date",
        "archive_without_date",
    }:
        context.web_payload.update(
            source_publication_date="2021-01-07",
            source_is_archived=True,
            generated_title="2021 CISA SolarWinds Supply Chain Incident",
        )
    if case == "quality_article":
        context.web_payload["extracted_text"] = (
            "Legal/privacy: This site monitors network traffic.\n\nCISA investigated SolarWinds in January 2021.\n\nOrganizations should apply incident mitigations."
        )
    if case == "archive_without_date":
        context.web_payload["source_publication_date"] = None
    if case == "invalid_source_date":
        context.web_payload["source_publication_date"] = "2021-02-31"
    if context.web_task == "article":
        context.web_payload["model"] = "gpt-5.4-mini-2026-03-17"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            context.web_requests.append((self.path, self.headers.get("Authorization"), request))
            status = {"denied": 409, "uncertain": 502, "redirect": 307}.get(case, 200)
            if case == "denied_reduce" and len(context.web_requests) == 2:
                status = 409
            self.send_response(status)
            if case == "redirect":
                self.send_header("Location", context.web_base + "/responses")
            self.end_headers()
            output = {"paragraph_ids": [1, 2]}
            if context.web_task != "article":
                output = {"value": "Grounded metadata"}
            if case == "historical_title":
                output = {"value": "2021 SolarWinds incident: CISA response"}
            if case == "archive_without_date":
                output = {"value": "Archived SolarWinds incident response"}
            if case == "complementary_subtitle":
                output = {
                    "value": "Orion compromise prompted joint federal response and recovery guidance"
                }
            if case == "duplicate_subtitle":
                output = {"value": "2021 CISA major SolarWinds supply chain incident"}
            if case == "empty_ids":
                output = {"paragraph_ids": []}
            if case == "negative_ids":
                output = {"paragraph_ids": [-1]}
            if case == "blank_paragraph":
                output = {"paragraph_ids": [3]}
            if case == "unknown_ids":
                output = {"paragraph_ids": [99]}
            if case == "duplicate_ids":
                output = {"paragraph_ids": [1, 1]}
            if case == "reversed_ids":
                output = {"paragraph_ids": [2, 1]}
            if case == "boolean_ids":
                output = {"paragraph_ids": [True]}
            if case == "wrong_output":
                output = {"paragraph_ids": "1"}
            if case == "blank_value":
                output = {"value": "  "}
            if case == "blank_reduce" and len(context.web_requests) == 2:
                output = {"value": " "}
            if case == "extra_output":
                output["invented"] = True
            if case == "bad_json":
                self.wfile.write(b"not json")
                return
            if case == "oversize_response":
                self.wfile.write(b"x" * 262145)
                return
            response = {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(output)}],
                    }
                ],
            }
            if case == "empty_output":
                response["output"] = []
            if case == "incomplete":
                response["status"] = "incomplete"
            if case == "refusal":
                response["output"][0]["content"] = [{"type": "refusal", "refusal": "No"}]
            self.wfile.write(json.dumps(response).encode())

    context.web_server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context.web_base = f"http://127.0.0.1:{context.web_server.server_port}/provider/v1"
    context.web_thread = threading.Thread(
        target=lambda: context.web_server.serve_forever(poll_interval=0.01), daemon=True
    )
    context.web_thread.start()
    context.add_cleanup(context.web_server.server_close)
    context.add_cleanup(context.web_server.shutdown)


@when("the bounded web transformation command executes")
def when_command(context):
    """Invoke the production CLI with isolated input and environment."""
    case = context.web_case
    env = {
        "OPENAI_API_KEY": "offline-capability",
        "OPENAI_BASE_URL": context.web_base,
        "OPENAI_API_BASE": context.web_base,
        "OPENAI_MAX_RETRIES": "0",
        "HTTP_PROXY": "http://127.0.0.1:1",
        "http_proxy": "http://127.0.0.1:1",
        "NO_PROXY": "",
    }
    if case == "missing_key":
        del env["OPENAI_API_KEY"]
    if case == "missing_base":
        del env["OPENAI_BASE_URL"]
    if case == "conflicting_base":
        env["OPENAI_API_BASE"] = "http://127.0.0.1:1/provider/v1"
    for scenario, value in {
        "non_loopback": "https://example.org/provider/v1",
        "wrong_path": "http://127.0.0.1/v1",
        "base_query": context.web_base + "?query=yes",
        "credentials_in_base": "http://name:password@127.0.0.1/provider/v1",
        "malformed_base": "http://[invalid/provider/v1",
    }.items():
        if case == scenario:
            env["OPENAI_BASE_URL"] = env["OPENAI_API_BASE"] = value
    if case == "transport":
        env["OPENAI_BASE_URL"] = env["OPENAI_API_BASE"] = "http://127.0.0.1:1/provider/v1"
    if case == "nonzero_retries":
        env["OPENAI_MAX_RETRIES"] = "2"
    if case == "blank_paragraph":
        context.web_payload["extracted_text"] += "\n\n "
    if case == "empty_source":
        context.web_payload["extracted_text"] = " "
    if case == "unknown_field":
        context.web_payload["tools"] = []
    if case == "wrong_type":
        context.web_payload["extracted_text"] = 42
    if case == "wrong_model":
        context.web_payload["model"] = "other-model"
    if case == "input_bytes":
        context.web_payload["extracted_text"] = "x" * 262145
    if case == "request_bytes":
        context.web_payload["extracted_text"] = "x" * 100000
    raw = json.dumps(context.web_payload)
    if case == "invalid_json":
        raw = "{"
    if case == "non_object":
        raw = "[]"
    args = ["extract", "article-text"]
    if context.web_task != "article":
        args = [
            "summarize",
            "map-reduce",
            "--task",
            context.web_task,
            "--model",
            "gpt-5.4-mini-2026-03-17",
        ]
    if case == "metadata_wrong_model":
        args[-1] = "other-model"
    with tempfile.TemporaryDirectory() as temp:
        source = "-"
        if case in {"file_input", "missing_file"}:
            source = str(Path(temp) / "input.json")
            if case == "file_input":
                Path(source).write_text(raw)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, env, clear=True), patch("sys.stdin", io.StringIO(raw)):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                context.web_exit = main(args + ["--input-json", source, "--format", "json"])
        context.web_result = json.loads(stdout.getvalue())
        context.web_stderr = stderr.getvalue()


@then('the web transformation contract for "{case}" holds')
def then_contract(context, case):
    """Verify results and exact gateway dispatch bounds."""
    successful = case in {"article", "title", "subtitle", "summary", "file_input", "proxy_ignored"}
    successful = successful or case in {
        "quality_article",
        "historical_title",
        "complementary_subtitle",
        "archive_without_date",
    }
    result = context.web_result
    assert context.web_stderr == ""
    if successful:
        assert context.web_exit == 0, result
        assert_matches_published_schema(
            "extract-article-text" if context.web_task == "article" else "summarize-map-reduce",
            "response",
            result,
        )
        assert result["status"] == "ok", result
        assert result["error"] is None
        assert result["retry_trace"] == []
        assert result["retry_failure_count"] == result["retry_rounds_used"] == 0
        if context.web_task == "article":
            expected_text = (
                "CISA investigated SolarWinds in January 2021.\n\nOrganizations should apply incident mitigations."
                if case == "quality_article"
                else "Article body.\n\nMore evidence."
            )
            assert result["text"] == expected_text
            assert result["span_count"] == 2
        else:
            assert result["task"] == context.web_task
            if case not in {"historical_title", "complementary_subtitle", "archive_without_date"}:
                assert result["value"] == "Grounded metadata"
            assert result["map_reduce"] == {"map_calls": 1, "reduce_calls": 1, "chunk_count": 1}
    else:
        failure = CommandFailure.model_validate(result)
        assert set(result) == {"status", "error"}, result
        assert context.web_exit == failure.exit_status, result
        assert context.web_exit == (2 if failure.error.code in INVALID_INPUT_FAILURE_CODES else 1)
        assert failure.error.code
        if case == "denied":
            assert (context.web_exit, failure.error.code) == (1, "provider_failed")
        if not failure.error.details:
            assert case in {
                "invalid_json",
                "non_object",
                "empty_source",
                "unknown_field",
                "wrong_type",
                "input_bytes",
                "missing_file",
                "wrong_model",
                "invalid_source_date",
            }
        else:
            assert set(failure.error.details) == set(TransformFailureDetails.model_fields)
            expected_task = None if context.web_task == "article" else context.web_task
            assert failure.error.details["task"] == expected_task
            assert failure.error.details["retry_trace"] == []
        if case == "missing_key":
            assert (context.web_exit, failure.error.code) == (2, "invalid_configuration")
        if case == "invalid_json":
            assert (context.web_exit, failure.error.code) == (2, "invalid_input")
        assert "offline-capability" not in json.dumps(result)
        assert "Article body" not in json.dumps(result)
    before_network = {
        "invalid_json",
        "non_object",
        "empty_source",
        "unknown_field",
        "wrong_type",
        "wrong_model",
        "missing_key",
        "missing_base",
        "conflicting_base",
        "non_loopback",
        "wrong_path",
        "base_query",
        "nonzero_retries",
        "input_bytes",
        "request_bytes",
        "missing_file",
        "transport",
        "invalid_source_date",
        "metadata_wrong_model",
        "credentials_in_base",
        "malformed_base",
    }
    expected = 0 if case in before_network else 1
    if case in {
        "title",
        "subtitle",
        "summary",
        "denied_reduce",
        "blank_reduce",
        "historical_title",
        "missing_title_year",
        "complementary_subtitle",
        "duplicate_subtitle",
        "archive_without_date",
    }:
        expected = 2
    assert len(context.web_requests) == expected, context.web_requests
    for path, authorization, payload in context.web_requests:
        assert path == "/provider/v1/responses"
        assert authorization == "Bearer offline-capability"
        assert set(payload) == {"model", "input", "text", "max_output_tokens"}
        assert payload["max_output_tokens"] == 2000
        assert payload["model"] == "gpt-5.4-mini-2026-03-17"
        assert payload["text"]["format"]["type"] == "json_schema"
        assert "untrusted" in payload["input"][0]["content"]
    if len(context.web_requests) == 2:
        assert context.web_requests[0][2] != context.web_requests[1][2]

    if case == "quality_article":
        instruction = context.web_requests[0][2]["input"][0]["content"]
        assert "legal/privacy" in instruction
        assert "incident mitigations" in instruction
    if case in {
        "historical_title",
        "missing_title_year",
        "complementary_subtitle",
        "duplicate_subtitle",
        "archive_without_date",
    }:
        for _, _, request in context.web_requests:
            data = json.loads(request["input"][1]["content"])
            assert data["source_publication_date"] == context.web_payload["source_publication_date"]
            assert data["source_is_archived"] is True
            assert data["generated_title"] == context.web_payload["generated_title"]
            assert "historical" in request["input"][0]["content"]
        assert "complement" in context.web_requests[-1][2]["input"][0]["content"]
