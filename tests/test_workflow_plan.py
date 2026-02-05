"""
Workflow plan tests for Biblicus task dependencies.
"""

from __future__ import annotations

from typing import Dict

from biblicus.corpus import Corpus
from biblicus.extraction import (
    create_extraction_configuration_manifest,
    create_extraction_snapshot_manifest,
    write_extraction_snapshot_manifest,
)
from biblicus.retrieval import create_configuration_manifest, create_snapshot_manifest
from biblicus.workflow import (
    TASK_KIND_ALIASES,
    build_plan_for_extract,
    build_plan_for_index,
    build_plan_for_query,
    normalize_task_kind,
)


def _create_corpus(tmp_path, *, with_item: bool) -> Corpus:
    corpus = Corpus.init(tmp_path)
    if with_item:
        corpus.ingest_note("Hello world", title="Test")
    return corpus


def _write_pipeline_extraction_snapshot(
    corpus: Corpus, *, pipeline_config: Dict[str, object]
) -> None:
    config_manifest = create_extraction_configuration_manifest(
        extractor_id="pipeline",
        name="default",
        configuration=pipeline_config,
    )
    snapshot_manifest = create_extraction_snapshot_manifest(corpus, configuration=config_manifest)
    snapshot_dir = corpus.extraction_snapshot_dir(
        extractor_id="pipeline", snapshot_id=snapshot_manifest.snapshot_id
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    write_extraction_snapshot_manifest(snapshot_dir=snapshot_dir, manifest=snapshot_manifest)


def _write_retrieval_snapshot(corpus: Corpus, *, retriever_id: str) -> None:
    config_manifest = create_configuration_manifest(
        retriever_id=retriever_id,
        name="index",
        configuration={},
    )
    snapshot = create_snapshot_manifest(corpus, configuration=config_manifest, stats={})
    corpus.write_snapshot(snapshot)


def test_plan_empty_corpus_with_load_handler_orders_dependencies(tmp_path):
    """
    Empty corpus uses load, extract, index in order when a load handler exists.
    """
    corpus = _create_corpus(tmp_path, with_item=False)
    plan = build_plan_for_index(corpus, "tf-vector", load_handler_available=True)
    kinds = [task.kind for task in plan.tasks]
    assert kinds == ["load", "extract", "index"]
    assert plan.status == "ready"


def test_plan_nonempty_corpus_without_snapshot_runs_extract_then_index(tmp_path):
    """
    Non-empty corpora without extraction snapshots require extract before index.
    """
    corpus = _create_corpus(tmp_path, with_item=True)
    plan = build_plan_for_index(corpus, "tf-vector")
    kinds = [task.kind for task in plan.tasks]
    assert kinds == ["extract", "index"]
    assert plan.tasks[0].status == "ready"
    assert plan.tasks[1].status == "ready"


def test_plan_with_current_extraction_snapshot_marks_extract_complete(tmp_path):
    """
    Existing extraction snapshots for the current catalog mark extract complete.
    """
    corpus = _create_corpus(tmp_path, with_item=True)
    pipeline_config = {"steps": [{"extractor_id": "pass-through-text", "configuration": {}}]}
    _write_pipeline_extraction_snapshot(corpus, pipeline_config=pipeline_config)
    plan = build_plan_for_index(corpus, "tf-vector", pipeline_config=pipeline_config)
    kinds = [task.kind for task in plan.tasks]
    assert kinds == ["extract", "index"]
    assert plan.tasks[0].status == "complete"
    assert plan.tasks[1].status == "ready"


def test_plan_query_only_when_index_is_current(tmp_path):
    """
    When a compatible retrieval snapshot exists, query has no dependencies.
    """
    corpus = _create_corpus(tmp_path, with_item=True)
    pipeline_config = {"steps": [{"extractor_id": "pass-through-text", "configuration": {}}]}
    _write_pipeline_extraction_snapshot(corpus, pipeline_config=pipeline_config)
    _write_retrieval_snapshot(corpus, retriever_id="tf-vector")
    plan = build_plan_for_query(corpus, "tf-vector", pipeline_config=pipeline_config)
    assert [task.kind for task in plan.tasks] == ["query"]
    assert plan.root.depends_on == []


def test_extract_stale_when_catalog_generated_at_changes(tmp_path):
    """
    Extraction becomes stale after catalog changes.
    """
    corpus = _create_corpus(tmp_path, with_item=True)
    pipeline_config = {"steps": [{"extractor_id": "pass-through-text", "configuration": {}}]}
    _write_pipeline_extraction_snapshot(corpus, pipeline_config=pipeline_config)
    corpus.ingest_note("More text", title="More")
    plan = build_plan_for_extract(corpus, pipeline_config=pipeline_config)
    assert plan.root.status == "ready"


def test_alias_normalization_is_deterministic():
    """
    Task kind aliases normalize to the canonical verb.
    """
    for alias, expected in TASK_KIND_ALIASES.items():
        assert normalize_task_kind(alias) == expected
    assert normalize_task_kind("index") == "index"
