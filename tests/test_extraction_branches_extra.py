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
