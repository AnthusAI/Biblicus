"""
URL text extraction with source-aware fetch orchestration.
"""

from __future__ import annotations

import io
import json
import os
import random
import re
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from .html_structured_pipeline import enrich_web_extraction_structured
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

URL_TEXT_PROMPT_VERSION = "url-text-v1"
URL_TEXT_DEFAULT_TIMEOUT_SECONDS = 20.0
URL_TEXT_DEFAULT_MAX_RETRIES = 2
URL_TEXT_DEFAULT_BACKOFF_SECONDS = 0.8
URL_TEXT_GROBID_URL_ENV = "BIBLICUS_GROBID_URL"
URL_TEXT_GROBID_TIMEOUT_SECONDS = 180.0
YOUTUBE_TRANSCRIPT_MAX_WAIT_ENV = "BIBLICUS_YOUTUBE_TRANSCRIPT_MAX_WAIT_SECONDS"
YOUTUBE_TRANSCRIPT_INITIAL_BACKOFF_ENV = "BIBLICUS_YOUTUBE_TRANSCRIPT_INITIAL_BACKOFF_SECONDS"
YOUTUBE_TRANSCRIPT_MAX_BACKOFF_ENV = "BIBLICUS_YOUTUBE_TRANSCRIPT_MAX_BACKOFF_SECONDS"
YOUTUBE_TRANSCRIPT_DEFAULT_MAX_WAIT_SECONDS = 3600.0
YOUTUBE_TRANSCRIPT_DEFAULT_INITIAL_BACKOFF_SECONDS = 30.0
YOUTUBE_TRANSCRIPT_DEFAULT_MAX_BACKOFF_SECONDS = 300.0

_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


