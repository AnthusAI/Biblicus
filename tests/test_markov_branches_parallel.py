from types import SimpleNamespace

from biblicus.analysis import markov


def test_markov_llm_observation_parallel(monkeypatch):
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda client, system_prompt, user_prompt: '{"label": "p", "label_confidence": 0.9, "summary": "s"}',
    )
    monkeypatch.setattr(markov, "_parse_json_object", lambda text, error_label: {"label": "p", "label_confidence": 0.9, "summary": "s"})
    # speed up timing
    monkeypatch.setattr(markov.time, "perf_counter", lambda: 0.0)
    config = SimpleNamespace(
        llm_observations=SimpleNamespace(
            enabled=True,
            client=SimpleNamespace(response_format=None),
            prompt_template="{segment}",
            system_prompt=None,
            cache=SimpleNamespace(enabled=False),
            max_workers=2,
        ),
        embeddings=SimpleNamespace(enabled=False),
    )
    segments = [
        markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="body1"),
        markov.MarkovAnalysisSegment(item_id="i", segment_index=2, text="body2"),
    ]
    observations = markov._build_observations(segments=segments, config=config, cache_context=None)
    assert all(obs.llm_label == "p" for obs in observations)
