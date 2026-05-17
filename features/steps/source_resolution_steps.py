from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from behave import given, then, when

from features.environment import run_biblicus
from features.steps.cli_steps import _corpus_path, _record_ingest

DOCUMENTCLOUD_URL = "https://www.documentcloud.org/documents/27013007-govuscourtsnysd6422871181/"
DOCUMENTCLOUD_PDF_URL = (
    "https://s3.documentcloud.org/documents/27013007/govuscourtsnysd6422871181.pdf"
)


@given("a fake public DocumentCloud document source is available")
def step_fake_public_documentcloud_source(context) -> None:
    _start_fake_documentcloud_server(context, access="public", status="success")


@given("a fake private DocumentCloud document source is available")
def step_fake_private_documentcloud_source(context) -> None:
    _start_fake_documentcloud_server(context, access="private", status="success")


@when(
    'I ingest the fake DocumentCloud source into corpus "{corpus_name}" with import rationale "{rationale}"'
)
def step_ingest_fake_documentcloud_source_with_rationale(
    context, corpus_name: str, rationale: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    context.last_source = DOCUMENTCLOUD_URL
    result = run_biblicus(
        context,
        ["--corpus", str(corpus), "ingest", "--import-rationale", rationale, DOCUMENTCLOUD_URL],
        extra_env=getattr(context, "extra_env", None),
    )
    _record_ingest(context, result)


@when('I ingest the fake DocumentCloud Portable Document Format asset into corpus "{corpus_name}"')
def step_ingest_fake_documentcloud_pdf_asset(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    context.last_source = DOCUMENTCLOUD_PDF_URL
    result = run_biblicus(
        context,
        ["--corpus", str(corpus), "ingest", DOCUMENTCLOUD_PDF_URL],
        extra_env=getattr(context, "extra_env", None),
    )
    _record_ingest(context, result)


@when('I attempt to ingest the fake DocumentCloud source into corpus "{corpus_name}"')
def step_attempt_ingest_fake_documentcloud_source(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    context.last_source = DOCUMENTCLOUD_URL
    context.last_result = run_biblicus(
        context,
        ["--corpus", str(corpus), "ingest", DOCUMENTCLOUD_URL],
        extra_env=getattr(context, "extra_env", None),
    )
    context.last_ingest = None


@then('the shown item metadata path "{path}" equals "{expected}"')
def step_shown_metadata_path_equals_string(context, path: str, expected: str) -> None:
    value = _metadata_path_value(context.last_shown, path)
    assert value == expected, f"Expected {path}={expected!r}, got {value!r}"


@then('the shown item metadata path "{path}" equals {expected:d}')
def step_shown_metadata_path_equals_integer(context, path: str, expected: int) -> None:
    value = _metadata_path_value(context.last_shown, path)
    assert value == expected, f"Expected {path}={expected!r}, got {value!r}"


def _start_fake_documentcloud_server(context, *, access: str, status: str) -> None:
    class FakeDocumentCloudHandler(BaseHTTPRequestHandler):
        def log_message(self, message_format, *args):
            return

        def do_GET(self):
            if self.path.startswith("/api/documents/27013007/"):
                _send_json(self, _documentcloud_payload(context, access=access, status=status))
                return
            if self.path == "/documents/27013007/govuscourtsnysd6422871181.pdf":
                _send_bytes(self, b"%PDF-1.7\nfake documentcloud pdf\n", "application/pdf")
                return
            if self.path == "/documents/27013007/govuscourtsnysd6422871181.txt":
                _send_bytes(self, b"DocumentCloud full text wins\n", "text/plain")
                return
            self.send_response(404)
            self.end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeDocumentCloudHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    context.httpd = httpd
    host, port = httpd.server_address
    base_url = f"http://{host}:{port}"
    context.extra_env["BIBLICUS_DOCUMENTCLOUD_API_BASE"] = f"{base_url}/api"
    context.extra_env["BIBLICUS_DOCUMENTCLOUD_ASSET_BASE"] = base_url


def _documentcloud_payload(context, *, access: str, status: str) -> dict[str, Any]:
    asset_base = context.extra_env["BIBLICUS_DOCUMENTCLOUD_ASSET_BASE"]
    return {
        "id": 27013007,
        "access": access,
        "asset_url": f"{asset_base}/",
        "canonical_url": DOCUMENTCLOUD_URL,
        "created_at": "2026-02-14T04:30:25.456918Z",
        "file_hash": "fake-hash",
        "language": "eng",
        "organization": {"id": 758, "name": "Techdirt", "slug": "techdirt"},
        "page_count": 64,
        "slug": "govuscourtsnysd6422871181",
        "status": status,
        "title": "gov.uscourts.nysd.642287.118.1",
        "updated_at": "2026-02-14T04:32:25.646939Z",
        "user": {"id": 5762, "name": "Mike Masnick", "username": "mmasnick"},
    }


def _send_json(handler: BaseHTTPRequestHandler, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    _send_bytes(handler, data, "application/json")


def _send_bytes(handler: BaseHTTPRequestHandler, data: bytes, media_type: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", media_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _metadata_path_value(item: dict[str, Any], path: str) -> Any:
    assert item is not None
    value: Any = item.get("metadata") or {}
    for part in path.split("."):
        assert isinstance(value, dict), f"Cannot traverse {path!r} through {value!r}"
        value = value.get(part)
    return value
