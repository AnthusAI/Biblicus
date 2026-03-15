from __future__ import annotations

import json
from pathlib import Path
import types

from behave import given, then, when

from biblicus.constants import COLLECTION_SCHEMA_VERSION
from biblicus.corpus import Corpus
from biblicus.models import CorpusConfig

from features.environment import run_biblicus
from features.steps.remote_source_steps import _ensure_fake_azure_blob


def _collection_root(context, name: str) -> Path:
    return (context.workdir / "collections" / name).resolve()


def _write_collection_config(path: Path, payload: dict) -> None:
    meta_dir = path / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    config_path = meta_dir / "config.json"
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_source_profile(context, *, profile_name: str, kind: str, extra_fields: dict) -> None:
    import yaml

    path = Path(context.workdir) / ".biblicus" / "config.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"sources": [{"name": profile_name, "kind": kind, **extra_fields}]}
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")


def _load_catalog(corpus_path: Path) -> dict:
    catalog_path = corpus_path / "metadata" / "catalog.json"
    return json.loads(catalog_path.read_text(encoding="utf-8"))


@given('a collection "{name}" is configured for Azure Blob container "{container}"')
def step_configure_collection_azure(context, name: str, container: str) -> None:
    collection_root = _collection_root(context, name)
    _write_source_profile(
        context,
        profile_name="demo-profile",
        kind="azure-blob",
        extra_fields={
            "connection_string": "UseDevelopmentStorage=true",
            "account_name": "acct",
        },
    )
    payload = {
        "schema_version": COLLECTION_SCHEMA_VERSION,
        "created_at": "2026-02-20T00:00:00Z",
        "collection_name": name,
        "source": {
            "kind": "azure-blob",
            "profile": "demo-profile",
            "container": container,
            "prefix": "",
        },
        "discovery": {"mode": "subfolder", "depth": 1, "include_root_files": False},
        "corpus_root": f"corpora/{name}",
        "auto_create": True,
        "deletion_policy": "archive",
    }
    _write_collection_config(collection_root, payload)


@given('a collection "{name}" is configured to partition subfolders as tables')
def step_configure_collection_partition(context, name: str) -> None:
    collection_root = _collection_root(context, name)
    _write_source_profile(
        context,
        profile_name="demo-profile",
        kind="azure-blob",
        extra_fields={
            "connection_string": "UseDevelopmentStorage=true",
            "account_name": "acct",
        },
    )
    payload = {
        "schema_version": COLLECTION_SCHEMA_VERSION,
        "created_at": "2026-02-20T00:00:00Z",
        "collection_name": name,
        "source": {
            "kind": "azure-blob",
            "profile": "demo-profile",
            "container": name,
            "prefix": "",
        },
        "discovery": {"mode": "partition", "depth": 1, "include_root_files": False},
        "corpus_root": f"corpora/{name}",
        "auto_create": True,
        "deletion_policy": "archive",
    }
    _write_collection_config(collection_root, payload)


@given("the collection has remote subfolders:")
def step_collection_remote_subfolders(context) -> None:
    _ensure_fake_azure_blob(context)
    blobs = getattr(context, "fake_azure_blobs", [])
    for row in context.table:
        blobs.append(
            types.SimpleNamespace(
                name=f"{row['name']}/.keep",
                content=b"",
                etag="seed",
                last_modified=None,
                content_type="text/plain",
            )
        )
    context.fake_azure_blobs = blobs


@given('the remote folder "{folder}" contains objects:')
def step_collection_remote_objects(context, folder: str) -> None:
    _ensure_fake_azure_blob(context)
    blobs = getattr(context, "fake_azure_blobs", [])
    for row in context.table:
        blobs.append(
            types.SimpleNamespace(
                name=row["key"],
                content=row["content"].encode("utf-8"),
                etag="etag",
                last_modified=None,
                content_type="text/plain",
            )
        )
    context.fake_azure_blobs = blobs


@when('I pull the collection "{name}"')
def step_pull_collection(context, name: str) -> None:
    collection_root = _collection_root(context, name)
    result = run_biblicus(
        context,
        ["collection", "pull", "--collection", str(collection_root)],
        extra_env=getattr(context, "extra_env", None),
    )
    context.last_result = result


@then('a corpus exists at "{path}"')
def step_corpus_exists(context, path: str) -> None:
    corpus_path = Path(context.workdir) / path
    config_path = corpus_path / "metadata" / "config.json"
    assert config_path.is_file(), f"Missing corpus config at {config_path}"


@given('a corpus exists at "{path}"')
def step_given_corpus_exists(context, path: str) -> None:
    corpus_path = Path(context.workdir) / path
    Corpus.init(corpus_path, force=True)


@then('the corpus "{corpus_path}" contains a mirrored item for "{remote_key}"')
def step_corpus_contains_mirrored_item(context, corpus_path: str, remote_key: str) -> None:
    corpus_root = Path(context.workdir) / corpus_path
    config_path = corpus_root / "metadata" / "config.json"
    config = CorpusConfig.model_validate(json.loads(config_path.read_text(encoding="utf-8")))
    source = config.source
    assert source is not None
    source_name = source.name or source.container or source.bucket or "remote"
    relative_key = remote_key
    if source.prefix and relative_key.startswith(source.prefix):
        relative_key = relative_key[len(source.prefix) :].lstrip("/")
    item_path = corpus_root / "imports" / "remote" / source_name / relative_key
    assert item_path.is_file(), f"Missing mirrored item at {item_path}"


@then('the corpus "{corpus_path}" is archived')
def step_corpus_archived(context, corpus_path: str) -> None:
    corpus_root = Path(context.workdir) / corpus_path
    archive_root = corpus_root.parent / ".archived"
    assert archive_root.is_dir(), "Archive directory missing"
    target = Path(corpus_path).name
    matches = [path for path in archive_root.iterdir() if path.name.startswith(target)]
    assert matches, f"Expected archived corpus for {target}"


@then('the corpus "{corpus_path}" has an item tagged with table "{table}"')
def step_corpus_item_tagged_table(context, corpus_path: str, table: str) -> None:
    corpus_root = Path(context.workdir) / corpus_path
    catalog = _load_catalog(corpus_root)
    expected_tag = f"table:{table}"
    for item in catalog.get("items", {}).values():
        tags = item.get("tags", [])
        if expected_tag in tags:
            return
    raise AssertionError(f"Missing table tag {expected_tag}")
