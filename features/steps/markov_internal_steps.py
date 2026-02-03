from __future__ import annotations

import builtins
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, List

from behave import given, then, when

from biblicus.analysis.markov import (
    MarkovStateName,
    MarkovStateNamingResponse,
    _add_boundary_segments,
    _apply_boundary_labels,
    _apply_start_end_labels,
    _apply_topic_modeling,
    _assign_state_names,
    _build_observations,
    _build_states,
    _compute_state_position_stats,
    _Document,
    _encode_observations,
    _fit_and_decode,
    _fixed_window_segments,
    _llm_segments,
    _parse_json_list,
    _parse_json_object,
    _segment_documents,
    _span_markup_segments,
    _state_naming_context_pack,
    _tfidf_encode,
    _validate_state_names,
    _verify_end_label,
    _write_graphviz,
)
from biblicus.analysis.models import (
    MarkovAnalysisArtifactsConfig,
    MarkovAnalysisArtifactsGraphVizConfig,
    MarkovAnalysisConfiguration,
    MarkovAnalysisDecodedPath,
    MarkovAnalysisEmbeddingsConfig,
    MarkovAnalysisLlmObservationsConfig,
    MarkovAnalysisModelConfig,
    MarkovAnalysisObservation,
    MarkovAnalysisObservationsConfig,
    MarkovAnalysisReportConfig,
    MarkovAnalysisSegment,
    MarkovAnalysisSegmentationConfig,
    MarkovAnalysisSpanMarkupSegmentationConfig,
    MarkovAnalysisState,
    MarkovAnalysisStateNamingConfig,
    MarkovAnalysisTopicModelingConfig,
    MarkovAnalysisTransition,
)
from biblicus.text.markup import TextAnnotatedSpan
from biblicus.text.models import TextAnnotateResult, TextExtractResult, TextExtractSpan


def _record_error(context, func: Callable[[], Any]) -> None:
    try:
        func()
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I add markov boundary segments for an empty segment list")
def step_add_markov_boundary_segments_empty(context) -> None:
    context.last_boundary_segments = _add_boundary_segments(segments=[])


@then("the markov boundary segments result is empty")
def step_boundary_segments_result_empty(context) -> None:
    segments = getattr(context, "last_boundary_segments", None)
    assert isinstance(segments, list)
    assert segments == []


@given("the Markov end label verifier returns:")
def step_set_markov_end_label_verifier_response(context) -> None:
    context.markov_end_label_verifier_response_text = str(context.text or "").strip()


@when('I apply start/end labels to span-markup payloads for item "{item_id}":')
def step_apply_start_end_labels_with_rejected_end(context, item_id: str) -> None:
    payloads = json.loads(str(context.text or "[]"))
    assert isinstance(payloads, list)

    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion
    response_text = str(getattr(context, "markov_end_label_verifier_response_text", "")).strip()

    def fake_generate_completion(*args, **kwargs):  # type: ignore[no-untyped-def]
        return response_text

    try:
        markov_module.generate_completion = fake_generate_completion  # type: ignore[assignment]
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return spans.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "start_label_value": "START",
                        "end_label_value": "END",
                        "end_reject_label_value": "END_REJECTED",
                        "end_reject_reason_prefix": "Reason",
                        "end_label_verifier": {
                            "client": {
                                "provider": "openai",
                                "model": "gpt-4o-mini",
                                "api_key": "test-key",
                            },
                            "system_prompt": "Verify end:\n{text}",
                            "prompt_template": "Return end decision.",
                        },
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.last_segments = _apply_start_end_labels(
            item_id=item_id, payloads=payloads, config=config
        )
    finally:
        markov_module.generate_completion = original_generate_completion  # type: ignore[assignment]


@then("the start/end labeled segments include a prefixed START segment")
def step_start_end_labeled_segments_include_start(context) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert segments
    assert segments[0].text.startswith("START\n")


@then("the start/end labeled segments include a rejected END segment with a reason")
def step_start_end_labeled_segments_include_rejected_end(context) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert segments
    assert segments[-1].text.startswith("END_REJECTED\nReason: truncated\n")


@then("the end label is not applied to the final segment")
def step_end_label_not_applied(context) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert segments
    assert not segments[-1].text.startswith("END\n")
    assert not segments[-1].text.startswith("END_REJECTED\n")


@then("the rejected END segment includes no reason line")
def step_rejected_end_no_reason_line(context) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert segments
    assert segments[-1].text.startswith("END_REJECTED\n")
    assert "Reason:" not in segments[-1].text


@when('I apply start/end labels without an end label for item "{item_id}":')
def step_apply_start_end_labels_without_end_label(context, item_id: str) -> None:
    payloads = json.loads(str(context.text or "[]"))
    assert isinstance(payloads, list)
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "segmentation": {
                "method": "span_markup",
                "span_markup": {
                    "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test-key"},
                    "prompt_template": "Return spans.",
                    "system_prompt": "Current text:\n---\n{text}\n---\n",
                    "start_label_value": "START",
                },
            },
            "model": {"family": "gaussian", "n_states": 2},
            "observations": {"encoder": "tfidf"},
        }
    )
    context.last_segments = _apply_start_end_labels(
        item_id=item_id, payloads=payloads, config=config
    )


@when('I apply start/end labels with rejected end but no rejection label for item "{item_id}":')
def step_apply_start_end_labels_rejected_end_without_rejection_label(context, item_id: str) -> None:
    payloads = json.loads(str(context.text or "[]"))
    assert isinstance(payloads, list)

    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion
    response_text = str(getattr(context, "markov_end_label_verifier_response_text", "")).strip()

    def fake_generate_completion(*args, **kwargs):  # type: ignore[no-untyped-def]
        return response_text

    try:
        markov_module.generate_completion = fake_generate_completion  # type: ignore[assignment]
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return spans.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "start_label_value": "START",
                        "end_label_value": "END",
                        "end_label_verifier": {
                            "client": {
                                "provider": "openai",
                                "model": "gpt-4o-mini",
                                "api_key": "test-key",
                            },
                            "system_prompt": "Verify end:\n{text}",
                            "prompt_template": "Return end decision.",
                        },
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.last_segments = _apply_start_end_labels(
            item_id=item_id, payloads=payloads, config=config
        )
    finally:
        markov_module.generate_completion = original_generate_completion  # type: ignore[assignment]


@when('I apply start/end labels with rejected end and no reason for item "{item_id}":')
def step_apply_start_end_labels_rejected_end_without_reason(context, item_id: str) -> None:
    payloads = json.loads(str(context.text or "[]"))
    assert isinstance(payloads, list)

    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion
    response_text = str(getattr(context, "markov_end_label_verifier_response_text", "")).strip()

    def fake_generate_completion(*args, **kwargs):  # type: ignore[no-untyped-def]
        return response_text

    try:
        markov_module.generate_completion = fake_generate_completion  # type: ignore[assignment]
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return spans.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "start_label_value": "START",
                        "end_label_value": "END",
                        "end_reject_label_value": "END_REJECTED",
                        "end_reject_reason_prefix": "Reason",
                        "end_label_verifier": {
                            "client": {
                                "provider": "openai",
                                "model": "gpt-4o-mini",
                                "api_key": "test-key",
                            },
                            "system_prompt": "Verify end:\n{text}",
                            "prompt_template": "Return end decision.",
                        },
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        context.last_segments = _apply_start_end_labels(
            item_id=item_id, payloads=payloads, config=config
        )
    finally:
        markov_module.generate_completion = original_generate_completion  # type: ignore[assignment]


