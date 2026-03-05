"""
Remote source adapters for Biblicus corpora.
"""

from __future__ import annotations

import hashlib
import mimetypes
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from .errors import RemoteSourceDependencyError
from .models import RemoteCorpusSourceConfig, RemoteSourceItem
from .user_config import SourceProfileConfig


def _isoformat_timestamp(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_etag(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    stripped = value.strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        stripped = stripped[1:-1]
    return stripped or None


class S3RemoteSource:
    """
    Remote source adapter for Amazon S3.
    """

    def __init__(self, config: RemoteCorpusSourceConfig, aws: SourceProfileConfig) -> None:
        self._config = config
        self._aws = aws
        self._client = self._build_client()

    def _build_client(self):
        try:
            import boto3
        except ImportError as import_error:
            raise RemoteSourceDependencyError(
                'Remote S3 sources require boto3. Install it with pip install "biblicus[aws]".'
            ) from import_error
        return boto3.client(
            "s3",
            region_name=self._aws.region,
            aws_access_key_id=self._aws.access_key_id,
            aws_secret_access_key=self._aws.secret_access_key,
            aws_session_token=self._aws.session_token,
            endpoint_url=self._aws.endpoint_url,
        )

    def list_items(self) -> list[RemoteSourceItem]:
        """
        List items available in the configured S3 bucket and prefix.

        :return: Remote source items describing each object.
        :rtype: list[RemoteSourceItem]
        :raises ValueError: If required configuration fields are missing.
        """
        bucket = self._config.bucket
        prefix = self._config.prefix or ""
        response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        contents = response.get("Contents") or []
        items = []
        for entry in contents:
            key = entry.get("Key")
            if not key or key.endswith("/"):
                continue
            etag = _normalize_etag(entry.get("ETag"))
            last_modified = _isoformat_timestamp(entry.get("LastModified"))
            size = int(entry.get("Size") or 0)
            content_type = entry.get("ContentType")
            items.append(
                RemoteSourceItem(
                    key=key,
                    source_uri=f"s3://{bucket}/{key}",
                    etag=etag,
                    last_modified=last_modified,
                    size=size,
                    content_type=content_type,
                )
            )
        return items

    def fetch_bytes(self, item: RemoteSourceItem) -> Tuple[bytes, Optional[str]]:
        """
        Fetch the raw bytes for a remote S3 object.

        :param item: Remote source item to download.
        :type item: RemoteSourceItem
        :return: Tuple containing the object bytes and content type.
        :rtype: tuple[bytes, Optional[str]]
        """
        response = self._client.get_object(Bucket=self._config.bucket, Key=item.key)
        body = response["Body"].read()
        content_type = response.get("ContentType") or item.content_type
        return body, content_type


class AzureBlobRemoteSource:
    """
    Remote source adapter for Azure Blob Storage.
    """

    def __init__(self, config: RemoteCorpusSourceConfig, azure: SourceProfileConfig) -> None:
        self._config = config
        self._azure = azure
        self._client = self._build_client()

    def _build_client(self):
        try:
            from azure.storage.blob import ContainerClient
        except ImportError as import_error:
            raise RemoteSourceDependencyError(
                "Remote Azure Blob sources require azure-storage-blob. "
                'Install it with pip install "biblicus[azure]".'
            ) from import_error
        if self._azure.connection_string:
            return ContainerClient.from_connection_string(
                self._azure.connection_string, self._config.container
            )
        account_name = self._azure.account_name
        account_url = self._azure.account_url or f"https://{account_name}.blob.core.windows.net"
        return ContainerClient.from_account_url(
            account_url, self._config.container, credential=self._azure.account_key
        )

    def list_items(self) -> list[RemoteSourceItem]:
        """
        List items available in the configured Azure blob container and prefix.

        :return: Remote source items describing each blob.
        :rtype: list[RemoteSourceItem]
        :raises ValueError: If required configuration fields are missing.
        """
        prefix = self._config.prefix or ""
        items = []
        for entry in self._client.list_blobs(name_starts_with=prefix):
            key = entry.name
            if not key or key.endswith("/"):
                continue
            etag = _normalize_etag(getattr(entry, "etag", None))
            last_modified = _isoformat_timestamp(getattr(entry, "last_modified", None))
            size = int(getattr(entry, "size", 0) or 0)
            content_type = None
            content_settings = getattr(entry, "content_settings", None)
            if content_settings is not None:
                content_type = getattr(content_settings, "content_type", None)
            account = self._azure.account_name or "account"
            items.append(
                RemoteSourceItem(
                    key=key,
                    source_uri=f"azure-blob://{account}/{self._config.container}/{key}",
                    etag=etag,
                    last_modified=last_modified,
                    size=size,
                    content_type=content_type,
                )
            )
        return items

    def fetch_bytes(self, item: RemoteSourceItem) -> Tuple[bytes, Optional[str]]:
        """
        Fetch the raw bytes for a remote Azure blob.

        :param item: Remote source item to download.
        :type item: RemoteSourceItem
        :return: Tuple containing the blob bytes and content type.
        :rtype: tuple[bytes, Optional[str]]
        """
        downloader = self._client.download_blob(item.key)
        content = downloader.readall()
        return content, item.content_type


def parse_google_drive_folder_id(folder_url: str) -> Optional[str]:
    """
    Parse the folder identifier from a Google Drive folder URL.

    :param folder_url: Google Drive folder URL.
    :type folder_url: str
    :return: Parsed folder identifier when present.
    :rtype: str or None
    """
    parsed = urlparse(folder_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if "folders" in path_parts:
        index = path_parts.index("folders")
        if len(path_parts) > index + 1:
            candidate = path_parts[index + 1].strip()
            if candidate:
                return candidate
    query_id = parse_qs(parsed.query).get("id", [])
    if query_id:
        candidate = (query_id[0] or "").strip()
        if candidate:
            return candidate
    return None


class GoogleDriveRemoteSource:
    """
    Remote source adapter for Google Drive shared folders.
    """

    def __init__(self, config: RemoteCorpusSourceConfig, profile: SourceProfileConfig) -> None:
        self._config = config
        self._profile = profile
        self._mirror_dir = Path(tempfile.mkdtemp(prefix="biblicus-gdrive-"))
        self._mirrored = False
        self._closed = False

    def close(self) -> None:
        """
        Remove the local mirror directory.

        :return: None.
        :rtype: None
        """
        if self._closed:
            return
        self._closed = True
        if self._mirror_dir.exists():
            shutil.rmtree(self._mirror_dir, ignore_errors=True)

    def __enter__(self) -> "GoogleDriveRemoteSource":
        """
        Enter the context manager and return the source.

        :return: The current Google Drive remote source instance.
        :rtype: GoogleDriveRemoteSource
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Exit the context manager and clean up mirror resources.

        :param exc_type: Exception type if raised.
        :type exc_type: type or None
        :param exc_value: Exception value if raised.
        :type exc_value: BaseException or None
        :param traceback: Traceback if raised.
        :type traceback: TracebackType or None
        :return: None.
        :rtype: None
        """
        _ = exc_type
        _ = exc_value
        _ = traceback
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            return

    def _mirror_folder(self) -> None:
        if self._mirrored:
            return
        folder_url = (self._config.folder_url or "").strip()
        if not folder_url:
            raise ValueError("Remote Google Drive source requires folder_url")
        try:
            import gdown
        except ImportError as import_error:
            raise RemoteSourceDependencyError(
                "Remote Google Drive sources require gdown. "
                'Install it with pip install "biblicus[google-drive]".'
            ) from import_error
        planned_downloads = gdown.download_folder(
            url=folder_url,
            output=str(self._mirror_dir),
            quiet=True,
            remaining_ok=True,
            skip_download=True,
        )
        if planned_downloads is None:
            raise ValueError("Failed to list Google Drive folder contents")
        prefix = self._config.prefix or ""
        for planned in planned_downloads:
            if prefix and not str(planned.path).startswith(prefix):
                continue
            target = Path(planned.local_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            downloaded = self._download_file_by_id(file_id=str(planned.id), target=target)
            if not downloaded:
                try:
                    gdown.download(id=str(planned.id), output=str(target), quiet=True)
                    downloaded = True
                except Exception:
                    downloaded = False
            if not downloaded:
                continue
        self._mirrored = True

    def _download_file_by_id(self, *, file_id: str, target: Path) -> bool:
        query = urlencode({"id": file_id})
        url = f"https://drive.usercontent.google.com/download?{query}"
        request = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        try:
            with urlopen(request, timeout=120) as response:
                content_type = response.headers.get_content_type()
                if content_type == "text/html":
                    return False
                with target.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
        except Exception:
            return False
        return True

    def _content_root(self) -> Path:
        self._mirror_folder()
        return self._mirror_dir

    def list_items(self) -> list[RemoteSourceItem]:
        """
        List items mirrored from the configured Google Drive folder.

        :return: Remote source items describing each downloaded file.
        :rtype: list[RemoteSourceItem]
        """
        root = self._content_root()
        folder_url = (self._config.folder_url or "").strip()
        folder_id = parse_google_drive_folder_id(folder_url) or "folder"
        prefix = self._config.prefix or ""
        items = []
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue
            key = file_path.relative_to(root).as_posix()
            if prefix and not key.startswith(prefix):
                continue
            stat = file_path.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            media_type, _ = mimetypes.guess_type(file_path.name)
            etag = hashlib.sha256(file_path.read_bytes()).hexdigest()
            items.append(
                RemoteSourceItem(
                    key=key,
                    source_uri=f"gdrive://{folder_id}/{key}",
                    etag=etag,
                    last_modified=_isoformat_timestamp(last_modified),
                    size=int(stat.st_size),
                    content_type=media_type,
                )
            )
        return items

    def fetch_bytes(self, item: RemoteSourceItem) -> Tuple[bytes, Optional[str]]:
        """
        Fetch the raw bytes for a mirrored Google Drive file.

        :param item: Remote source item to download.
        :type item: RemoteSourceItem
        :return: Tuple containing file bytes and content type.
        :rtype: tuple[bytes, Optional[str]]
        """
        path = self._content_root() / item.key
        payload = path.read_bytes()
        media_type, _ = mimetypes.guess_type(path.name)
        content_type = item.content_type or media_type
        return payload, content_type


def iter_items(source: object) -> Iterable[RemoteSourceItem]:
    """
    Return the iterable of items for a supported remote source adapter.

    :param source: Remote source adapter instance.
    :type source: object
    :return: Iterable of remote source items.
    :rtype: Iterable[RemoteSourceItem]
    :raises ValueError: If the source adapter type is unsupported.
    """
    if isinstance(source, S3RemoteSource):
        return source.list_items()
    if isinstance(source, AzureBlobRemoteSource):
        return source.list_items()
    if isinstance(source, GoogleDriveRemoteSource):
        return source.list_items()
    raise ValueError("Unsupported remote source")