class UrlTextExtractionError(RuntimeError):
    """
    Structured URL extraction error.

    :ivar code: Stable machine-readable error code.
    :vartype code: str
    :ivar message: Human-readable error message.
    :vartype message: str
    :ivar details: Optional diagnostic details.
    :vartype details: dict[str, Any]
    """

    def __init__(self, *, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = str(code)
        self.message = str(message)
        self.details = dict(details or {})
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Render this error as a JSON-serializable object.

        :return: Structured error payload.
        :rtype: dict[str, Any]
        """
        payload: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


def load_url_text_input_json(path_or_dash: str) -> Dict[str, Any]:
    """
    Load URL text extraction input JSON from a file path or standard input.

    :param path_or_dash: JSON path or ``-`` for standard input.
    :type path_or_dash: str
    :return: Parsed JSON object.
    :rtype: dict[str, Any]
    :raises ValueError: If JSON is invalid or not an object.
    """
    source = str(path_or_dash or "").strip() or "-"
    if source == "-":
        import sys

        raw_text = sys.stdin.read()
    else:
        with open(source, "r", encoding="utf-8") as handle:
            raw_text = handle.read()
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid input JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be an object")
    return payload


def extract_url_text(
    *,
    source_uri: str,
    reference_title: str = "",
    timeout_seconds: float = URL_TEXT_DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = URL_TEXT_DEFAULT_MAX_RETRIES,
    backoff_seconds: float = URL_TEXT_DEFAULT_BACKOFF_SECONDS,
) -> Dict[str, Any]:
    """
    Extract text from a source URL using source-aware fetch strategy.

    :param source_uri: Source URL.
    :type source_uri: str
    :param reference_title: Optional reference title context.
    :type reference_title: str
    :param timeout_seconds: Per-attempt timeout in seconds.
    :type timeout_seconds: float
    :param max_retries: Maximum retries for transient fetch failures.
    :type max_retries: int
    :param backoff_seconds: Base backoff delay in seconds.
    :type backoff_seconds: float
    :return: Structured extraction payload.
    :rtype: dict[str, Any]
    """
    uri = str(source_uri or "").strip()
    if not uri:
        raise UrlTextExtractionError(code="missing_source_uri", message="source_uri is required")

    source_kind = _classify_source_kind(uri)
    attempts: List[Dict[str, Any]] = []
    strategy = {
        "youtube": "youtube-direct-markitdown",
        "pdf": "pdf-grobid-only",
        "web": "markdown-then-html-then-direct",
    }[source_kind]

    try:
        if source_kind == "youtube":
            converted = _attempt_direct_markitdown(uri=uri, source_kind=source_kind, attempts=attempts)
        elif source_kind == "pdf":
            converted = _extract_pdf_first(
                uri=uri,
                source_kind=source_kind,
                attempts=attempts,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            )
        else:
            converted = _extract_web(
                uri=uri,
                source_kind=source_kind,
                attempts=attempts,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            )
    except UrlTextExtractionError as exc:
        return {
            "status": "failed",
            "source_kind": source_kind,
            "strategy": strategy,
            "text": "",
            "markdown": "",
            "title": None,
            "content_type": None,
            "prompt_version": URL_TEXT_PROMPT_VERSION,
            "attempts": attempts,
            "error": exc.to_dict(),
        }

    text = str(converted.get("text") or "").strip()
    if not text:
        return {
            "status": "failed",
            "source_kind": source_kind,
            "strategy": strategy,
            "text": "",
            "markdown": "",
            "title": None,
            "content_type": str(converted.get("content_type") or "") or None,
            "prompt_version": URL_TEXT_PROMPT_VERSION,
            "attempts": attempts,
            "error": {
                "code": "empty_text",
                "message": "URL extraction completed but produced empty text.",
            },
        }

    markdown = str(converted.get("markdown") or text)
    title = str(converted.get("title") or "").strip() or None
    content_type = str(converted.get("content_type") or "").strip() or None
    if source_kind == "web" and not isinstance(converted.get("structured"), dict):
        converted = enrich_web_extraction_structured(
            converted,
            source_uri=uri,
            html_content=str(converted.get("html_content") or ""),
            reference_title=str(reference_title or ""),
        )
        text = str(converted.get("text") or text).strip()
        markdown = str(converted.get("markdown") or markdown)
        title = str(converted.get("title") or title or "").strip() or title
    return {
        "status": "ok",
        "source_kind": source_kind,
        "strategy": strategy,
        "text": text,
        "markdown": markdown,
        "title": title,
        "content_type": content_type,
        "method": str(converted.get("method") or "") or None,
        "grobid": converted.get("grobid") if isinstance(converted.get("grobid"), dict) else None,
        "structured": converted.get("structured") if isinstance(converted.get("structured"), dict) else None,
        "prompt_version": URL_TEXT_PROMPT_VERSION,
        "attempts": attempts,
        "error": None,
    }


def _extract_pdf_first(
    *,
    uri: str,
    source_kind: str,
    attempts: List[Dict[str, Any]],
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
) -> Dict[str, Any]:
    fetch_result = _fetch_url_bytes(
        uri=uri,
        source_kind=source_kind,
        step="pdf_fetch",
        accept="application/pdf, application/octet-stream;q=0.9, */*;q=0.1",
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
    )
    attempts.extend(fetch_result["attempts"])
    if not fetch_result["ok"]:
        raise UrlTextExtractionError(
            code="pdf_fetch_failed",
            message=f"Could not fetch PDF content from {uri}",
            details={"source_uri": uri, "fetch_error": fetch_result.get("error")},
        )
    try:
        converted = _convert_pdf_with_grobid(
            data=fetch_result["body"],
            source_uri=fetch_result["final_url"] or uri,
            content_type=fetch_result["content_type"],
        )
    except Exception as exc:  # pragma: no cover - endpoint/runtime dependent
        attempts.append(
            {
                "step": "pdf_convert_grobid",
                "result": "failed",
                "error": str(exc),
            }
        )
        raise
    attempts.append(
        {
            "step": "pdf_convert_grobid",
            "result": "ok",
            "content_type": fetch_result["content_type"],
            "text_length": len(str(converted.get("text") or "")),
        }
    )
    if not str(converted.get("text") or "").strip():
        raise UrlTextExtractionError(
            code="grobid_empty_text",
            message="GROBID PDF conversion produced empty text.",
            details={"source_uri": uri},
        )
    return converted


def _extract_web(
    *,
    uri: str,
    source_kind: str,
    attempts: List[Dict[str, Any]],
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
) -> Dict[str, Any]:
    html_content = ""
    for step, accept in (
        ("web_markdown_fetch", "text/markdown, text/html;q=0.9, text/plain;q=0.8, */*;q=0.1"),
        ("web_html_fetch", "text/html, application/xhtml+xml;q=0.9, */*;q=0.8"),
    ):
        fetch_result = _fetch_url_bytes(
            uri=uri,
            source_kind=source_kind,
            step=step,
            accept=accept,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
        attempts.extend(fetch_result["attempts"])
        if not fetch_result["ok"]:
            continue
        step_html = _html_body_from_fetch(fetch_result)
        if step_html:
            html_content = step_html
        try:
            converted = _convert_bytes_with_markitdown(
                data=fetch_result["body"],
                source_uri=fetch_result["final_url"] or uri,
                content_type=fetch_result["content_type"],
            )
            if html_content:
                converted["html_content"] = html_content
            attempts.append(
                {
                    "step": f"{step}_convert",
                    "result": "ok",
                    "content_type": fetch_result["content_type"],
                    "text_length": len(str(converted.get("text") or "")),
                }
            )
            if str(converted.get("text") or "").strip():
                return converted
            attempts.append(
                {
                    "step": f"{step}_convert",
                    "result": "failed",
                    "error": "conversion produced empty text",
                }
            )
        except Exception as exc:  # pragma: no cover - covered by tests through monkeypatch
            attempts.append(
                {
                    "step": f"{step}_convert",
                    "result": "failed",
                    "error": str(exc),
                }
            )

    return _attempt_direct_markitdown(uri=uri, source_kind=source_kind, attempts=attempts)


def _attempt_direct_markitdown(
    *,
    uri: str,
    source_kind: str,
    attempts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    try:
        converted = _convert_direct_with_markitdown(uri)
        attempts.append(
            {
                "step": "direct_markitdown",
                "source_kind": source_kind,
                "result": "ok",
                "text_length": len(str(converted.get("text") or "")),
            }
        )
        youtube_retry = converted.get("youtube_transcript_retry")
        if isinstance(youtube_retry, dict):
            for entry in youtube_retry.get("attempts") or []:
                if isinstance(entry, dict):
                    attempts.append(entry)
        if str(converted.get("text") or "").strip():
            return converted
        raise UrlTextExtractionError(
            code="direct_conversion_empty",
            message="Direct MarkItDown conversion produced empty text.",
        )
    except UrlTextExtractionError:
        raise
    except Exception as exc:
        attempts.append(
            {
                "step": "direct_markitdown",
                "source_kind": source_kind,
                "result": "failed",
                "error": str(exc),
            }
        )
        raise UrlTextExtractionError(
            code="direct_conversion_failed",
            message="Direct MarkItDown conversion failed.",
            details={"source_uri": uri, "error": str(exc)},
        ) from exc


def _fetch_url_bytes(
    *,
    uri: str,
    source_kind: str,
    step: str,
    accept: str,
    timeout_seconds: float,
    max_retries: int,
    backoff_seconds: float,
) -> Dict[str, Any]:
    attempts: List[Dict[str, Any]] = []
    retries = max(0, int(max_retries))
    timeout = max(float(timeout_seconds), 1.0)
    base_backoff = max(float(backoff_seconds), 0.0)

    for attempt_index in range(retries + 1):
        request = Request(
            uri,
            headers={
                "User-Agent": _BROWSER_USER_AGENT,
                "Accept": accept,
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read()
                content_type = _normalize_content_type(response.headers.get("Content-Type"))
                status = int(getattr(response, "status", response.getcode()))
                final_url = str(getattr(response, "url", "") or uri)
                attempts.append(
                    {
                        "step": step,
                        "source_kind": source_kind,
                        "attempt": attempt_index + 1,
                        "result": "ok",
                        "accept": accept,
                        "http_status": status,
                        "content_type": content_type,
                        "final_url": final_url,
                    }
                )
                return {
                    "ok": True,
                    "body": body,
                    "content_type": content_type,
                    "final_url": final_url,
                    "attempts": attempts,
                    "error": None,
                }
        except HTTPError as exc:
            attempts.append(
                {
                    "step": step,
                    "source_kind": source_kind,
                    "attempt": attempt_index + 1,
                    "result": "failed",
                    "accept": accept,
                    "http_status": int(exc.code),
                    "error": str(exc),
                }
            )
            if not _is_retryable_http_status(int(exc.code)) or attempt_index >= retries:
                break
        except URLError as exc:
            attempts.append(
                {
                    "step": step,
                    "source_kind": source_kind,
                    "attempt": attempt_index + 1,
                    "result": "failed",
                    "accept": accept,
                    "error": str(exc),
                }
            )
            if attempt_index >= retries:
                break
        if base_backoff > 0:
            time.sleep(base_backoff * (2 ** attempt_index))

    return {
        "ok": False,
        "body": b"",
        "content_type": None,
        "final_url": uri,
        "attempts": attempts,
        "error": {
            "code": "manual_fetch_failed",
            "message": f"Manual fetch failed for {uri}",
        },
    }


def _convert_bytes_with_markitdown(
    *,
    data: bytes,
    source_uri: str,
    content_type: Optional[str],
    file_extension: Optional[str] = None,
) -> Dict[str, Any]:
    converter = _build_markitdown_converter()
    extension = file_extension or _infer_file_extension(source_uri=source_uri, content_type=content_type)
    result = converter.convert(io.BytesIO(data), file_extension=extension, url=source_uri)
    payload = _markitdown_payload(result)
    payload["content_type"] = content_type
    return payload


def _convert_direct_with_markitdown(source_uri: str) -> Dict[str, Any]:
    if _classify_source_kind(source_uri) == "youtube":
        return _convert_youtube_markdown(source_uri)
    converter = _build_markitdown_converter()
    result = converter.convert(source_uri)
    payload = _markitdown_payload(result)
    payload["content_type"] = None
    return payload


def _canonicalize_youtube_watch_url(source_uri: str) -> str:
    parsed = urlparse(str(source_uri or "").strip())
    host = (parsed.netloc or "").lower()
    video_id = _youtube_video_id_from_uri(source_uri)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    if host.endswith("youtube.com") or host == "youtu.be":
        return str(source_uri or "").strip()
    return str(source_uri or "").strip()


def _youtube_video_id_from_uri(source_uri: str) -> str:
    parsed = urlparse(str(source_uri or "").strip())
    host = (parsed.netloc or "").lower()
    if host == "youtu.be":
        token = (parsed.path or "").strip("/").split("/")[0]
        return token.strip()
    if host.endswith("youtube.com"):
        query = parse_qs(parsed.query or "")
        if query.get("v"):
            return str(query["v"][0]).strip()
        path = parsed.path or ""
        if path.startswith("/shorts/"):
            return path.removeprefix("/shorts/").split("/")[0].strip()
        if path.startswith("/embed/"):
            return path.removeprefix("/embed/").split("/")[0].strip()
    return ""


def _is_low_quality_youtube_markdown(text: str) -> bool:
    normalized = str(text or "").strip()
    if not normalized:
        return True
    if "### Transcript" in normalized:
        return False
    if normalized.startswith("# YouTube") and "### Description" in normalized:
        return False
    sample = normalized[:500]
    footer_markers = (
        "About](https://www.youtube.com/about",
        "© 20",
        "NFL Sunday Ticket",
        "How YouTube works",
    )
    return any(marker in sample for marker in footer_markers)


def _youtube_transcript_retry_settings() -> Dict[str, float]:
    return {
        "max_wait_seconds": _positive_env_float(
            YOUTUBE_TRANSCRIPT_MAX_WAIT_ENV,
            YOUTUBE_TRANSCRIPT_DEFAULT_MAX_WAIT_SECONDS,
        ),
        "initial_backoff_seconds": _positive_env_float(
            YOUTUBE_TRANSCRIPT_INITIAL_BACKOFF_ENV,
            YOUTUBE_TRANSCRIPT_DEFAULT_INITIAL_BACKOFF_SECONDS,
        ),
        "max_backoff_seconds": _positive_env_float(
            YOUTUBE_TRANSCRIPT_MAX_BACKOFF_ENV,
            YOUTUBE_TRANSCRIPT_DEFAULT_MAX_BACKOFF_SECONDS,
        ),
    }


def _positive_env_float(env_name: str, default: float) -> float:
    raw = str(os.environ.get(env_name) or "").strip()
    if not raw:
        return default
    try:
        parsed = float(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _is_retryable_youtube_transcript_error(error: BaseException) -> bool:
    if isinstance(error, UrlTextExtractionError):
        code = str(error.code or "").strip().lower()
        if code in {
            "youtube_transcript_unavailable",
            "direct_conversion_empty",
            "direct_conversion_failed",
        }:
            return True
        details = error.details if isinstance(error.details, dict) else {}
        nested_error = str(details.get("error") or "").lower()
        if "429" in nested_error or "too many requests" in nested_error:
            return True
        return True
    message = str(error or "").lower()
    retry_markers = (
        "429",
        "too many requests",
        "timedtext",
        "transcript",
        "youtube",
        "connection reset",
        "connection aborted",
        "temporarily unavailable",
        "service unavailable",
        "503",
        "502",
        "504",
        "no element found",
        "parseerror",
    )
    return any(marker in message for marker in retry_markers)


def _fetch_youtube_transcript_text(video_id: str, *, languages: Optional[List[str]] = None) -> str:
    if not video_id:
        return ""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ModuleNotFoundError:
        return ""
    requested = [str(language).strip() for language in (languages or ["en"]) if str(language).strip()]
    if not requested:
        requested = ["en"]
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id, languages=requested)
        return " ".join(str(part.text) for part in transcript).strip()
    except Exception as exc:
        raise UrlTextExtractionError(
            code="youtube_transcript_unavailable",
            message="youtube-transcript-api could not fetch captions for this video.",
            details={"video_id": video_id, "error": str(exc)},
        ) from exc


def _attempt_youtube_transcript_only_once(source_uri: str) -> Dict[str, Any]:
    watch_uri = _canonicalize_youtube_watch_url(source_uri)
    video_id = _youtube_video_id_from_uri(watch_uri)
    if not video_id:
        raise UrlTextExtractionError(
            code="youtube_transcript_unavailable",
            message="Could not resolve a YouTube video id from the source URI.",
            details={"source_uri": watch_uri},
        )
    transcript = _fetch_youtube_transcript_text(video_id)
    heading = f"YouTube video {video_id}"
    markdown = f"# YouTube\n\n## {heading}\n\n### Transcript\n{transcript}\n"
    return {
        "text": markdown,
        "markdown": markdown,
        "title": heading,
        "content_type": None,
        "method": "youtube-transcript-api",
    }


def _attempt_youtube_markdown_once(source_uri: str, *, prefer_transcript_api: bool = False) -> Dict[str, Any]:
    if prefer_transcript_api:
        return _attempt_youtube_transcript_only_once(source_uri)

    watch_uri = _canonicalize_youtube_watch_url(source_uri)
    video_id = _youtube_video_id_from_uri(watch_uri)
    title: Optional[str] = None
    markdown = ""
    text = ""

    converter = _build_markitdown_converter()
    try:
        result = converter.convert(watch_uri, youtube_transcript_languages=["en"])
        payload = _markitdown_payload(result)
        title = payload.get("title")
        markdown = str(payload.get("markdown") or "")
        text = str(payload.get("text") or "")
    except Exception as exc:
        if _is_retryable_youtube_transcript_error(exc):
            text = ""
        else:
            raise UrlTextExtractionError(
                code="direct_conversion_failed",
                message="YouTube MarkItDown conversion failed.",
                details={"source_uri": watch_uri, "video_id": video_id or None, "error": str(exc)},
            ) from exc

    if _is_low_quality_youtube_markdown(text):
        transcript = _fetch_youtube_transcript_text(video_id) if video_id else ""
        if transcript:
            heading = title or f"YouTube video {video_id}"
            markdown = f"# YouTube\n\n## {heading}\n\n### Transcript\n{transcript}\n"
            text = markdown
        else:
            raise UrlTextExtractionError(
                code="youtube_transcript_unavailable",
                message="YouTube transcript could not be retrieved via MarkItDown or youtube-transcript-api.",
                details={"source_uri": watch_uri, "video_id": video_id or None},
            )
    elif video_id and "### Transcript" not in text:
        transcript = _fetch_youtube_transcript_text(video_id)
        if transcript:
            text = f"{text.rstrip()}\n\n### Transcript\n{transcript}\n"
            markdown = text

    if not str(text or "").strip():
        raise UrlTextExtractionError(
            code="direct_conversion_empty",
            message="YouTube MarkItDown conversion produced empty text.",
            details={"source_uri": watch_uri, "video_id": video_id or None},
        )

    return {
        "text": text,
        "markdown": markdown or text,
        "title": title,
        "content_type": None,
    }


def _convert_youtube_markdown(source_uri: str) -> Dict[str, Any]:
    settings = _youtube_transcript_retry_settings()
    deadline = time.monotonic() + settings["max_wait_seconds"]
    backoff = settings["initial_backoff_seconds"]
    retry_attempts: List[Dict[str, Any]] = []
    last_error: Optional[UrlTextExtractionError] = None
    started_at = time.monotonic()

    while True:
        attempt_number = len(retry_attempts) + 1
        attempt_started = time.monotonic()
        prefer_transcript_api = attempt_number > 1
        try:
            payload = _attempt_youtube_markdown_once(
                source_uri,
                prefer_transcript_api=prefer_transcript_api,
            )
            retry_attempts.append(
                {
                    "step": "youtube_transcript",
                    "attempt": attempt_number,
                    "result": "ok",
                    "method": payload.get("method") or ("youtube-transcript-api" if prefer_transcript_api else "markitdown"),
                    "elapsed_seconds": round(time.monotonic() - attempt_started, 3),
                }
            )
            payload["youtube_transcript_retry"] = {
                "attempt_count": attempt_number,
                "waited_seconds": round(time.monotonic() - started_at, 3),
                "max_wait_seconds": settings["max_wait_seconds"],
                "attempts": retry_attempts,
            }
            return payload
        except UrlTextExtractionError as exc:
            last_error = exc
            retry_attempts.append(
                {
                    "step": "youtube_transcript",
                    "attempt": attempt_number,
                    "result": "failed",
                    "method": "youtube-transcript-api" if prefer_transcript_api else "markitdown",
                    "error_code": exc.code,
                    "error": exc.message,
                    "elapsed_seconds": round(time.monotonic() - attempt_started, 3),
                }
            )
            if not _is_retryable_youtube_transcript_error(exc):
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sleep_seconds = min(backoff, remaining, settings["max_backoff_seconds"])
            sleep_seconds = sleep_seconds * (0.85 + random.random() * 0.3)
            retry_attempts[-1]["sleep_seconds"] = round(sleep_seconds, 3)
            time.sleep(sleep_seconds)
            backoff = min(max(backoff * 2.0, settings["initial_backoff_seconds"]), settings["max_backoff_seconds"])

    if last_error is None:
        last_error = UrlTextExtractionError(
            code="youtube_transcript_unavailable",
            message="YouTube transcript extraction failed without a structured error.",
            details={"source_uri": source_uri},
        )
    details = dict(last_error.details)
    details["youtube_transcript_retry"] = {
        "attempt_count": len(retry_attempts),
        "waited_seconds": round(time.monotonic() - started_at, 3),
        "max_wait_seconds": settings["max_wait_seconds"],
        "attempts": retry_attempts,
    }
    raise UrlTextExtractionError(
        code=last_error.code,
        message=(
            f"{last_error.message} "
            f"(exhausted YouTube retry budget after {details['youtube_transcript_retry']['waited_seconds']}s)."
        ),
        details=details,
    ) from last_error


def _convert_pdf_with_grobid(
    *,
    data: bytes,
    source_uri: str,
    content_type: Optional[str],
) -> Dict[str, Any]:
    from .grobid_runtime import ensure_grobid_running, resolve_grobid_base_url

    try:
        base_url = ensure_grobid_running(resolve_grobid_base_url())
    except RuntimeError as exc:
        raise UrlTextExtractionError(
            code="grobid_unreachable",
            message=str(exc),
            details={"source_uri": source_uri},
        ) from exc

    endpoint = f"{base_url}/api/processFulltextDocument"
    boundary = f"----biblicus{uuid.uuid4().hex}"
    body = _multipart_form_data(
        fields={
            "consolidateHeader": "1",
            "consolidateCitations": "1",
            "includeRawCitations": "0",
            "includeRawAffiliations": "0",
        },
        files={
            "input": ("document.pdf", data, "application/pdf"),
        },
        boundary=boundary,
    )
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "User-Agent": _BROWSER_USER_AGENT,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/xml, text/xml;q=0.9, */*;q=0.1",
        },
    )
    from .grobid_client import call_grobid_with_limits

    def _request_once() -> str:
        try:
            with urlopen(request, timeout=URL_TEXT_GROBID_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise UrlTextExtractionError(
                code="grobid_http_error",
                message=f"GROBID HTTP error: {exc}",
                details={"source_uri": source_uri, "http_status": int(exc.code)},
            ) from exc
        except UrlTextExtractionError:
            raise
        except Exception as exc:
            raise UrlTextExtractionError(
                code="grobid_request_failed",
                message=f"GROBID request failed: {exc}",
                details={"source_uri": source_uri},
            ) from exc

    xml_text = call_grobid_with_limits(_request_once)

    text, title, structured = _tei_to_structured_text(xml_text)
    return {
        "text": text,
        "markdown": text,
        "title": title,
        "content_type": content_type or _normalize_content_type("application/pdf"),
        "method": "grobid",
        "grobid": {
            "base_url": base_url,
            "endpoint": endpoint,
        },
        "structured": structured,
    }


def _tei_to_structured_text(tei_xml: str) -> tuple[str, Optional[str], Dict[str, Any]]:
    xml_text = str(tei_xml or "").strip()
    if not xml_text:
        return "", None, {
            "authors": [],
            "citations": [],
            "summary": {"authors_count": 0, "citations_count": 0, "citations_with_identifiers": 0},
            "warnings": [{"code": "empty_tei_xml", "message": "GROBID returned empty TEI XML."}],
        }
    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        return "", None, {
            "authors": [],
            "citations": [],
            "summary": {"authors_count": 0, "citations_count": 0, "citations_with_identifiers": 0},
            "warnings": [{"code": "tei_parse_failed", "message": f"Could not parse TEI XML: {exc}"}],
        }

    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    title = _normalize_inline_text(
        root.findtext(".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title", default="", namespaces=ns)
    )
    abstract = _normalize_inline_text(
        "".join(root.findtext(".//tei:teiHeader/tei:profileDesc/tei:abstract", default="", namespaces=ns) or "")
    )

    blocks: List[str] = []
    if title:
        blocks.append(f"# {title}")
    if abstract:
        blocks.append("## Abstract")
        blocks.append(abstract)

    body = root.find(".//tei:text/tei:body", ns)
    if body is not None:
        for div in body.findall(".//tei:div", ns):
            head = _normalize_inline_text("".join(div.findtext("tei:head", default="", namespaces=ns) or ""))
            if head:
                blocks.append(f"## {head}")
            paragraphs = div.findall("tei:p", ns)
            for paragraph in paragraphs:
                text = _normalize_inline_text("".join(paragraph.itertext()))
                if text:
                    blocks.append(text)
            # If a div has no direct <p>, fall back to inline text as a paragraph.
            if not paragraphs:
                text = _normalize_inline_text("".join(div.itertext()))
                if text and (not head or text.lower() != head.lower()):
                    blocks.append(text)

    assembled = "\n\n".join(block for block in blocks if block).strip()

    authors, author_warnings = _extract_tei_authors(root, ns)
    citations, citation_warnings = _extract_tei_citations(root, ns)
    citations_with_identifiers = sum(
        1
        for citation in citations
        if any(
            str(citation.get(key) or "").strip()
            for key in ("doi", "arxiv_id", "isbn")
        )
    )
    structured = {
        "authors": authors,
        "citations": citations,
        "summary": {
            "authors_count": len(authors),
            "citations_count": len(citations),
            "citations_with_identifiers": citations_with_identifiers,
        },
        "warnings": [*author_warnings, *citation_warnings],
    }
    return assembled, title or None, structured


def _extract_tei_authors(root: ET.Element, ns: Dict[str, str]) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    author_rows: List[Dict[str, Any]] = []
    warnings: List[Dict[str, str]] = []
    nodes = root.findall(".//tei:teiHeader/tei:fileDesc/tei:sourceDesc//tei:analytic/tei:author", ns)
    if not nodes:
        nodes = root.findall(".//tei:teiHeader//tei:titleStmt/tei:author", ns)
    for index, node in enumerate(nodes):
        pers_name = node.find("tei:persName", ns)
        raw_name = _normalize_inline_text("".join(pers_name.itertext())) if pers_name is not None else ""
        if not raw_name:
            raw_name = _normalize_inline_text("".join(node.itertext()))
        name = _normalize_person_name(raw_name)
        if not name:
            warnings.append(
                {"code": "author_name_missing", "message": f"Author entry {index + 1} is missing a usable name."}
            )
            continue
        orcid = _normalize_orcid(_first_non_empty(node.findall(".//tei:idno", ns), {"ORCID", "orcid"}))
        email = _normalize_inline_text("".join(node.findtext(".//tei:email", default="", namespaces=ns) or ""))
        affiliation = _normalize_inline_text(" ".join(_affiliation_parts(node, ns)))
        author_rows.append(
            {
                "name": name,
                "normalized_name": _normalize_author_identity_name(name),
                "orcid": orcid or None,
                "email": email or None,
                "affiliation": affiliation or None,
            }
        )
    return _dedupe_author_rows(author_rows), warnings


def _extract_tei_citations(root: ET.Element, ns: Dict[str, str]) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    warnings: List[Dict[str, str]] = []
    citations: List[Dict[str, Any]] = []
    nodes = root.findall(".//tei:listBibl//tei:biblStruct", ns)
    if not nodes:
        warnings.append(
            {"code": "citations_missing", "message": "No TEI bibliography entries were present in the GROBID output."}
        )
        return citations, warnings
    for index, node in enumerate(nodes):
        analytic = node.find("tei:analytic", ns)
        monogr = node.find("tei:monogr", ns)
        title = _normalize_inline_text(
            "".join(
                (
                    (analytic.findtext("tei:title", default="", namespaces=ns) if analytic is not None else "")
                    or (monogr.findtext("tei:title", default="", namespaces=ns) if monogr is not None else "")
                )
                or ""
            )
        )
        year = _extract_citation_year(node, ns)
        doi = _normalize_doi(_first_non_empty(node.findall(".//tei:idno", ns), {"DOI", "doi"}))
        arxiv_id = _normalize_arxiv_id(_first_non_empty(node.findall(".//tei:idno", ns), {"arXiv", "arxiv"}))
        isbn = _normalize_inline_text(_first_non_empty(node.findall(".//tei:idno", ns), {"ISBN", "isbn"}))
        url = _extract_citation_url(node, ns)
        venue = _normalize_inline_text(
            "".join(
                (
                    (monogr.findtext("tei:title", default="", namespaces=ns) if monogr is not None else "")
                    or node.findtext(".//tei:series/tei:title", default="", namespaces=ns)
                    or ""
                )
            )
        )
        citation_authors = _extract_citation_author_names(node, ns)
        raw = _normalize_inline_text(" ".join(node.itertext()))
        if not title and not raw:
            warnings.append(
                {"code": "citation_unusable", "message": f"Citation entry {index + 1} has no usable title or raw content."}
            )
            continue
        citations.append(
            {
                "title": title or None,
                "authors": citation_authors,
                "year": year,
                "venue": venue or None,
                "doi": doi or None,
                "arxiv_id": arxiv_id or None,
                "isbn": isbn or None,
                "url": url or None,
                "raw": raw or None,
            }
        )
    return citations, warnings


def _extract_citation_author_names(node: ET.Element, ns: Dict[str, str]) -> List[str]:
    names: List[str] = []
    for author in node.findall(".//tei:author", ns):
        pers_name = author.find("tei:persName", ns)
        raw_name = _normalize_inline_text("".join(pers_name.itertext())) if pers_name is not None else ""
        if not raw_name:
            raw_name = _normalize_inline_text("".join(author.itertext()))
        name = _normalize_person_name(raw_name)
        if name:
            names.append(name)
    deduped: List[str] = []
    seen: set[str] = set()
    for name in names:
        key = _normalize_author_identity_name(name)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped


def _extract_citation_year(node: ET.Element, ns: Dict[str, str]) -> Optional[int]:
    values: List[str] = []
    for date_node in node.findall(".//tei:date", ns):
        when = _normalize_inline_text(str(date_node.get("when") or ""))
        if when:
            values.append(when)
        text = _normalize_inline_text("".join(date_node.itertext()))
        if text:
            values.append(text)
    for value in values:
        match = re.search(r"\b(19|20)\d{2}\b", value)
        if match:
            return int(match.group(0))
    return None


def _extract_citation_url(node: ET.Element, ns: Dict[str, str]) -> Optional[str]:
    for ptr in node.findall(".//tei:ptr", ns):
        target = _normalize_inline_text(str(ptr.get("target") or ""))
        if target.startswith("http://") or target.startswith("https://"):
            return target
    for ref in node.findall(".//tei:ref", ns):
        target = _normalize_inline_text(str(ref.get("target") or ""))
        if target.startswith("http://") or target.startswith("https://"):
            return target
        text = _normalize_inline_text("".join(ref.itertext()))
        if text.startswith("http://") or text.startswith("https://"):
            return text
    return None


def _first_non_empty(nodes: List[ET.Element], preferred_types: set[str]) -> str:
    preferred: List[str] = []
    fallback: List[str] = []
    for node in nodes:
        value = _normalize_inline_text("".join(node.itertext()))
        if not value:
            continue
        node_type = _normalize_inline_text(str(node.get("type") or ""))
        if node_type in preferred_types:
            preferred.append(value)
        else:
            fallback.append(value)
    if preferred:
        return preferred[0]
    if fallback:
        return fallback[0]
    return ""


def _affiliation_parts(author_node: ET.Element, ns: Dict[str, str]) -> List[str]:
    parts: List[str] = []
    for aff in author_node.findall(".//tei:affiliation", ns):
        text = _normalize_inline_text(" ".join(aff.itertext()))
        if text:
            parts.append(text)
    deduped: List[str] = []
    seen: set[str] = set()
    for part in parts:
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(part)
    return deduped


def _normalize_person_name(value: str) -> str:
    text = _normalize_inline_text(value)
    if not text:
        return ""
    text = re.sub(r"^\d+\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ,;")
    return text


def _normalize_author_identity_name(value: str) -> str:
    text = _normalize_inline_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _normalize_orcid(value: str) -> str:
    text = _normalize_inline_text(value)
    if not text:
        return ""
    match = re.search(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])", text)
    if match:
        return match.group(1).upper()
    return text


def _normalize_doi(value: str) -> str:
    text = _normalize_inline_text(value)
    if not text:
        return ""
    match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", text)
    if match:
        return match.group(1)
    return ""


def _normalize_arxiv_id(value: str) -> str:
    text = _normalize_inline_text(value)
    if not text:
        return ""
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def _dedupe_author_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        identity = str(row.get("orcid") or row.get("normalized_name") or "").strip().lower()
        if not identity:
            continue
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(row)
    return deduped


def _multipart_form_data(
    *,
    fields: Dict[str, str],
    files: Dict[str, tuple[str, bytes, str]],
    boundary: str,
) -> bytes:
    chunks: List[bytes] = []
    boundary_bytes = boundary.encode("utf-8")
    for key, value in fields.items():
        chunks.extend(
            [
                b"--" + boundary_bytes + b"\r\n",
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    for key, (filename, payload, content_type) in files.items():
        chunks.extend(
            [
                b"--" + boundary_bytes + b"\r\n",
                (
                    f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode("utf-8"),
                payload,
                b"\r\n",
            ]
        )
    chunks.append(b"--" + boundary_bytes + b"--\r\n")
    return b"".join(chunks)


def _normalize_inline_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_markitdown_converter() -> Any:
    try:
        from markitdown import MarkItDown
    except ModuleNotFoundError as exc:
        raise UrlTextExtractionError(
            code="missing_markitdown_dependency",
            message=(
                "MarkItDown is required for URL text extraction. "
                "Install it with pip install \"biblicus[markitdown]\"."
            ),
        ) from exc
    return MarkItDown(enable_plugins=True)


def _markitdown_payload(result: Any) -> Dict[str, Any]:
    text = str(getattr(result, "text_content", "") or "")
    markdown = str(getattr(result, "markdown", "") or text)
    title = str(getattr(result, "title", "") or "").strip() or None
    return {"text": text, "markdown": markdown, "title": title}


def _classify_source_kind(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    if host.endswith("youtube.com") or host.endswith("youtu.be"):
        return "youtube"
    if path.endswith(".pdf"):
        return "pdf"
    return "web"


def _html_body_from_fetch(fetch_result: Dict[str, Any]) -> str:
    content_type = _normalize_content_type(fetch_result.get("content_type"))
    if content_type not in {"text/html", "application/xhtml+xml"}:
        return ""
    body = fetch_result.get("body")
    if not isinstance(body, (bytes, bytearray)):
        return ""
    for encoding in ("utf-8", "latin-1"):
        try:
            return bytes(body).decode(encoding)
        except UnicodeDecodeError:
            continue
    return bytes(body).decode("utf-8", errors="replace")


def _normalize_content_type(raw_content_type: Optional[str]) -> Optional[str]:
    text = str(raw_content_type or "").strip().lower()
    if not text:
        return None
    return text.split(";", 1)[0].strip() or None


def _infer_file_extension(*, source_uri: str, content_type: Optional[str]) -> str:
    content = _normalize_content_type(content_type)
    if content == "application/pdf":
        return ".pdf"
    if content in {"text/markdown", "text/x-markdown"}:
        return ".md"
    if content in {"text/plain"}:
        return ".txt"
    if content in {"text/html", "application/xhtml+xml"}:
        return ".html"

    path = (urlparse(source_uri).path or "").lower()
    if path.endswith(".pdf"):
        return ".pdf"
    if path.endswith(".md") or path.endswith(".markdown"):
        return ".md"
    if path.endswith(".txt"):
        return ".txt"
    return ".html"


def _is_retryable_http_status(status_code: int) -> bool:
    return status_code in {408, 425, 429, 500, 502, 503, 504}