@when("I attempt to apply topic modeling with enabled true but no configuration")
def step_attempt_apply_topic_modeling_missing_configuration(context) -> None:
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(enabled=True, configuration=None),  # type: ignore[arg-type]
    )
    observations: List[MarkovAnalysisObservation] = []

    def _invoke() -> None:
        _apply_topic_modeling(observations=observations, config=config)

    _record_error(context, _invoke)


@when("I attempt to apply topic modeling with only boundary segments")
def step_attempt_apply_topic_modeling_only_boundaries(context) -> None:
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(
            enabled=True, configuration=SimpleNamespace()
        ),
    )
    observations: List[MarkovAnalysisObservation] = [
        MarkovAnalysisObservation(
            item_id="item",
            segment_index=1,
            segment_text="START",
            topic_id=None,
            topic_label=None,
        ),
        MarkovAnalysisObservation(
            item_id="item",
            segment_index=2,
            segment_text="END",
            topic_id=None,
            topic_label=None,
        ),
    ]

    def _invoke() -> None:
        _apply_topic_modeling(observations=observations, config=config)

    _record_error(context, _invoke)


@when("I attempt to apply topic modeling that returns no assignment for a segment")
def step_attempt_apply_topic_modeling_missing_assignment(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_run_topic_modeling_for_documents = markov_module.run_topic_modeling_for_documents

    def fake_run_topic_modeling_for_documents(*args, **kwargs):  # type: ignore[no-untyped-def]
        missing_topic = SimpleNamespace(topic_id=0, label="Missing", document_ids=[])
        return SimpleNamespace(topics=[missing_topic])

    try:
        markov_module.run_topic_modeling_for_documents = fake_run_topic_modeling_for_documents  # type: ignore[assignment]
        config = MarkovAnalysisConfiguration.model_construct(
            schema_version=1,
            topic_modeling=MarkovAnalysisTopicModelingConfig.model_construct(
                enabled=True, configuration=SimpleNamespace()
            ),
        )
        observations: List[MarkovAnalysisObservation] = [
            MarkovAnalysisObservation(
                item_id="item",
                segment_index=1,
                segment_text="Alpha",
                topic_id=None,
                topic_label=None,
            )
        ]

        def _invoke() -> None:
            _apply_topic_modeling(observations=observations, config=config)

        _record_error(context, _invoke)
    finally:
        markov_module.run_topic_modeling_for_documents = original_run_topic_modeling_for_documents  # type: ignore[assignment]


@when("I build markov states with an out-of-range predicted state id")
def step_build_markov_states_out_of_range(context) -> None:
    segments = [MarkovAnalysisSegment(item_id="item", segment_index=1, text="Alpha")]
    context.last_states = _build_states(
        segments=segments,
        predicted_states=[99],
        n_states=2,
        max_exemplars=5,
    )


@then("the built markov states include no exemplars for the unknown state id")
def step_built_states_no_exemplars_for_unknown(context) -> None:
    states = getattr(context, "last_states", None)
    assert isinstance(states, list)
    assert all(len(state.exemplars or []) == 0 for state in states)


@when("I build markov states with max exemplars 1 and a boundary token")
def step_build_markov_states_boundary_token_replaces(context) -> None:
    segments = [
        MarkovAnalysisSegment(item_id="item", segment_index=1, text="Alpha"),
        MarkovAnalysisSegment(item_id="item", segment_index=2, text="START"),
    ]
    context.last_states = _build_states(
        segments=segments,
        predicted_states=[0, 0],
        n_states=1,
        max_exemplars=1,
    )


@then('the built markov state exemplars end with "START"')
def step_built_states_exemplar_ends_with_start(context) -> None:
    states = getattr(context, "last_states", None)
    assert isinstance(states, list)
    assert states
    exemplars = states[0].exemplars or []
    assert exemplars
    assert exemplars[-1] == "START"


@when("I assign markov state names with only START and END states")
def step_assign_markov_state_names_only_boundaries(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "report": {
                "state_naming": {
                    "enabled": True,
                    "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test-key"},
                    "system_prompt": "Context:\n{context_pack}",
                    "prompt_template": "Return names for states: {state_ids}",
                }
            },
        }
    )
    states = [
        MarkovAnalysisState(state_id=0, label=None, exemplars=["START"]),
        MarkovAnalysisState(state_id=1, label=None, exemplars=["END"]),
    ]
    context.last_states = _assign_state_names(states=states, decoded_paths=[], config=config)


@then('the assigned markov state labels include "START"')
def step_assigned_markov_state_labels_include_start(context) -> None:
    states = getattr(context, "last_states", None)
    assert isinstance(states, list)
    labels = {state.label for state in states}
    assert "START" in labels


@then('the assigned markov state labels include "END"')
def step_assigned_markov_state_labels_include_end(context) -> None:
    states = getattr(context, "last_states", None)
    assert isinstance(states, list)
    labels = {state.label for state in states}
    assert "END" in labels


@when("I apply markov boundary labels with a middle state")
def step_apply_markov_boundary_labels_with_middle_state(context) -> None:
    states = [
        MarkovAnalysisState(state_id=0, label="Alpha", exemplars=[]),
        MarkovAnalysisState(state_id=1, label="Middle", exemplars=[]),
        MarkovAnalysisState(state_id=2, label="Omega", exemplars=[]),
    ]
    context.last_states = _apply_boundary_labels(
        states=states,
        start_state_id=0,
        end_state_id=2,
    )


@then('the middle markov state label remains "Middle"')
def step_middle_markov_state_label_remains_middle(context) -> None:
    states = getattr(context, "last_states", None)
    assert isinstance(states, list)
    middle_state = next(state for state in states if state.state_id == 1)
    assert middle_state.label == "Middle"


@when("I compute state position stats with a single-state decoded path")
def step_compute_state_position_stats_single_state_path(context) -> None:
    decoded_paths = [MarkovAnalysisDecodedPath(item_id="item", state_sequence=[0])]
    context.last_position_stats = _compute_state_position_stats(
        decoded_paths=decoded_paths,
        start_state_id=None,
        end_state_id=None,
    )


@then("the computed position stats are empty")
def step_computed_position_stats_empty(context) -> None:
    stats = getattr(context, "last_position_stats", None)
    assert isinstance(stats, dict)
    assert stats == {}


