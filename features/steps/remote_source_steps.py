from __future__ import annotations

import io
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from behave import given, then, when

from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _meta_dir(corpus: Path) -> Path:
    return corpus / "metadata"


def _write_corpus_config(corpus: Path, config: Dict[str, Any]) -> None:
    meta_dir = _meta_dir(corpus)
    meta_dir.mkdir(parents=True, exist_ok=True)
    config_path = meta_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _load_catalog(corpus: Path) -> Dict[str, Any]:
    catalog_path = _meta_dir(corpus) / "catalog.json"
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def _ensure_fake_boto3(context) -> None:
    if getattr(context, "_fake_boto3_remote_installed", False):
        return
    original_modules = {}
    if "boto3" in sys.modules:
        original_modules["boto3"] = sys.modules["boto3"]

    class FakeS3Client:
        def list_objects_v2(self, *, Bucket: str, Prefix: str = "", **kwargs) -> Dict[str, Any]:
            _ = Bucket
            _ = kwargs
            objects = []
            for obj in context.fake_s3_objects:
                if not obj.key.startswith(Prefix):
                    continue
                objects.append(
                    {
                        "Key": obj.key,
                        "ETag": obj.etag,
                        "LastModified": obj.last_modified,
                        "Size": len(obj.content),
                        "ContentType": obj.content_type,
                    }
                )
            return {"Contents": objects}

        def get_object(self, *, Bucket: str, Key: str) -> Dict[str, Any]:
            _ = Bucket
            for obj in context.fake_s3_objects:
                if obj.key == Key:
                    return {
                        "Body": io.BytesIO(obj.content),
                        "ETag": obj.etag,
                        "LastModified": obj.last_modified,
                        "ContentType": obj.content_type,
                    }
            raise KeyError(f"Missing object: {Key}")

    def client(service_name: str, **kwargs):
        _ = kwargs
        if service_name != "s3":
            raise ValueError(f"Unsupported service: {service_name}")
        return FakeS3Client()

    boto3_module = types.ModuleType("boto3")
    boto3_module.client = client
    sys.modules["boto3"] = boto3_module
    context._fake_boto3_remote_installed = True
    context._fake_boto3_remote_original = original_modules

    if not hasattr(context, "fake_s3_objects"):
        context.fake_s3_objects = []


def _install_boto3_unavailable(context) -> None:
    if getattr(context, "_fake_boto3_remote_unavailable", False):
        return
    original_modules = {}
    if "boto3" in sys.modules:
        original_modules["boto3"] = sys.modules["boto3"]
    sys.modules.pop("boto3", None)

    class _Blocker:
        def find_spec(self, fullname, path, target=None):
            if fullname == "boto3" or fullname.startswith("boto3."):
                raise ImportError("boto3 blocked for test")
            return None

    blocker = _Blocker()
    sys.meta_path.insert(0, blocker)
    context._fake_boto3_remote_unavailable = True
    context._fake_boto3_remote_blocker = blocker
    context._fake_boto3_remote_original = original_modules


def _ensure_fake_azure_blob(context) -> None:
    if getattr(context, "_fake_azure_blob_installed", False):
        return
    original_modules = {}
    for name in [
        "azure",
        "azure.storage",
        "azure.storage.blob",
    ]:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    class FakeDownloader:
        def __init__(self, blob) -> None:
            self._blob = blob

        def readall(self) -> bytes:
            return self._blob.content

    class ContainerClient:
        def __init__(self, *, account: str, container: str, credential: object) -> None:
            _ = credential
            self._account = account
            self._container = container

        @classmethod
        def from_connection_string(cls, conn_str: str, container_name: str):
            _ = conn_str
            return cls(account="acct", container=container_name, credential=object())

        @classmethod
        def from_account_url(cls, account_url: str, container_name: str, credential: object):
            _ = account_url
            return cls(account="acct", container=container_name, credential=credential)

        def list_blobs(self, *, name_starts_with: str = ""):
            for blob in context.fake_azure_blobs:
                if not blob.name.startswith(name_starts_with):
                    continue
                yield types.SimpleNamespace(
                    name=blob.name,
                    etag=blob.etag,
                    last_modified=blob.last_modified,
                    size=len(blob.content),
                    content_settings=types.SimpleNamespace(content_type=blob.content_type),
                )

        def download_blob(self, blob: str):
            for obj in context.fake_azure_blobs:
                if obj.name == blob:
                    return FakeDownloader(obj)
            raise KeyError(f"Missing blob: {blob}")

    azure_module = types.ModuleType("azure")
    storage_module = types.ModuleType("azure.storage")
    blob_module = types.ModuleType("azure.storage.blob")
    blob_module.ContainerClient = ContainerClient
    storage_module.blob = blob_module
    azure_module.storage = storage_module
    sys.modules["azure"] = azure_module
    sys.modules["azure.storage"] = storage_module
    sys.modules["azure.storage.blob"] = blob_module

    context._fake_azure_blob_installed = True
    context._fake_azure_blob_original = original_modules
    if not hasattr(context, "fake_azure_blobs"):
        context.fake_azure_blobs = []


