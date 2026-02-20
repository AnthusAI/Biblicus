from __future__ import annotations

import io
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from behave import given, then, when

from biblicus.models import RemoteCorpusSourceConfig
from biblicus.remote_sources import (
    AzureBlobRemoteSource,
    S3RemoteSource,
    _isoformat_timestamp,
    _normalize_etag,
    iter_items,
)
from biblicus.user_config import SourceProfileConfig

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


def _write_source_profile(
    context, *, profile_name: str, kind: str, extra_fields: Optional[Dict[str, Any]] = None
) -> None:
    import yaml

    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    path = Path(workdir) / ".biblicus" / "config.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {"name": profile_name, "kind": kind}
    if extra_fields:
        profile.update(extra_fields)
    payload = {"sources": [profile]}
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")


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
                content_settings = None
                if blob.content_type is not None:
                    content_settings = types.SimpleNamespace(content_type=blob.content_type)
                yield types.SimpleNamespace(
                    name=blob.name,
                    etag=blob.etag,
                    last_modified=blob.last_modified,
                    size=len(blob.content),
                    content_settings=content_settings,
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
    _write_source_profile(context, profile_name="demo-profile", kind="s3")
    config = {
        "schema_version": 2,
        "created_at": "2026-02-19T12:00:00Z",
        "corpus_uri": corpus.as_uri(),
        "raw_dir": ".",
        "source": {
            "kind": "s3",
            "profile": "demo-profile",
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
    _write_source_profile(
        context,
        profile_name="demo-profile",
        kind="azure-blob",
        extra_fields={"account_name": account},
    )
    config = {
        "schema_version": 2,
        "created_at": "2026-02-19T12:00:00Z",
        "corpus_uri": corpus.as_uri(),
        "raw_dir": ".",
        "source": {
            "kind": "azure-blob",
            "profile": "demo-profile",
            "name": "demo",
            "container": container,
            "prefix": prefix,
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
        content_type = row.get("content_type", "text/markdown")
        if isinstance(content_type, str) and not content_type.strip():
            content_type = None
        blobs.append(
            types.SimpleNamespace(
                name=row["name"],
                content=row["content"].encode("utf-8"),
                etag=row["etag"],
                last_modified=_parse_timestamp(row["last_modified"]),
                content_type=content_type,
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


@when('I normalize a remote source etag "{etag}"')
def step_normalize_remote_source_etag(context, etag: str) -> None:
    context.normalized_etag = _normalize_etag(etag)


@when("I normalize a quoted remote source etag")
def step_normalize_remote_source_etag_quoted(context) -> None:
    context.normalized_etag = _normalize_etag('"etag"')


@when("I normalize a remote source etag with no value")
def step_normalize_remote_source_etag_empty(context) -> None:
    context.normalized_etag = _normalize_etag("")


@then('the normalized remote source etag equals "{etag}"')
def step_normalized_remote_source_etag_equals(context, etag: str) -> None:
    assert context.normalized_etag == etag


@then("the normalized remote source etag is None")
def step_normalized_remote_source_etag_none(context) -> None:
    assert context.normalized_etag is None


@when("I normalize a remote source timestamp with no value")
def step_normalize_remote_source_timestamp_none(context) -> None:
    context.normalized_timestamp = _isoformat_timestamp(None)


@when('I normalize a remote source timestamp "{timestamp}"')
def step_normalize_remote_source_timestamp(context, timestamp: str) -> None:
    parsed = datetime.fromisoformat(timestamp)
    context.normalized_timestamp = _isoformat_timestamp(parsed)


@then('the normalized remote source timestamp equals "{timestamp}"')
def step_normalized_remote_source_timestamp_equals(context, timestamp: str) -> None:
    assert context.normalized_timestamp == timestamp


@then("the normalized remote source timestamp is None")
def step_normalized_remote_source_timestamp_none(context) -> None:
    assert context.normalized_timestamp is None


@given("a configured fake S3 remote source adapter")
def step_configured_fake_s3_adapter(context) -> None:
    _ensure_fake_boto3(context)
    config = RemoteCorpusSourceConfig(
        kind="s3",
        profile="demo-profile",
        name="demo",
        bucket="demo",
        prefix="docs/",
    )
    aws = SourceProfileConfig(
        name="demo-profile",
        kind="s3",
        access_key_id="test-key",
        secret_access_key="test-secret",
        session_token=None,
        region=None,
    )
    context.s3_adapter = S3RemoteSource(config, aws)


@given("a configured fake Azure Blob remote source adapter")
def step_configured_fake_azure_adapter(context) -> None:
    _ensure_fake_azure_blob(context)
    config = RemoteCorpusSourceConfig(
        kind="azure-blob",
        profile="demo-profile",
        name="demo",
        container="demo",
        prefix="docs/",
    )
    azure = SourceProfileConfig(
        name="demo-profile",
        kind="azure-blob",
        connection_string="UseDevelopmentStorage=true",
    )
    context.azure_adapter = AzureBlobRemoteSource(config, azure)


@when("I iterate remote source items for the S3 adapter")
def step_iterate_s3_adapter(context) -> None:
    context.iterated_items = list(iter_items(context.s3_adapter))


@when("I iterate remote source items for the Azure adapter")
def step_iterate_azure_adapter(context) -> None:
    context.iterated_items = list(iter_items(context.azure_adapter))


@then("the iterated remote source item count is 1")
def step_iterated_item_count(context) -> None:
    assert len(context.iterated_items) == 1


@when("I iterate remote source items for an unsupported adapter")
def step_iterate_unsupported_adapter(context) -> None:
    try:
        iter_items(object())
    except Exception as exc:
        context.remote_source_iteration_error = str(exc)
    else:
        context.remote_source_iteration_error = None


@then('the remote source iteration error includes "{message}"')
def step_iteration_error_includes(context, message: str) -> None:
    assert context.remote_source_iteration_error is not None
    assert message in context.remote_source_iteration_error


def _attempt_remote_source_validate(context, payload: Dict[str, Any]) -> None:
    try:
        RemoteCorpusSourceConfig.model_validate(payload)
    except Exception as exc:
        context.remote_source_validation_error = str(exc)
    else:
        context.remote_source_validation_error = None


@when("I validate a remote source config with unsupported kind")
def step_validate_remote_source_invalid_kind(context) -> None:
    _attempt_remote_source_validate(
        context, {"kind": "gcs", "name": "demo", "profile": "demo-profile"}
    )


@when("I validate a remote source config without a profile")
def step_validate_remote_source_missing_profile(context) -> None:
    _attempt_remote_source_validate(context, {"kind": "s3", "name": "demo", "bucket": "demo"})


@when("I validate a remote source config without an S3 bucket")
def step_validate_remote_source_missing_bucket(context) -> None:
    _attempt_remote_source_validate(
        context, {"kind": "s3", "name": "demo", "profile": "demo-profile"}
    )


@when("I validate a remote source config without an Azure container")
def step_validate_remote_source_missing_container(context) -> None:
    _attempt_remote_source_validate(
        context, {"kind": "azure-blob", "name": "demo", "profile": "demo-profile"}
    )


@then('the remote source validation error includes "{message}"')
def step_remote_source_validation_error_includes(context, message: str) -> None:
    assert context.remote_source_validation_error is not None
    assert message in context.remote_source_validation_error
