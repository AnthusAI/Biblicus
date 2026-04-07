from pathlib import Path


from biblicus.corpus import Corpus, _merge_metadata, _merge_tags
from biblicus.models import CatalogItem, CorpusCatalog


def test_merge_metadata_and_tags_preserve_existing():
    merged = _merge_metadata({"tags": ["a"]}, {"tags": ["b"], "title": "T"})
    assert set(merged["tags"]) == {"a", "b"}
    merged_tags = _merge_tags(["x"], merged.get("tags"))
    assert set(merged_tags) == {"a", "b", "x"}


def test_prune_remote_items_respects_other_storage(tmp_path: Path):
    corpus = Corpus(tmp_path)
    catalog = CorpusCatalog(
        schema_version=2,
        generated_at="2024-01-01T00:00:00Z",
        corpus_uri=tmp_path.as_uri(),
        raw_dir="raw",
        items={},
        order=[],
    )
    corpus.meta_dir.mkdir(parents=True, exist_ok=True)
    item = CatalogItem(
        id="keep",
        relpath="raw/local/file.txt",
        sha256="",
        bytes=1,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={},
        created_at="now",
        source_uri="file://local",
    )
    catalog.items[item.id] = item
    catalog.order.append(item.id)
    corpus._write_catalog(catalog)
    pruned = corpus._prune_remote_items(storage_subdir="imports/remote/name", remote_uris=set())
    assert pruned == 0
    assert corpus._load_catalog().items["keep"].relpath == "raw/local/file.txt"
