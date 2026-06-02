"""
LLM-guided structured metadata extraction for HTML web articles.

Uses a single multi-turn conversation (authors, publication date, bibliography)
so later turns can reuse cached context. Output matches GROBID-shaped structured
payloads used by spaCy dedup and Papyrus citation ingestion.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Dict, List, Optional

from .ai.models import LlmClientConfig

HTML_STRUCTURED_PROMPT_VERSION = "html-structured-v1"
HTML_STRUCTURED_DEFAULT_MODEL = "gpt-5.4-nano"
HTML_STRUCTURED_MAX_ARTICLE_CHARS = 120_000
HTML_STRUCTURED_ENABLE_ENV = "BIBLICUS_HTML_LLM_STRUCTURED"


def html_llm_structured_enabled() -> bool:
    """
    Return whether LLM HTML structured extraction should run.

    :return: True unless explicitly disabled via environment.
    :rtype: bool
    """
    raw = str(os.environ.get(HTML_STRUCTURED_ENABLE_ENV) or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return True


def enrich_web_extraction_with_llm_structured(
    converted: Dict[str, Any],
    *,
    source_uri: str,
    html_content: str = "",
    reference_title: str = "",
    model: str = HTML_STRUCTURED_DEFAULT_MODEL,
    completion_resolver: Optional[Callable[..., Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Attach GROBID-shaped structured metadata to a markitdown web extraction result.

    :param converted: Markitdown conversion payload with text/markdown/title.
    :type converted: dict[str, Any]
    :param source_uri: Article URL.
    :type source_uri: str
    :param html_content: Raw HTML when available; otherwise markdown/text is used.
    :type html_content: str
    :param reference_title: Optional reference title hint.
    :type reference_title: str
    :param model: OpenAI model identifier.
    :type model: str
    :param completion_resolver: Optional test hook for JSON completions.
    :type completion_resolver: Callable[..., dict[str, Any]] or None
    :return: Updated conversion payload.
    :rtype: dict[str, Any]
    """
    if not html_llm_structured_enabled():
        return converted
    article_body = str(html_content or "").strip()
    if not article_body:
        article_body = str(converted.get("markdown") or converted.get("text") or "").strip()
    if not article_body:
        return converted

    try:
        structured, llm_meta = extract_html_structured_metadata(
            article_content=article_body,
            content_kind="html" if str(html_content or "").strip() else "markdown",
            source_uri=source_uri,
            page_title=str(converted.get("title") or "").strip(),
            reference_title=reference_title,
            model=model,
            completion_resolver=completion_resolver,
        )
    except Exception as exc:  # pragma: no cover - exercised via tests with resolver
        warnings = converted.get("llm_structured_warnings")
        if not isinstance(warnings, list):
            warnings = []
        warnings.append(
            {
                "code": "llm_structured_failed",
                "message": str(exc),
            }
        )
        return {**converted, "llm_structured_warnings": warnings}

    if (
        not structured.get("authors")
        and not structured.get("citations")
        and not structured.get("publication_date")
    ):
        return converted

    return {
        **converted,
        "method": "llm-html",
        "structured": structured,
        "llm_structured": llm_meta,
    }


