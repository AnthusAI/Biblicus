from contextlib import suppress

from biblicus import corpus


def test_corpus_merge_tags_and_title(tmp_path):
    markdown = tmp_path / "note.md"
    markdown.write_text("---\ntitle: Hello\n---\nBody", encoding="utf-8")
    c = corpus.Corpus.init(tmp_path)
    c.ingest_source(markdown)
    catalog = c.load_catalog()
    item = catalog.items[next(iter(catalog.items))]
    assert item.title == "Hello"


def test_corpus_reserved_dir_names_excluded(tmp_path):
    c = corpus.Corpus.init(tmp_path)
    reserved = set(c._reserved_dir_names())
    assert "metadata" in reserved


def test_corpus_delete_extraction_snapshot_missing(tmp_path):
    c = corpus.Corpus.init(tmp_path)
    # should simply raise FileNotFoundError when missing
    with suppress(FileNotFoundError):
        c.delete_extraction_snapshot(extractor_id="pipeline", snapshot_id="none")

