"""
Helpers for deduplicating spaCy NER output against structured extraction metadata.

Structured metadata may come from GROBID (PDF), LLM HTML extraction, or Papyrus
urlExtraction attachments.
"""

from __future__ import annotations

import re
from typing import Any


def is_grobid_extraction_metadata(metadata: dict[str, Any] | None) -> bool:
    """
    Return True when extraction metadata indicates GROBID structured parsing ran.

    :param metadata: Per-item extraction metadata from a snapshot artifact.
    :type metadata: dict[str, object] or None
    :return: Whether GROBID structured data should be honored.
    :rtype: bool
    """
    if not isinstance(metadata, dict):
        return False
    method = str(metadata.get("method") or "").strip().lower()
    if method in {"grobid", "llm-html", "html-heuristics", "html-heuristics+llm-html", "html-heuristics-partial"}:
        return True
    structured = metadata.get("structured")
    if isinstance(structured, dict) and (
        structured.get("authors") or structured.get("citations")
    ):
        return True
    # Papyrus reference attachments store a summary under urlExtraction.structured
    url_extraction = metadata.get("urlExtraction")
    if isinstance(url_extraction, dict):
        nested = url_extraction.get("structured")
        if isinstance(nested, dict) and (nested.get("authors") or nested.get("citations")):
            return True
    return False


def grobid_structured_from_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """
    Resolve the structured authors/citations payload from extraction metadata.

    :param metadata: Per-item extraction metadata.
    :type metadata: dict[str, object] or None
    :return: Structured payload with authors and citations lists.
    :rtype: dict[str, object]
    """
    if not isinstance(metadata, dict):
        return {}
    structured = metadata.get("structured")
    if isinstance(structured, dict):
        return structured
    url_extraction = metadata.get("urlExtraction")
    if isinstance(url_extraction, dict) and isinstance(url_extraction.get("structured"), dict):
        return url_extraction["structured"]
    return {}


def grobid_blocked_surface_forms(structured: dict[str, Any]) -> set[str]:
    """
    Build normalized surface forms that spaCy should not re-emit after GROBID extraction.

    :param structured: GROBID structured payload with authors[] and citations[].
    :type structured: dict[str, object]
    :return: Lowercased normalized tokens and phrases to suppress.
    :rtype: set[str]
    """
    blocked: set[str] = set()
    authors = structured.get("authors") if isinstance(structured.get("authors"), list) else []
    for author in authors:
        if not isinstance(author, dict):
            continue
        for key in ("name", "normalized_name"):
            _add_blocked_phrase(blocked, str(author.get(key) or ""))
    publication_date = str(structured.get("publication_date") or "").strip()
    if publication_date:
        _add_blocked_phrase(blocked, publication_date)
    publication_date_raw = str(structured.get("publication_date_raw") or "").strip()
    if publication_date_raw:
        _add_blocked_phrase(blocked, publication_date_raw)
    citations = structured.get("citations") if isinstance(structured.get("citations"), list) else []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        _add_blocked_phrase(blocked, str(citation.get("title") or ""))
        _add_blocked_phrase(blocked, str(citation.get("raw") or ""))
        citation_authors = citation.get("authors")
        if isinstance(citation_authors, list):
            for name in citation_authors:
                _add_blocked_phrase(blocked, str(name or ""))
    return blocked


def should_suppress_ner_entity(
    *,
    label: str,
    entity_type: str,
    blocked_forms: set[str],
) -> bool:
    """
    Return True when an spaCy entity duplicates GROBID author/citation structure.

    :param label: Entity surface text from spaCy.
    :type label: str
    :param entity_type: spaCy entity label (PER, ORG, ...).
    :type entity_type: str
    :param blocked_forms: Normalized forms from :func:`grobid_blocked_surface_forms`.
    :type blocked_forms: set[str]
    :return: Whether to drop this entity before graph export.
    :rtype: bool
    """
    normalized_label = _normalize_form(label)
    if not normalized_label:
        return False
    if normalized_label in blocked_forms:
        return True
    # Author lists often mis-tag surnames as ORG; block any single-token author surname.
    if entity_type in {"PER", "ORG", "NORP", "PERSON"}:
        for blocked in blocked_forms:
            if not blocked or " " in blocked:
                continue
            if normalized_label == blocked or normalized_label == _normalize_form(blocked.split()[-1]):
                return True
    return False


def _add_blocked_phrase(blocked: set[str], value: str) -> None:
    cleaned = value.strip()
    if not cleaned:
        return
    normalized = _normalize_form(cleaned)
    if normalized:
        blocked.add(normalized)
    for token in re.findall(r"[A-Za-z][A-Za-z0-9\-']*", cleaned):
        token_norm = _normalize_form(token)
        if token_norm and len(token_norm) >= 2:
            blocked.add(token_norm)


def _normalize_form(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", normalized).strip()