def extract_html_structured_metadata(
    *,
    article_content: str,
    content_kind: str,
    source_uri: str,
    page_title: str = "",
    reference_title: str = "",
    model: str = HTML_STRUCTURED_DEFAULT_MODEL,
    completion_resolver: Optional[Callable[..., Dict[str, Any]]] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Run the three-turn LLM structured extraction conversation.

    :param article_content: HTML or markdown article body.
    :type article_content: str
    :param content_kind: ``html`` or ``markdown``.
    :type content_kind: str
    :param source_uri: Source URL.
    :type source_uri: str
    :param page_title: Extracted page title if known.
    :type page_title: str
    :param reference_title: Optional reference title hint.
    :type reference_title: str
    :param model: OpenAI model identifier.
    :type model: str
    :param completion_resolver: Optional resolver for JSON completions.
    :type completion_resolver: Callable[..., dict[str, Any]] or None
    :return: Tuple of structured payload and LLM provenance metadata.
    :rtype: tuple[dict[str, Any], dict[str, Any]]
    """
    resolver = completion_resolver or _openai_json_completion
    clip = _clip_article(article_content)
    clipped_text = str(clip["text"])
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You extract bibliographic structure from web articles. "
                "Use only the provided article content. "
                "Return strict JSON objects when asked; do not invent references."
            ),
        },
        {
            "role": "user",
            "content": _initial_article_prompt(
                source_uri=source_uri,
                page_title=page_title,
                reference_title=reference_title,
                content_kind=content_kind,
                article_content=clipped_text,
            ),
        },
    ]

    authors_payload = resolver(
        model=model,
        messages=[
            *messages,
            {
                "role": "user",
                "content": (
                    "From this article, list the author names of the article itself "
                    "(not cited works). Return JSON: "
                    '{"authors":[{"name":"Full Name","normalized_name":"family given"}]}. '
                    "Use an empty authors array when unknown."
                ),
            },
        ],
    )
    messages.append(
        {
            "role": "assistant",
            "content": json.dumps(authors_payload, ensure_ascii=False),
        }
    )

    date_payload = resolver(
        model=model,
        messages=[
            *messages,
            {
                "role": "user",
                "content": (
                    "What is this article's publication date? "
                    'Return JSON: {"publication_date":"YYYY-MM-DD or YYYY-MM or YYYY or null","raw":"verbatim date text or null"}. '
                    "Prefer the article publication date over modified/updated timestamps when both appear."
                ),
            },
        ],
    )
    messages.append(
        {
            "role": "assistant",
            "content": json.dumps(date_payload, ensure_ascii=False),
        }
    )

    references_payload = resolver(
        model=model,
        messages=[
            *messages,
            {
                "role": "user",
                "content": (
                    "List bibliography entries this article cites (works referenced), "
                    "not navigation, ads, related posts, or same-site links. "
                    "Return JSON: "
                    '{"citations":[{"title":"...","authors":["..."],"year":2020,"doi":"10.x/... or null",'
                    '"url":"https://... or null","raw":"citation line or null",'
                    '"citing_context":"short note on how this article uses or characterizes the cited work, or null"}]}. '
                    "Use an empty citations array when none are present."
                ),
            },
        ],
    )

    authors = _normalize_authors(authors_payload.get("authors"))
    publication_date, publication_date_raw = _normalize_publication_date(date_payload)
    citations, citation_warnings = _normalize_citations(references_payload.get("citations"))
    warnings: List[Dict[str, str]] = list(citation_warnings)
    if clip.get("truncated"):
        warnings.append(
            {
                "code": "article_truncated",
                "message": (
                    f"Article content truncated to {HTML_STRUCTURED_MAX_ARTICLE_CHARS} characters "
                    "for LLM structured extraction."
                ),
            }
        )

    citations_with_identifiers = sum(
        1
        for citation in citations
        if any(str(citation.get(key) or "").strip() for key in ("doi", "arxiv_id", "isbn", "url"))
    )
    structured: Dict[str, Any] = {
        "authors": authors,
        "citations": citations,
        "publication_date": publication_date,
        "publication_date_raw": publication_date_raw,
        "summary": {
            "authors_count": len(authors),
            "citations_count": len(citations),
            "citations_with_identifiers": citations_with_identifiers,
        },
        "warnings": warnings,
    }
    llm_meta = {
        "model": model,
        "prompt_version": HTML_STRUCTURED_PROMPT_VERSION,
        "source_uri": source_uri,
        "content_kind": content_kind,
        "article_chars": len(article_content),
        "article_chars_sent": clip["length"],
        "turns": 3,
    }
    return structured, llm_meta


def _initial_article_prompt(
    *,
    source_uri: str,
    page_title: str,
    reference_title: str,
    content_kind: str,
    article_content: str,
) -> str:
    return "\n".join(
        [
            f"Source URI: {source_uri}",
            f"Page title: {page_title or '(unknown)'}",
            f"Reference title hint: {reference_title or '(none)'}",
            f"Content kind: {content_kind}",
            "",
            "Article content:",
            article_content,
        ]
    )


def _clip_article(article_content: str) -> Dict[str, Any]:
    text = str(article_content or "").replace("\x00", "")
    if len(text) <= HTML_STRUCTURED_MAX_ARTICLE_CHARS:
        return {"text": text, "length": len(text), "truncated": False}
    return {
        "text": text[:HTML_STRUCTURED_MAX_ARTICLE_CHARS],
        "length": HTML_STRUCTURED_MAX_ARTICLE_CHARS,
        "truncated": True,
    }


def _normalize_authors(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for entry in value:
        if isinstance(entry, str):
            name = _clean_person_name(entry)
        elif isinstance(entry, dict):
            name = _clean_person_name(str(entry.get("name") or entry.get("normalized_name") or ""))
        else:
            continue
        if not name:
            continue
        key = _normalize_identity(name)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"name": name, "normalized_name": _normalize_person_name(name)})
    return rows


def _normalize_publication_date(payload: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    raw = str(payload.get("raw") or payload.get("publication_date") or "").strip() or None
    token = str(payload.get("publication_date") or "").strip()
    if not token and raw:
        token = raw
    if not token:
        return None, raw
    normalized = token.replace("/", "-").replace(".", "-").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        return normalized, raw
    if re.fullmatch(r"\d{4}-\d{2}", normalized):
        return f"{normalized}-01", raw
    year_match = re.fullmatch(r"(\d{4})", normalized)
    if year_match:
        return f"{year_match.group(1)}-01-01", raw
    return None, raw


def _normalize_citations(value: Any) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    warnings: List[Dict[str, str]] = []
    if not isinstance(value, list):
        return [], warnings
    rows: List[Dict[str, Any]] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        authors = [
            _clean_person_name(str(name))
            for name in (entry.get("authors") or [])
            if isinstance(entry.get("authors"), list) and _clean_person_name(str(name))
        ]
        year = _coerce_year(entry.get("year"))
        doi = _normalize_doi(entry.get("doi"))
        url = str(entry.get("url") or "").strip() or None
        raw = str(entry.get("raw") or "").strip() or None
        citing_context = str(entry.get("citing_context") or entry.get("citingContext") or "").strip() or None
        if not title and not raw and not doi and not url:
            warnings.append(
                {
                    "code": "citation_unusable",
                    "message": f"LLM citation entry {index + 1} has no title, identifier, or raw line.",
                }
            )
            continue
        rows.append(
            {
                "title": title or None,
                "authors": authors,
                "year": year,
                "venue": str(entry.get("venue") or "").strip() or None,
                "doi": doi,
                "arxiv_id": _normalize_arxiv_id(entry.get("arxiv_id") or entry.get("arxivId")),
                "isbn": str(entry.get("isbn") or "").strip() or None,
                "url": url,
                "raw": raw,
                "citing_context": citing_context,
            }
        )
    return rows, warnings


def _openai_json_completion(*, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    try:
        import openai
    except ImportError as import_error:
        raise ValueError(
            "LLM HTML structured extraction requires the openai package. "
            'Install it with pip install "biblicus[openai]".'
        ) from import_error
    api_key = LlmClientConfig(provider="openai", model=model).resolve_api_key()
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(model=model, messages=list(messages))
    text = str(response.choices[0].message.content or "").strip()
    payload = _parse_json_object(text)
    if not isinstance(payload, dict):
        raise ValueError("LLM HTML structured extraction returned a non-object JSON payload")
    return payload


def _parse_json_object(text: str) -> Dict[str, Any]:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    payload: Any = json.loads(cleaned)
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("LLM HTML structured extraction must return a JSON object")
    return payload


def _clean_person_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_person_name(value: str) -> str:
    tokens = [token for token in _clean_person_name(value).split(" ") if token]
    if not tokens:
        return ""
    if len(tokens) == 1:
        return tokens[0].lower()
    return f"{tokens[-1].lower()} {' '.join(token.lower() for token in tokens[:-1])}".strip()


def _normalize_identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean_person_name(value).lower()).strip()


def _coerce_year(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1000 <= value <= 3000 else None
    match = re.search(r"\b(19|20)\d{2}\b", str(value))
    return int(match.group(0)) if match else None


def _normalize_doi(value: Any) -> Optional[str]:
    token = str(value or "").strip()
    if not token:
        return None
    lowered = token.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lowered.startswith(prefix):
            token = token[len(prefix) :]
            break
    token = token.strip().strip(".")
    return token or None


def _normalize_arxiv_id(value: Any) -> Optional[str]:
    token = str(value or "").strip()
    if not token:
        return None
    lowered = token.lower()
    for prefix in ("https://arxiv.org/abs/", "http://arxiv.org/abs/", "arxiv:"):
        if lowered.startswith(prefix):
            token = token[len(prefix) :]
            break
    return token.strip() or None