@when("I write a GraphViz file for a model with no boundary exemplars and an unobserved edge")
def step_write_graphviz_no_boundary_exemplars_unobserved_edge(context) -> None:
    run_dir = Path(context.workdir) / "graphviz-no-boundaries"
    run_dir.mkdir(parents=True, exist_ok=True)
    graphviz = MarkovAnalysisArtifactsGraphVizConfig(
        min_edge_weight=0.0,
        rankdir="LR",
        start_state_id=None,
        end_state_id=None,
    )
    states = [
        MarkovAnalysisState(state_id=0, label=None, exemplars=[]),
        MarkovAnalysisState(state_id=1, label=None, exemplars=[]),
        MarkovAnalysisState(state_id=2, label=None, exemplars=[]),
    ]
    transitions = [
        MarkovAnalysisTransition(from_state=0, to_state=1, weight=1.0),
        MarkovAnalysisTransition(from_state=0, to_state=2, weight=1.0),
    ]
    decoded_paths = [MarkovAnalysisDecodedPath(item_id="item", state_sequence=[0, 1])]
    _write_graphviz(
        run_dir=run_dir,
        transitions=transitions,
        graphviz=graphviz,
        states=states,
        decoded_paths=decoded_paths,
    )
    context.graphviz_no_boundary_text = (run_dir / "transitions.dot").read_text(encoding="utf-8")


@then("the GraphViz file does not include start and end ranks")
def step_graphviz_file_omits_ranks(context) -> None:
    text = getattr(context, "graphviz_no_boundary_text", "")
    assert "rank=min" not in text
    assert "rank=max" not in text


@then('the GraphViz file does not contain "0 -> 2"')
def step_graphviz_file_omits_unobserved_edge(context) -> None:
    text = getattr(context, "graphviz_no_boundary_text", "")
    assert "0 -> 2" not in text


@when(
    "I attempt fixed window segmentation with max_characters {max_characters:d} and overlap_characters {overlap_characters:d}"
)
def step_attempt_fixed_window_validation(
    context, max_characters: int, overlap_characters: int
) -> None:
    def _invoke() -> None:
        _fixed_window_segments(
            item_id="item",
            text="AlphaBeta",
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )

    _record_error(context, _invoke)


@when(
    'I snapshot fixed window segmentation on text "{text}" with max_characters {max_characters:d} and overlap_characters {overlap_characters:d}'
)
def step_run_fixed_window_segmentation(
    context, text: str, max_characters: int, overlap_characters: int
) -> None:
    segments = _fixed_window_segments(
        item_id="item",
        text=text,
        max_characters=max_characters,
        overlap_characters=overlap_characters,
    )
    context.last_segments = segments
    context.last_error = None


@when(
    "I snapshot fixed window segmentation on empty text with max_characters {max_characters:d} and overlap_characters {overlap_characters:d}"
)
def step_run_fixed_window_segmentation_empty_text(
    context, max_characters: int, overlap_characters: int
) -> None:
    segments = _fixed_window_segments(
        item_id="item",
        text="",
        max_characters=max_characters,
        overlap_characters=overlap_characters,
    )
    context.last_segments = segments
    context.last_error = None


@then("the fixed window segmentation returns {count:d} segments")
def step_fixed_window_returns_segment_count(context, count: int) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert len(segments) == count


@then("the fixed window segmentation returns more than 1 segment")
def step_fixed_window_returns_more_than_one(context) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert len(segments) > 1


@when("I attempt to parse JSON list {raw_json} for label {label_json}")
def step_attempt_parse_json_list(context, raw_json: str, label_json: str) -> None:
    raw = raw_json.strip('"')
    label = label_json.strip('"')

    def _invoke() -> None:
        _parse_json_list(raw, error_label=label)

    _record_error(context, _invoke)


@when("I attempt to parse JSON object {raw_json} for label {label_json}")
def step_attempt_parse_json_object(context, raw_json: str, label_json: str) -> None:
    raw = raw_json.strip('"')
    label = label_json.strip('"')

    def _invoke() -> None:
        _parse_json_object(raw, error_label=label)

    _record_error(context, _invoke)


@when("I attempt to segment documents with unsupported segmentation method")
def step_attempt_segment_documents_unsupported_method(context) -> None:
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(method="unsupported", fixed_window=None, llm=None),  # type: ignore[arg-type]
        observations=MarkovAnalysisObservationsConfig(),
        model=MarkovAnalysisModelConfig(),
        llm_observations=MarkovAnalysisLlmObservationsConfig(),
        embeddings=MarkovAnalysisEmbeddingsConfig(),
        artifacts=MarkovAnalysisArtifactsConfig(),
    )
    documents = [_Document(item_id="item", text="Alpha.")]

    def _invoke() -> None:
        _segment_documents(documents=documents, config=config)

    _record_error(context, _invoke)


@when("I attempt to segment documents that produce no segments")
def step_attempt_segment_documents_produce_no_segments(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "segmentation": {"method": "sentence"},
            "model": {"family": "gaussian", "n_states": 2},
        }
    )
    documents = [_Document(item_id="item", text="")]

    def _invoke() -> None:
        _segment_documents(documents=documents, config=config)

    _record_error(context, _invoke)


@when("I attempt to segment a document with llm method but missing llm config")
def step_attempt_llm_segments_missing_llm_config(context) -> None:
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(method="llm", fixed_window=None, llm=None),  # type: ignore[arg-type]
        observations=MarkovAnalysisObservationsConfig(),
        model=MarkovAnalysisModelConfig(),
        llm_observations=MarkovAnalysisLlmObservationsConfig(),
        embeddings=MarkovAnalysisEmbeddingsConfig(),
        artifacts=MarkovAnalysisArtifactsConfig(),
    )

    def _invoke() -> None:
        _llm_segments(item_id="item", text="Alpha.", config=config)

    _record_error(context, _invoke)


@when("I attempt llm segmentation with json object segments not a list")
def step_attempt_llm_segments_invalid_json_object(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion

    def fake_generate_completion(*args, **kwargs):  # type: ignore[no-untyped-def]
        return '{"segments":"Alpha"}'

    markov_module.generate_completion = fake_generate_completion  # type: ignore[assignment]
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "llm",
                    "llm": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                            "response_format": "json_object",
                        },
                        "prompt_template": "{text}",
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
            }
        )

        def _invoke() -> None:
            _llm_segments(item_id="item", text="Alpha.", config=config)

        _record_error(context, _invoke)
    finally:
        markov_module.generate_completion = original_generate_completion  # type: ignore[assignment]


@when('I snapshot llm segmentation that returns an empty segment and "Alpha"')
def step_run_llm_segmentation_filters_empty(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion

    def fake_generate_completion(*args, **kwargs):  # type: ignore[no-untyped-def]
        return '["", "Alpha"]'

    markov_module.generate_completion = fake_generate_completion  # type: ignore[assignment]
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "llm",
                    "llm": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "{text}",
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
            }
        )
        segments = _llm_segments(item_id="item", text="Alpha.", config=config)
        context.last_segments = segments
        context.last_error = None
    finally:
        markov_module.generate_completion = original_generate_completion  # type: ignore[assignment]


