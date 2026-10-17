from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

from biblicus import corpus as corpus_module
from biblicus.corpus import Corpus
from biblicus.models import RemoteCorpusSourceConfig


@dataclass
class FakeRemoteObject:
    """Test double: fake remote object."""

    key: str
    source_uri: str
    etag: Optional[str]
    last_modified: Optional[str]
    content_type: Optional[str]


class FakeRemoteSource:
    """Test double: fake remote source."""

    listed_objects: List[FakeRemoteObject] = []
    object_payloads: Dict[str, Tuple[bytes, Optional[str]]] = {}
    constructed_kinds: List[str] = []

    def __init__(self, source_config, profile) -> None:
        FakeRemoteSource.constructed_kinds.append(source_config.kind)

    def list_items(self) -> List[FakeRemoteObject]:
        """Return the scripted remote listing."""
        return list(FakeRemoteSource.listed_objects)

    def fetch_bytes(self, item: FakeRemoteObject) -> Tuple[bytes, Optional[str]]:
        """Return the scripted payload for a remote object."""
        return FakeRemoteSource.object_payloads[item.key]


PROFILE_KINDS = {
    "s3-profile": "s3",
    "azure-profile": "azure-blob",
    "ftp-profile": "ftp",
}


@pytest.fixture
def remote_corpus(monkeypatch, tmp_path) -> Corpus:
    """Return an initialized corpus wired to fake remote sources."""
    FakeRemoteSource.listed_objects = []
    FakeRemoteSource.object_payloads = {}
    FakeRemoteSource.constructed_kinds = []
    monkeypatch.setattr(corpus_module, "S3RemoteSource", FakeRemoteSource)
    monkeypatch.setattr(corpus_module, "AzureBlobRemoteSource", FakeRemoteSource)
    monkeypatch.setattr(
        corpus_module,
        "resolve_source_profile",
        lambda profile_name: type("Profile", (), {"kind": PROFILE_KINDS[profile_name]})(),
    )
    initialized_corpus = Corpus.init(tmp_path / "corpus")
    return Corpus(initialized_corpus.root)


def configure_remote_source(corpus: Corpus, source_config) -> None:
    """Configure remote source."""
    corpus.config = corpus.config.model_copy(update={"source": source_config})


def s3_source_config(**overrides) -> RemoteCorpusSourceConfig:
    """Return an S3 remote source configuration for tests."""
    values = dict(kind="s3", profile="s3-profile", bucket="papers-bucket", prefix="prefix/")
    values.update(overrides)
    return RemoteCorpusSourceConfig(**values)


def remote_object(
    key: str,
    *,
    etag: Optional[str] = "etag-1",
    last_modified: Optional[str] = "2026-01-01T00:00:00Z",
    content_type: Optional[str] = None,
    source_uri: Optional[str] = None,
) -> FakeRemoteObject:
    """Return a fake remote object listing entry."""
    return FakeRemoteObject(
        key=key,
        source_uri=source_uri or f"s3://papers-bucket/{key}",
        etag=etag,
        last_modified=last_modified,
        content_type=content_type,
    )


def items_by_source_uri(corpus: Corpus):
    """Return catalog items keyed by source uniform resource identifier."""
    return {item.source_uri: item for item in corpus.load_catalog().items.values()}


def test_pull_source_requires_configured_remote_source(remote_corpus):
    """Verify pull source requires configured remote source."""
    with pytest.raises(ValueError, match="Remote source is not configured"):
        remote_corpus.pull_source()


def test_pull_source_rejects_profile_kind_mismatch(remote_corpus):
    """Verify pull source rejects profile kind mismatch."""
    configure_remote_source(remote_corpus, s3_source_config(profile="azure-profile"))

    with pytest.raises(ValueError, match="does not match source profile kind: s3 vs azure-blob"):
        remote_corpus.pull_source()


