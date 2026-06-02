"""
Shared web page metadata extraction for references and entity extraction.

Uses the same BeautifulSoup heuristic stack as URL text / graph intake
(``html_heuristics`` + optional ``html_structured_pipeline``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .html_heuristics import (
    HtmlHeuristicDocument,
    extract_html_heuristics,
    heuristic_document_to_structured,
)
from .html_structured_pipeline import enrich_web_extraction_structured, html_heuristics_enabled

WEB_REFERENCE_METADATA_VERSION = "web-reference-metadata-v1"
LOCAL_HTML_SOURCE_URI = "https://papyrus.local/imported-html"


def extraction_metadata_from_web_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shape web metadata for corpus extraction snapshots and graph NER dedup.

    :param payload: Output from :func:`extract_web_reference_metadata_from_html`.
    :type payload: dict[str, Any]
    :return: Metadata dict for :class:`~biblicus.models.ExtractedText`.
    :rtype: dict[str, Any]
    """
    structured = payload.get("structured") if isinstance(payload.get("structured"), dict) else {}
    method = str(payload.get("method") or "html-heuristics").strip() or "html-heuristics"
    metadata: Dict[str, Any] = {
        "method": method,
        "structured": structured,
    }
    title = str(payload.get("title") or "").strip()
    if title:
        metadata["title"] = title
    authors = payload.get("authors")
    if isinstance(authors, list) and authors:
        metadata["authors"] = list(authors)
    if payload.get("publicationDate"):
        metadata["publicationDate"] = payload.get("publicationDate")
    layers = payload.get("layers")
    if isinstance(layers, list) and layers:
        metadata["htmlHeuristicLayers"] = list(layers)
    return metadata


def extract_web_reference_metadata_from_html(
    html: str,
    *,
    source_uri: str = "",
    reference_title: str = "",
    use_llm_fallback: bool = False,
    model: str = "",
    completion_resolver: Any = None,
) -> Dict[str, Any]:
    """
    Extract reference-oriented metadata from HTML using layered heuristics.

    :param html: Raw HTML document.
    :type html: str
    :param source_uri: Canonical page URL for link resolution and provenance.
    :type source_uri: str
    :param reference_title: Optional title hint for LLM fallback.
    :type reference_title: str
    :param use_llm_fallback: When True, run LLM structured enrichment if heuristics are sparse.
    :type use_llm_fallback: bool
    :param model: OpenAI model id for LLM fallback.
    :type model: str
    :param completion_resolver: Optional test hook for LLM fallback.
    :return: JSON-serializable metadata payload.
    :rtype: dict[str, Any]
    """
    html_body = str(html or "")
    uri = str(source_uri or "").strip() or LOCAL_HTML_SOURCE_URI
    if not html_body.strip():
        return _empty_payload(source_uri=uri, method="empty_html")

    if not html_heuristics_enabled():
        return _empty_payload(
            source_uri=uri,
            method="html_heuristics_disabled",
            warnings=[{"code": "html_heuristics_disabled", "message": "HTML heuristics are disabled."}],
        )

    try:
        doc = extract_html_heuristics(html_body, source_uri=uri)
    except ValueError as exc:
        return _empty_payload(
            source_uri=uri,
            method="html_heuristics_unavailable",
            warnings=[{"code": "html_heuristics_unavailable", "message": str(exc)}],
        )

    structured = heuristic_document_to_structured(doc)
    method = "html-heuristics"
    subtitle = _subtitle_from_document(doc)

    if use_llm_fallback:
        enriched = enrich_web_extraction_structured(
            {"text": doc.body_text or "", "markdown": doc.body_text or "", "title": doc.title},
            source_uri=uri,
            html_content=html_body,
            reference_title=reference_title,
            model=model,
            completion_resolver=completion_resolver,
        )
        llm_structured = enriched.get("structured") if isinstance(enriched.get("structured"), dict) else None
        if isinstance(llm_structured, dict):
            structured = llm_structured
            method = str(enriched.get("method") or method)
        if not doc.title:
            doc_title = str(enriched.get("title") or "").strip()
            if doc_title:
                doc.title = doc_title
        if not subtitle:
            subtitle = _subtitle_from_structured(structured)

    return _document_to_payload(doc, structured=structured, method=method, subtitle=subtitle)


def extract_web_reference_metadata_from_url(
    source_uri: str,
    *,
    reference_title: str = "",
    use_llm_fallback: bool = False,
    model: str = "",
    completion_resolver: Any = None,
    timeout_seconds: float = 20.0,
) -> Dict[str, Any]:
    """
    Fetch a web page and extract reference metadata.

    :param source_uri: HTTP(S) URL.
    :type source_uri: str
    :param reference_title: Optional title hint for LLM fallback.
    :type reference_title: str
    :param use_llm_fallback: Whether to run LLM fallback when heuristics are sparse.
    :type use_llm_fallback: bool
    :param model: OpenAI model for LLM fallback.
    :type model: str
    :param completion_resolver: Optional LLM test hook.
    :param timeout_seconds: Fetch timeout.
    :type timeout_seconds: float
    :return: Metadata payload.
    :rtype: dict[str, Any]
    """
    uri = str(source_uri or "").strip()
    if not uri.lower().startswith(("http://", "https://")):
        return _empty_payload(
            source_uri=uri,
            method="unsupported_uri",
            warnings=[{"code": "unsupported_uri", "message": "Web metadata requires an http(s) URL."}],
        )
    html, fetch_warnings = _fetch_html(uri, timeout_seconds=timeout_seconds)
    payload = extract_web_reference_metadata_from_html(
        html,
        source_uri=uri,
        reference_title=reference_title,
        use_llm_fallback=use_llm_fallback,
        model=model,
        completion_resolver=completion_resolver,
    )
    warnings = list(payload.get("warnings") or [])
    warnings.extend(fetch_warnings)
    payload["warnings"] = warnings
    return payload