@when("I attempt span markup segmentation with missing config")
def step_attempt_span_markup_segments_missing_config(context) -> None:
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        segmentation=MarkovAnalysisSegmentationConfig.model_construct(
            method="span_markup", fixed_window=None, llm=None, span_markup=None  # type: ignore[arg-type]
        ),
        observations=MarkovAnalysisObservationsConfig(),
        model=MarkovAnalysisModelConfig(),
        llm_observations=MarkovAnalysisLlmObservationsConfig(),
        embeddings=MarkovAnalysisEmbeddingsConfig(),
        artifacts=MarkovAnalysisArtifactsConfig(),
    )

    def _invoke() -> None:
        _span_markup_segments(item_id="item", text="Alpha.", config=config)

    _record_error(context, _invoke)


@when('I snapshot span markup segmentation with an empty span and "Alpha"')
def step_run_span_markup_segments_filters_empty(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_apply_text_extract = markov_module.apply_text_extract

    def fake_apply_text_extract(request):  # type: ignore[no-untyped-def]
        return TextExtractResult(
            marked_up_text=request.text,
            spans=[
                TextExtractSpan(index=1, start_char=0, end_char=0, text=""),
                TextExtractSpan(index=2, start_char=0, end_char=5, text="Alpha"),
            ],
            warnings=[],
        )

    markov_module.apply_text_extract = fake_apply_text_extract  # type: ignore[assignment]
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return the requested text.",
                        "system_prompt": "Current text:\\n---\\n{text}\\n---\\nWhen finished, call done.",
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
            }
        )
        segments = _span_markup_segments(item_id="item", text="Alpha.", config=config)
        context.last_segments = segments
        context.last_error = None
    finally:
        markov_module.apply_text_extract = original_apply_text_extract  # type: ignore[assignment]


@then("the llm segmentation returns {count:d} segment")
def step_llm_segmentation_returns_count(context, count: int) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert len(segments) == count


@then("the span markup segmentation returns {count:d} segment")
def step_span_markup_segmentation_returns_count(context, count: int) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert len(segments) == count


@when("I attempt to encode observations with unsupported observations encoder")
def step_attempt_encode_observations_unsupported_encoder(context) -> None:
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        segmentation=MarkovAnalysisSegmentationConfig(),
        observations=MarkovAnalysisObservationsConfig.model_construct(  # type: ignore[arg-type]
            encoder="unsupported",
            tfidf=None,
            text_source="segment_text",
            categorical_source="llm_label",
            numeric_source="llm_label_confidence",
        ),
        model=MarkovAnalysisModelConfig(),
        llm_observations=MarkovAnalysisLlmObservationsConfig(),
        embeddings=MarkovAnalysisEmbeddingsConfig(),
        artifacts=MarkovAnalysisArtifactsConfig(),
    )

    def _invoke() -> None:
        _encode_observations(observations=[], config=config)

    _record_error(context, _invoke)


@when("I attempt to encode hybrid observations with missing embeddings")
def step_attempt_encode_hybrid_observations_missing_embeddings(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "observations": {"encoder": "hybrid"},
            "model": {"family": "gaussian", "n_states": 2},
        }
    )
    observations = [
        MarkovAnalysisObservation(
            item_id="item", segment_index=1, segment_text="Alpha", embedding=None
        )
    ]

    def _invoke() -> None:
        _encode_observations(observations=observations, config=config)

    _record_error(context, _invoke)


@when(
    'I encode hybrid observations using categorical_source "{categorical_source}" and '
    'numeric_source "{numeric_source}"'
)
def step_encode_hybrid_observations_with_sources(
    context, categorical_source: str, numeric_source: str
) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "observations": {
                "encoder": "hybrid",
                "categorical_source": categorical_source,
                "numeric_source": numeric_source,
            },
            "model": {"family": "gaussian", "n_states": 2},
        }
    )
    observations = [
        MarkovAnalysisObservation(
            item_id="item",
            segment_index=2,
            segment_text="Alpha",
            llm_label="ignored",
            llm_summary="alpha",
            llm_label_confidence=0.5,
            embedding=[0.1],
        ),
        MarkovAnalysisObservation(
            item_id="item",
            segment_index=2,
            segment_text="Beta",
            llm_label="ignored",
            llm_summary="beta",
            llm_label_confidence=0.5,
            embedding=[0.2],
        ),
    ]
    matrix, _lengths = _encode_observations(observations=observations, config=config)
    context.last_hybrid_matrix = matrix
    context.last_error = None


@then("the hybrid encoding vector width equals {width:d}")
def step_hybrid_encoding_vector_width_equals(context, width: int) -> None:
    matrix = getattr(context, "last_hybrid_matrix", None)
    assert isinstance(matrix, list)
    assert matrix
    first = matrix[0]
    assert isinstance(first, list)
    assert len(first) == width


@then("the hybrid encoding numeric feature equals {expected:f}")
def step_hybrid_encoding_numeric_feature_equals(context, expected: float) -> None:
    matrix = getattr(context, "last_hybrid_matrix", None)
    assert isinstance(matrix, list)
    first = matrix[0]
    assert isinstance(first, list)
    numeric_value = first[1]
    assert float(numeric_value) == expected


@when(
    "I attempt to tfidf encode texts with max_features {max_features:d} and ngram_range {ngram_range_json}"
)
def step_attempt_tfidf_encode_invalid(context, max_features: int, ngram_range_json: str) -> None:
    raw = ngram_range_json.strip('"')
    parts = [int(token.strip()) for token in raw.strip("[]").split(",") if token.strip()]
    ngram_range = (parts[0], parts[1])

    def _invoke() -> None:
        _tfidf_encode(texts=["Alpha Beta"], max_features=max_features, ngram_range=ngram_range)

    _record_error(context, _invoke)


@when("I tfidf encode texts with max_features {max_features:d} and ngram_range {ngram_range_json}")
def step_run_tfidf_encode(context, max_features: int, ngram_range_json: str) -> None:
    raw = ngram_range_json.strip('"')
    parts = [int(token.strip()) for token in raw.strip("[]").split(",") if token.strip()]
    ngram_range = (parts[0], parts[1])
    vectors = _tfidf_encode(
        texts=["alpha beta", "alpha gamma"], max_features=max_features, ngram_range=ngram_range
    )
    context.last_tfidf_vectors = vectors
    context.last_error = None


@then("the tfidf encoding produces vectors with width {width:d}")
def step_tfidf_vectors_have_width(context, width: int) -> None:
    vectors = getattr(context, "last_tfidf_vectors", None)
    assert isinstance(vectors, list)
    assert vectors
    first = vectors[0]
    assert isinstance(first, list)
    assert len(first) == width


@when("I fit and decode a categorical Markov model without numpy")
def step_fit_and_decode_categorical_without_numpy(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {"schema_version": 1, "model": {"family": "categorical", "n_states": 2}}
    )

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "numpy":
            raise ImportError("numpy not available")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = guarded_import  # type: ignore[assignment]
    try:
        predicted, transitions, n_states = _fit_and_decode(
            observations=[0, 1],
            lengths=[2],
            config=config,
        )
        context.last_predicted_states = predicted
        context.last_error = None
        assert n_states == 2
        assert transitions is not None
    finally:
        builtins.__import__ = original_import  # type: ignore[assignment]


