import json
import time
from types import SimpleNamespace
from pathlib import Path

from biblicus import extraction


def test_extraction_heartbeat_and_cache(tmp_path, monkeypatch):
    manifest = extraction.ExtractionSnapshotManifest(
        snapshot_id="s1",
        configuration=extraction.ExtractionConfigurationManifest(
            configuration_id="c1",
            extractor_id="pipeline",
            name="cfg",
            created_at="2024",
            configuration={},
        ),
        corpus_uri="file://",
        catalog_generated_at="2024",
        created_at="2024",
        items=[],
        stats={},
    )
    catalog = SimpleNamespace(items={}, order=[], generated_at="2024", corpus_uri="file://")

    # create stage cache file
    snap_dir = tmp_path / "snap"
    stage_dir = snap_dir / "stages" / "stage0" / "text"
    stage_dir.mkdir(parents=True)
    (stage_dir / "item1.txt").write_text("cached", encoding="utf-8")

    class DummyExtractor(extraction.BaseExtractor):
        extractor_id = "stage0"

        def validate_config(self, config):  # noqa: D401
            return {}

        def extract_text(self, corpus, item, config, previous_extractions):  # noqa: D401,ARG002
            time.sleep(0.1)
            return extraction.ExtractedText(text="", producer_extractor_id=self.extractor_id)

    monkeypatch.setattr(extraction, "get_extractor", lambda eid: DummyExtractor())

    item = extraction.CatalogItem(
        item_id="item1",
        relpath="raw/file.txt",
        sha256="x",
        bytes=1,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={},
    )
    catalog.items = {"item1": item}
    catalog.order = ["item1"]

    snapshot_dir = tmp_path / "snap"
    manifest_dir = snapshot_dir
    manifest_path = manifest_dir / "manifest.json"
    manifest_dir.mkdir(exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")

    result = extraction.build_extraction_snapshot(
        catalog=catalog,
        manifest=manifest,
        snapshot_dir=snapshot_dir,
        parsed_config=extraction.PipelineExtractorConfig(stages=[extraction.PipelineStageSpec(extractor_id="stage0", configuration={})]),
        max_workers=1,
    )

    assert result.stats["total_items"] == 1
    # cached text reused should mark extracted_items
    assert result.items[0].status == "extracted"
