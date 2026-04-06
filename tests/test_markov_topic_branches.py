import pytest
from types import SimpleNamespace

from biblicus.analysis import markov
from biblicus.analysis.models import (
    MarkovAnalysisConfiguration,
    MarkovAnalysisObservationsConfig,
    MarkovAnalysisObservationsEncoder,
    MarkovAnalysisModelConfig,
    MarkovAnalysisModelFamily,
    MarkovAnalysisSegment,
    MarkovAnalysisTopicModelingConfig,
    MarkovAnalysisSegmentationConfig,
    MarkovAnalysisLlmObservationsConfig,
    TopicModelingConfiguration,
)


def _base_config():
    return MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        text_source=markov.MarkovAnalysisTextSourceConfig.model_construct(),
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(),
        observations=MarkovAnalysisObservationsConfig.model_construct(
            encoder=MarkovAnalysisObservationsEncoder.TFIDF
        ),
        model=MarkovAnalysisModelConfig.model_construct(family=MarkovAnalysisModelFamily.GAUSSIAN),
        topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(
            enabled=True, configuration=TopicModelingConfiguration.model_construct()
        ),
        llm_observations=MarkovAnalysisLlmObservationsConfig.model_construct(),
    )


def test_apply_topic_modeling_requires_non_boundary_segments():
    config = _base_config()
    boundary = markov.MarkovAnalysisObservation(item_id="i", segment_index=1, segment_text="START")
    with pytest.raises(ValueError):
        markov._apply_topic_modeling(observations=[boundary], config=config, artifacts_dir=None)


def test_encode_observations_categorical_requires_labels():
    config = _base_config()
    config.model = MarkovAnalysisModelConfig.model_construct(family=MarkovAnalysisModelFamily.CATEGORICAL)
    config.observations.categorical_source = "llm_label"
    observations = [
        markov.MarkovAnalysisObservation(item_id="i", segment_index=1, segment_text="a", llm_label="x"),
        markov.MarkovAnalysisObservation(item_id="i", segment_index=2, segment_text="b", llm_label="y"),
    ]
    encoded, lengths = markov._encode_observations(observations=observations, config=config)
    assert encoded == [0, 1]
    assert lengths == [2]


def test_encode_observations_embedded_requires_embeddings():
    config = _base_config()
    config.model = MarkovAnalysisModelConfig.model_construct(family=MarkovAnalysisModelFamily.GAUSSIAN)
    config.observations.encoder = MarkovAnalysisObservationsEncoder.EMBEDDING
    obs = markov.MarkovAnalysisObservation(item_id="i", segment_index=1, segment_text="a", embedding=[0.1, 0.2])
    encoded, lengths = markov._encode_observations(observations=[obs], config=config)
    assert lengths == [1]
    assert encoded == [[0.1, 0.2]]


def test_segment_span_markup_retry_falls_back_to_llm(monkeypatch):
    config = _base_config()
    # enable span markup with prepend_label to hit exception then fallback to _llm_segments
    from biblicus.analysis.models import MarkovAnalysisSpanMarkupSegmentationConfig
    config.segmentation.span_markup = MarkovAnalysisSpanMarkupSegmentationConfig.model_construct(
        prompt_template="tpl",
        client={"provider": "mock", "model": "demo"},
        prepend_label=True,
        label_attribute="label",
        chunk_characters=None,
    )
    def fake_apply_text_extract(request):
        raise ValueError("boom")
    monkeypatch.setattr(markov, "apply_text_extract", fake_apply_text_extract)
    dummy_result = SimpleNamespace(spans=[SimpleNamespace(text="body", attributes={"label": "LBL"})])
    monkeypatch.setattr(markov, "apply_text_annotate", lambda request: dummy_result)
    monkeypatch.setattr(
        markov,
        "_llm_segments",
        lambda *, item_id, text, config: [MarkovAnalysisSegment(item_id=item_id, segment_index=1, text=text)],
    )
    segments = markov._span_markup_segments(
        item_id="i",
        text="hello world",
        config=config,
    )
    assert segments
