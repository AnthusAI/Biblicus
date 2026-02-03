from __future__ import annotations

from typing import List
from unittest.mock import patch

from behave import when

from biblicus.analysis.markov import _build_observations
from biblicus.analysis.models import MarkovAnalysisConfiguration, MarkovAnalysisSegment


def _segments_from_csv(*, csv_text: str) -> List[MarkovAnalysisSegment]:
    tokens = [token.strip() for token in (csv_text or "").split(",") if token.strip()]
    segments: List[MarkovAnalysisSegment] = []
    for index, token in enumerate(tokens, start=1):
        segments.append(MarkovAnalysisSegment(item_id="item", segment_index=index, text=token))
    return segments


def _recipe_with_embeddings_enabled() -> MarkovAnalysisConfiguration:
    return MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "embeddings": {
                "enabled": True,
                "client": {
                    "provider": "openai",
                    "model": "text-embedding-3-small",
                    "api_key": "test-key",
                    "batch_size": 16,
                    "parallelism": 2,
                },
                "text_source": "segment_text",
            },
            "observations": {"encoder": "embedding"},
            "model": {"family": "gaussian", "n_states": 2},
        }
    )


@when('I attempt to build markov observations with embeddings for segments "{segments_csv}"')
def step_attempt_build_markov_observations_embeddings(context, segments_csv: str) -> None:
    segments = _segments_from_csv(csv_text=segments_csv)
    config = _recipe_with_embeddings_enabled()
    try:
        _build_observations(segments=segments, config=config)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when(
    'I attempt to build markov observations with embeddings for segments "{segments_csv}" returning {count:d} vectors'
)
def step_attempt_build_markov_observations_embeddings_wrong_count(
    context, segments_csv: str, count: int
) -> None:
    segments = _segments_from_csv(csv_text=segments_csv)
    config = _recipe_with_embeddings_enabled()
    vectors: List[List[float]] = [[0.0, 0.0] for _ in range(count)]
    try:
        with patch(
            "biblicus.analysis.markov.generate_embeddings_batch",
            return_value=vectors,
        ):
            _build_observations(segments=segments, config=config)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc
