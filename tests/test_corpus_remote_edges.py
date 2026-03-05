from pathlib import Path
from types import SimpleNamespace

import json

from biblicus.corpus import Corpus
from biblicus.models import CorpusCatalog, CorpusConfig, RemoteCorpusSourceConfig, RemoteSourceItem
from biblicus.user_config import SourceProfileConfig


def _make_corpus(tmp_path: Path) -> Corpus:
    corpus = Corpus(tmp_path)
    corpus.meta_dir.mkdir(parents=True, exist_ok=True)
    catalog = CorpusCatalog(
        schema_version=2,
        generated_at="2024-01-01T00:00:00Z",
        corpus_uri=tmp_path.as_uri(),
        raw_dir="raw",
        items={},
        order=[],
    )
    corpus._write_catalog(catalog)
    return corpus


def _write_corpus_config(root: Path, source_config: RemoteCorpusSourceConfig) -> None:
    meta_dir = root / ".biblicus"
    meta_dir.mkdir(parents=True, exist_ok=True)
    config = CorpusConfig(
        schema_version=2,
        created_at="2024-01-01T00:00:00Z",
        corpus_uri=root.as_uri(),
        raw_dir="raw",
        source=source_config,
    )
    (meta_dir / "config.json").write_text(
        json.dumps(config.model_dump(mode="json"), sort_keys=True),
        encoding="utf-8",
    )


def test_resolve_remote_source_name_defaults():
    corpus = Corpus(Path("/tmp"))
    source = SimpleNamespace(kind="s3", bucket="my-bucket", container=None, name=None)
    assert corpus._resolve_remote_source_name(source) == "my-bucket"
    source = SimpleNamespace(kind="azure-blob", bucket=None, container="my-container", name=None)
    assert corpus._resolve_remote_source_name(source) == "my-container"
    source = SimpleNamespace(
        kind="google-drive",
        bucket=None,
        container=None,
        folder_url="https://drive.google.com/drive/folders/folder-id-123?usp=drive_link",
        name=None,
    )
    assert corpus._resolve_remote_source_name(source) == "folder-id-123"


def test_relative_remote_key_strips_prefix():
    corpus = Corpus(Path("/tmp"))
    key = "prefix/path/file.txt"
    assert corpus._relative_remote_key(key, prefix="prefix/") == "path/file.txt"


def test_remote_item_unchanged_checks_etag_and_last_modified():
    corpus = Corpus(Path("/tmp"))
    existing = SimpleNamespace(
        metadata={"biblicus": {"source_etag": "etag1", "source_last_modified": "y"}}
    )
    item = SimpleNamespace(etag="etag1", last_modified="z")
    assert corpus._remote_item_unchanged(existing, item)
    item2 = SimpleNamespace(etag=None, last_modified="y")
    assert corpus._remote_item_unchanged(existing, item2)


def test_pull_source_uses_context_manager(monkeypatch, tmp_path):
    source_config = RemoteCorpusSourceConfig(
        kind="google-drive",
        profile="profile",
        name="demo",
        folder_url="https://drive.google.com/drive/folders/folder123?usp=drive_link",
    )
    _write_corpus_config(tmp_path, source_config)
    corpus = _make_corpus(tmp_path)
    state = {"entered": False, "exited": False}

    class StubGoogleDriveSource:
        def __init__(self, config, profile):
            self._config = config
            self._profile = profile

        def __enter__(self):
            state["entered"] = True
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            _ = exc_type
            _ = exc_value
            _ = traceback
            state["exited"] = True

        def list_items(self):
            return [
                RemoteSourceItem(
                    key="demo.txt",
                    source_uri="gdrive://folder123/demo.txt",
                    etag="etag",
                    last_modified="2024-01-01T00:00:00Z",
                    size=5,
                    content_type="text/plain",
                )
            ]

        def fetch_bytes(self, item):
            _ = item
            return b"hello", "text/plain"

    monkeypatch.setattr("biblicus.corpus.GoogleDriveRemoteSource", StubGoogleDriveSource)
    monkeypatch.setattr(
        "biblicus.corpus.resolve_source_profile",
        lambda name: SourceProfileConfig(name=name, kind="google-drive"),
    )

    result = corpus.pull_source()

    assert state["entered"] is True
    assert state["exited"] is True
    assert result.downloaded == 1
