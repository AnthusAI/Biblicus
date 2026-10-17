"""
Source-specific resolution for Biblicus ingestion.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from .time import utc_now_iso

_DOCUMENTCLOUD_VIEWER_PATTERN = re.compile(r"^/documents/(?P<id>\d+)-(?P<slug>[^/]+)/?$")
_DOCUMENTCLOUD_API_PATTERN = re.compile(r"^/api/documents/(?P<id>\d+)/?$")
_DOCUMENTCLOUD_ASSET_PATTERN = re.compile(
    r"^/documents/(?P<id>\d+)/(?P<slug>[^/]+)\.(?P<extension>pdf|txt)$"
)


class ResolvedSource(BaseModel):
    """
    Source payload resolved through a source-specific adapter.

    :ivar data: Raw item bytes to store.
    :vartype data: bytes
    :ivar filename: Suggested raw item filename.
    :vartype filename: str
    :ivar media_type: Internet Assigned Numbers Authority media type.
    :vartype media_type: str
    :ivar source_uri: Canonical source uniform resource identifier.
    :vartype source_uri: str
    :ivar title: Optional title from the source.
    :vartype title: str or None
    :ivar metadata: Structured metadata to store with the raw item.
    :vartype metadata: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    data: bytes
    filename: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    title: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class DocumentCloudReference:
    """
    Parsed DocumentCloud source reference.

    :ivar document_id: DocumentCloud numeric document identifier.
    :vartype document_id: int
    :ivar slug: Optional document slug from the source.
    :vartype slug: str or None
    """

    document_id: int
    slug: Optional[str] = None


@dataclass(frozen=True)
class DocumentCloudResolver:
    """
    Resolver for public DocumentCloud document sources.
    """

    api_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "BIBLICUS_DOCUMENTCLOUD_API_BASE", "https://api.www.documentcloud.org/api"
        ).rstrip("/")
    )
    asset_base_url: Optional[str] = field(
        default_factory=lambda: os.environ.get("BIBLICUS_DOCUMENTCLOUD_ASSET_BASE")
    )

    def matches(self, source_uri: str) -> bool:
        """
        Return whether a source uniform resource identifier is a DocumentCloud source.

        :param source_uri: Source uniform resource identifier.
        :type source_uri: str
        :return: True when this resolver handles the source.
        :rtype: bool
        """
        return _parse_documentcloud_reference(source_uri) is not None

    def resolve(self, source_uri: str) -> ResolvedSource:
        """
        Resolve a DocumentCloud source to the original Portable Document Format asset.

        :param source_uri: DocumentCloud source uniform resource identifier.
        :type source_uri: str
        :return: Resolved source payload.
        :rtype: ResolvedSource
        :raises ValueError: If the source cannot be parsed or resolved.
        """
        reference = _parse_documentcloud_reference(source_uri)
        if reference is None:
            raise ValueError(f"Unsupported DocumentCloud source: {source_uri}")

        metadata_uri = (
            f"{self.api_base_url}/documents/{reference.document_id}/"
            "?expand=user%2Corganization%2Cprojects%2Crevisions%2Csections%2Cnotes.user"
        )
        document = _load_json(metadata_uri)
        if not isinstance(document, dict):
            raise ValueError("DocumentCloud metadata response must be an object")
        document_id = document.get("id")
        if document_id != reference.document_id:
            raise ValueError("DocumentCloud metadata response id does not match source")
        status = document.get("status")
        if status != "success":
            raise ValueError(f"DocumentCloud document is not ready: status={status!r}")
        access = document.get("access")
        if access != "public":
            raise ValueError(f"DocumentCloud document is not public: access={access!r}")

        slug = _required_string(document, "slug")
        asset_base_url = (self.asset_base_url or _required_string(document, "asset_url")).rstrip(
            "/"
        )
        canonical_uri = _required_string(document, "canonical_url")
        title = document.get("title") if isinstance(document.get("title"), str) else None
        pdf_uri = f"{asset_base_url}/documents/{reference.document_id}/{slug}.pdf"
        full_text_uri = f"{asset_base_url}/documents/{reference.document_id}/{slug}.txt"

        pdf_bytes = _load_bytes(pdf_uri)
        return ResolvedSource(
            data=pdf_bytes,
            filename=f"{slug}.pdf",
            media_type="application/pdf",
            source_uri=canonical_uri,
            title=title,
            metadata={
                "source_resolution": {
                    "resolver": "documentcloud",
                    "identity_key": f"documentcloud:{reference.document_id}",
                    "canonical_uri": canonical_uri,
                    "raw_asset_uri": pdf_uri,
                    "metadata_uri": metadata_uri,
                    "retrieved_at": utc_now_iso(),
                    "derived_assets": {
                        "full_text_uri": full_text_uri,
                    },
                },
                "documentcloud": {
                    "id": reference.document_id,
                    "slug": slug,
                    "file_hash": document.get("file_hash"),
                    "language": document.get("language"),
                    "page_count": document.get("page_count"),
                    "status": status,
                    "access": access,
                    "created_at": document.get("created_at"),
                    "updated_at": document.get("updated_at"),
                    "organization": document.get("organization"),
                    "user": document.get("user"),
                },
            },
        )


def resolve_source(source_uri: str) -> Optional[ResolvedSource]:
    """
    Resolve a source through the source-specific resolver registry.

    :param source_uri: Source uniform resource identifier.
    :type source_uri: str
    :return: Resolved source payload, or None when no source-specific resolver matches.
    :rtype: ResolvedSource or None
    """
    resolvers = [DocumentCloudResolver()]
    for resolver in resolvers:
        if resolver.matches(source_uri):
            return resolver.resolve(source_uri)
    return None


def _parse_documentcloud_reference(source_uri: str) -> Optional[DocumentCloudReference]:
    parsed = urlparse(source_uri)
    host = parsed.netloc.lower()
    path = parsed.path
    if host == "www.documentcloud.org":
        match = _DOCUMENTCLOUD_VIEWER_PATTERN.match(path)
        if match:
            return DocumentCloudReference(
                document_id=int(match.group("id")), slug=match.group("slug")
            )
    if host == "api.www.documentcloud.org":
        match = _DOCUMENTCLOUD_API_PATTERN.match(path)
        if match:
            return DocumentCloudReference(document_id=int(match.group("id")))
    if host.endswith("documentcloud.org"):
        match = _DOCUMENTCLOUD_ASSET_PATTERN.match(path)
        if match:
            return DocumentCloudReference(
                document_id=int(match.group("id")), slug=match.group("slug")
            )
    return None


def _load_json(url: str) -> Any:
    request = Request(url, headers={"User-Agent": "biblicus/0"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _load_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "biblicus/0"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def _required_string(document: Dict[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"DocumentCloud metadata missing required field: {key}")
    return value.strip()
