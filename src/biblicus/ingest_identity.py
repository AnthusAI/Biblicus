"""
Canonical identity extraction for ingest duplicate detection.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import unquote, urlparse

_ARXIV_ID_PATTERN = re.compile(
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})(?:v\d+)?)",
    re.IGNORECASE,
)
_ARXIV_VERSION_SUFFIX_PATTERN = re.compile(r"v\d+$", re.IGNORECASE)
_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)
_DOCUMENTCLOUD_IDENTITY_PATTERN = re.compile(r"documentcloud:(?P<id>\d+)", re.IGNORECASE)
_IDENTITY_METADATA_FIELDS = {
    "arxiv_id",
    "canonical_uri",
    "doi",
    "full_text_uri",
    "identity_key",
    "metadata_uri",
    "pdf_url",
    "raw_asset_uri",
    "source",
    "source_uri",
    "source_url",
    "url",
}


def canonical_ingest_identity_keys(
    *, source_uri: Optional[str], metadata: Optional[Mapping[str, Any]]
) -> List[str]:
    """
    Return canonical identity keys that should be unique within a corpus.

    :param source_uri: Source uniform resource identifier for the ingest request.
    :type source_uri: str or None
    :param metadata: Curated metadata attached to the ingest request.
    :type metadata: Mapping[str, Any] or None
    :return: Canonical identity keys such as ``arxiv:2505.22954`` or ``doi:10.1038/x``.
    :rtype: list[str]
    """
    identity_values: List[str] = []
    if isinstance(source_uri, str) and source_uri.strip():
        identity_values.append(source_uri)
    if metadata:
        identity_values.extend(_metadata_identity_values(metadata))

    keys: List[str] = []
    for value in identity_values:
        arxiv_key = _arxiv_identity_key(value)
        if arxiv_key:
            keys.append(arxiv_key)
        doi_key = _doi_identity_key(value)
        if doi_key:
            keys.append(doi_key)
        documentcloud_key = _documentcloud_identity_key(value)
        if documentcloud_key:
            keys.append(documentcloud_key)
    return _deduplicate(keys)


def _metadata_identity_values(metadata: Mapping[str, Any]) -> List[str]:
    values: List[str] = []
    for key, value in metadata.items():
        normalized_key = str(key).strip().lower()
        if normalized_key in _IDENTITY_METADATA_FIELDS:
            values.extend(_string_values(value))
        if isinstance(value, Mapping):
            values.extend(_metadata_identity_values(value))
        elif isinstance(value, list):
            values.extend(_metadata_identity_values_from_sequence(value))
    return values


def _metadata_identity_values_from_sequence(values: Iterable[Any]) -> List[str]:
    collected: List[str] = []
    for value in values:
        if isinstance(value, Mapping):
            collected.extend(_metadata_identity_values(value))
        elif isinstance(value, list):
            collected.extend(_metadata_identity_values_from_sequence(value))
    return collected


def _string_values(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        collected: List[str] = []
        for nested_value in value.values():
            collected.extend(_string_values(nested_value))
        return collected
    if isinstance(value, list):
        collected = []
        for nested_value in value:
            collected.extend(_string_values(nested_value))
        return collected
    return []


def _arxiv_identity_key(value: str) -> Optional[str]:
    candidate = _arxiv_candidate(value)
    if candidate is None:
        return None
    match = _ARXIV_ID_PATTERN.search(candidate)
    if match is None:
        return None
    arxiv_id = match.group("id").rstrip("/")
    arxiv_id = re.sub(r"\.pdf$", "", arxiv_id, flags=re.IGNORECASE)
    arxiv_id = _ARXIV_VERSION_SUFFIX_PATTERN.sub("", arxiv_id)
    return f"arxiv:{arxiv_id.lower()}"


def _arxiv_candidate(value: str) -> Optional[str]:
    candidate = unquote(value.strip())
    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"} and "arxiv.org" not in parsed.netloc.lower():
        return None
    return candidate


def _doi_identity_key(value: str) -> Optional[str]:
    candidate = _doi_candidate(value)
    match = _DOI_PATTERN.search(candidate)
    if match is None:
        return None
    doi = match.group(0).strip().rstrip(".,;)")
    return f"doi:{doi.lower()}"


def _doi_candidate(value: str) -> str:
    candidate = unquote(value.strip())
    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"}:
        host = parsed.netloc.lower()
        path = parsed.path.lstrip("/")
        if host in {"doi.org", "dx.doi.org", "www.doi.org"}:
            candidate = path
        elif host.endswith("nature.com") and path.startswith("articles/"):
            article_id = path.split("/", 1)[1].split("/", 1)[0]
            candidate = f"10.1038/{article_id}"
    candidate = re.sub(r"^doi:\s*", "", candidate, flags=re.IGNORECASE)
    return candidate


def _documentcloud_identity_key(value: str) -> Optional[str]:
    candidate = unquote(value.strip())
    explicit_match = _DOCUMENTCLOUD_IDENTITY_PATTERN.search(candidate)
    if explicit_match:
        return f"documentcloud:{explicit_match.group('id')}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        return None
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    if host == "www.documentcloud.org" and len(path_parts) >= 2 and path_parts[0] == "documents":
        document_prefix = path_parts[1].split("-", 1)[0]
        if document_prefix.isdigit():
            return f"documentcloud:{document_prefix}"
    if (
        host == "api.www.documentcloud.org"
        and len(path_parts) >= 3
        and path_parts[:2] == ["api", "documents"]
        and path_parts[2].isdigit()
    ):
        return f"documentcloud:{path_parts[2]}"
    if host.endswith("documentcloud.org") and len(path_parts) >= 2 and path_parts[0] == "documents":
        if path_parts[1].isdigit():
            return f"documentcloud:{path_parts[1]}"
    return None


def _deduplicate(values: Iterable[str]) -> List[str]:
    deduplicated: List[str] = []
    seen: Dict[str, None] = {}
    for value in values:
        if value not in seen:
            seen[value] = None
            deduplicated.append(value)
    return deduplicated
