from types import SimpleNamespace
from pathlib import Path
import json

from biblicus.analysis import markov
from biblicus.analysis.models import (
    MarkovAnalysisConfiguration,
    MarkovAnalysisFixedWindowSegmentationConfig,
    MarkovAnalysisLlmObservationsCacheConfig,
    MarkovAnalysisLlmObservationsConfig,
    MarkovAnalysisLlmSegmentationConfig,
    MarkovAnalysisModelConfig,
    MarkovAnalysisModelFamily,
    MarkovAnalysisObservationsConfig,
    MarkovAnalysisSegmentationConfig,
    MarkovAnalysisSegmentationMethod,
    MarkovAnalysisSpanMarkupSegmentationConfig,
    MarkovAnalysisTextSourceConfig,
    MarkovAnalysisTopicModelingConfig,
)
from biblicus.models import CorpusCatalog, ExtractionSnapshotReference


def test_collect_documents_sample_size_and_empty(tmp_path):
    snapshot_dir = tmp_path / "snap"
    (snapshot_dir / "text").mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "text" / "i1.txt").write_text("hello world", encoding="utf-8")
    (snapshot_dir / "text" / "i2.txt").write_text("short", encoding="utf-8")
    (snapshot_dir / "text" / "i3.txt").write_text("", encoding="utf-8")

    class DummyCorpus:
        def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):  # noqa: ARG002
            return SimpleNamespace(
                items=[
                    SimpleNamespace(item_id="i1", status="extracted", final_text_relpath="text/i1.txt"),
                    SimpleNamespace(item_id="i2", status="extracted", final_text_relpath="text/i2.txt"),
                    SimpleNamespace(item_id="i3", status="extracted", final_text_relpath="text/i3.txt"),
                ]
            )

        def extraction_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return snapshot_dir

    documents, report = markov._collect_documents(
        corpus=DummyCorpus(),
        extraction_snapshot=ExtractionSnapshotReference(extractor_id="ex", snapshot_id="snap"),
        config=MarkovAnalysisTextSourceConfig(sample_size=1),
    )
    assert len(documents) == 1
    assert "Text collection truncated to sample_size" in report.warnings
    assert report.empty_texts == 1


def test_segment_documents_threaded_llm(monkeypatch):
    documents = [
        markov._Document(item_id="a", text="one"),
        markov._Document(item_id="b", text="two"),
    ]
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        text_source=MarkovAnalysisTextSourceConfig.model_construct(),
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(
            method=MarkovAnalysisSegmentationMethod.LLM,
            max_workers=2,
            fixed_window=MarkovAnalysisFixedWindowSegmentationConfig.model_construct(),
            llm=MarkovAnalysisLlmSegmentationConfig.model_construct(),
            span_markup=MarkovAnalysisSpanMarkupSegmentationConfig.model_construct(
                client={"provider": "mock"},
                prompt_template="{text}",
            ),
        ),
        observations=MarkovAnalysisObservationsConfig.model_construct(),
        model=MarkovAnalysisModelConfig.model_construct(family=MarkovAnalysisModelFamily.GAUSSIAN),
        topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(),
        llm_observations=MarkovAnalysisLlmObservationsConfig.model_construct(enabled=False),
    )

    monkeypatch.setattr(
        markov, "_llm_segments", lambda item_id, text, config: [markov.MarkovAnalysisSegment(item_id=item_id, segment_index=1, text=text)]
    )
    segments = markov._segment_documents(documents=documents, config=config)
    assert any(seg.text == "START" for seg in segments)
    assert any(seg.text == "END" for seg in segments)


def test_run_markov_stats_generated_segments(monkeypatch, tmp_path):
    catalog = CorpusCatalog.model_construct(
        schema_version=1,
        generated_at="2024-01-01T00:00:00Z",
        corpus_uri="file://dummy",
        raw_dir=".",
        latest_run_id=None,
        latest_snapshot_id=None,
        items={},
        order=[],
    )

    class DummyCorpus:
        def __init__(self, root: Path):
            self.root = root

        def load_catalog(self):
            return catalog

        def analysis_run_dir(self, analysis_id, snapshot_id):  # noqa: ARG002
            run_dir = self.root / "analysis" / snapshot_id
            run_dir.mkdir(parents=True, exist_ok=True)
            return run_dir

    dummy_corpus = DummyCorpus(tmp_path)
    snapshot = ExtractionSnapshotReference(extractor_id="ex", snapshot_id="snap1")

    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        text_source=MarkovAnalysisTextSourceConfig.model_construct(),
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(
            method=MarkovAnalysisSegmentationMethod.SENTENCE,
            max_workers=1,
            fixed_window=MarkovAnalysisFixedWindowSegmentationConfig.model_construct(),
            llm=MarkovAnalysisLlmSegmentationConfig.model_construct(),
            span_markup=MarkovAnalysisSpanMarkupSegmentationConfig.model_construct(
                client={"provider": "mock"}, prompt_template="{text}"
            ),
        ),
        observations=MarkovAnalysisObservationsConfig.model_construct(),
        model=MarkovAnalysisModelConfig.model_construct(family=MarkovAnalysisModelFamily.GAUSSIAN),
        topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(),
        llm_observations=MarkovAnalysisLlmObservationsConfig.model_construct(
            enabled=True,
            cache=MarkovAnalysisLlmObservationsCacheConfig.model_construct(enabled=False),
            client={"provider": "mock"},
            prompt_template="{segment}",
        ),
    )

    segment = markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="body")
    observation = markov.MarkovAnalysisObservation(
        item_id="i",
        segment_index=1,
        segment_text="body",
        llm_label="label",
        llm_summary="summary",
        llm_label_confidence=0.5,
    )
    text_report = markov.MarkovAnalysisTextCollectionReport(
        status=markov.MarkovAnalysisStageStatus.COMPLETE,
        source_items=1,
        documents=1,
        sample_size=None,
        min_text_characters=None,
        empty_texts=0,
        skipped_items=0,
        warnings=[],
        errors=[],
    )

    monkeypatch.setattr(markov, "_collect_documents", lambda **kwargs: ([markov._Document(item_id="i", text="body")], text_report))
    monkeypatch.setattr(markov, "_segment_documents", lambda **kwargs: [segment])
    monkeypatch.setattr(markov, "_apply_topic_modeling", lambda observations, config, artifacts_dir: (observations, None))
    monkeypatch.setattr(markov, "_build_observations", lambda **kwargs: [observation])
    monkeypatch.setattr(markov, "_fit_and_decode", lambda **kwargs: ([0], [], 1))
    monkeypatch.setattr(markov, "_write_segments", lambda **kwargs: None)
    monkeypatch.setattr(markov, "_write_observations", lambda **kwargs: None)
    monkeypatch.setattr(markov, "_write_transitions_json", lambda **kwargs: None)
    monkeypatch.setattr(markov, "_write_latest_pointer", lambda **kwargs: None)
    monkeypatch.setattr(markov, "_write_analysis_run_manifest", lambda **kwargs: None)

    output = markov._run_markov(
        corpus=dummy_corpus,
        configuration_name="cfg",
        config=config,
        extraction_snapshot=snapshot,
    )
    assert output.snapshot.stats["llm_observations"]["generated_segments"] == 1
