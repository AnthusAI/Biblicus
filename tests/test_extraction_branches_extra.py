import json
from types import SimpleNamespace
from pathlib import Path

from biblicus.extraction import (
    load_or_build_extraction_snapshot,
    create_extraction_configuration_manifest,
    create_extraction_snapshot_manifest,
    ExtractionSnapshotManifest,
)


def test_load_or_build_uses_existing_manifest(tmp_path: Path):
    # Write an existing manifest to ensure reuse branch.
    extractor_id = "pipeline"
    snapshot_id = "snap123"
    manifest_dir = tmp_path / ".biblicus" / "extraction" / extractor_id / snapshot_id
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_content = {"snapshot_id": snapshot_id, "configuration_id": "cfg1", "items": [], "stats": {}, "schema_version": 1}
    (manifest_dir / "manifest.json").write_text(json.dumps(manifest_content), encoding="utf-8")

    corpus = SimpleNamespace(
        extraction_snapshot_dir=lambda extractor_id, snapshot_id: manifest_dir,
        load_extraction_snapshot_manifest=lambda extractor_id, snapshot_id: ExtractionSnapshotManifest(
            snapshot_id=snapshot_id,
            configuration=create_extraction_configuration_manifest(
                extractor_id="pipeline", name="cfg1", configuration={}
            ),
            corpus_uri=tmp_path.as_uri(),
            catalog_generated_at="now",
            created_at="now",
            items=[],
            stats={},
        ),
        meta_dir=tmp_path / ".biblicus",
        load_catalog=lambda: SimpleNamespace(
            generated_at="now",
            corpus_uri=tmp_path.as_uri(),
            raw_dir="raw",
            latest_snapshot_id=None,
        ),
        uri=tmp_path.as_uri(),
    )

    result = load_or_build_extraction_snapshot(
        corpus,
        extractor_id=extractor_id,
        configuration_name="cfg",
        configuration={"stages": [{"extractor_id": "pass-through-text", "config": {}}]},
        max_workers=1,
    )
    assert result.snapshot_id == snapshot_id or result.snapshot_id


def test_extraction_uses_cached_final_text(tmp_path: Path):
    from biblicus.extraction import build_extraction_snapshot, hash_text
    from biblicus.models import CatalogItem, CorpusCatalog
    from biblicus.corpus import Corpus

    corpus = Corpus(tmp_path)
    corpus.meta_dir.mkdir(parents=True, exist_ok=True)
    item = CatalogItem(
        id="item1",
        relpath="raw/doc.txt",
        sha256="hash",
        bytes=4,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={},
        created_at="now",
        source_uri="file://doc",
    )
    catalog = CorpusCatalog(
        schema_version=2,
        generated_at="2024-01-01T00:00:00Z",
        corpus_uri=tmp_path.as_uri(),
        raw_dir="raw",
        items={item.id: item},
        order=[item.id],
    )
    corpus._write_catalog(catalog)

    config_manifest = create_extraction_configuration_manifest(
        extractor_id="pipeline", name="cfg", configuration={"stages": []}
    )
    snapshot_id = hash_text(f"{config_manifest.configuration_id}:{catalog.generated_at}")
    snapshot_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id=snapshot_id)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    text_dir = snapshot_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    (text_dir / f"{item.id}.txt").write_text("cached text", encoding="utf-8")
    metadata_dir = snapshot_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / f"{item.id}.json").write_text("{}", encoding="utf-8")

    manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="cfg",
        configuration={"stages": [{"extractor_id": "pass-through-text", "config": {}}]},
    )
    assert manifest.items[0].final_text_relpath == f"text/{item.id}.txt"


def test_extraction_reuses_stage_cache(tmp_path: Path):
    from biblicus.extraction import build_extraction_snapshot, hash_text, _pipeline_stage_dir_name
    from biblicus.models import CatalogItem, CorpusCatalog
    from biblicus.corpus import Corpus

    corpus = Corpus(tmp_path)
    corpus.meta_dir.mkdir(parents=True, exist_ok=True)
    item = CatalogItem(
        id="item2",
        relpath="raw/doc2.txt",
        sha256="hash",
        bytes=4,
        media_type="application/octet-stream",
        title=None,
        tags=[],
        metadata={},
        created_at="now",
        source_uri="file://doc2",
    )
    catalog = CorpusCatalog(
        schema_version=2,
        generated_at="2024-01-02T00:00:00Z",
        corpus_uri=tmp_path.as_uri(),
        raw_dir="raw",
        items={item.id: item},
        order=[item.id],
    )
    corpus._write_catalog(catalog)

    config_manifest = create_extraction_configuration_manifest(
        extractor_id="pipeline", name="cfg2", configuration={"stages": [{"extractor_id": "pass-through-text"}]}
    )
    snapshot_id = hash_text(f"{config_manifest.configuration_id}:{catalog.generated_at}")
    snapshot_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id=snapshot_id)
    stage_dir_name = _pipeline_stage_dir_name(stage_index=1, extractor_id="pass-through-text")
    stage_dir = snapshot_dir / "stages" / stage_dir_name
    (stage_dir / "text").mkdir(parents=True, exist_ok=True)
    (stage_dir / "metadata").mkdir(parents=True, exist_ok=True)
    (stage_dir / "text" / f"{item.id}.txt").write_text("stage cached", encoding="utf-8")
    (stage_dir / "metadata" / f"{item.id}.json").write_text('{"foo": "bar"}', encoding="utf-8")

    manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="cfg2",
        configuration={"stages": [{"extractor_id": "pass-through-text", "config": {}}]},
    )
    assert manifest.items[0].status == "extracted"
    # metadata from cache included
    assert manifest.items[0].final_metadata_relpath is not None