def title_subtitle_resolution_from_web_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map web metadata payload to Papyrus title/subtitle resolution shape.

    :param metadata: Output from :func:`extract_web_reference_metadata_from_html`.
    :type metadata: dict[str, Any]
    :return: Title/subtitle fields for reference curation signals.
    :rtype: dict[str, Any]
    """
    title = str(metadata.get("title") or "").strip()
    subtitle = str(metadata.get("subtitle") or "").strip()
    if not title:
        return {}
    source_uri = str(metadata.get("sourceUri") or "").strip()
    layers = metadata.get("layers") if isinstance(metadata.get("layers"), list) else []
    layer_hint = ", ".join(str(layer) for layer in layers[:4]) if layers else "html_heuristics"
    return {
        "title": title,
        "subtitle": subtitle,
        "titleMode": "original_web_metadata",
        "subtitleMode": "original_web_metadata" if subtitle else "unresolved",
        "source": str(metadata.get("method") or "html_heuristics"),
        "sourceUrls": [source_uri] if source_uri else [],
        "rationale": f"Resolved from structured HTML metadata ({layer_hint}).",
    }


def _document_to_payload(
    doc: HtmlHeuristicDocument,
    *,
    structured: Dict[str, Any],
    method: str,
    subtitle: str,
) -> Dict[str, Any]:
    author_names = [str(row.get("name") or "").strip() for row in doc.authors if isinstance(row, dict)]
    author_names = [name for name in author_names if name]
    return {
        "schemaVersion": WEB_REFERENCE_METADATA_VERSION,
        "sourceUri": doc.source_uri,
        "title": doc.title,
        "subtitle": subtitle or None,
        "authors": author_names,
        "authorsStructured": list(doc.authors),
        "publicationDate": doc.publication_date,
        "publicationDateRaw": doc.publication_date_raw,
        "updatedAt": doc.updated_at,
        "structured": structured,
        "method": method,
        "layers": list(doc.layers),
        "rawMetadata": dict(doc.raw_metadata),
        "warnings": list(doc.warnings),
        "referenceCandidates": list(doc.reference_candidates),
        "citationCount": len(structured.get("citations") or []) if isinstance(structured, dict) else 0,
    }


def _subtitle_from_document(doc: HtmlHeuristicDocument) -> str:
    raw = doc.raw_metadata if isinstance(doc.raw_metadata, dict) else {}
    open_graph = raw.get("open_graph") if isinstance(raw.get("open_graph"), dict) else {}
    for key in ("og:description", "description"):
        value = str(open_graph.get(key) or "").strip()
        if value and value != str(doc.title or "").strip():
            return value
    twitter = raw.get("twitter_card") if isinstance(raw.get("twitter_card"), dict) else {}
    description = str(twitter.get("twitter:description") or "").strip()
    if description and description != str(doc.title or "").strip():
        return description
    return ""


def _subtitle_from_structured(structured: Dict[str, Any]) -> str:
    if not isinstance(structured, dict):
        return ""
    raw = structured.get("raw_metadata") if isinstance(structured.get("raw_metadata"), dict) else {}
    heuristic = raw.get("heuristic") if isinstance(raw.get("heuristic"), dict) else raw
    open_graph = heuristic.get("open_graph") if isinstance(heuristic.get("open_graph"), dict) else {}
    value = str(open_graph.get("og:description") or "").strip()
    return value


def _fetch_html(source_uri: str, *, timeout_seconds: float) -> tuple[str, List[Dict[str, str]]]:
    from .url_text import URL_TEXT_DEFAULT_MAX_RETRIES, _fetch_url_bytes, _html_body_from_fetch

    warnings: List[Dict[str, str]] = []
    for step, accept in (
        ("web_html_fetch", "text/html, application/xhtml+xml;q=0.9, */*;q=0.8"),
        ("web_markdown_fetch", "text/markdown, text/html;q=0.9, text/plain;q=0.8, */*;q=0.1"),
    ):
        fetch_result = _fetch_url_bytes(
            uri=source_uri,
            source_kind="web",
            step=step,
            accept=accept,
            timeout_seconds=timeout_seconds,
            max_retries=URL_TEXT_DEFAULT_MAX_RETRIES,
            backoff_seconds=0.8,
        )
        if not fetch_result.get("ok"):
            error = fetch_result.get("error") if isinstance(fetch_result.get("error"), dict) else {}
            warnings.append(
                {
                    "code": str(error.get("code") or "fetch_failed"),
                    "message": str(error.get("message") or f"Fetch failed during {step}."),
                }
            )
            continue
        html = _html_body_from_fetch(fetch_result)
        if html.strip():
            return html, warnings
        warnings.append({"code": "empty_html_body", "message": f"No HTML body returned during {step}."})
    return "", warnings


def _empty_payload(
    *,
    source_uri: str,
    method: str,
    warnings: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    return {
        "schemaVersion": WEB_REFERENCE_METADATA_VERSION,
        "sourceUri": source_uri,
        "title": None,
        "subtitle": None,
        "authors": [],
        "authorsStructured": [],
        "publicationDate": None,
        "publicationDateRaw": None,
        "updatedAt": None,
        "structured": {"authors": [], "citations": [], "warnings": list(warnings or [])},
        "method": method,
        "layers": [],
        "rawMetadata": {},
        "warnings": list(warnings or []),
        "referenceCandidates": [],
        "citationCount": 0,
    }
