import json
from pathlib import Path

from biblicus.analysis import markov
from biblicus.corpus import Corpus
from biblicus.models import ExtractionSnapshotReference


def _write_extraction_snapshot(corpus: Corpus, snapshot_id: str = "s1") -> None:
    text_dir = corpus.root / "extracted" / "pipeline" / snapshot_id / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    (text_dir / "item.txt").write_text("hello world", encoding="utf-8")
    manifest = {
        "snapshot_id": snapshot_id,
        "configuration": {
            "configuration_id": "cfg",
            "extractor_id": "pipeline",
            "name": "default",
            "created_at": "t",
            "configuration": {},
        },
        "corpus_uri": corpus.uri,
        "catalog_generated_at": corpus.catalog_generated_at(),
        "created_at": "t",
        "items": [
            {
                "item_id": "item-1",
                "status": "extracted",
                "final_text_relpath": "text/item.txt",
                "final_metadata_relpath": None,
                "final_stage_index": 1,
                "final_stage_extractor_id": "pipeline",
                "final_producer_extractor_id": "pipeline",
                "final_source_stage_index": None,
                "error_type": None,
                "error_message": None,
                "stage_results": [],
            }
        ],
        "stats": {},
    }
    (text_dir.parent / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_markov_run_uses_cached_observations(tmp_path: Path) -> None:
    """
    Ensure run_stats properly capture cached LLM observations when they are loaded from disk.
    """
    corpus = Corpus.init(tmp_path / "corp")
    _write_extraction_snapshot(corpus)

    config = markov.MarkovAnalysisConfiguration(
        llm_observations={
            "enabled": True,
            "client": {"provider": "openai", "model": "gpt-4o-mini"},
            "prompt_template": "{segment}",
            "cache": {"enabled": False},
        },
        topic_modeling={"enabled": False},
    )
    cfg_manifest = markov._create_configuration_manifest(name="default", config=config)
    extraction_ref = ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id="s1")
    snapshot_id = markov._analysis_snapshot_id(
        configuration_id=cfg_manifest.configuration_id,
        extraction_snapshot=extraction_ref,
        catalog_generated_at=corpus.catalog_generated_at(),
    )
    run_dir = corpus.analysis_run_dir(analysis_id="markov", snapshot_id=snapshot_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    segment = markov.MarkovAnalysisSegment(item_id="item-1", segment_index=1, text="body")
    observation = markov.MarkovAnalysisObservation(
        item_id="item-1", segment_index=1, segment_text="body", llm_label="lbl", llm_summary="sum"
    )
    extraction_manifest_path = corpus.extraction_snapshot_dir(
        extractor_id="pipeline", snapshot_id="s1"
    ) / "manifest.json"
    assert extraction_manifest_path.is_file()

    (run_dir / "segments.jsonl").write_text(segment.model_dump_json() + "\n", encoding="utf-8")
    (run_dir / "observations.jsonl").write_text(observation.model_dump_json() + "\n", encoding="utf-8")

    original_fit = markov._fit_and_decode
    markov._fit_and_decode = lambda observations, lengths, config: (
        [0 for _ in observations],
        [],
        1,
    )
    try:
        markov._run_markov(
            corpus=corpus,
            configuration_name="default",
            config=config,
            extraction_snapshot=extraction_ref,
        )
    finally:
        markov._fit_and_decode = original_fit

    manifest_path = run_dir / "manifest.json"
    stats = json.loads(manifest_path.read_text(encoding="utf-8"))["stats"]
    assert stats["llm_observations"]["cached_segments"] == 1
    assert stats["llm_observations"]["generated_segments"] == 0