@when("I fit and decode a gaussian Markov model without numpy")
def step_fit_and_decode_gaussian_without_numpy(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {"schema_version": 1, "model": {"family": "gaussian", "n_states": 2}}
    )

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "numpy":
            raise ImportError("numpy not available")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = guarded_import  # type: ignore[assignment]
    try:
        predicted, transitions, n_states = _fit_and_decode(
            observations=[[0.0], [1.0]],
            lengths=[2],
            config=config,
        )
        context.last_predicted_states = predicted
        context.last_error = None
        assert n_states == 2
        assert transitions is not None
    finally:
        builtins.__import__ = original_import  # type: ignore[assignment]


@when("I build observations with embeddings from llm summaries")
def step_build_observations_with_llm_summary_embeddings(context) -> None:
    import sys
    import types

    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion
    original_dspy = sys.modules.get("dspy")

    class _FakeEmbedder:  # noqa: N801 - external dependency uses PascalCase
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            _ = args, kwargs

        def __call__(self, inputs, **kwargs):  # type: ignore[no-untyped-def]
            _ = kwargs
            inputs_list = inputs if isinstance(inputs, list) else [inputs]
            vectors = [[float(len(str(text)))] for text in inputs_list]
            if isinstance(inputs, list):
                return vectors
            return vectors[0]

    dspy_module = types.ModuleType("dspy")
    dspy_module.Embedder = _FakeEmbedder
    sys.modules["dspy"] = dspy_module

    def fake_generate_completion(*args: object, **kwargs: object) -> str:
        return '{"summary":"Alpha"}'

    setattr(markov_module, "generate_completion", fake_generate_completion)
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "segmentation": {"method": "sentence"},
                "observations": {"encoder": "tfidf"},
                "model": {"family": "gaussian", "n_states": 2},
                "llm_observations": {
                    "enabled": True,
                    "client": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "api_key": "test-key",
                    },
                    "prompt_template": "{segment}",
                },
                "embeddings": {
                    "enabled": True,
                    "text_source": "llm_summary",
                    "client": {
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "api_key": "test-key",
                    },
                },
            }
        )
        segments = [MarkovAnalysisSegment(item_id="item", segment_index=1, text="Alpha")]
        observations = _build_observations(segments=segments, config=config)
        context.last_observations = observations
        context.last_error = None
    finally:
        setattr(markov_module, "generate_completion", original_generate_completion)
        if original_dspy is None:
            sys.modules.pop("dspy", None)
        else:
            sys.modules["dspy"] = original_dspy


@then("the observations include embeddings")
def step_observations_include_embeddings(context) -> None:
    observations = getattr(context, "last_observations", None)
    assert isinstance(observations, list)
    assert observations
    assert observations[0].embedding is not None


@when("I encode categorical observations")
def step_encode_categorical_observations(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "observations": {"encoder": "tfidf", "categorical_source": "llm_label"},
            "model": {"family": "categorical", "n_states": 2},
        }
    )
    observations = [
        MarkovAnalysisObservation(
            item_id="item", segment_index=1, segment_text="Alpha", llm_label="x"
        ),
        MarkovAnalysisObservation(
            item_id="item", segment_index=2, segment_text="Beta", llm_label="y"
        ),
    ]
    encoded, _lengths = _encode_observations(observations=observations, config=config)
    context.last_encoded = encoded
    context.last_error = None


@then("the categorical encoding includes integers")
def step_categorical_encoding_includes_integers(context) -> None:
    encoded = getattr(context, "last_encoded", None)
    assert isinstance(encoded, list)
    assert all(isinstance(value, int) for value in encoded)


@when("I fit and decode a categorical Markov model with numpy")
def step_fit_and_decode_categorical_with_numpy(context) -> None:
    import sys
    import types

    original_numpy = sys.modules.get("numpy")
    try:
        import numpy as numpy_module

        context.numpy_available = numpy_module is not None
    except ImportError:
        numpy_module = types.ModuleType("numpy")

        def asarray(values: object, dtype: object = None) -> object:
            return values

        numpy_module.asarray = asarray
        sys.modules["numpy"] = numpy_module
        context.numpy_available = True

    config = MarkovAnalysisConfiguration.model_validate(
        {"schema_version": 1, "model": {"family": "categorical", "n_states": 2}}
    )
    predicted, transitions, n_states = _fit_and_decode(
        observations=[0, 1],
        lengths=[2],
        config=config,
    )
    context.last_predicted_states = predicted
    assert n_states == 2
    assert transitions is not None
    if original_numpy is None:
        sys.modules.pop("numpy", None)
    else:
        sys.modules["numpy"] = original_numpy


@when("I fit and decode a gaussian Markov model with numpy")
def step_fit_and_decode_gaussian_with_numpy(context) -> None:
    import sys
    import types

    original_numpy = sys.modules.get("numpy")
    try:
        import numpy as numpy_module

        context.numpy_available = numpy_module is not None
    except ImportError:
        numpy_module = types.ModuleType("numpy")

        def asarray(values: object, dtype: object = None) -> object:
            return values

        numpy_module.asarray = asarray
        sys.modules["numpy"] = numpy_module
        context.numpy_available = True

    config = MarkovAnalysisConfiguration.model_validate(
        {"schema_version": 1, "model": {"family": "gaussian", "n_states": 2}}
    )
    predicted, transitions, n_states = _fit_and_decode(
        observations=[[0.0], [1.0]],
        lengths=[2],
        config=config,
    )
    context.last_predicted_states = predicted
    assert n_states == 2
    assert transitions is not None
    if original_numpy is None:
        sys.modules.pop("numpy", None)
    else:
        sys.modules["numpy"] = original_numpy


@when("I build a Markov state naming context pack with a token budget of {budget:d}")
def step_build_state_naming_context_pack(context, budget: int) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "report": {
                "state_naming": {
                    "enabled": True,
                    "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                    "system_prompt": "Context:\\n{context_pack}",
                    "prompt_template": "Return names for states: {state_ids}",
                    "token_budget": budget,
                    "max_exemplars_per_state": 2,
                    "max_name_words": 3,
                }
            },
        }
    )
    states = [
        MarkovAnalysisState(state_id=0, label=None, exemplars=["Alpha alpha alpha alpha"]),
        MarkovAnalysisState(state_id=1, label=None, exemplars=["Beta beta beta beta"]),
    ]
    context_pack, _policy = _state_naming_context_pack(states=states, config=config)
    context.last_context_pack = context_pack


@then("the state naming context pack includes {count:d} block")
def step_state_naming_context_pack_block_count(context, count: int) -> None:
    context_pack = getattr(context, "last_context_pack", None)
    assert context_pack is not None
    assert context_pack.evidence_count == count


