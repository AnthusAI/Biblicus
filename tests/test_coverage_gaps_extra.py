import json
import os
import sys
import types
from argparse import Namespace
from io import BytesIO
from pathlib import Path

import pytest

from biblicus import cli
from biblicus.ai.models import LlmClientConfig
from biblicus.analysis import markov, topic_modeling
from biblicus.analysis.models import (
    MarkovAnalysisSpanMarkupSegmentationConfig,
    TopicModelingEntityRemovalConfig,
)
from biblicus.corpus import Corpus
from biblicus.evaluation.benchmark_runner import BenchmarkConfig, BenchmarkRunner, CategoryConfig
from biblicus.evaluation.metrics.entity_metrics import normalize_entity_value, calculate_string_similarity
from biblicus.evaluation.stt_benchmark import STTBenchmark, STTBenchmarkReport, calculate_wer
from biblicus.sync.amplify_publisher import AmplifyPublisher
from biblicus.evaluation.metrics import entity_metrics
from biblicus import inference, user_config


def test_span_markup_config_requires_verifier():
    client = LlmClientConfig(provider="openai", model="gpt-4o-mini")
    with pytest.raises(ValueError):
        MarkovAnalysisSpanMarkupSegmentationConfig(
            client=client,
            prompt_template="Return spans",
            system_prompt="{text}",
            end_label_value="END",
        )
    with pytest.raises(ValueError):
        MarkovAnalysisSpanMarkupSegmentationConfig(
            client=client,
            prompt_template="Return spans",
            system_prompt="{text}",
            end_reject_label_value="STOP",
        )


def test_entity_metric_normalization_branches():
    assert normalize_entity_value("2024-01-01", "date") == "2024-01-01"
    assert normalize_entity_value("$1,234.50 total", "total") == "1234.50"
    assert normalize_entity_value("Acme LLC", "company") == "acme"
    assert "street" in normalize_entity_value("12 st.", "address")
    assert calculate_string_similarity("", "") == 1.0
    assert calculate_string_similarity("a", "") == 0.0


def test_stt_benchmark_edge_branches(tmp_path):
    wer_missing = calculate_wer("a b", "")
    assert wer_missing["deletions"] == 2
    wer_insertions = calculate_wer("", "a b")
    assert wer_insertions["insertions"] == 2

    report = STTBenchmarkReport(
        evaluation_timestamp="now",
        corpus_path="c",
        provider_name="p",
        provider_configuration={},
        total_audio_files=0,
        avg_wer=0.0,
        median_wer=0.0,
        avg_substitutions=0.0,
        avg_deletions=0.0,
        avg_insertions=0.0,
        avg_cer=0.0,
        median_cer=0.0,
        avg_precision=0.0,
        avg_recall=0.0,
        avg_f1=0.0,
        median_f1=0.0,
        per_audio_results=[],
    )
    csv_path = tmp_path / "empty.csv"
    report.to_csv(csv_path)
    assert not csv_path.exists()

    corpus_root = tmp_path / "corpus"
    text_dir = corpus_root / "extracted" / "pipeline" / "snap" / "text"
    text_dir.mkdir(parents=True)
    (text_dir / "clip.txt").write_text("hello", encoding="utf-8")
    benchmark = STTBenchmark(types.SimpleNamespace(root=corpus_root))
    with pytest.raises(ValueError):
        benchmark.evaluate_extraction("snap", ground_truth_dir=corpus_root / "missing_gt")


