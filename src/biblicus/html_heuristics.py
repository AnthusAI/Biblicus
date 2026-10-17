"""
Heuristic structured metadata extraction from HTML using BeautifulSoup.

Extracts article metadata and bibliography candidates from common markup patterns
(JSON-LD, Open Graph, meta tags, reference sections, footer links) before optional
LLM refinement.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

REFERENCE_HEADING_RE = re.compile(
    r"\b(references|bibliography|sources|citations|works\s+cited|further\s+reading)\b",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", re.IGNORECASE)
BYLINE_CLASS_RE = re.compile(r"\b(byline|author|writers?)\b", re.IGNORECASE)
JSON_LD_ARTICLE_TYPES = {
    "article",
    "newsarticle",
    "blogposting",
    "scholarlyarticle",
    "report",
    "techarticle",
}
FOOTER_BOTTOM_FRACTION = 0.25


@dataclass
class HtmlHeuristicDocument:
    """
    Parsed heuristic document payload.

    :ivar source_uri: Page URL when known.
    :vartype source_uri: str
    :ivar title: Resolved article title.
    :vartype title: str or None
    :ivar authors: Author rows with name and normalized_name.
    :vartype authors: list[dict[str, str]]
    :ivar publication_date: ISO date when resolved (YYYY-MM-DD).
    :vartype publication_date: str or None
    :ivar publication_date_raw: Verbatim date string from markup.
    :vartype publication_date_raw: str or None
    :ivar updated_at: ISO date for last update when known.
    :vartype updated_at: str or None
    :ivar body_html: Main article HTML subset when detected.
    :vartype body_html: str
    :ivar body_text: Plain text from body_html.
    :vartype body_text: str
    :ivar links: External link candidates with anchor text.
    :vartype links: list[dict[str, str]]
    :ivar reference_candidates: Unnormalized bibliography rows.
    :vartype reference_candidates: list[dict[str, Any]]
    :ivar citations: GROBID-shaped bibliography entries.
    :vartype citations: list[dict[str, Any]]
    :ivar raw_metadata: Layered extraction provenance.
    :vartype raw_metadata: dict[str, Any]
    :ivar warnings: Non-fatal extraction warnings.
    :vartype warnings: list[dict[str, str]]
    :ivar layers: Ordered layer ids that contributed fields.
    :vartype layers: list[str]
    """

    source_uri: str = ""
    title: Optional[str] = None
    authors: List[Dict[str, str]] = field(default_factory=list)
    publication_date: Optional[str] = None
    publication_date_raw: Optional[str] = None
    updated_at: Optional[str] = None
    body_html: str = ""
    body_text: str = ""
    links: List[Dict[str, str]] = field(default_factory=list)
    reference_candidates: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[Dict[str, str]] = field(default_factory=list)
    layers: List[str] = field(default_factory=list)


def extract_html_heuristics(
    html: str,
    *,
    source_uri: str = "",
    footer_link_fraction: float = FOOTER_BOTTOM_FRACTION,
) -> HtmlHeuristicDocument:
    """
    Parse HTML and extract structured metadata using layered heuristics.

    :param html: Raw HTML document.
    :type html: str
    :param source_uri: Optional canonical page URL for resolving relative links.
    :type source_uri: str
    :param footer_link_fraction: Bottom fraction of DOM used for link harvesting.
    :type footer_link_fraction: float
    :return: Heuristic document payload.
    :rtype: HtmlHeuristicDocument
    :raises ValueError: If BeautifulSoup is not installed.
    """
    soup = _build_soup(html)
    doc = HtmlHeuristicDocument(source_uri=str(source_uri or "").strip())
    raw: Dict[str, Any] = {}

    json_ld_rows = _extract_json_ld(soup)
    if json_ld_rows:
        raw["json_ld"] = json_ld_rows
        _merge_json_ld(doc, json_ld_rows)

    og = _extract_open_graph(soup)
    if og:
        raw["open_graph"] = og
        _merge_open_graph(doc, og)

    twitter = _extract_twitter_cards(soup)
    if twitter:
        raw["twitter_card"] = twitter
        _merge_twitter(doc, twitter)

    html_meta = _extract_html_meta(soup)
    if html_meta:
        raw["html_meta"] = html_meta
        _merge_html_meta(doc, html_meta)

    byline = _extract_byline_authors(soup)
    if byline:
        raw["byline"] = byline
        _merge_authors(doc, byline, layer="html_byline")

    _extract_body(soup, doc)

    reference_candidates = _extract_reference_section_candidates(soup, source_uri=doc.source_uri)
    footer_candidates = _extract_footer_link_candidates(
        soup,
        source_uri=doc.source_uri,
        bottom_fraction=footer_link_fraction,
    )
    footer_node = soup.find("footer")
    if footer_node is not None:
        footer_candidates.extend(
            _extract_link_candidates_from_node(
                footer_node,
                source_uri=doc.source_uri,
                source_label="footer_element",
            )
        )
        if "footer_element" not in doc.layers:
            doc.layers.append("footer_element")
    doc.reference_candidates = _dedupe_reference_candidates(reference_candidates + footer_candidates)
    if doc.reference_candidates:
        raw["reference_candidates"] = doc.reference_candidates
        if "reference_section" not in doc.layers and reference_candidates:
            doc.layers.append("reference_section")
        if footer_candidates and "footer_links" not in doc.layers:
            doc.layers.append("footer_links")

    doc.citations = _normalize_reference_candidates(doc.reference_candidates)
    doc.links = [
        {
            "href": str(row.get("url") or ""),
            "text": str(row.get("title") or row.get("raw") or ""),
            "source": str(row.get("source") or ""),
        }
        for row in doc.reference_candidates
        if str(row.get("url") or "").strip()
    ]
    doc.raw_metadata = raw

    if not doc.title:
        doc.warnings.append(
            {"code": "title_missing", "message": "No article title found in heuristic layers."}
        )
    if not doc.authors:
        doc.warnings.append(
            {"code": "authors_missing", "message": "No authors found in heuristic layers."}
        )
    if not doc.citations:
        doc.warnings.append(
            {
                "code": "citations_missing",
                "message": "No bibliography candidates normalized from heuristic layers.",
            }
        )
    return doc


def heuristic_document_to_structured(doc: HtmlHeuristicDocument) -> Dict[str, Any]:
    """
    Convert a heuristic document into GROBID-shaped structured metadata.

    :param doc: Parsed heuristic document.
    :type doc: HtmlHeuristicDocument
    :return: Structured payload for graph/citation ingestion.
    :rtype: dict[str, Any]
    """
    citations_with_identifiers = sum(
        1
        for citation in doc.citations
        if any(str(citation.get(key) or "").strip() for key in ("doi", "arxiv_id", "isbn", "url"))
    )
    return {
        "authors": list(doc.authors),
        "citations": list(doc.citations),
        "publication_date": doc.publication_date,
        "publication_date_raw": doc.publication_date_raw,
        "updated_at": doc.updated_at,
        "title": doc.title,
        "summary": {
            "authors_count": len(doc.authors),
            "citations_count": len(doc.citations),
            "citations_with_identifiers": citations_with_identifiers,
            "reference_candidates_count": len(doc.reference_candidates),
        },
        "warnings": list(doc.warnings),
        "raw_metadata": dict(doc.raw_metadata),
        "layers": list(doc.layers),
    }


def structured_metadata_is_sufficient(structured: Dict[str, Any] | None) -> bool:
    """
    Return True when heuristic structured metadata is strong enough to skip LLM.

    :param structured: GROBID-shaped structured dict.
    :type structured: dict[str, object] or None
    :return: Whether LLM fallback can be skipped.
    :rtype: bool
    """
    if not isinstance(structured, dict):
        return False
    authors = structured.get("authors") if isinstance(structured.get("authors"), list) else []
    citations = structured.get("citations") if isinstance(structured.get("citations"), list) else []
    if authors and structured.get("publication_date"):
        return True
    if not citations:
        return bool(authors)
    strong_citations = 0
    for entry in citations:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("doi") or "").strip() or str(entry.get("url") or "").strip():
            strong_citations += 1
            continue
        title = str(entry.get("title") or "").strip()
        year = entry.get("year")
        author_count = len(entry.get("authors") or []) if isinstance(entry.get("authors"), list) else 0
        if len(title) >= 12 and year is not None and author_count >= 1:
            strong_citations += 1
    return strong_citations >= 1 or (len(citations) >= 3 and authors)


def _build_soup(html: str) -> Any:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ValueError(
            "HTML heuristic extraction requires beautifulsoup4. "
            'Install it with pip install "biblicus[web]".'
        ) from exc
    parser = "lxml"
    try:
        import lxml  # noqa: F401
    except ImportError:
        parser = "html.parser"
    return BeautifulSoup(str(html or ""), parser)


def _extract_json_ld(soup: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = _normalize_inline_text(node.string or node.get_text() or "")
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _flatten_json_ld(payload):
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _flatten_json_ld(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        rows: List[Dict[str, Any]] = []
        for entry in payload:
            rows.extend(_flatten_json_ld(entry))
        return rows
    if not isinstance(payload, dict):
        return []
    graph = payload.get("@graph")
    if isinstance(graph, list):
        return [entry for entry in graph if isinstance(entry, dict)]
    return [payload]


def _merge_json_ld(doc: HtmlHeuristicDocument, rows: List[Dict[str, Any]]) -> None:
    for row in rows:
        types = _json_ld_types(row)
        if not types & JSON_LD_ARTICLE_TYPES:
            continue
        if not doc.title:
            doc.title = _first_non_empty(
                [
                    row.get("headline"),
                    row.get("name"),
                    row.get("alternativeHeadline"),
                ]
            )
        _merge_authors(doc, _json_ld_authors(row), layer="json_ld")
        published = _first_non_empty([row.get("datePublished"), row.get("dateCreated")])
        if published and not doc.publication_date:
            doc.publication_date_raw = published
            doc.publication_date = _normalize_date_token(published)
            doc.layers.append("json_ld")
        modified = _first_non_empty([row.get("dateModified"), row.get("dateUpdated")])
        if modified and not doc.updated_at:
            doc.updated_at = _normalize_date_token(modified)
    if doc.layers and "json_ld" not in doc.layers:
        doc.layers.append("json_ld")


def _json_ld_types(row: Dict[str, Any]) -> set[str]:
    raw_type = row.get("@type")
    tokens: List[str] = []
    if isinstance(raw_type, str):
        tokens = [raw_type]
    elif isinstance(raw_type, list):
        tokens = [str(entry) for entry in raw_type]
    return {token.split("/")[-1].lower() for token in tokens}


def _json_ld_authors(row: Dict[str, Any]) -> List[str]:
    authors: List[str] = []
    author_value = row.get("author")
    if isinstance(author_value, list):
        for entry in author_value:
            authors.extend(_json_ld_author_names(entry))
    else:
        authors.extend(_json_ld_author_names(author_value))
    return authors


def _json_ld_author_names(value: Any) -> List[str]:
    if isinstance(value, str):
        name = _normalize_inline_text(value)
        return [name] if name else []
    if not isinstance(value, dict):
        return []
    name = _first_non_empty([value.get("name"), value.get("givenName"), value.get("familyName")])
    if name:
        return [name]
    return []


def _extract_open_graph(soup: Any) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for meta in soup.find_all("meta"):
        prop = str(meta.get("property") or meta.get("name") or "").strip().lower()
        content = _normalize_inline_text(str(meta.get("content") or ""))
        if not prop or not content:
            continue
        if prop in {
            "og:title",
            "og:description",
            "article:published_time",
            "article:modified_time",
            "article:author",
            "og:article:author",
            "og:article:published_time",
        }:
            values[prop] = content
    return values


def _merge_open_graph(doc: HtmlHeuristicDocument, og: Dict[str, str]) -> None:
    if not doc.title and og.get("og:title"):
        doc.title = og["og:title"]
    published = og.get("article:published_time") or og.get("og:article:published_time")
    if published and not doc.publication_date:
        doc.publication_date_raw = published
        doc.publication_date = _normalize_date_token(published)
    modified = og.get("article:modified_time")
    if modified and not doc.updated_at:
        doc.updated_at = _normalize_date_token(modified)
    author = og.get("article:author") or og.get("og:article:author")
    if author:
        _merge_authors(doc, [author], layer="open_graph")


def _extract_twitter_cards(soup: Any) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for meta in soup.find_all("meta"):
        name = str(meta.get("name") or "").strip().lower()
        content = _normalize_inline_text(str(meta.get("content") or ""))
        if name.startswith("twitter:") and content:
            values[name] = content
    return values


def _merge_twitter(doc: HtmlHeuristicDocument, twitter: Dict[str, str]) -> None:
    if not doc.title:
        doc.title = twitter.get("twitter:title") or doc.title
    creator = twitter.get("twitter:creator")
    if creator:
        cleaned = creator.lstrip("@").strip()
        if cleaned:
            _merge_authors(doc, [cleaned], layer="twitter_card")


def _extract_html_meta(soup: Any) -> Dict[str, str]:
    values: Dict[str, str] = {}
    title_node = soup.find("title")
    if title_node:
        title = _normalize_inline_text(title_node.get_text())
        if title:
            values["html_title"] = title
    for meta in soup.find_all("meta"):
        name = str(meta.get("name") or "").strip().lower()
        content = _normalize_inline_text(str(meta.get("content") or ""))
        if name == "author" and content:
            values["meta_author"] = content
        if name in {"dc.date", "dcterms.created", "citation_publication_date"} and content:
            values.setdefault("meta_date", content)
    return values


def _merge_html_meta(doc: HtmlHeuristicDocument, html_meta: Dict[str, str]) -> None:
    if not doc.title and html_meta.get("html_title"):
        doc.title = html_meta["html_title"]
    if html_meta.get("meta_author"):
        _merge_authors(doc, [html_meta["meta_author"]], layer="html_meta")
    if html_meta.get("meta_date") and not doc.publication_date:
        doc.publication_date_raw = html_meta["meta_date"]
        doc.publication_date = _normalize_date_token(html_meta["meta_date"])
        if "html_meta" not in doc.layers:
            doc.layers.append("html_meta")


def _extract_byline_authors(soup: Any) -> List[str]:
    names: List[str] = []
    for node in soup.find_all(True, class_=BYLINE_CLASS_RE):
        text = _normalize_inline_text(node.get_text(" ", strip=True))
        if text and len(text) <= 120:
            names.append(text)
    for node in soup.find_all(["header", "article"]):
        for child in node.find_all(["p", "span", "div"], limit=40):
            classes = " ".join(child.get("class") or []).lower()
            if "byline" not in classes and "author" not in classes:
                continue
            text = _normalize_inline_text(child.get_text(" ", strip=True))
            if text and len(text) <= 120:
                names.append(text)
    return names


def _extract_body(soup: Any, doc: HtmlHeuristicDocument) -> None:
    article = soup.find("article") or soup.find("main") or soup.body
    if article is None:
        return
    doc.body_html = str(article)
    doc.body_text = _normalize_block_text(article.get_text("\n", strip=True))


def _extract_reference_section_candidates(soup: Any, *, source_uri: str) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        label = _normalize_inline_text(heading.get_text())
        if not label or not REFERENCE_HEADING_RE.search(label):
            continue
        for list_node in _reference_lists_after_heading(heading):
            for item in list_node.find_all("li", recursive=False):
                raw = _normalize_inline_text(item.get_text(" ", strip=True))
                if not raw:
                    continue
                link = item.find("a", href=True)
                href = _resolve_href(str(link.get("href") or ""), source_uri) if link else None
                candidates.append(
                    {
                        "source": "reference_section",
                        "raw": raw,
                        "title": _guess_title_from_reference_line(raw),
                        "url": href,
                        "heading": label,
                    }
                )
    return candidates


def _reference_lists_after_heading(heading: Any) -> List[Any]:
    lists: List[Any] = []
    for sibling in heading.find_all_next(["ol", "ul"], limit=3):
        parent_heading = sibling.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
        if parent_heading is heading:
            lists.append(sibling)
    return lists


def _extract_link_candidates_from_node(
    node: Any,
    *,
    source_uri: str,
    source_label: str,
) -> List[Dict[str, Any]]:
    source_host = (urlparse(source_uri).netloc or "").lower()
    candidates: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in node.find_all("a", href=True):
        href = _resolve_href(str(anchor.get("href") or ""), source_uri)
        if not href or not href.startswith("http"):
            continue
        host = (urlparse(href).netloc or "").lower()
        if source_host and host == source_host:
            continue
        text = _normalize_inline_text(anchor.get_text(" ", strip=True))
        if not text or len(text) < 4:
            continue
        key = f"{href}|{text.lower()}"
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "source": source_label,
                "raw": text,
                "title": text,
                "url": href,
            }
        )
    return candidates


def _extract_footer_link_candidates(
    soup: Any,
    *,
    source_uri: str,
    bottom_fraction: float,
) -> List[Dict[str, Any]]:
    body = soup.body
    if body is None:
        return []
    all_nodes = list(body.find_all(True))
    if not all_nodes:
        return []
    start_index = int(len(all_nodes) * (1.0 - max(0.05, min(bottom_fraction, 0.5))))
    bottom_nodes = all_nodes[start_index:]
    candidates: List[Dict[str, Any]] = []
    for node in bottom_nodes:
        candidates.extend(
            _extract_link_candidates_from_node(
                node,
                source_uri=source_uri,
                source_label="footer_links",
            )
        )
    return candidates


def _normalize_reference_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        raw = str(candidate.get("raw") or "").strip()
        title = str(candidate.get("title") or raw).strip()
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        year_match = YEAR_RE.search(raw)
        year = int(year_match.group(0)) if year_match else None
        doi_match = DOI_RE.search(raw)
        authors = _guess_authors_from_reference_line(raw)
        rows.append(
            {
                "title": title[:500] or None,
                "authors": authors,
                "year": year,
                "venue": None,
                "doi": doi_match.group(0) if doi_match else None,
                "arxiv_id": None,
                "isbn": None,
                "url": str(candidate.get("url") or "").strip() or None,
                "raw": raw or None,
                "citing_context": None,
                "candidate_source": str(candidate.get("source") or ""),
            }
        )
    return rows


def _dedupe_reference_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        raw = str(candidate.get("raw") or "").strip().lower()
        url = str(candidate.get("url") or "").strip().lower()
        key = url or raw
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _merge_authors(doc: HtmlHeuristicDocument, names: List[str], *, layer: str) -> None:
    existing = {row.get("normalized_name") for row in doc.authors if isinstance(row, dict)}
    expanded: List[str] = []
    for name in names:
        cleaned = _normalize_inline_text(name)
        if not cleaned:
            continue
        if re.search(r"\s+and\s+", cleaned, flags=re.IGNORECASE):
            expanded.extend(
                part.strip()
                for part in re.split(r"\s+and\s+", cleaned, flags=re.IGNORECASE)
                if part.strip()
            )
        else:
            expanded.append(cleaned)
    for cleaned in expanded:
        normalized = _normalize_person_name(cleaned)
        if normalized in existing:
            continue
        existing.add(normalized)
        doc.authors.append({"name": cleaned, "normalized_name": normalized})
    if expanded and layer not in doc.layers:
        doc.layers.append(layer)


def _guess_title_from_reference_line(raw: str) -> str:
    text = _normalize_inline_text(raw)
    if not text:
        return ""
    without_year = YEAR_RE.sub("", text).strip(" .,;")
    parts = re.split(r"\.\s+", without_year)
    if len(parts) >= 2 and len(parts[-1]) >= 8:
        return parts[-1].strip()
    return text[:240]


def _guess_authors_from_reference_line(raw: str) -> List[str]:
    text = _normalize_inline_text(raw)
    if not text:
        return []
    head = text.split(".", 1)[0]
    if len(head) > 120:
        return []
    if " et al" in head.lower():
        head = head.split(" et al", 1)[0]
    if "," in head and len(head.split(",")) <= 4:
        return [part.strip() for part in head.split(",") if part.strip()]
    if " and " in head.lower():
        return [part.strip() for part in re.split(r"\s+and\s+", head, flags=re.IGNORECASE) if part.strip()]
    return [head] if 2 <= len(head) <= 80 else []


def _resolve_href(href: str, source_uri: str) -> Optional[str]:
    token = str(href or "").strip()
    if not token or token.startswith("#"):
        return None
    if token.startswith("http://") or token.startswith("https://"):
        return token
    if source_uri:
        return urljoin(source_uri, token)
    return token


def _normalize_date_token(value: str) -> Optional[str]:
    token = str(value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = token[:-1]
    if "T" in token:
        token = token.split("T", 1)[0]
    normalized = token.replace("/", "-")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        return normalized
    if re.fullmatch(r"\d{4}-\d{2}", normalized):
        return f"{normalized}-01"
    year_match = re.fullmatch(r"(\d{4})", normalized)
    if year_match:
        return f"{year_match.group(1)}-01-01"
    return None


def _normalize_person_name(value: str) -> str:
    tokens = [token for token in _normalize_inline_text(value).split(" ") if token]
    if not tokens:
        return ""
    if len(tokens) == 1:
        return tokens[0].lower()
    return f"{tokens[-1].lower()} {' '.join(token.lower() for token in tokens[:-1])}".strip()


def _normalize_inline_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_block_text(value: str) -> str:
    lines = [line.strip() for line in str(value or "").splitlines()]
    return "\n".join(line for line in lines if line)


def _first_non_empty(values: List[Any]) -> str:
    for value in values:
        token = _normalize_inline_text(str(value or ""))
        if token:
            return token
    return ""
