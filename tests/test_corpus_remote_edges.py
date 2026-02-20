from pathlib import Path
from types import SimpleNamespace

from biblicus.corpus import Corpus
from biblicus.models import CorpusCatalog


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


def test_resolve_remote_source_name_defaults():
    corpus = Corpus(Path("/tmp"))
    source = SimpleNamespace(kind="s3", bucket="my-bucket", container=None, name=None)
    assert corpus._resolve_remote_source_name(source) == "my-bucket"
    source = SimpleNamespace(kind="azure-blob", bucket=None, container="my-container", name=None)
    assert corpus._resolve_remote_source_name(source) == "my-container"


def test_relative_remote_key_strips_prefix():
    corpus = Corpus(Path("/tmp"))
    key = "prefix/path/file.txt"
    assert corpus._relative_remote_key(key, prefix="prefix/") == "path/file.txt"


def test_remote_item_unchanged_checks_etag_and_last_modified():
    corpus = Corpus(Path("/tmp"))
    existing = SimpleNamespace(metadata={"biblicus": {"source_etag": "etag1", "source_last_modified": "y"}})
    item = SimpleNamespace(etag="etag1", last_modified="z")
    assert corpus._remote_item_unchanged(existing, item)
    item2 = SimpleNamespace(etag=None, last_modified="y")
    assert corpus._remote_item_unchanged(existing, item2)
