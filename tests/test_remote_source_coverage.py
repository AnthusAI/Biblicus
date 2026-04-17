import io
import sys
import types
from datetime import datetime, timezone

import pytest

from biblicus.models import RemoteCorpusSourceConfig
from biblicus.remote_sources import (
    AzureBlobRemoteSource,
    S3RemoteSource,
    _isoformat_timestamp,
    _normalize_etag,
    iter_items,
)
from biblicus.user_config import (
    BiblicusUserConfig,
    OpenAiUserConfig,
    SourceProfileConfig,
    resolve_openai_api_key,
    resolve_source_profile,
)
from biblicus.testing_values import build_test_value


def _install_fake_boto3(monkeypatch, *, objects):
    class FakeClient:
        def list_objects_v2(self, *, Bucket, Prefix="", **kwargs):
            _ = Bucket
            _ = kwargs
            contents = []
            for obj in objects:
                if not obj["Key"].startswith(Prefix):
                    continue
                contents.append(obj)
            return {"Contents": contents}

        def get_object(self, *, Bucket, Key):
            _ = Bucket
            for obj in objects:
                if obj["Key"] == Key:
                    return {
                        "Body": io.BytesIO(obj["Body"]),
                        "ETag": obj.get("ETag"),
                        "LastModified": obj.get("LastModified"),
                        "ContentType": obj.get("ContentType"),
                    }
            raise KeyError(f"Missing object: {Key}")

    def client(service_name, **kwargs):
        _ = kwargs
        if service_name != "s3":
            raise ValueError(f"Unsupported service: {service_name}")
        return FakeClient()

    module = types.ModuleType("boto3")
    module.client = client
    monkeypatch.setitem(sys.modules, "boto3", module)


def _install_fake_azure_blob(monkeypatch, *, blobs):
    class FakeDownloader:
        def __init__(self, payload):
            self._payload = payload

        def readall(self):
            return self._payload

    class ContainerClient:
        def __init__(self, *, account, container, credential):
            _ = credential
            self._account = account
            self._container = container

        @classmethod
        def from_connection_string(cls, conn_str, container_name):
            _ = conn_str
            return cls(account="acct", container=container_name, credential=object())

        @classmethod
        def from_account_url(cls, account_url, container_name, credential):
            _ = account_url
            return cls(account="acct", container=container_name, credential=credential)

        def list_blobs(self, *, name_starts_with=""):
            for blob in blobs:
                if not blob["name"].startswith(name_starts_with):
                    continue
                content_settings = blob.get("content_settings")
                if content_settings is None and "content_settings" not in blob:
                    content_settings = types.SimpleNamespace(content_type=blob.get("content_type"))
                yield types.SimpleNamespace(
                    name=blob["name"],
                    etag=blob.get("etag"),
                    last_modified=blob.get("last_modified"),
                    size=len(blob.get("content") or b""),
                    content_settings=content_settings,
                )

        def download_blob(self, blob):
            for obj in blobs:
                if obj["name"] == blob:
                    return FakeDownloader(obj.get("content") or b"")
            raise KeyError(f"Missing blob: {blob}")

    azure_module = types.ModuleType("azure")
    storage_module = types.ModuleType("azure.storage")
    blob_module = types.ModuleType("azure.storage.blob")
    blob_module.ContainerClient = ContainerClient
    storage_module.blob = blob_module
    azure_module.storage = storage_module
    monkeypatch.setitem(sys.modules, "azure", azure_module)
    monkeypatch.setitem(sys.modules, "azure.storage", storage_module)
    monkeypatch.setitem(sys.modules, "azure.storage.blob", blob_module)


def test_remote_source_helpers():
    assert _isoformat_timestamp(None) is None
    naive = datetime(2026, 2, 19, 12, 0, 0)
    assert _isoformat_timestamp(naive) == "2026-02-19T12:00:00Z"
    aware = datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc)
    assert _isoformat_timestamp(aware) == "2026-02-19T12:00:00Z"
    assert _normalize_etag(None) is None
    assert _normalize_etag("") is None
    assert _normalize_etag('"abc"') == "abc"


def test_s3_remote_source_list_and_fetch(monkeypatch):
    last_modified = datetime(2026, 2, 19, 10, 0, 0, tzinfo=timezone.utc)
    _install_fake_boto3(
        monkeypatch,
        objects=[
            {
                "Key": "docs/a.md",
                "ETag": '"etag1"',
                "LastModified": last_modified,
                "Size": 5,
                "ContentType": "text/markdown",
                "Body": b"alpha",
            },
            {
                "Key": "docs/",
                "ETag": None,
                "LastModified": last_modified,
                "Size": 0,
                "ContentType": None,
                "Body": b"",
            },
        ],
    )
    config = RemoteCorpusSourceConfig(
        kind="s3",
        profile="profile",
        name="demo",
        bucket="bucket",
        prefix="docs/",
    )
    aws = SourceProfileConfig(
        name="profile",
        kind="s3",
        access_key_id="id",
        secret_access_key=build_test_value("cfg", "s3", "secret"),
        session_token=None,
        region="us-east-1",
    )
    source = S3RemoteSource(config, aws)
    items = source.list_items()
    assert len(items) == 1
    assert items[0].etag == "etag1"
    assert items[0].last_modified == "2026-02-19T10:00:00Z"
    payload, content_type = source.fetch_bytes(items[0])
    assert payload == b"alpha"
    assert content_type == "text/markdown"
    assert iter_items(source)[0].source_uri == "s3://bucket/docs/a.md"