@when("I assign Markov state names with a provider response")
def step_assign_state_names_with_provider_response(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion

    def fake_generate_completion(*args: object, **kwargs: object) -> str:
        return (
            '{"state_names":['
            '{"state_id":0,"name":"greeting"},'
            '{"state_id":1,"name":"billing question"}'
            "]}"
        )

    setattr(markov_module, "generate_completion", fake_generate_completion)
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                        "system_prompt": "Context:\\n{context_pack}",
                        "prompt_template": "Return names for states: {state_ids}",
                        "token_budget": 200,
                        "max_exemplars_per_state": 1,
                        "max_name_words": 3,
                    }
                },
            }
        )
        states = [
            MarkovAnalysisState(state_id=0, label=None, exemplars=["Hello there"]),
            MarkovAnalysisState(state_id=1, label=None, exemplars=["Payment questions"]),
        ]
        decoded_paths = [MarkovAnalysisDecodedPath(item_id="item", state_sequence=[0, 1])]
        context.last_named_states = _assign_state_names(
            states=states, decoded_paths=decoded_paths, config=config
        )
    finally:
        setattr(markov_module, "generate_completion", original_generate_completion)


@when("I assign Markov state names with a verb phrase response")
def step_assign_state_names_with_verb_phrase_response(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion

    def fake_generate_completion(*args: object, **kwargs: object) -> str:
        return (
            '{"state_names":['
            '{"state_id":0,"name":"is greeting"},'
            '{"state_id":1,"name":"to resolve billing"}'
            "]}"
        )

    setattr(markov_module, "generate_completion", fake_generate_completion)
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                        "system_prompt": "Context:\\n{context_pack}",
                        "prompt_template": "Return names for states: {state_ids}",
                        "token_budget": 200,
                        "max_exemplars_per_state": 1,
                        "max_name_words": 3,
                        "max_retries": 0,
                    }
                },
            }
        )
        states = [
            MarkovAnalysisState(state_id=0, label=None, exemplars=["Hello there"]),
            MarkovAnalysisState(state_id=1, label=None, exemplars=["Payment questions"]),
        ]
        decoded_paths = [MarkovAnalysisDecodedPath(item_id="item", state_sequence=[0, 1])]
        try:
            _assign_state_names(states=states, decoded_paths=decoded_paths, config=config)
        except ValueError as exc:
            context.last_state_naming_error = str(exc)
        else:
            context.last_state_naming_error = None
    finally:
        setattr(markov_module, "generate_completion", original_generate_completion)


@then('the Markov state naming fails with "{message}"')
def step_state_naming_fails_with_message(context, message: str) -> None:
    error_message = getattr(context, "last_state_naming_error", None)
    assert error_message is not None
    assert message in error_message


@then("the Markov state labels include:")
def step_markov_state_labels_include(context) -> None:
    named_states = getattr(context, "last_named_states", None)
    assert named_states is not None
    labels_by_id = {state.state_id: state.label for state in named_states}
    for row in context.table:
        state_id = int(row["state_id"])
        expected = row["label"]
        if expected == "":
            expected = None
        assert labels_by_id.get(state_id) == expected


@then("the Markov state naming returns no states")
def step_markov_state_naming_returns_no_states(context) -> None:
    named_states = getattr(context, "last_named_states", None)
    assert named_states == []


@then("the fit and decode returns predicted states")
def step_fit_and_decode_returns_predicted_states(context) -> None:
    predicted = getattr(context, "last_predicted_states", None)
    assert isinstance(predicted, list)
    assert predicted


def _state_naming_validation_case(case: str) -> tuple[MarkovStateNamingResponse, List[int], int]:
    state_ids = [0, 1]
    max_name_words = 3
    if case == "empty name":
        response = MarkovStateNamingResponse(
            state_names=[
                MarkovStateName(state_id=0, name=""),
                MarkovStateName(state_id=1, name="billing"),
            ]
        )
    elif case == "punctuation":
        response = MarkovStateNamingResponse(
            state_names=[
                MarkovStateName(state_id=0, name="greeting!"),
                MarkovStateName(state_id=1, name="billing"),
            ]
        )
    elif case == "infinitive phrase":
        response = MarkovStateNamingResponse(
            state_names=[
                MarkovStateName(state_id=0, name="to greet"),
                MarkovStateName(state_id=1, name="billing"),
            ]
        )
    elif case == "duplicate state id":
        response = MarkovStateNamingResponse(
            state_names=[
                MarkovStateName(state_id=0, name="greeting"),
                MarkovStateName(state_id=0, name="billing"),
            ]
        )
    elif case == "duplicate state name":
        response = MarkovStateNamingResponse(
            state_names=[
                MarkovStateName(state_id=0, name="greeting"),
                MarkovStateName(state_id=1, name="greeting"),
            ]
        )
    elif case == "missing state ids":
        response = MarkovStateNamingResponse(
            state_names=[MarkovStateName(state_id=0, name="greeting")]
        )
    else:
        raise AssertionError(f"Unknown state naming validation case: {case}")
    return response, state_ids, max_name_words


@when('I validate state naming response with "{case}"')
def step_validate_state_naming_response_case(context, case: str) -> None:
    response, state_ids, max_name_words = _state_naming_validation_case(case)

    def _invoke() -> None:
        _validate_state_names(
            response=response,
            state_ids=state_ids,
            max_name_words=max_name_words,
        )

    _record_error(context, _invoke)


@when("I assign Markov state names with retries")
def step_assign_state_names_with_retries_and_prefixes(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion
    responses = iter(
        [
            ('{"state_names":[' '{"state_id":2,"name":"is greeting"}' "]}"),
            ('{"state_names":[' '{"state_id":2,"name":"Initial contact"}' "]}"),
        ]
    )

    def fake_generate_completion(*args: object, **kwargs: object) -> str:
        _ = args, kwargs
        return next(responses)

    setattr(markov_module, "generate_completion", fake_generate_completion)
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                        "system_prompt": "Context:\n{context_pack}",
                        "prompt_template": "Return names for states: {state_ids}",
                        "token_budget": 200,
                        "max_exemplars_per_state": 1,
                        "max_name_words": 3,
                        "max_retries": 1,
                    }
                },
            }
        )
        states = [
            MarkovAnalysisState(state_id=0, label=None, exemplars=["START"]),
            MarkovAnalysisState(state_id=1, label=None, exemplars=["END"]),
            MarkovAnalysisState(state_id=2, label=None, exemplars=["Hello there"]),
        ]
        decoded_paths = [MarkovAnalysisDecodedPath(item_id="item", state_sequence=[0, 2, 1])]
        context.last_named_states = _assign_state_names(
            states=states, decoded_paths=decoded_paths, config=config
        )
    finally:
        setattr(markov_module, "generate_completion", original_generate_completion)


