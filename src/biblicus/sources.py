"""
Source loading helpers for Biblicus ingestion.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


def _looks_like_uri(value: str) -> bool:
    """
    Check whether a string resembles a uniform resource identifier.

    :param value: Candidate string.
    :type value: str
    :return: True if the string has a valid uniform resource identifier scheme prefix.
    :rtype: bool
    """

    return "://" in value and value.split("://", 1)[0].isidentifier()


def _filename_from_url_path(path: str) -> str:
    """
    Derive a filename from a uniform resource locator path.

    :param path: Uniform resource locator path component.
    :type path: str
    :return: Filename or a fallback name.
    :rtype: str
    """

    filename = Path(unquote(path)).name
    return filename or "download"


def _media_type_from_filename(name: str) -> str:
    """
    Guess media type from a filename.

    :param name: Filename to inspect.
    :type name: str
    :return: Guessed media type or application/octet-stream.
    :rtype: str
    """

    media_type, _ = mimetypes.guess_type(name)
    return media_type or "application/octet-stream"


@dataclass(frozen=True)
class SourcePayload:
    """
    Loaded source payload for ingestion.

    :ivar data: Raw bytes from the source.
    :vartype data: bytes
    :ivar filename: Suggested filename for the payload.
    :vartype filename: str
    :ivar media_type: Internet Assigned Numbers Authority media type for the payload.
    :vartype media_type: str
    :ivar source_uri: Source uniform resource identifier used to load the payload.
    :vartype source_uri: str
    """

    data: bytes
    filename: str
    media_type: str
    source_uri: str


def load_source(source: str | Path, *, source_uri: Optional[str] = None) -> SourcePayload:
    """
    Load bytes from a source reference.

    :param source: File path or uniform resource locator to load.
    :type source: str or Path
    :param source_uri: Optional override for the source uniform resource identifier.
    :type source_uri: str or None
    :return: Source payload with bytes and metadata.
    :rtype: SourcePayload
    :raises ValueError: If a file:// uniform resource identifier has a non-local host.
    :raises NotImplementedError: If the uniform resource identifier scheme is unsupported.
    """

    if isinstance(source, Path):
        path = source.resolve()
        media_type = _media_type_from_filename(path.name)
        if path.suffix.lower() in {".md", ".markdown"}:
            media_type = "text/markdown"
        return SourcePayload(
            data=path.read_bytes(),
            filename=path.name,
            media_type=media_type,
            source_uri=source_uri or path.as_uri(),
        )

    if _looks_like_uri(source):
        parsed = urlparse(source)
        if parsed.scheme == "file":
            if parsed.netloc not in ("", "localhost"):
                raise ValueError(f"Unsupported file uniform resource identifier host: {parsed.netloc!r}")
            path = Path(unquote(parsed.path)).resolve()
            return load_source(path, source_uri=source_uri or source)

        if parsed.scheme in {"http", "https"}:
            request = Request(source, headers={"User-Agent": "biblicus/0"})
            with urlopen(request, timeout=30) as response:
                response_bytes = response.read()
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip()
                filename = _filename_from_url_path(parsed.path)
                media_type = content_type or _media_type_from_filename(filename)
                if Path(filename).suffix.lower() in {".md", ".markdown"}:
                    media_type = "text/markdown"
                return SourcePayload(
                    data=response_bytes,
                    filename=filename,
                    media_type=media_type,
                    source_uri=source_uri or source,
                )

        raise NotImplementedError(
            f"Unsupported source uniform resource identifier scheme: {parsed.scheme}://"
        )

    path = Path(source).resolve()
    return load_source(path, source_uri=source_uri)
