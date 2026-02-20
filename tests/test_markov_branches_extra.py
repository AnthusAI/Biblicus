from types import SimpleNamespace

from biblicus.analysis import markov
from biblicus.analysis.models import MarkovAnalysisConfiguration


def test_markov_span_markup_falls_back_to_llm(monkeypatch):
    # Force span_markup to raise non-transient error so llm segmentation is used.
    monkeypatch.setattr(
        markov,
        "apply_text_extract",
        lambda request: (_ for _ in ()).throw(ValueError("hard fail")),
    )
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda client, system_prompt, user_prompt: '["seg1"]',
    )
    llm_config = SimpleNamespace(
        prompt_template="{text}",
        system_prompt=None,
        client=SimpleNamespace(response_format=None),
    )
    markup_config = SimpleNamespace(
        label_attribute=None,
        prepend_label=False,
        chunk_characters=None,
        chunk_overlap_characters=0,
        system_prompt=None,
        prompt_template="extract",
        max_rounds=1,
        max_edits_per_round=1,
        normalize_nested_spans=False,
        client={"provider": "openai", "model": "gpt-4o"},
    )
    config = SimpleNamespace(segmentation=SimpleNamespace(span_markup=markup_config, llm=llm_config))
    segments = markov._span_markup_segments(item_id="i", text="hello", config=config)
    assert len(segments) == 1


def test_markov_llm_observation_handles_start_end(monkeypatch):
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda client, system_prompt, user_prompt: '{"label": "x", "label_confidence": 0.5, "summary": "s"}',
    )
    monkeypatch.setattr(markov, "_parse_json_object", lambda text, error_label: json.loads(text))
    config = SimpleNamespace(
        llm_observations=SimpleNamespace(
            enabled=True,
            client=SimpleNamespace(response_format=None),
            prompt_template="{segment}",
            system_prompt=None,
            cache=SimpleNamespace(enabled=False),
            max_workers=1,
        ),
        embeddings=SimpleNamespace(enabled=False),
    )
    observations = markov._build_observations(
        segments=[
            markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="START"),
            markov.MarkovAnalysisSegment(item_id="i", segment_index=2, text="END"),
            markov.MarkovAnalysisSegment(item_id="i", segment_index=3, text="body"),
        ],
        config=config,
        cache_context=None,
    )
    assert observations[0].llm_label == "START"
    assert observations[1].llm_label == "END"
    assert observations[2].llm_label in {"x", "unknown"}
