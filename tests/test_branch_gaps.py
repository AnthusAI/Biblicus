import json
import types
from argparse import Namespace
from pathlib import Path

import pytest

from biblicus import inference, cli
from biblicus.analysis import markov, topic_modeling
from biblicus.analysis.markov import (
    MarkovAnalysisConfiguration,
    MarkovAnalysisSegment,
    MarkovAnalysisTextSourceConfig,
    _load_topic_modeling_report,
    _span_markup_segments,
)
from biblicus.corpus import Corpus
from biblicus.evaluation import benchmark_runner
from biblicus.extraction import (
    ExtractionItemResult,
    ExtractionSnapshotManifest,
    ExtractionStageResult,
    create_extraction_configuration_manifest,
)
from biblicus.models import ExtractionSnapshotReference


def test_inference_openai_user_config(monkeypatch):
    class _Cfg:
        def __init__(self):
            self.huggingface = None
            self.openai = types.SimpleNamespace(api_key="cfg-openai-branch")

    monkeypatch.setattr("biblicus.user_config.load_user_config", lambda: _Cfg())
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resolved = inference.resolve_api_key(provider=inference.ApiProvider.OPENAI)
    assert resolved == "cfg-openai-branch"


def test_markov_load_topic_modeling_report_invalid_json(tmp_path: Path):
    bad = tmp_path / "topic_modeling.json"
    bad.write_text(json.dumps({"topics": []}), encoding="utf-8")
    result = _load_topic_modeling_report(run_dir=tmp_path)
    assert result is None


def test_markov_span_markup_normalization(monkeypatch):
    cfg = MarkovAnalysisConfiguration(
        segmentation={
            "method": "span_markup",
            "span_markup": {
                "client": {"provider": "openai", "model": "gpt-4o"},
                "prompt_template": "label",
                "chunk_characters": 4,
                "chunk_overlap_characters": 0,
                "label_attribute": "label",
                "prepend_label": True,
            },
        }
    )

    class _Span:
        def __init__(self, text: str = "dup", label: str = "L"):
            self.text = text
            self.attributes = {"label": label}

    monkeypatch.setattr(markov, "apply_text_annotate", lambda request: types.SimpleNamespace(spans=[_Span(), _Span()]))
    segments = _span_markup_segments(item_id="id", text="abcd", config=cfg)
    # duplicate body should be collapsed to single normalized segment
    assert len(segments) == 1
    assert segments[0].text.replace("\n", " ").strip() == "L dup"


def test_markov_collect_documents_sample_truncation(tmp_path: Path):
    corpus = Corpus.init(tmp_path / "c")
    # create manifest with two items
    text_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id="s1") / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    (text_dir / "a.txt").write_text("hello", encoding="utf-8")
    (text_dir / "b.txt").write_text("world", encoding="utf-8")
    item_a = ExtractionItemResult(
        item_id="a",
        status="extracted",
        final_text_relpath="text/a.txt",
        final_stage_index=1,
        final_stage_extractor_id="pipeline",
        final_producer_extractor_id="pipeline",
        stage_results=[
            ExtractionStageResult(
                stage_index=1,
                extractor_id="pipeline",
                status="extracted",
                text_relpath="text/a.txt",
                text_characters=5,
            )
        ],
    )
    item_b = item_a.model_copy(update={"item_id": "b", "final_text_relpath": "text/b.txt"})
    cfg_manifest = create_extraction_configuration_manifest(
        extractor_id="pipeline",
        name="test",
        configuration={},
    )
    manifest = ExtractionSnapshotManifest(
        snapshot_id="s1",
        configuration=cfg_manifest,
        corpus_uri=corpus.uri,
        catalog_generated_at=corpus.catalog_generated_at(),
        created_at="2024-01-01T00:00:00Z",
        items=[item_a, item_b],
        stats={},
    )
    (corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id="s1") / "manifest.json").write_text(
        manifest.model_dump_json(), encoding="utf-8"
    )
    docs, report = markov._collect_documents(
        corpus=corpus,
        extraction_snapshot=ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id="s1"),
        config=MarkovAnalysisTextSourceConfig(sample_size=1, min_text_characters=None),
    )
    assert len(docs) == 1
    assert "Text collection truncated" in " ".join(report.warnings)


def test_topic_modeling_llm_itemize_empty(monkeypatch):
    documents = [topic_modeling.TopicModelingDocument(document_id="d", source_item_id="s", text="body")]
    cfg = topic_modeling.TopicModelingLlmExtractionConfig(
        enabled=True,
        method=topic_modeling.TopicModelingLlmExtractionMethod.ITEMIZE,
        client={"provider": "openai", "model": "gpt-4o"},
        prompt_template="{text}",
    )
    monkeypatch.setattr(topic_modeling, "generate_completion", lambda client, system_prompt, user_prompt: "[]")
    with pytest.raises(ValueError):
        topic_modeling._apply_llm_extraction(documents=documents, config=cfg)


def test_cli_benchmark_run_category_not_found(monkeypatch, tmp_path: Path):
    cfg = benchmark_runner.BenchmarkConfig(
        benchmark_name="b",
        categories={"only": benchmark_runner.CategoryConfig(name="only", dataset="d", corpus_path=tmp_path, ground_truth_subdir="gt", primary_metric="f1")},
        pipelines=[],
        aggregate_weights={},
    )
    monkeypatch.setattr(benchmark_runner.BenchmarkConfig, "load", lambda path: cfg)
    cfg_path = tmp_path / "cfg.yml"
    cfg_path.write_text("dummy", encoding="utf-8")
    args = Namespace(config=str(cfg_path), pipelines=None, category="missing", output=None)
    with pytest.raises(ValueError):
        cli.cmd_benchmark_run(args)


def test_cli_benchmark_status_ready(tmp_path: Path, monkeypatch):
    corpus_dir = tmp_path / "corpora"
    gt = corpus_dir / "funsd_benchmark" / ".biblicus" / "funsd_ground_truth"
    gt.mkdir(parents=True, exist_ok=True)
    (gt / "doc.txt").write_text("gt", encoding="utf-8")
    args = Namespace(corpus_dir=str(corpus_dir))
    # Should not raise; ready branch includes count
    cli.cmd_benchmark_status(args)


def test_corpus_reserved_path(tmp_path: Path):
    corpus = Corpus.init(tmp_path / "corp")
    assert corpus._is_reserved_path(corpus.meta_dir / "config.json") is True


def test_benchmark_runner_pipeline_error(monkeypatch, tmp_path: Path):
    cfg = benchmark_runner.BenchmarkConfig(
        benchmark_name="b",
        categories={
            "c": benchmark_runner.CategoryConfig(
                name="c",
                dataset="d",
                corpus_path=tmp_path,
                ground_truth_subdir="gt",
                primary_metric="f1",
            )
        },
        pipelines=[tmp_path / "missing.yml"],
        aggregate_weights={},
    )
    runner = benchmark_runner.BenchmarkRunner(config=cfg)
    # ground truth missing triggers FileNotFoundError inside run_category
    with pytest.raises(FileNotFoundError):
        runner.run_category(cfg.categories["c"])
