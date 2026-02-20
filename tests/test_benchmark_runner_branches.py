from types import SimpleNamespace

from biblicus.evaluation.benchmark_runner import CategoryConfig, CategoryResult, run_category


def test_run_category_tracks_primary_metric(monkeypatch, tmp_path):
    cat_config = CategoryConfig(
        name="cat",
        dataset="ds",
        primary_metric="f1",
        pipelines=[SimpleNamespace(name="p1")],
    )
    cat_dir = tmp_path

    class FakeRunner:
        def run_pipeline(self, pipeline_name):
            return SimpleNamespace(
                avg_f1=0.9,
                avg_recall=0.8,
                avg_precision=0.85,
                avg_word_error_rate=0.1,
                avg_lcs_ratio=0.7,
                avg_bigram_overlap=0.6,
                avg_sequence_accuracy=0.5,
                total_documents=2,
            )

    result: CategoryResult = run_category(cat_dir, cat_config, FakeRunner())
    assert result.best_pipeline == "p1"
    assert result.primary_score == 0.9
