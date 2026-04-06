import pytest

from biblicus.analysis import markov
from biblicus.analysis.models import (
    LlmClientConfig,
    MarkovAnalysisConfiguration,
    MarkovAnalysisFixedWindowSegmentationConfig,
    MarkovAnalysisLlmSegmentationConfig,
    MarkovAnalysisSegmentationConfig,
    MarkovAnalysisSegmentationMethod,
    MarkovAnalysisSpanMarkupSegmentationConfig,
    MarkovAnalysisSpanMarkupEndLabelVerifierConfig,
    MarkovAnalysisTextSourceConfig,
    MarkovAnalysisObservationsConfig,
    MarkovAnalysisModelConfig,
    MarkovAnalysisModelFamily,
    MarkovAnalysisTopicModelingConfig,
    MarkovAnalysisLlmObservationsConfig,
    MarkovAnalysisLlmObservationsCacheConfig,
)


def _base_config(**kwargs):
    return MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        text_source=MarkovAnalysisTextSourceConfig.model_construct(),
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(
            method=MarkovAnalysisSegmentationMethod.SPAN_MARKUP,
            max_workers=1,
            fixed_window=MarkovAnalysisFixedWindowSegmentationConfig.model_construct(),
            llm=MarkovAnalysisLlmSegmentationConfig.model_construct(
                client=LlmClientConfig.model_construct(provider="mock", model="m"),
                prompt_template="{text}",
            ),
            span_markup=MarkovAnalysisSpanMarkupSegmentationConfig.model_construct(
                client=LlmClientConfig.model_construct(provider="mock", model="m"),
                prompt_template="tmpl",
                **kwargs,
            ),
        ),
        observations=MarkovAnalysisObservationsConfig.model_construct(),
        model=MarkovAnalysisModelConfig.model_construct(family=MarkovAnalysisModelFamily.GAUSSIAN),
        topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(),
        llm_observations=MarkovAnalysisLlmObservationsConfig.model_construct(
            enabled=False,
            cache=MarkovAnalysisLlmObservationsCacheConfig.model_construct(enabled=False),
        ),
    )


def test_span_markup_missing_label_raises():
    config = _base_config(prepend_label=True, label_attribute=None)
    markov.apply_text_annotate = lambda request: type("Resp", (), {"spans": [type("S", (), {"text": "t", "attributes": {}})()]})()
    with pytest.raises(ValueError):
        markov._span_markup_segments(item_id="i", text="body", config=config)


def test_span_markup_end_label_rejects(monkeypatch):
    verifier = MarkovAnalysisSpanMarkupEndLabelVerifierConfig.model_construct(
        client=LlmClientConfig.model_construct(provider="mock", model="m"),
        prompt_template="{text}",
        system_prompt="sys {text}",
    )
    config = _base_config(
        prepend_label=False,
        label_attribute=None,
        end_label_value="END",  # triggers verifier call
        end_label_verifier=verifier,
        end_reject_label_value="REJECT",
    )

    # force verifier to return not-end with reason
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda **kwargs: "{\"is_end\": false, \"reason\": \"bad\"}",
    )
    # simulate annotate returning spans with labels
    fake_span = type(
        "Span",
        (),
        {"text": "text", "attributes": {"label": "L"}},
    )
    monkeypatch.setattr(
        markov,
        "apply_text_extract",
        lambda request: type("Resp", (), {"spans": [fake_span]})(),
    )

    payloads = [{"segment_index": 1, "text": "text"}]
    segments = markov._apply_start_end_labels(item_id="i", payloads=payloads, config=config)
    assert segments[-1].text.startswith("REJECT")


def test_llm_observation_cache_stats(monkeypatch, tmp_path):
    # set up cache dir with one cached label
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "items").mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "items" / "i.json"
    cache_path.write_text(
        markov.json.dumps(
            {
                "segments": [
                    {
                        "segment_index": 1,
                        "segment_text_hash": markov.hash_text("body"),
                        "llm_label": "cached",
                        "llm_label_confidence": 0.9,
                        "llm_summary": "sum",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    cache_context = markov._LlmObservationCacheContext(
        enabled=True,
        cache_id="cid",
        cache_dir=cache_dir,
        cached_segments=0,
        generated_segments=0,
    )

    config = _base_config()
    config.llm_observations = config.llm_observations.model_copy(
        update={
            "enabled": True,
            "cache": config.llm_observations.cache.model_copy(update={"enabled": True}),
            "client": {"provider": "mock"},
            "prompt_template": "{segment}",
        }
    )

    # force labeling to return predictable payload
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda **kwargs: "{\"label\": \"x\", \"label_confidence\": 0.1, \"summary\": \"s\"}",
    )

    updated = markov._build_observations(
        segments=[markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="body"),
                  markov.MarkovAnalysisSegment(item_id="i", segment_index=2, text="new")],
        config=config,
        cache_context=cache_context,
    )

    assert cache_context.cached_segments == 1
    assert cache_context.generated_segments == 1
    assert updated[0].llm_label == "cached"
    assert updated[1].llm_label == "x"
