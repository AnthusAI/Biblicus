from pathlib import Path

from biblicus.corpus import Corpus, _merge_metadata, _merge_tags
from biblicus.models import CorpusCatalog, CatalogItem


def test_merge_metadata_prefers_frontmatter():
    frontmatter = {"title": "T", "tags": ["a"], "biblicus": {"id": "1"}}
    sidecar = {"title": "S", "media_type": "text/plain"}
    merged = _merge_metadata(frontmatter, sidecar)
    assert merged["title"] == "T"
    assert merged["media_type"] == "text/plain"


def test_merge_tags_deduplicates_and_orders():
    result = _merge_tags(["a", "b"], ["b", "c"])
    assert result == ["a", "b", "c"]


def test_corpus_remote_prune_removes_missing(tmp_path: Path):
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
    # Add one remote item in catalog
    item = CatalogItem(
        id="i1",
        relpath="imports/remote/source/a.txt",
        sha256="h",
        bytes=1,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={"biblicus": {"id": "i1"}, "title": "a"},
        created_at="now",
        source_uri="remote://a",
    )
    catalog.items[item.id] = item
    catalog.order.append(item.id)
    corpus._write_catalog(catalog)

    # create file to ensure deletion
    (corpus.root / item.relpath).parent.mkdir(parents=True, exist_ok=True)
    (corpus.root / item.relpath).write_text("x", encoding="utf-8")

    pruned = corpus._prune_remote_items(storage_subdir="imports/remote/source", remote_uris=set())
    assert pruned == 1
    catalog2 = corpus._load_catalog()
    assert not catalog2.items