def test_pull_source_rejects_unsupported_kind(remote_corpus):
    """Verify pull source rejects unsupported kind."""
    unsupported_source = RemoteCorpusSourceConfig.model_construct(
        kind="ftp", profile="ftp-profile", name=None, bucket=None, container=None, prefix=""
    )
    configure_remote_source(remote_corpus, unsupported_source)

    with pytest.raises(ValueError, match="Unsupported remote source kind: ftp"):
        remote_corpus.pull_source()


def test_pull_source_mirrors_updates_and_prunes_remote_items(remote_corpus):
    """Verify pull source mirrors updates and prunes remote items."""
    configure_remote_source(remote_corpus, s3_source_config())
    (remote_corpus.root / ".biblicusignore").write_text("*.tmp\n", encoding="utf-8")
    markdown_payload = (
        b"---\ntitle: Remote Notes\ntags:\n  - existing\n---\nBody text for the remote notes.\n"
    )
    FakeRemoteSource.listed_objects = [
        remote_object("prefix/"),
        remote_object("prefix/scratch.tmp"),
        remote_object("prefix/notes/doc.md", content_type="text/plain; charset=utf-8"),
        remote_object("prefix/data/blob.bin", content_type="application/octet-stream"),
        remote_object("prefix/data/report.txt", etag=None, content_type=None),
        remote_object("prefix/data/obsolete.txt"),
    ]
    FakeRemoteSource.object_payloads = {
        "prefix/notes/doc.md": (markdown_payload, None),
        "prefix/data/blob.bin": (b"\x00\x01binary", None),
        "prefix/data/report.txt": (b"plain report", ""),
        "prefix/data/obsolete.txt": (b"soon removed", "text/plain"),
    }

    first_result = remote_corpus.pull_source(
        tag_resolver=lambda relative_key: (
            ["remote"] if relative_key.endswith(".md") or relative_key.endswith(".bin") else []
        )
    )

    assert (first_result.listed, first_result.skipped, first_result.downloaded) == (6, 2, 4)
    assert first_result.pruned == 0
    catalog_items = items_by_source_uri(remote_corpus)
    markdown_item = catalog_items["s3://papers-bucket/prefix/notes/doc.md"]
    assert markdown_item.media_type == "text/markdown"
    assert markdown_item.title == "Remote Notes"
    assert set(markdown_item.tags) == {"existing", "remote"}
    markdown_text = (remote_corpus.root / markdown_item.relpath).read_text("utf-8")
    assert "source_etag: etag-1" in markdown_text
    blob_item = catalog_items["s3://papers-bucket/prefix/data/blob.bin"]
    assert blob_item.relpath.endswith("imports/remote/papers-bucket/data/blob.bin")
    assert blob_item.tags == ["remote"]
    report_item = catalog_items["s3://papers-bucket/prefix/data/report.txt"]
    assert report_item.media_type == "text/plain"
    assert report_item.metadata["biblicus"]["source_last_modified"] == "2026-01-01T00:00:00Z"
    original_blob_path = remote_corpus.root / blob_item.relpath

    FakeRemoteSource.listed_objects = [
        remote_object("prefix/notes/doc.md"),
        remote_object("prefix/data/report.txt", etag=None),
        remote_object(
            "prefix/data/renamed.bin",
            etag="etag-2",
            source_uri="s3://papers-bucket/prefix/data/blob.bin",
        ),
    ]
    FakeRemoteSource.object_payloads["prefix/data/renamed.bin"] = (b"\x00\x02binary", None)

    second_result = remote_corpus.pull_source()

    assert (second_result.skipped, second_result.updated, second_result.pruned) == (2, 1, 1)
    assert not original_blob_path.exists()
    assert not Path(str(original_blob_path) + ".biblicus.yml").exists()
    updated_items = items_by_source_uri(remote_corpus)
    renamed_item = updated_items["s3://papers-bucket/prefix/data/blob.bin"]
    assert renamed_item.id == blob_item.id
    assert renamed_item.relpath.endswith("data/renamed.bin")
    assert "s3://papers-bucket/prefix/data/obsolete.txt" not in updated_items
    assert FakeRemoteSource.constructed_kinds == ["s3", "s3"]