@when("I attempt to assign Markov state names without a client")
def step_attempt_assign_state_names_without_client(context) -> None:
    config = MarkovAnalysisConfiguration.model_construct(
        schema_version=1,
        report=MarkovAnalysisReportConfig.model_construct(
            state_naming=MarkovAnalysisStateNamingConfig.model_construct(
                enabled=True,
                client=None,
                system_prompt="Context:\n{context_pack}",
                prompt_template="Return names for states: {state_ids}",
                max_retries=0,
            )
        ),
    )
    states = [MarkovAnalysisState(state_id=0, label=None, exemplars=["Hello there"])]

    def _invoke() -> None:
        _assign_state_names(states=states, decoded_paths=[], config=config)

    _record_error(context, _invoke)


@when("I assign Markov state names with no states")
def step_assign_state_names_with_no_states(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "report": {
                "state_naming": {
                    "enabled": True,
                    "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                    "system_prompt": "Context:\n{context_pack}",
                    "prompt_template": "Return names for states: {state_ids}",
                }
            },
        }
    )
    context.last_named_states = _assign_state_names(states=[], decoded_paths=[], config=config)


@when("I attempt to assign Markov state names with retries exhausted")
def step_attempt_assign_state_names_retries_exhausted(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion

    def fake_generate_completion(*args: object, **kwargs: object) -> str:
        _ = args, kwargs
        return '{"state_names":[{"state_id":0,"name":"is greeting"}]}'

    setattr(markov_module, "generate_completion", fake_generate_completion)
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                        "system_prompt": "Context:\n{context_pack}",
                        "prompt_template": "Return names for states: {state_ids}",
                        "max_retries": 0,
                        "max_name_words": 3,
                    }
                },
            }
        )
        states = [MarkovAnalysisState(state_id=0, label=None, exemplars=["Hello there"])]

        def _invoke() -> None:
            _assign_state_names(states=states, decoded_paths=[], config=config)

        _record_error(context, _invoke)
    finally:
        setattr(markov_module, "generate_completion", original_generate_completion)


@when("I assign Markov state names with a missing label in validation output")
def step_assign_state_names_with_missing_label_in_validation_output(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion
    original_validate_state_names = markov_module._validate_state_names

    def fake_generate_completion(*args: object, **kwargs: object) -> str:
        _ = args, kwargs
        return (
            '{"state_names":[' '{"state_id":0,"name":"Alpha"},' '{"state_id":1,"name":"Beta"}' "]}"
        )

    def fake_validate_state_names(*args: object, **kwargs: object) -> dict[int, str]:
        _ = args, kwargs
        return {0: "Alpha"}

    setattr(markov_module, "generate_completion", fake_generate_completion)
    setattr(markov_module, "_validate_state_names", fake_validate_state_names)
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "report": {
                    "state_naming": {
                        "enabled": True,
                        "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                        "system_prompt": "Context:\n{context_pack}",
                        "prompt_template": "Return names for states: {state_ids}",
                        "max_name_words": 3,
                    }
                },
            }
        )
        states = [
            MarkovAnalysisState(state_id=0, label=None, exemplars=["Hello there"]),
            MarkovAnalysisState(state_id=1, label=None, exemplars=["Payment questions"]),
        ]
        decoded_paths = [MarkovAnalysisDecodedPath(item_id="item", state_sequence=[0, 1])]
        context.last_named_states = _assign_state_names(
            states=states, decoded_paths=decoded_paths, config=config
        )
    finally:
        setattr(markov_module, "_validate_state_names", original_validate_state_names)
        setattr(markov_module, "generate_completion", original_generate_completion)


@when("I attempt span markup segmentation with prepend label but no label attribute")
def step_attempt_span_markup_prepend_without_label_attribute(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_apply_text_annotate = markov_module.apply_text_annotate

    def fake_apply_text_annotate(*args: object, **kwargs: object) -> TextAnnotateResult:
        _ = args, kwargs
        span = TextAnnotatedSpan(
            index=1,
            start_char=0,
            end_char=5,
            text="Hello",
            attributes={},
        )
        return TextAnnotateResult(marked_up_text="Hello", spans=[span])

    setattr(markov_module, "apply_text_annotate", fake_apply_text_annotate)
    try:
        segmentation = MarkovAnalysisSegmentationConfig.model_construct(
            method="span_markup",
            fixed_window=None,
            llm=None,
            span_markup=MarkovAnalysisSpanMarkupSegmentationConfig.model_construct(
                client={"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                prompt_template="Return segments.",
                system_prompt="Current text:\n---\n{text}\n---\n",
                prepend_label=True,
                label_attribute=None,
            ),
        )
        config = MarkovAnalysisConfiguration.model_construct(
            schema_version=1, segmentation=segmentation
        )

        def _invoke() -> None:
            _span_markup_segments(item_id="item", text="Hello", config=config)

        _record_error(context, _invoke)
    finally:
        setattr(markov_module, "apply_text_annotate", original_apply_text_annotate)


@when("I attempt span markup segmentation with missing label value")
def step_attempt_span_markup_missing_label_value(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_apply_text_annotate = markov_module.apply_text_annotate

    def fake_apply_text_annotate(*args: object, **kwargs: object) -> TextAnnotateResult:
        _ = args, kwargs
        span = TextAnnotatedSpan(
            index=1,
            start_char=0,
            end_char=5,
            text="Hello",
            attributes={},
        )
        return TextAnnotateResult(marked_up_text="Hello", spans=[span])

    setattr(markov_module, "apply_text_annotate", fake_apply_text_annotate)
    try:
        segmentation = MarkovAnalysisSegmentationConfig.model_construct(
            method="span_markup",
            fixed_window=None,
            llm=None,
            span_markup=MarkovAnalysisSpanMarkupSegmentationConfig.model_construct(
                client={"provider": "openai", "model": "gpt-4o-mini", "api_key": "test"},
                prompt_template="Return segments.",
                system_prompt="Current text:\n---\n{text}\n---\n",
                prepend_label=True,
                label_attribute="label",
            ),
        )
        config = MarkovAnalysisConfiguration.model_construct(
            schema_version=1, segmentation=segmentation
        )

        def _invoke() -> None:
            _span_markup_segments(item_id="item", text="Hello", config=config)

        _record_error(context, _invoke)
    finally:
        setattr(markov_module, "apply_text_annotate", original_apply_text_annotate)


@when("I apply start/end labels with an end verifier decision")
def step_apply_start_end_labels_with_verifier(context) -> None:
    import biblicus.analysis.markov as markov_module

    original_generate_completion = markov_module.generate_completion

    def fake_generate_completion(*args: object, **kwargs: object) -> str:
        _ = args, kwargs
        return '{"is_end": true, "reason": "ok"}'

    setattr(markov_module, "generate_completion", fake_generate_completion)
    try:
        config = MarkovAnalysisConfiguration.model_validate(
            {
                "schema_version": 1,
                "segmentation": {
                    "method": "span_markup",
                    "span_markup": {
                        "client": {
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                            "api_key": "test-key",
                        },
                        "prompt_template": "Return the segments.",
                        "system_prompt": "Current text:\n---\n{text}\n---\n",
                        "end_label_value": "End",
                        "end_label_verifier": {
                            "client": {
                                "provider": "openai",
                                "model": "gpt-4o-mini",
                                "api_key": "test-key",
                            },
                            "system_prompt": "Verify end:\n{text}",
                            "prompt_template": "Return end decision.",
                        },
                    },
                },
                "model": {"family": "gaussian", "n_states": 2},
                "observations": {"encoder": "tfidf"},
            }
        )
        payloads = [{"segment_index": 1, "body": "Goodbye", "text": "Goodbye"}]
        context.last_segments = _apply_start_end_labels(
            item_id="item",
            payloads=payloads,
            config=config,
        )
    finally:
        setattr(markov_module, "generate_completion", original_generate_completion)


@then("the end label is applied to the final segment")
def step_end_label_applied_to_final_segment(context) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert segments
    assert segments[-1].text.startswith("End\n")


@when("I verify end label without a verifier configured")
def step_verify_end_label_without_verifier(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "segmentation": {
                "method": "span_markup",
                "span_markup": {
                    "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test-key"},
                    "prompt_template": "Return the segments.",
                    "system_prompt": "Current text:\n---\n{text}\n---\n",
                },
            },
            "model": {"family": "gaussian", "n_states": 2},
            "observations": {"encoder": "tfidf"},
        }
    )
    context.last_end_label_decision = _verify_end_label(text="Goodbye", config=config)


@then("the end label verification returns no decision")
def step_end_label_verification_returns_none(context) -> None:
    decision = getattr(context, "last_end_label_decision", None)
    assert decision is None


@when("I apply start/end labels with no payloads")
def step_apply_start_end_labels_no_payloads(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "segmentation": {
                "method": "span_markup",
                "span_markup": {
                    "client": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "test-key"},
                    "prompt_template": "Return the segments.",
                    "system_prompt": "Current text:\n---\n{text}\n---\n",
                },
            },
            "model": {"family": "gaussian", "n_states": 2},
            "observations": {"encoder": "tfidf"},
        }
    )
    context.last_segments = _apply_start_end_labels(
        item_id="item",
        payloads=[],
        config=config,
    )


