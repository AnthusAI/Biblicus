from types import SimpleNamespace
from pathlib import Path

import pytest

from biblicus.analysis import markov
from biblicus.analysis.models import (
    MarkovAnalysisConfiguration,
    MarkovAnalysisSegmentationConfig,
    MarkovAnalysisTextSourceConfig,
    MarkovAnalysisObservationsConfig,
    MarkovAnalysisLlmObservationsCacheConfig,
    MarkovAnalysisLlmObservationsConfig,
    MarkovAnalysisModelConfig,
    MarkovAnalysisModelFamily,
    MarkovAnalysisObservation,
    MarkovAnalysisSegment,
    MarkovAnalysisTopicModelingConfig,
    TopicModelingConfiguration,
)
from biblicus.models import ExtractionSnapshotReference


class DummyCorpus:
    def __init__(self, root: Path):
        self.root = root
        self.uri = "file://corpus"
        self.meta_dir = root

    def load_catalog(self):
        return SimpleNamespace(generated_at="now", corpus_uri=self.uri)

    def analysis_run_dir(self, analysis_id: str, snapshot_id: str):  # noqa: ARG002
        return self.root / "analysis" / snapshot_id

    def analysis_dir(self, analysis_id: str):  # noqa: ARG002
        return self.root / "analysis"

    def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
        return self.root / "graph" / snapshot_id

    def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):  # noqa: ARG002
        return SimpleNamespace(items=[])


def _minimal_config(topic_enabled: bool = False) -> MarkovAnalysisConfiguration:
    return MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        text_source=MarkovAnalysisTextSourceConfig.model_construct(),
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(),
        observations=MarkovAnalysisObservationsConfig.model_construct(),
        model=MarkovAnalysisModelConfig.model_construct(family=MarkovAnalysisModelFamily.GAUSSIAN),
        topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(
            enabled=topic_enabled,
            configuration=TopicModelingConfiguration.model_construct() if topic_enabled else None,
        ),
        llm_observations=MarkovAnalysisLlmObservationsConfig.model_construct(),
    )


def test_markov_reuses_cached_observations_and_reapplies_topic(monkeypatch, tmp_path):
    corpus = DummyCorpus(tmp_path)
    config = _minimal_config(topic_enabled=True)
    snapshot = ExtractionSnapshotReference(extractor_id="x", snapshot_id="snap1")

    run_dir = tmp_path / "analysis" / "snap"
    run_dir.mkdir(parents=True, exist_ok=True)
    obs_cache = run_dir / "observations.jsonl"
    obs_cache.write_text("[]", encoding="utf-8")

    observation = MarkovAnalysisObservation(item_id="i", segment_index=1, segment_text="hello")
    segment = MarkovAnalysisSegment(item_id="i", segment_index=1, text="hello")

    text_report = markov.MarkovAnalysisTextCollectionReport(
        status=markov.MarkovAnalysisStageStatus.COMPLETE,
        source_items=0,
        documents=0,
        sample_size=None,
        min_text_characters=None,
        empty_texts=0,
        skipped_items=0,
        warnings=[],
        errors=[],
    )
    monkeypatch.setattr(markov, "_collect_documents", lambda **kwargs: ([], text_report))
    monkeypatch.setattr(markov, "_segment_documents", lambda **kwargs: [segment])
    monkeypatch.setattr(markov, "_load_segments", lambda p: [segment])
    monkeypatch.setattr(markov, "_build_observations", lambda **kwargs: [observation])
    monkeypatch.setattr(markov, "_load_observations", lambda p: [observation])
    applied = {}
    topic_report = SimpleNamespace(topics=[], warnings=[], errors=[])
    monkeypatch.setattr(
        markov,
        "_apply_topic_modeling",
        lambda observations, config, artifacts_dir: ([*observations], topic_report),
    )
    monkeypatch.setattr(markov, "_load_topic_modeling_report", lambda run_dir: None)
    monkeypatch.setattr(markov, "_write_analysis_run_manifest", lambda **kwargs: None)
    monkeypatch.setattr(markov, "_write_latest_pointer", lambda **kwargs: None)
    monkeypatch.setattr(markov, "_write_topic_modeling_report", lambda **kwargs: applied.setdefault("called", True))
    monkeypatch.setattr(markov, "_fit_and_decode", lambda **kwargs: ([0], [], 1))
    monkeypatch.setattr(markov, "_write_transitions_json", lambda **kwargs: None)
    monkeypatch.setattr(markov, "_write_topic_assignments", lambda **kwargs: None)
    monkeypatch.setattr(markov, "_write_graphviz", lambda **kwargs: None)
    class DummyReport(SimpleNamespace):
        def model_dump_json(self, *a, **k):
            return "{}"

    # short-circuit before MarkovAnalysisReport validation: cause _run_markov to raise our sentinel
    class StopRun(RuntimeError):
        pass

    monkeypatch.setattr(markov, "MarkovAnalysisReport", lambda **kwargs: (_ for _ in ()).throw(StopRun()))

    # Shortcut: call the inner function that would otherwise validate transitions/states,
    # by patching _build_states to a minimal valid state list.
    monkeypatch.setattr(
        markov,
        "_build_states",
        lambda **kwargs: [markov.MarkovAnalysisState(state_id=0, label="s", exemplars=[])],
    )

    with pytest.raises(StopRun):
        markov._run_markov(
            corpus=corpus,
            configuration_name="cfg",
            config=config,
            extraction_snapshot=snapshot,
        )
    # ensure topic modeling was reapplied even with cached observations
    assert applied.get("called", False)


def test_build_observations_handles_start_and_completion_errors(monkeypatch):
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        text_source=MarkovAnalysisTextSourceConfig.model_construct(),
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(),
        observations=MarkovAnalysisObservationsConfig.model_construct(),
        model=MarkovAnalysisModelConfig.model_construct(family=MarkovAnalysisModelFamily.CATEGORICAL),
        topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(),
        llm_observations=MarkovAnalysisLlmObservationsConfig.model_construct(
            enabled=True,
            cache=MarkovAnalysisLlmObservationsCacheConfig.model_construct(enabled=False),
            client={"provider": "mock"},
            prompt_template="{segment}",
        ),
    )

    segments = [
        MarkovAnalysisSegment(item_id="i", segment_index=1, text="START"),
        MarkovAnalysisSegment(item_id="i", segment_index=2, text="segment text"),
    ]

    def fake_completion(**kwargs):
        raise ValueError("bad response")

    monkeypatch.setattr(markov, "generate_completion", fake_completion)
    observations = markov._build_observations(segments=segments, config=config, cache_context=None)
    assert observations[0].llm_label == "START"
    assert observations[1].llm_label == "unknown"


def test_load_llm_observation_cache_handles_bad_content(tmp_path):
    cache = tmp_path / "bad.json"
    cache.write_text('{"segments": [{"segment_index": "x"}, "notdict"]}', encoding="utf-8")
    loaded = markov._load_llm_observation_cache(cache)
    assert loaded == {}
