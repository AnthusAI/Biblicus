import json

from biblicus.analysis import markov
from biblicus.analysis.models import (
    MarkovAnalysisConfiguration,
    MarkovAnalysisSegmentationConfig,
    MarkovAnalysisSegmentationMethod,
    MarkovAnalysisLlmSegmentationConfig,
)


def test_cached_topic_report_incompatible_recomputes(tmp_path, capsys):
    report_path = tmp_path / "topic_modeling.json"
    report_path.write_text(json.dumps({"topics": "bad"}), encoding="utf-8")
    assert markov._load_topic_modeling_report(run_dir=tmp_path) is None
    assert "recomputing" in capsys.readouterr().err


def test_llm_segments_retry_non_transient(monkeypatch):
    def fake_extract(request):  # noqa: ARG001
        raise ValueError("permanent")

    monkeypatch.setattr(markov, "apply_text_extract", fake_extract)
    monkeypatch.setattr(markov, "_is_transient_llm_error", lambda msg: False)
    monkeypatch.setattr(
        markov, "generate_completion", lambda **kwargs: "[\"abc\"]"
    )
    config = MarkovAnalysisConfiguration(
        segmentation=MarkovAnalysisSegmentationConfig(
            method=MarkovAnalysisSegmentationMethod.LLM,
            llm=MarkovAnalysisLlmSegmentationConfig(
                prompt_template="{text}",
                client={"provider": "mock", "model": "m"},
            ),
        ),
    )
    segments = markov._llm_segments(item_id="i", text="abc", config=config)
    assert segments[0].text == "abc"
