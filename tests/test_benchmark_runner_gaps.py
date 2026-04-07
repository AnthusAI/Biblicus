
from biblicus.evaluation import benchmark_runner


class DummySnapshot:
    def __init__(self, snapshot_id: str):
        self.snapshot_id = snapshot_id


def test_run_category_best_score_and_error_path(tmp_path, monkeypatch):
    corpus_dir = tmp_path / "corpus"
    gt_dir = corpus_dir / "meta" / "gt"
    gt_dir.mkdir(parents=True)

    pipeline_ok = tmp_path / "p1.yml"
    pipeline_bad = tmp_path / "missing.yml"
    pipeline_ok.write_text("extractor_id: pipeline\nconfig: {}\n", encoding="utf-8")
    # missing.yml intentionally absent to trigger exception

    config = benchmark_runner.BenchmarkConfig(
        benchmark_name="demo",
        categories={},
        pipelines=[pipeline_ok, pipeline_bad],
        aggregate_weights={},
        output_dir=tmp_path,
    )

    runner = benchmark_runner.BenchmarkRunner(config=config)

    # fake corpus
    class FakeCorpus:
        meta_dir = corpus_dir / "meta"

        def extract(self, extractor_id, config):  # noqa: ARG002
            return DummySnapshot("snap1")

    monkeypatch.setattr(benchmark_runner.Corpus, "open", lambda p: FakeCorpus())

    # fake OCRBenchmark
    class FakeReport:
        avg_f1 = 0.5
        avg_recall = 0.4
        avg_precision = 0.6
        avg_word_error_rate = 0.1
        avg_lcs_ratio = 0.2
        avg_bigram_overlap = 0.3
        avg_sequence_accuracy = 0.7
        total_documents = 3

    class FakeBenchmark:
        def __init__(self, corpus):  # noqa: ARG002
            pass

        def evaluate_extraction(self, snapshot_reference, ground_truth_dir):  # noqa: ARG002
            return FakeReport()

    monkeypatch.setattr(benchmark_runner, "OCRBenchmark", FakeBenchmark)

    cat = benchmark_runner.CategoryConfig(
        name="forms",
        dataset="forms",
        corpus_path=corpus_dir,
        ground_truth_subdir="gt",
        primary_metric="f1",
    )

    result = runner.run_category(cat)
    assert result.best_pipeline == "p1"
    assert result.best_score == 0.5
    # second pipeline missing file should have been skipped via error path
    assert len(result.pipelines) == 1
