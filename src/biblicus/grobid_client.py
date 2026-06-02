"""
Shared GROBID request helpers (concurrency limits and retries).
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, TypeVar

from .url_text import UrlTextExtractionError

T = TypeVar("T")

_GROBID_SEMAPHORE: threading.Semaphore | None = None
_GROBID_SEMAPHORE_LOCK = threading.Lock()

RETRYABLE_GROBID_ERROR_CODES = frozenset(
    {
        "grobid_request_failed",
        "grobid_http_error",
        "grobid_unreachable",
    }
)
RETRYABLE_HTTP_STATUSES = frozenset({429, 502, 503, 504})


def grobid_max_concurrent_requests() -> int:
    """
    Resolve the maximum number of in-flight GROBID HTTP requests.

    :return: Concurrency limit (at least 1).
    :rtype: int
    """
    raw = str(os.environ.get("BIBLICUS_GROBID_MAX_CONCURRENT", "2")).strip()
    try:
        value = int(raw)
    except ValueError:
        value = 2
    return max(1, value)


def grobid_max_retries() -> int:
    """
    Resolve how many times to retry a retryable GROBID failure.

    :return: Retry count (at least 1 attempt).
    :rtype: int
    """
    raw = str(os.environ.get("BIBLICUS_GROBID_MAX_RETRIES", "3")).strip()
    try:
        value = int(raw)
    except ValueError:
        value = 3
    return max(1, value)


def _grobid_semaphore() -> threading.Semaphore:
    global _GROBID_SEMAPHORE
    with _GROBID_SEMAPHORE_LOCK:
        if _GROBID_SEMAPHORE is None:
            _GROBID_SEMAPHORE = threading.Semaphore(grobid_max_concurrent_requests())
        return _GROBID_SEMAPHORE


def is_retryable_grobid_error(exc: UrlTextExtractionError) -> bool:
    """
    Return True when a GROBID error is likely transient.

    :param exc: GROBID extraction error.
    :type exc: UrlTextExtractionError
    :return: Whether to retry the request.
    :rtype: bool
    """
    if exc.code not in RETRYABLE_GROBID_ERROR_CODES:
        return False
    if exc.code == "grobid_http_error":
        details = exc.details if isinstance(exc.details, dict) else {}
        status = details.get("http_status")
        if status is not None and int(status) not in RETRYABLE_HTTP_STATUSES:
            return False
    return True


def call_grobid_with_limits(operation: Callable[[], T]) -> T:
    """
    Run a GROBID HTTP operation with concurrency limiting and retries.

    :param operation: Callable that performs one GROBID request.
    :type operation: collections.abc.Callable
    :return: Operation result.
    :rtype: T
    :raises UrlTextExtractionError: When all attempts fail.
    """
    attempts = grobid_max_retries()
    last_error: UrlTextExtractionError | None = None
    from .grobid_runtime import ensure_grobid_running

    with _grobid_semaphore():
        for attempt in range(1, attempts + 1):
            try:
                ensure_grobid_running()
                return operation()
            except UrlTextExtractionError as exc:
                last_error = exc
                if attempt >= attempts or not is_retryable_grobid_error(exc):
                    raise
                backoff = min(8.0, 0.75 * (2 ** (attempt - 1)))
                time.sleep(backoff)
    if last_error is not None:
        raise last_error
    raise UrlTextExtractionError(code="grobid_request_failed", message="GROBID request failed.")