def test_pull_source_uses_azure_blob_source_and_rejects_non_utf8_markdown(remote_corpus):
    """Verify pull source uses azure blob source and rejects non utf8 markdown."""
    configure_remote_source(
        remote_corpus,
        RemoteCorpusSourceConfig(
            kind="azure-blob", profile="azure-profile", container="papers-container"
        ),
    )
    FakeRemoteSource.listed_objects = [remote_object("broken.markdown")]
    FakeRemoteSource.object_payloads = {"broken.markdown": (b"\xff\xfe\xfa", None)}

    with pytest.raises(ValueError, match="Markdown must be Unicode Transformation Format 8"):
        remote_corpus.pull_source()

    assert FakeRemoteSource.constructed_kinds == ["azure-blob"]


def test_resolve_remote_source_name_prefers_name_then_falls_back_to_remote(remote_corpus):
    """Verify resolve remote source name prefers name then falls back to remote."""
    named_source = s3_source_config(name="  My Papers  ")
    unnamed_source = RemoteCorpusSourceConfig.model_construct(
        kind="azure-blob",
        profile="azure-profile",
        name="  ",
        bucket=None,
        container=None,
        prefix="",
    )

    assert remote_corpus._resolve_remote_source_name(
        named_source
    ) == corpus_module._sanitize_filename("My Papers")
    assert remote_corpus._resolve_remote_source_name(unnamed_source) == "remote"


def test_remote_item_unchanged_handles_missing_metadata_block(remote_corpus):
    """Verify remote item unchanged handles missing metadata block."""
    existing_item = type("ExistingItem", (), {"metadata": {"biblicus": "corrupt"}})()

    assert (
        remote_corpus._remote_item_unchanged(
            existing_item, remote_object("prefix/a.txt", etag=None, last_modified=None)
        )
        is False
    )


def test_write_remote_item_replaces_stale_markdown_sidecar(remote_corpus):
    """Verify write remote item replaces stale markdown sidecar."""
    relpath = "raw/imports/remote/notes.md"
    stale_sidecar = remote_corpus.root / "raw/imports/remote/notes.md.biblicus.yml"
    stale_sidecar.parent.mkdir(parents=True, exist_ok=True)
    stale_sidecar.write_text("title: stale\n", encoding="utf-8")

    catalog_item = remote_corpus._write_remote_item(
        data=b"Plain markdown body\n",
        relpath=relpath,
        source_uri="s3://papers-bucket/notes.md",
        source_etag=None,
        source_last_modified=None,
        content_type=None,
        item_id=None,
        created_at="2025-12-31T00:00:00Z",
    )

    assert not stale_sidecar.exists()
    assert catalog_item.media_type == "text/markdown"
    assert catalog_item.title is None
    assert catalog_item.created_at == "2025-12-31T00:00:00Z"
    assert catalog_item.metadata["biblicus"]["source"] == "s3://papers-bucket/notes.md"


def test_prune_remote_items_keeps_items_outside_remote_storage(remote_corpus):
    """Verify prune remote items keeps items outside remote storage."""
    local_note = remote_corpus.ingest_note("Local note body", title="Local Note")

    pruned = remote_corpus._prune_remote_items(
        storage_subdir="imports/remote/papers-bucket", remote_uris=set()
    )

    assert pruned == 0
    assert local_note.item_id in remote_corpus.load_catalog().items


def test_delete_item_files_tolerates_missing_content_and_sidecar(remote_corpus):
    """Verify delete item files tolerates missing content and sidecar."""
    remote_corpus._delete_item_files("raw/imports/remote/never-written.bin")

    assert not (remote_corpus.root / "raw/imports/remote/never-written.bin").exists()
