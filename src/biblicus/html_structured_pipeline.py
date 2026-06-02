"""
Orchestrate HTML structured metadata extraction: heuristics first, LLM fallback.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

from .html_heuristics import (
    extract_html_heuristics,
    heuristic_document_to_structured,
    structured_metadata_is_sufficient,
)
from .html_structured import (
    HTML_STRUCTURED_DEFAULT_MODEL,
    enrich_web_extraction_with_llm_structured,
    html_llm_structured_enabled,
)

HTML_HEURISTICS_ENABLE_ENV = "BIBLICUS_HTML_HEURISTICS"
HTML_STRUCTURED_PIPELINE_VERSION = "html-structured-pipeline-v1"


def html_heuristics_enabled() -> bool:
    """
    Return whether BeautifulSoup heuristics should run for web HTML.

    :return: True unless explicitly disabled via environment.
    :rtype: bool
    """
    raw = str(os.environ.get(HTML_HEURISTICS_ENABLE_ENV) or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return True


def enrich_web_extraction_structured(
    converted: Dict[str, Any],
    *,
    source_uri: str,
    html_content: str = "",
    reference_title: str = "",
    model: str = HTML_STRUCTURED_DEFAULT_MODEL,
    completion_resolver: Optional[Callable[..., Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Attach structured metadata using HTML heuristics, then optional LLM fallback.

    :param converted: Markitdown conversion payload.
    :type converted: dict[str, Any]
    :param source_uri: Article URL.
    :type source_uri: str
    :param html_content: Raw HTML when available.
    :type html_content: str
    :param reference_title: Optional reference title hint.
    :type reference_title: str
    :param model: OpenAI model for LLM fallback.
    :type model: str
    :param completion_resolver: Optional LLM test hook.
    :type completion_resolver: Callable[..., dict[str, Any]] or None
    :return: Updated conversion payload.
    :rtype: dict[str, Any]
    """
    html = str(html_content or "").strip()
    structured: Dict[str, Any] | None = None
    provenance: Dict[str, Any] = {"pipeline_version": HTML_STRUCTURED_PIPELINE_VERSION}

    if html and html_heuristics_enabled():
        try:
            doc = extract_html_heuristics(html, source_uri=source_uri)
            structured = heuristic_document_to_structured(doc)
            if doc.title and not converted.get("title"):
                converted = {**converted, "title": doc.title}
            provenance["heuristics"] = {
                "layers": list(doc.layers),
                "reference_candidates": len(doc.reference_candidates),
            }
        except ValueError as exc:
            warnings = converted.get("html_heuristic_warnings")
            if not isinstance(warnings, list):
                warnings = []
            warnings.append({"code": "html_heuristics_unavailable", "message": str(exc)})
            converted = {**converted, "html_heuristic_warnings": warnings}

    if structured and structured_metadata_is_sufficient(structured):
        return {
            **converted,
            "method": "html-heuristics",
            "structured": structured,
            "html_structured": provenance,
        }

    if not html_llm_structured_enabled():
        if structured and (structured.get("authors") or structured.get("citations")):
            return {
                **converted,
                "method": "html-heuristics-partial",
                "structured": structured,
                "html_structured": provenance,
            }
        return converted

    llm_payload = enrich_web_extraction_with_llm_structured(
        converted,
        source_uri=source_uri,
        html_content=html,
        reference_title=reference_title,
        model=model,
        completion_resolver=completion_resolver,
    )
    llm_structured = (
        llm_payload.get("structured") if isinstance(llm_payload.get("structured"), dict) else None
    )
    if isinstance(llm_structured, dict):
        merged = _merge_structured(structured, llm_structured)
        provenance["llm"] = llm_payload.get("llm_structured")
        return {
            **llm_payload,
            "method": _resolve_method(structured, llm_structured),
            "structured": merged,
            "html_structured": provenance,
        }
    if structured:
        return {
            **converted,
            "method": "html-heuristics-partial",
            "structured": structured,
            "html_structured": provenance,
        }
    return llm_payload


def _resolve_method(
    heuristic: Dict[str, Any] | None,
    llm: Dict[str, Any],
) -> str:
    if isinstance(heuristic, dict) and (heuristic.get("authors") or heuristic.get("citations")):
        return "html-heuristics+llm-html"
    return "llm-html"


def _merge_structured(
    heuristic: Dict[str, Any] | None,
    llm: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(heuristic, dict):
        return dict(llm)
    merged = dict(llm)
    if not merged.get("authors") and heuristic.get("authors"):
        merged["authors"] = heuristic["authors"]
    if not merged.get("publication_date") and heuristic.get("publication_date"):
        merged["publication_date"] = heuristic["publication_date"]
        merged["publication_date_raw"] = heuristic.get("publication_date_raw")
    if not merged.get("citations") and heuristic.get("citations"):
        merged["citations"] = heuristic["citations"]
    heuristic_warnings = heuristic.get("warnings") if isinstance(heuristic.get("warnings"), list) else []
    llm_warnings = merged.get("warnings") if isinstance(merged.get("warnings"), list) else []
    merged["warnings"] = [*heuristic_warnings, *llm_warnings]
    if heuristic.get("raw_metadata"):
        merged["raw_metadata"] = {
            "heuristic": heuristic.get("raw_metadata"),
            "llm_layers": merged.get("layers"),
        }
    summary = merged.get("summary") if isinstance(merged.get("summary"), dict) else {}
    authors = merged.get("authors") if isinstance(merged.get("authors"), list) else []
    citations = merged.get("citations") if isinstance(merged.get("citations"), list) else []
    merged["summary"] = {
        **summary,
        "authors_count": len(authors),
        "citations_count": len(citations),
        "citations_with_identifiers": sum(
            1
            for row in citations
            if isinstance(row, dict)
            and any(str(row.get(key) or "").strip() for key in ("doi", "arxiv_id", "isbn", "url"))
        ),
    }
    return merged
