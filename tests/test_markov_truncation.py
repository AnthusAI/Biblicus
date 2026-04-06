from pathlib import Path

from biblicus.analysis.markov import _collect_documents
from biblicus.analysis.models import MarkovAnalysisTextSourceConfig
from biblicus.extraction import (
    ExtractionConfigurationManifest,
    ExtractionItemResult,
    ExtractionSnapshotManifest,
)
from biblicus.models import ExtractionSnapshotReference


class _FakeCorpus:
    def __init__(self, manifest, run_root: Path):
        self._manifest = manifest
        self._run_root = run_root

    def load_extraction_snapshot_manifest(self, *, extractor_id: str, snapshot_id: str):
        return self._manifest

    def extraction_snapshot_dir(self, *, extractor_id: str, snapshot_id: str) -> Path:
        return self._run_root


def test_markov_collect_documents_truncates_and_warns(tmp_path):
    run_root = tmp_path / "snap"
    run_root.mkdir(parents=True)
    text_a = run_root / "a.txt"
    text_b = run_root / "b.txt"
    text_a.write_text("first", encoding="utf-8")
    text_b.write_text("second", encoding="utf-8")

    config_manifest = ExtractionConfigurationManifest(
        configuration_id="cfg",
        extractor_id="ext",
        name="default",
        created_at="now",
        configuration={},
    )

    manifest = ExtractionSnapshotManifest(
        snapshot_id="snap",
        configuration=config_manifest,
        corpus_uri="file:///tmp",
        catalog_generated_at="now",
        created_at="now",
        items=[
            ExtractionItemResult(
                item_id="item-1",
                status="extracted",
                final_text_relpath=str(text_a.relative_to(run_root)),
                final_metadata_relpath=None,
                final_stage_index=None,
                final_stage_extractor_id=None,
                final_producer_extractor_id=None,
                final_source_stage_index=None,
                error_type=None,
                error_message=None,
                stage_results=[],
            ),
            ExtractionItemResult(
                item_id="item-2",
                status="extracted",
                final_text_relpath=str(text_b.relative_to(run_root)),
                final_metadata_relpath=None,
                final_stage_index=None,
                final_stage_extractor_id=None,
                final_producer_extractor_id=None,
                final_source_stage_index=None,
                error_type=None,
                error_message=None,
                stage_results=[],
            ),
        ],
        stats={},
    )

    corpus = _FakeCorpus(manifest=manifest, run_root=run_root)
    config = MarkovAnalysisTextSourceConfig(sample_size=1, min_text_characters=None)
    documents, report = _collect_documents(
        corpus=corpus,
        extraction_snapshot=ExtractionSnapshotReference(extractor_id="ext", snapshot_id="snap"),
        config=config,
    )

    assert len(documents) == 1
    assert report.warnings == ["Text collection truncated to sample_size"]
    assert report.status.value == "complete"
