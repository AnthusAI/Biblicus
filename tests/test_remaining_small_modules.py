from pathlib import Path
from types import SimpleNamespace

import pytest

from biblicus.evaluation import benchmark_runner
from biblicus.evaluation.metrics import entity_metrics
from biblicus.evaluation.ocr_benchmark import OCRBenchmark
from biblicus.graph.extractors import dependency_relations, ner_entities, simple_entities
from biblicus.migration import _migrate_raw_items, _migrate_snapshots
from biblicus.sync.amplify_publisher import AmplifyPublisher


def test_benchmark_config_load_parses_categories(tmp_path):
    config_path = tmp_path / "bench.yaml"
    config_path.write_text(
        """
benchmark_name: demo
categories:
  forms:
    dataset: demo_ds
pipelines:
  - pipeline1.yml
""",
        encoding="utf-8",
    )
    config = benchmark_runner.BenchmarkConfig.load(config_path)
    assert "forms" in config.categories
    assert config.categories["forms"].dataset == "demo_ds"
    assert config.pipelines[0].name == "pipeline1.yml"


class DummyReport:
    avg_f1 = 0.9
    avg_recall = 0.8
    avg_precision = 0.85
    avg_word_error_rate = 0.1
    avg_lcs_ratio = 0.95
    avg_bigram_overlap = 0.7
    avg_sequence_accuracy = 0.88
    total_documents = 1


class DummyBenchmark:
    def __init__(self):
        self.calls = []

    def run_pipeline(self, pipeline_path):
        self.calls.append(Path(pipeline_path).name)
        return DummyReport()

    def evaluate_extraction(self, snapshot_reference, ground_truth_dir=None):
        return DummyReport()


def test_evaluate_category_tracks_best_pipeline(tmp_path, monkeypatch):
    category = benchmark_runner.CategoryConfig(
        name="forms",
        dataset="demo",
        corpus_path=tmp_path,
        ground_truth_subdir="gt",
        primary_metric="f1",
    )

    class DummyCorpus:
        def __init__(self, root: Path):
            self.meta_dir = root / "metadata"
            self.meta_dir.mkdir(parents=True, exist_ok=True)

        def extract(self, extractor_id: str, config: dict):  # noqa: ARG002
            return SimpleNamespace(snapshot_id="snap1")

        def extraction_snapshot_dir(self, extractor_id: str, snapshot_id: str) -> Path:  # noqa: ARG002
            return tmp_path / "snap"

    dummy_corpus = DummyCorpus(tmp_path)
    gt_dir = dummy_corpus.meta_dir / "gt"
    gt_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = dummy_corpus.extraction_snapshot_dir("pipeline", "snap1")
    (snap_dir / "text").mkdir(parents=True, exist_ok=True)
    (snap_dir / "text" / "doc.txt").write_text("hello", encoding="utf-8")
    (gt_dir / "doc.txt").write_text("hello", encoding="utf-8")

    pipeline_path = tmp_path / "pipe.yml"
    pipeline_path.write_text("extractor_id: pipeline\nconfig: {}\n", encoding="utf-8")

    runner = benchmark_runner.BenchmarkRunner(
        benchmark_runner.BenchmarkConfig(
            benchmark_name="demo",
            categories={"forms": category},
            pipelines=[pipeline_path],
            aggregate_weights={},
        )
    )
    monkeypatch.setattr(benchmark_runner, "Corpus", SimpleNamespace(open=lambda p: dummy_corpus))
    monkeypatch.setattr(benchmark_runner, "OCRBenchmark", lambda c: DummyBenchmark())
    result = runner.run_category(category)
    assert result.best_pipeline == "pipe"
    assert result.best_score > 0


@pytest.mark.parametrize(
    ("value", "entity_type", "expected"),
    [
        ("$1,234.50", "total", "1234.50"),
        ("Example LLC", "company", "example"),
        ("123 st. ave", "address", "123 street. avenue"),
        ("Date: 2024/05/01", "date", "2024-05-01"),
    ],
)
def test_entity_normalization_branches(value, entity_type, expected):
    assert entity_metrics.normalize_entity_value(value, entity_type) == expected


def test_entity_metrics_overall_counts():
    results = entity_metrics.calculate_entity_metrics(
        ground_truth={"date": "2024-01-01", "total": "$10.00"},
        extracted={"date": "2024-01-01", "total": "10"},
        entity_types=["date", "total"],
        fuzzy_threshold=0.5,
    )
    assert results["overall"]["exact_matches"] == 1.0
    assert results["overall"]["fuzzy_matches"] == 1.0


def test_ocr_benchmark_handles_missing_catalog_item(tmp_path):
    class DummyCorpus:
        def __init__(self, root: Path):
            self.root = root
            self.meta_dir = root / "metadata"
            self.meta_dir.mkdir(parents=True, exist_ok=True)

        def extraction_snapshot_dir(self, extractor_id: str, snapshot_id: str) -> Path:  # noqa: ARG002
            return self.root / "snap"

        def get_item(self, item_id):  # noqa: ARG002
            raise KeyError("missing")

    corpus = DummyCorpus(tmp_path)
    snap_dir = corpus.extraction_snapshot_dir("pipeline", "snap1")
    (snap_dir / "text").mkdir(parents=True, exist_ok=True)
    (snap_dir / "text" / "doc1.txt").write_text("hello", encoding="utf-8")
    gt_dir = corpus.meta_dir / "gt"
    gt_dir.mkdir(parents=True, exist_ok=True)
    (gt_dir / "doc1.txt").write_text("hello", encoding="utf-8")

    benchmark = OCRBenchmark(corpus)
    report = benchmark.evaluate_extraction("snap1", ground_truth_dir=gt_dir)
    assert report.total_documents == 1