def test_amplify_config_file_fallback_and_retry(monkeypatch, tmp_path):
    monkeypatch.setenv("AMPLIFY_APPSYNC_ENDPOINT", "")
    monkeypatch.setenv("AMPLIFY_API_KEY", "")
    monkeypatch.setenv("AMPLIFY_S3_BUCKET", "")
    monkeypatch.setenv("AWS_REGION", "")
    monkeypatch.setenv("HOME", str(tmp_path))
    amplify_dir = tmp_path / ".biblicus"
    amplify_dir.mkdir()
    (amplify_dir / "amplify.env").write_text(
        "AMPLIFY_APPSYNC_ENDPOINT=https://example\nAMPLIFY_API_KEY=key\nAMPLIFY_S3_BUCKET=bucket\nAWS_REGION=us-east-1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("biblicus.sync.amplify_publisher.boto3.client", lambda *args, **kwargs: object())
    publisher = AmplifyPublisher("corpus")

    attempts = {"count": 0}

    def flaky(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise Exception("Network issue")
        return {}

    publisher._execute_graphql = flaky  # type: ignore[assignment]
    item = types.SimpleNamespace(
        id="i1",
        relpath="raw/a.txt",
        sha256="abc",
        bytes=1,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={},
        source_uri=None,
    )
    publisher._create_catalog_item(item)
    assert attempts["count"] == 3


def test_benchmark_runner_category(monkeypatch, tmp_path):
    corpus_path = tmp_path / "funsd_benchmark"
    meta_dir = corpus_path / ".biblicus" / "funsd_ground_truth"
    meta_dir.mkdir(parents=True)
    (meta_dir.parent / "config.json").write_text("{}", encoding="utf-8")
    pipeline_file = tmp_path / "pipeline.yml"
    pipeline_file.write_text("extractor_id: pipeline\nconfig: {}\n", encoding="utf-8")

    def fake_open(path):
        return types.SimpleNamespace(
            meta_dir=meta_dir.parent,
            extract=lambda extractor_id, config: types.SimpleNamespace(snapshot_id="snap1"),
        )

    class FakeBenchmark:
        def __init__(self, corpus):
            self.corpus = corpus

        def evaluate_extraction(self, snapshot_reference, ground_truth_dir):
            return types.SimpleNamespace(
                avg_f1=0.8,
                avg_recall=0.7,
                avg_precision=0.9,
                avg_word_error_rate=0.1,
                avg_lcs_ratio=0.2,
                avg_bigram_overlap=0.3,
                avg_sequence_accuracy=0.4,
                total_documents=1,
            )

    monkeypatch.setattr("biblicus.evaluation.benchmark_runner.Corpus.open", staticmethod(fake_open))
    monkeypatch.setattr("biblicus.evaluation.benchmark_runner.OCRBenchmark", FakeBenchmark)
    category = CategoryConfig(
        name="forms",
        dataset="funsd",
        corpus_path=corpus_path,
        ground_truth_subdir="funsd_ground_truth",
        primary_metric="f1",
    )
    config = BenchmarkConfig(
        benchmark_name="demo",
        categories={"forms": category},
        pipelines=[pipeline_file],
        aggregate_weights={"forms": 1.0},
        output_dir=tmp_path,
    )
    runner = BenchmarkRunner(config)
    result = runner.run_category(config.categories["forms"])
    assert result.best_pipeline == pipeline_file.stem


def test_topic_modeling_entity_removal_error_branches(monkeypatch, tmp_path):
    docs = [
        topic_modeling.TopicModelingDocument(
            document_id="d1", text="Alpha", source_item_id="s1"
        )
    ]

    with pytest.raises(ValueError):
        topic_modeling._apply_entity_removal(
            documents=docs,
            config=TopicModelingEntityRemovalConfig(enabled=True, provider="other", model="x"),
        )

    with pytest.raises(ValueError):
        topic_modeling._apply_entity_removal(
            documents=docs,
            config=TopicModelingEntityRemovalConfig(enabled=True, provider="spacy", model="missing"),
        )

    fake_spacy = types.SimpleNamespace(load=lambda model: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setitem(sys.modules, "spacy", fake_spacy)
    with pytest.raises(ValueError):
        topic_modeling._apply_entity_removal(
            documents=docs,
            config=TopicModelingEntityRemovalConfig(enabled=True, provider="spacy", model="en_core_web_sm"),
        )

    assert (
        topic_modeling._remove_entities_from_text(
            text="Alpha Beta",
            entities=[types.SimpleNamespace(label_="ORG", start_char=0, end_char=5)],
            entity_types={"ORG"},
            replace_with="",
        )
        == " Beta"
    )
    assert (
        topic_modeling._remove_entities_from_text(
            text="Alpha Beta",
            entities=[types.SimpleNamespace(label_="ORG", start_char=0, end_char=5)],
            entity_types={"ORG"},
            replace_with="[x]",
        )
        == "[x] Beta"
    )
    assert (
        topic_modeling._remove_entities_from_text(
            text="Alpha Beta",
            entities=[],
            entity_types={"ORG"},
            replace_with="",
        )
        == "Alpha Beta"
    )


def test_corpus_hooks_reserved_and_import(tmp_path):
    corpus = Corpus.init(tmp_path / "corpus")
    assert corpus._is_reserved_path(Path("/tmp/elsewhere")) is False
    assert corpus._is_reserved_path(corpus.root / ".biblicusignore") is True

    hooks_called = {"before": 0, "after": 0}

    class FakeMutation:
        def __init__(self):
            self.add_tags = ["extra"]

    class FakeHooks:
        def run_ingest_hooks(self, **kwargs):
            if kwargs["hook_point"].name == "before_ingest":
                hooks_called["before"] += 1
            else:
                hooks_called["after"] += 1
            return FakeMutation()

    corpus._hooks = FakeHooks()
    stream = BytesIO(b"hello")
    result = corpus.ingest_item_stream(stream, filename="sample.txt", media_type="text/plain", source_uri="urn:test")
    assert hooks_called["before"] == 1 and hooks_called["after"] == 1
    assert (corpus.root / result.relpath).exists()

    reserved = corpus.meta_dir / "config.json"
    reserved.parent.mkdir(parents=True, exist_ok=True)
    reserved.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        corpus._register_existing_file(path=reserved, tags=[], metadata=None, source_uri="file://bad")

    src_file = tmp_path / "import_me.md"
    src_file.write_text("---\ntitle: Doc\n---\nBody", encoding="utf-8")
    corpus._import_file(
        source_path=src_file,
        import_id="imp",
        relative_source_path="import_me.md",
        tags=["t"],
    )

    with pytest.raises(ValueError):
        corpus.purge(confirm="wrong-name")
    corpus.purge(confirm=corpus.name)


def test_cli_benchmark_and_dashboard(monkeypatch, tmp_path):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: types.SimpleNamespace(returncode=0))
    cli.cmd_benchmark_download(Namespace(datasets="funsd,unknown,scanned-arxiv", corpus_dir=str(tmp_path), count=None, force=True))

    result_file = tmp_path / "results.json"
    result_file.write_text(
        json.dumps({"benchmark_name": "demo", "timestamp": "today", "categories": {"forms": {"dataset": "ds", "documents_evaluated": 1, "best_pipeline": "p", "best_score": 0.9}}, "recommendations": {"best": "p"}}),
        encoding="utf-8",
    )
    cli.cmd_benchmark_report(Namespace(input=str(result_file), output=str(tmp_path / "report.md")))

    corpus_dir = tmp_path / "bench"
    gt_dir = corpus_dir / ".biblicus" / "funsd_ground_truth"
    gt_dir.mkdir(parents=True)
    (gt_dir.parent / "config.json").write_text("{}", encoding="utf-8")
    (gt_dir / "doc1.txt").write_text("text", encoding="utf-8")
    cli.cmd_benchmark_status(Namespace(corpus_dir=str(tmp_path)))

    class FakePublisher:
        def __init__(self, name):
            self.name = name

        def create_corpus(self):
            raise Exception("already exists")

        def sync_catalog(self, catalog_path, force=False):
            return types.SimpleNamespace(skipped=True, hash="abcd", errors=["err1"])

    class FakeCorpus:
        name = "fake"
        catalog_path = Path("catalog.json")

    import biblicus.sync.amplify_publisher as amplify_mod
    monkeypatch.setattr(amplify_mod, "AmplifyPublisher", FakePublisher)
    monkeypatch.setattr(cli, "Corpus", types.SimpleNamespace(open=lambda path: FakeCorpus(), discover=lambda: FakeCorpus()))
    assert cli.cmd_dashboard_sync(Namespace(corpus=None, force=False)) == 1


def test_markov_span_markup_and_llm_labels(monkeypatch):
    client = LlmClientConfig(provider="openai", model="gpt-4o-mini")
    config = markov.MarkovAnalysisConfiguration.model_validate(
        {
            "segmentation": {
                "method": "span_markup",
                "span_markup": {
                    "client": client.model_dump(),
                    "prompt_template": "label: {span}",
                    "system_prompt": "{text}",
                    "chunk_characters": 5,
                    "chunk_overlap_characters": 1,
                    "prepend_label": False,
                },
            },
            "model": {"family": "categorical", "n_states": 2},
            "report": {"max_state_exemplars": 1},
            "topic_modeling": {"enabled": False},
            "llm_observations": {"enabled": True, "client": client.model_dump(), "prompt_template": "Label {segment}"},
        }
    )

    def fake_extract(request):
        return types.SimpleNamespace(spans=[types.SimpleNamespace(text="Alpha"), types.SimpleNamespace(text="Beta")])

    monkeypatch.setattr(markov, "apply_text_extract", fake_extract)
    segments = markov._span_markup_segments(item_id="i1", text="AlphaBeta", config=config)
    assert segments

    monkeypatch.setattr(markov, "generate_completion", lambda **kwargs: '{"label":"x","label_confidence":1,"summary":"s"}')
    labeled = markov._build_observations(
        segments=[
            markov.MarkovAnalysisSegment(item_id="i1", segment_index=1, text="START"),
            markov.MarkovAnalysisSegment(item_id="i1", segment_index=2, text="body"),
        ],
        config=config,
        cache_context=None,
    )
    assert labeled[0].llm_label == "START"


def test_entity_metrics_paths():
    ground = {"date": "2024/01/01", "company": "Acme LLC", "address": "12 st.", "total": "$10.00"}
    extracted = {"date": "2024-01-01", "company": "Acme", "address": "12 street", "total": "$10.00"}
    metrics = entity_metrics.calculate_entity_metrics(ground, extracted)
    assert metrics["overall"]["exact_accuracy"] < 1
    f1 = entity_metrics.calculate_entity_f1([ground], [extracted])
    assert f1["overall"]["f1"] >= 0
    entities = entity_metrics.extract_entities_from_text("ACME Inc.\nTotal: $12.34\n123 Road")
    assert "total" in entities
    custom = entity_metrics.extract_entities_from_text(
        "custom", entity_patterns={"foo": r"custom"}
    )
    assert custom["foo"] == "custom"


def test_inference_hf_user_config(monkeypatch):
    class FakeHF:
        api_key = "hf-key"

    class FakeConfig:
        huggingface = FakeHF()
        openai = None

    monkeypatch.setenv("HUGGINGFACE_API_KEY", "")
    monkeypatch.setattr(user_config, "load_user_config", lambda *args, **kwargs: FakeConfig())
    assert inference.resolve_api_key(provider=inference.ApiProvider.HUGGINGFACE) == "hf-key"
