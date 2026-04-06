import json
from pathlib import Path


from biblicus import extraction
from biblicus.models import CatalogItem
from biblicus import corpus as corpus_mod
from biblicus.extraction import ExtractionSnapshotManifest


def _build_manifest(tmp_path: Path, items: list[CatalogItem]) -> ExtractionSnapshotManifest:
    return ExtractionSnapshotManifest.model_construct(
        schema_version=1,
        snapshot_id="snap1",
        extractor_id="pipeline",
        catalog_sha256="abc",
        catalog_generated_at="now",
        corpus_uri="file://dummy",
        created_at="now",
        configuration={"extractor_id": "pipeline", "stages": []},
        items=[],
        stats={
            "total_items": len(items),
            "already_text_items": 0,
            "needs_extraction_items": len(items),
            "extracted_items": 0,
            "extracted_nonempty_items": 0,
            "extracted_empty_items": 0,
            "skipped_items": 0,
            "errored_items": 0,
            "converted_items": 0,
        },
    )


def test_extraction_heartbeat_and_cache_paths(tmp_path, monkeypatch):
    corpus = corpus_mod.Corpus.init(tmp_path, force=True)
    corpus.ingest_item(
        b"hello",
        filename="i1.txt",
        media_type="text/plain",
        tags=[],
        metadata=None,
        source_uri="file://x",
    )
    snap_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id="snap1")
    snap_dir.mkdir(parents=True, exist_ok=True)
    _build_manifest(tmp_path, [])

    # ensure cache load path is hit by writing cached text
    stage_dir = snap_dir / "stages" / "1_select-text" / "text"
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "i1.txt").write_text("cached", encoding="utf-8")
    # also stage metadata to hit cache metadata branch
    meta_dir = snap_dir / "stages" / "1_select-text" / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "i1.json").write_text(json.dumps({"foo": "bar"}), encoding="utf-8")

    manifest = extraction.build_extraction_snapshot(
        corpus=corpus,
        extractor_id="pipeline",
        configuration_name="default",
        configuration={"stages": [{"extractor_id": "select-text", "config": {}}]},
        force=False,
        max_workers=1,
    )
    assert manifest.items[0].status in {"extracted", "skipped"}


def test_extraction_write_partial_manifest(tmp_path, monkeypatch):
    corpus = corpus_mod.Corpus.init(tmp_path, force=True)
    corpus.ingest_item(
        b"hello2",
        filename="i2.txt",
        media_type="text/plain",
        tags=[],
        metadata=None,
        source_uri="file://y",
    )
    manifest = extraction.build_extraction_snapshot(
        corpus=corpus,
        extractor_id="pipeline",
        configuration_name="default",
        configuration={"stages": [{"extractor_id": "select-text", "config": {}}]},
        force=False,
        max_workers=1,
    )
    manifest_path = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id=manifest.snapshot_id) / "manifest.json"
    assert manifest_path.is_file()