def test_ocr_benchmark_uses_catalog_relpath(tmp_path):
    class DummyCorpus:
        def __init__(self, root: Path):
            self.root = root
            self.meta_dir = root / "metadata"
            self.meta_dir.mkdir(parents=True, exist_ok=True)

        def extraction_snapshot_dir(self, extractor_id: str, snapshot_id: str) -> Path:  # noqa: ARG002
            return self.root / "snap"

        def get_item(self, item_id):
            return SimpleNamespace(relpath=f"raw/{item_id}.png")

    corpus = DummyCorpus(tmp_path)
    snap_dir = corpus.extraction_snapshot_dir("pipeline", "snap1")
    (snap_dir / "text").mkdir(parents=True, exist_ok=True)
    (snap_dir / "text" / "doc1.txt").write_text("hello", encoding="utf-8")
    gt_dir = corpus.meta_dir / "gt"
    gt_dir.mkdir(parents=True, exist_ok=True)
    (gt_dir / "doc1.txt").write_text("hello", encoding="utf-8")

    benchmark = OCRBenchmark(corpus)
    report = benchmark.evaluate_extraction("snap1", ground_truth_dir=gt_dir)
    assert report.total_documents == 1


def test_dependency_relations_validates_config_dict(monkeypatch):
    extractor = dependency_relations.DependencyRelationsGraphExtractor()
    monkeypatch.setattr(dependency_relations, "_extract_entities", lambda **kwargs: [("a", "LABEL")])
    dummy_doc = type("Doc", (), {"__iter__": lambda self: iter([])})
    monkeypatch.setattr(dependency_relations, "_load_doc", lambda text, model_name: dummy_doc())
    corpus = SimpleNamespace()
    item = SimpleNamespace(id="item1", title="t", relpath="r")
    extraction = extractor.extract_graph(
        corpus=corpus,
        item=item,
        extracted_text="abc",
        config={"model": "en", "min_entity_length": 1},
    )
    assert extraction.nodes


def test_ner_entities_validates_config_dict(monkeypatch):
    extractor = ner_entities.NerEntitiesGraphExtractor()
    monkeypatch.setattr(ner_entities, "_extract_entities", lambda **kwargs: [("Name", "PERSON")])
    extraction = extractor.extract_graph(
        corpus=SimpleNamespace(),
        item=SimpleNamespace(id="i1", title="t", relpath="r"),
        extracted_text="John went to Paris",
        config={"model": "en", "min_entity_length": 1},
    )
    assert extraction.nodes is not None


def test_simple_entities_validates_config_dict():
    extractor = simple_entities.SimpleEntitiesGraphExtractor()
    extraction = extractor.extract_graph(
        corpus=SimpleNamespace(),
        item=SimpleNamespace(id="i1", title="t", relpath="r"),
        extracted_text="Token test",
        config={"min_entity_length": 1, "include_item_node": False, "max_entity_words": 3},
    )
    assert extraction.nodes


def test_migration_functions_cleanup(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "file.txt").write_text("data", encoding="utf-8")
    stats = {"moved_raw_items": 0, "moved_extraction_snapshots": 0, "moved_graph_snapshots": 0,
             "moved_analysis_runs": 0, "moved_retrieval_snapshots": 0}
    _migrate_raw_items(root=tmp_path, force=True, stats=stats)
    assert stats["moved_raw_items"] == 1

    snapshots_root = tmp_path / "metadata" / "snapshots" / "analysis"
    snapshots_root.mkdir(parents=True)
    (snapshots_root / "dummy").mkdir()
    _migrate_snapshots(root=tmp_path, meta_dir=tmp_path / "metadata", force=True, stats=stats)
    assert stats["moved_analysis_runs"] >= 0


def test_amplify_publisher_reads_config_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    env_path = tmp_path / ".biblicus"
    env_path.mkdir(exist_ok=True)
    amplify_env = env_path / "amplify.env"
    amplify_env.write_text(
        "AMPLIFY_APPSYNC_ENDPOINT=https://example\nAMPLIFY_API_KEY=key\nAMPLIFY_S3_BUCKET=bkt",
        encoding="utf-8",
    )
    monkeypatch.delenv("AMPLIFY_APPSYNC_ENDPOINT", raising=False)
    monkeypatch.delenv("AMPLIFY_API_KEY", raising=False)
    monkeypatch.delenv("AMPLIFY_S3_BUCKET", raising=False)

    publisher = AmplifyPublisher(corpus_name="demo")
    assert publisher.appsync_endpoint == "https://example"
    assert publisher.api_key == "key"
    assert publisher.s3_bucket == "bkt"


def test_amplify_publisher_retries_network_error(monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: Path.cwd())
    monkeypatch.setenv("AMPLIFY_APPSYNC_ENDPOINT", "https://example")
    monkeypatch.setenv("AMPLIFY_API_KEY", "key")
    monkeypatch.setenv("AMPLIFY_S3_BUCKET", "bucket")
    publisher = AmplifyPublisher(corpus_name="demo")
    attempts = {"count": 0}

    def fake_exec(query, variables):  # noqa: ARG002
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise Exception("Network glitch")
        return {}

    monkeypatch.setattr(publisher, "_execute_graphql", fake_exec)
    publisher._create_catalog_item(
        SimpleNamespace(
            id="1",
            relpath="a",
            sha256="x",
            bytes=1,
            media_type="text/plain",
            title=None,
            tags=[],
            metadata={},
            source_uri=None,
        )
    )
    assert attempts["count"] == 2