def _install_azure_blob_unavailable(context) -> None:
    if getattr(context, "_fake_azure_blob_unavailable", False):
        return
    original_modules = {}
    for name in [
        "azure",
        "azure.storage",
        "azure.storage.blob",
    ]:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]
        sys.modules.pop(name, None)

    class _Blocker:
        def find_spec(self, fullname, path, target=None):
            if fullname.startswith("azure.storage.blob"):
                raise ImportError("azure blob blocked for test")
            return None

    blocker = _Blocker()
    sys.meta_path.insert(0, blocker)
    context._fake_azure_blob_unavailable = True
    context._fake_azure_blob_blocker = blocker
    context._fake_azure_blob_original = original_modules


def _parse_timestamp(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)


@given(
    'a remote S3 source is configured for corpus "{corpus_name}" with bucket "{bucket}" and prefix "{prefix}"'
)
def step_configure_s3_source(context, corpus_name: str, bucket: str, prefix: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    config = {
        "schema_version": 2,
        "created_at": "2026-02-19T12:00:00Z",
        "corpus_uri": corpus.as_uri(),
        "raw_dir": ".",
        "source": {
            "kind": "s3",
            "name": "demo",
            "bucket": bucket,
            "prefix": prefix,
        },
    }
    _write_corpus_config(corpus, config)


@given(
    'a remote Azure Blob source is configured for corpus "{corpus_name}" with account "{account}" and container "{container}" and prefix "{prefix}"'
)
def step_configure_azure_source(
    context, corpus_name: str, account: str, container: str, prefix: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    config = {
        "schema_version": 2,
        "created_at": "2026-02-19T12:00:00Z",
        "corpus_uri": corpus.as_uri(),
        "raw_dir": ".",
        "source": {
            "kind": "azure-blob",
            "name": "demo",
            "container": container,
            "prefix": prefix,
            "account_name": account,
        },
    }
    _write_corpus_config(corpus, config)


@given("a fake S3 source contains objects:")
@when("a fake S3 source contains objects:")
def step_fake_s3_objects(context) -> None:
    _ensure_fake_boto3(context)
    objects = []
    for row in context.table:
        objects.append(
            types.SimpleNamespace(
                key=row["key"],
                content=row["content"].encode("utf-8"),
                etag=row["etag"],
                last_modified=_parse_timestamp(row["last_modified"]),
                content_type="text/markdown",
            )
        )
    context.fake_s3_objects = objects


@given("a fake Azure Blob source contains blobs:")
@when("a fake Azure Blob source contains blobs:")
def step_fake_azure_blobs(context) -> None:
    _ensure_fake_azure_blob(context)
    blobs = []
    for row in context.table:
        blobs.append(
            types.SimpleNamespace(
                name=row["name"],
                content=row["content"].encode("utf-8"),
                etag=row["etag"],
                last_modified=_parse_timestamp(row["last_modified"]),
                content_type="text/markdown",
            )
        )
    context.fake_azure_blobs = blobs


@given("the azure blob dependency is unavailable")
def step_azure_blob_dependency_unavailable(context) -> None:
    _install_azure_blob_unavailable(context)


@when('I pull the remote source for corpus "{corpus_name}"')
def step_pull_remote_source(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        ["--corpus", str(corpus), "source", "pull"],
        extra_env=getattr(context, "extra_env", None),
    )
    context.last_result = result


@then("the catalog contains source uris:")
def step_catalog_contains_uris(context) -> None:
    corpus = context.last_corpus_root
    catalog = _load_catalog(corpus)
    source_values = {item["source_uri"] for item in catalog["items"].values()}
    for row in context.table:
        assert row[0] in source_values, f"Missing source uri: {row[0]}"


@then('the catalog does not contain source uri "{source_uri}"')
def step_catalog_missing_uri(context, source_uri: str) -> None:
    corpus = context.last_corpus_root
    catalog = _load_catalog(corpus)
    source_values = {item["source_uri"] for item in catalog["items"].values()}
    assert source_uri not in source_values, f"Unexpected source uri: {source_uri}"


@then('the catalog item for source uri "{source_uri}" has biblicus source etag "{etag}"')
def step_catalog_item_etag(context, source_uri: str, etag: str) -> None:
    corpus = context.last_corpus_root
    catalog = _load_catalog(corpus)
    for item in catalog["items"].values():
        if item["source_uri"] == source_uri:
            metadata = item.get("metadata") or {}
            biblicus_block = metadata.get("biblicus") or {}
            actual = biblicus_block.get("source_etag")
            assert actual == etag, f"Expected etag {etag} but got {actual}"
            return
    raise AssertionError(f"Source uri not found: {source_uri}")