def test_s3_remote_source_missing_credentials(monkeypatch):
    _install_fake_boto3(monkeypatch, objects=[])
    config = RemoteCorpusSourceConfig(kind="s3", profile="profile", name="demo", bucket="bucket")
    aws = SourceProfileConfig(
        name="profile",
        kind="s3",
        access_key_id=None,
        secret_access_key=None,
        session_token=None,
        region=None,
    )
    source = S3RemoteSource(config, aws)
    assert source.list_items() == []


def test_azure_remote_source_list_and_fetch(monkeypatch):
    last_modified = datetime(2026, 2, 19, 10, 0, 0, tzinfo=timezone.utc)
    _install_fake_azure_blob(
        monkeypatch,
        blobs=[
            {
                "name": "docs/a.md",
                "etag": '"etag1"',
                "last_modified": last_modified,
                "content": b"alpha",
                "content_type": "text/markdown",
            }
        ],
    )
    config = RemoteCorpusSourceConfig(
        kind="azure-blob",
        profile="profile",
        name="demo",
        container="container",
        prefix="docs/",
    )
    azure = SourceProfileConfig(
        name="profile",
        kind="azure-blob",
        connection_string="UseDevelopmentStorage=true",
        account_name="acct",
        account_key=None,
    )
    source = AzureBlobRemoteSource(config, azure)
    items = source.list_items()
    assert len(items) == 1
    assert items[0].etag == "etag1"
    assert items[0].last_modified == "2026-02-19T10:00:00Z"
    payload, content_type = source.fetch_bytes(items[0])
    assert payload == b"alpha"
    assert content_type == "text/markdown"
    assert iter_items(source)[0].source_uri == "azure-blob://acct/container/docs/a.md"


def test_azure_remote_source_missing_credentials(monkeypatch):
    _install_fake_azure_blob(monkeypatch, blobs=[])
    config = RemoteCorpusSourceConfig(
        kind="azure-blob",
        profile="profile",
        name="demo",
        container="container",
        prefix="docs/",
    )
    azure = SourceProfileConfig(
        name="profile",
        kind="azure-blob",
        connection_string=None,
        account_name=None,
        account_key=None,
    )
    source = AzureBlobRemoteSource(config, azure)
    assert source.list_items() == []


def test_azure_remote_source_account_url_branch(monkeypatch):
    last_modified = datetime(2026, 2, 19, 10, 0, 0, tzinfo=timezone.utc)
    _install_fake_azure_blob(
        monkeypatch,
        blobs=[
            {
                "name": "docs/",
                "etag": None,
                "last_modified": last_modified,
                "content": b"",
                "content_settings": None,
            },
            {
                "name": "docs/x.md",
                "etag": None,
                "last_modified": last_modified,
                "content": b"alpha",
                "content_settings": None,
            },
        ],
    )
    config = RemoteCorpusSourceConfig(
        kind="azure-blob",
        profile="profile",
        name="demo",
        container="container",
        prefix="docs/",
    )
    azure = SourceProfileConfig(
        name="profile",
        kind="azure-blob",
        connection_string=None,
        account_name="acct",
        account_key="key",
    )
    source = AzureBlobRemoteSource(config, azure)
    items = source.list_items()
    assert len(items) == 1
    assert items[0].source_uri == "azure-blob://acct/container/docs/x.md"


def test_iter_items_rejects_unknown_source():
    with pytest.raises(ValueError):
        iter_items(object())


def test_remote_corpus_source_config_validation():
    with pytest.raises(ValueError):
        RemoteCorpusSourceConfig(kind="gcs", profile="profile", name="demo")
    with pytest.raises(ValueError):
        RemoteCorpusSourceConfig(kind="s3", profile="profile", name="demo")
    with pytest.raises(ValueError):
        RemoteCorpusSourceConfig(kind="azure-blob", profile="profile", name="demo")
    RemoteCorpusSourceConfig(
        kind="azure-blob",
        profile="profile",
        name="demo",
        container="container",
    )


def test_resolve_openai_api_key_from_config(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    configured_key = build_test_value("cfg", "openai")
    cfg = BiblicusUserConfig(openai=OpenAiUserConfig(api_key=configured_key))
    assert resolve_openai_api_key(config=cfg) == configured_key


def test_resolve_s3_profile_env_override(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "env-id")
    env_secret = build_test_value("env", "secret")
    env_session = build_test_value("env", "session")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", env_secret)
    monkeypatch.setenv("AWS_SESSION_TOKEN", env_session)
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    cfg = BiblicusUserConfig(
        sources=[
            SourceProfileConfig(
                name="prod",
                kind="s3",
                access_key_id="cfg-id",
                secret_access_key=build_test_value("cfg", "secret"),
                session_token=None,
                region="us-east-1",
            )
        ]
    )
    resolved = resolve_source_profile("prod", config=cfg)
    assert resolved.access_key_id == "env-id"
    assert resolved.secret_access_key == env_secret
    assert resolved.session_token == env_session
    assert resolved.region == "us-west-2"


def test_resolve_azure_profile_env_override(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "env-acct")
    monkeypatch.setenv("AZURE_STORAGE_KEY", "env-key")
    cfg = BiblicusUserConfig(
        sources=[
            SourceProfileConfig(
                name="azure",
                kind="azure-blob",
                connection_string="cfg-conn",
                account_name="cfg-acct",
                account_key=build_test_value("cfg", "key"),
            )
        ]
    )
    resolved = resolve_source_profile("azure", config=cfg)
    assert resolved.connection_string == "UseDevelopmentStorage=true"
    assert resolved.account_name == "env-acct"
    assert resolved.account_key == "env-key"
