"""
Security helpers for standalone scripts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
import tarfile
import shutil
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]


def resolve_within_repo(
    path_value: str | Path,
    *,
    require_exists: bool,
    allow_temp_dir: bool = False,
) -> Path:
    """
    Resolve a path and enforce repository-root confinement.

    :param path_value: Input path value.
    :type path_value: str | Path
    :param require_exists: Whether the resolved path must already exist.
    :type require_exists: bool
    :param allow_temp_dir: Whether to also allow the system temporary directory root.
    :type allow_temp_dir: bool
    :return: Resolved, validated path.
    :rtype: Path
    :raises ValueError: If the path escapes all allowed roots.
    :raises FileNotFoundError: If required path does not exist.
    """
    resolved = Path(path_value).expanduser().resolve()
    allowed_roots = [REPO_ROOT]
    if allow_temp_dir:
        allowed_roots.append(Path(tempfile.gettempdir()).resolve())
    if not any((resolved == root) or (root in resolved.parents) for root in allowed_roots):
        raise ValueError(
            f"Path must be within one of: {', '.join(str(root) for root in allowed_roots)}"
        )
    if require_exists and not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")
    return resolved


def resolve_within(base_dir: Path, path_value: str | Path, *, require_exists: bool) -> Path:
    """
    Resolve a path and enforce confinement to a base directory.

    :param base_dir: Allowed root directory.
    :type base_dir: Path
    :param path_value: Input path value.
    :type path_value: str | Path
    :param require_exists: Whether the resolved path must already exist.
    :type require_exists: bool
    :return: Resolved, validated path.
    :rtype: Path
    :raises ValueError: If the path escapes the base directory.
    :raises FileNotFoundError: If required path does not exist.
    """
    base = base_dir.resolve()
    resolved = Path(path_value).expanduser().resolve()
    try:
        resolved.relative_to(base)
    except ValueError as error:
        raise ValueError(f"Path must be within {base}") from error
    if require_exists and not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")
    return resolved


def validate_https_url(url: str, *, allowed_hosts: Iterable[str]) -> str:
    """
    Validate HTTPS URL and host allowlist.

    :param url: URL to validate.
    :type url: str
    :param allowed_hosts: Allowed hostnames.
    :type allowed_hosts: Iterable[str]
    :return: Validated URL.
    :rtype: str
    :raises ValueError: If URL scheme or host is invalid.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme != "https":
        raise ValueError(f"Only https URLs are allowed: {url}")
    if host not in set(allowed_hosts):
        raise ValueError(f"Host is not allowed: {host}")
    return url


def safe_extract_tar(archive_path: Path, destination_dir: Path) -> None:
    """
    Safely extract tar archive members to a destination directory.

    :param archive_path: Tar archive path.
    :type archive_path: Path
    :param destination_dir: Extraction destination.
    :type destination_dir: Path
    :return: None
    :rtype: None
    :raises ValueError: If a member path is unsafe.
    """
    target_root = destination_dir.resolve()
    with tarfile.open(archive_path, "r:*") as archive:
        for member in archive.getmembers():
            member_name = member.name.lstrip("/")
            if not member_name:
                continue
            member_path = (target_root / member_name).resolve()
            try:
                member_path.relative_to(target_root)
            except ValueError as error:
                raise ValueError(f"Unsafe archive member path: {member.name}") from error
            if member.issym() or member.islnk():
                raise ValueError(f"Refusing symlink/hardlink in archive member: {member.name}")
            if member.isdir():
                member_path.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            member_path.parent.mkdir(parents=True, exist_ok=True)
            extracted_file = archive.extractfile(member)
            if extracted_file is None:
                continue
            with extracted_file, member_path.open("wb") as output_handle:
                shutil.copyfileobj(extracted_file, output_handle)