@then("the start/end labeling returns {count:d} segments")
def step_start_end_labeling_returns_count(context, count: int) -> None:
    segments = getattr(context, "last_segments", None)
    assert isinstance(segments, list)
    assert len(segments) == count


@when("I attempt to apply start/end labels without span markup config")
def step_attempt_apply_start_end_labels_without_config(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "segmentation": {"method": "sentence"},
            "model": {"family": "gaussian", "n_states": 2},
            "observations": {"encoder": "tfidf"},
        }
    )

    def _invoke() -> None:
        _apply_start_end_labels(
            item_id="item", payloads=[{"segment_index": 1, "body": "x", "text": "x"}], config=config
        )

    _record_error(context, _invoke)


@when("I build a Markov state naming context pack with state naming disabled")
def step_state_naming_context_pack_disabled(context) -> None:
    config = MarkovAnalysisConfiguration.model_validate(
        {
            "schema_version": 1,
            "report": {"state_naming": {"enabled": False}},
        }
    )
    states = [MarkovAnalysisState(state_id=0, label=None, exemplars=["Hello there"])]
    context_pack, _policy = _state_naming_context_pack(states=states, config=config)
    context.last_context_pack = context_pack


@when("I write a GraphViz transitions file with inferred start/end states")
def step_write_graphviz_transitions_with_inferred_roles(context) -> None:
    run_dir = context.workdir / "graphviz"
    run_dir.mkdir(parents=True, exist_ok=True)
    graphviz = MarkovAnalysisArtifactsGraphVizConfig(
        min_edge_weight=0.0,
        rankdir="LR",
        start_state_id=None,
        end_state_id=None,
    )
    states = [
        MarkovAnalysisState(state_id=0, label="Greeting", exemplars=["start\nHello"]),
        MarkovAnalysisState(state_id=1, label="Wrap-up", exemplars=["end\nBye"]),
        MarkovAnalysisState(
            state_id=2,
            label="Greeting follow-up",
            exemplars=["start\nHello", "start\nHello again"],
        ),
    ]
    transitions = [
        MarkovAnalysisTransition(from_state=1, to_state=0, weight=0.2),
        MarkovAnalysisTransition(from_state=0, to_state=1, weight=0.8),
    ]
    decoded_paths: List[MarkovAnalysisDecodedPath] = []
    _write_graphviz(
        run_dir=run_dir,
        transitions=transitions,
        graphviz=graphviz,
        states=states,
        decoded_paths=decoded_paths,
    )
    context.graphviz_text = (run_dir / "transitions.dot").read_text(encoding="utf-8")


@then("the graphviz output includes start and end ranks")
def step_graphviz_output_includes_start_end_ranks(context) -> None:
    text = getattr(context, "graphviz_text", "")
    assert "rank=min" in text
    assert "rank=max" in text


@then("the graphviz output omits end-state edges")
def step_graphviz_output_omits_end_edges(context) -> None:
    text = getattr(context, "graphviz_text", "")
    assert "1 -> 0" not in text


@then("the graphviz output includes model-only edge labels")
def step_graphviz_output_includes_model_only_labels(context) -> None:
    text = getattr(context, "graphviz_text", "")
    assert 'label="80.0%"' in text


@when("I write a GraphViz transitions file with explicit start/end states")
def step_write_graphviz_transitions_with_explicit_roles(context) -> None:
    run_dir = context.workdir / "graphviz-explicit"
    run_dir.mkdir(parents=True, exist_ok=True)
    graphviz = MarkovAnalysisArtifactsGraphVizConfig(
        min_edge_weight=0.0,
        rankdir="LR",
        start_state_id=2,
        end_state_id=0,
    )
    states = [
        MarkovAnalysisState(state_id=0, label="Alpha", exemplars=["end\nAlpha"]),
        MarkovAnalysisState(state_id=1, label="Beta", exemplars=["Beta"]),
        MarkovAnalysisState(state_id=2, label="Gamma", exemplars=["start\nGamma"]),
    ]
    transitions = [
        MarkovAnalysisTransition(from_state=2, to_state=1, weight=0.6),
        MarkovAnalysisTransition(from_state=1, to_state=0, weight=0.4),
    ]
    decoded_paths: List[MarkovAnalysisDecodedPath] = []
    _write_graphviz(
        run_dir=run_dir,
        transitions=transitions,
        graphviz=graphviz,
        states=states,
        decoded_paths=decoded_paths,
    )
    context.graphviz_text = (run_dir / "transitions.dot").read_text(encoding="utf-8")


@then("the graphviz output includes start state {state_id:d}")
def step_graphviz_output_includes_start_state(context, state_id: int) -> None:
    text = getattr(context, "graphviz_text", "")
    assert f"rank=min; {state_id};" in text


@then("the graphviz output includes end state {state_id:d}")
def step_graphviz_output_includes_end_state(context, state_id: int) -> None:
    text = getattr(context, "graphviz_text", "")
    assert f"rank=max; {state_id};" in text
