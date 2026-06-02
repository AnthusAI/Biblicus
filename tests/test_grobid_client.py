"""Tests for GROBID concurrency and retry helpers."""

from __future__ import annotations

import pytest

from biblicus.grobid_client import call_grobid_with_limits, is_retryable_grobid_error
from biblicus.url_text import UrlTextExtractionError


def test_is_retryable_grobid_error_for_transient_codes():
    assert is_retryable_grobid_error(
        UrlTextExtractionError(code="grobid_request_failed", message="timeout")
    )
    assert is_retryable_grobid_error(
        UrlTextExtractionError(
            code="grobid_http_error",
            message="busy",
            details={"http_status": 503},
        )
    )
    assert not is_retryable_grobid_error(
        UrlTextExtractionError(
            code="grobid_http_error",
            message="bad request",
            details={"http_status": 400},
        )
    )


def test_call_grobid_with_limits_retries(monkeypatch):
    attempts = {"count": 0}

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise UrlTextExtractionError(code="grobid_request_failed", message="temporary")
        return "ok"

    monkeypatch.setenv("BIBLICUS_GROBID_MAX_RETRIES", "3")
    monkeypatch.setenv("BIBLICUS_GROBID_MAX_CONCURRENT", "1")
    import biblicus.grobid_client as grobid_client

    grobid_client._GROBID_SEMAPHORE = None
    assert call_grobid_with_limits(flaky) == "ok"
    assert attempts["count"] == 2
