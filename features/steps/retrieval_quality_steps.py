from __future__ import annotations

import json
from typing import Dict

from behave import then, when
from pydantic import ValidationError

from biblicus.backends.hybrid import HybridBackend
from biblicus.backends.sqlite_full_text_search import (
    SqliteFullTextSearchRecipeConfig,
    _resolve_stop_words,
)
from biblicus.backends.vector import _build_snippet, _find_first_match
from biblicus.corpus import Corpus
from biblicus.models import QueryBudget
from biblicus.retrieval import create_recipe_manifest, create_run_manifest


def _corpus_path(context, name: str):
    workdir = getattr(context, "workdir", None)
    if workdir is None:
        raise AssertionError("Missing workdir in test context")
    return (workdir / name).resolve()


def _parse_expected_value(raw: str) -> object:
    text = raw.strip()
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _parse_weight_pairs(raw: str) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        key, value = token.split("=", 1)
        weights[key.strip()] = float(value.strip())
    return weights


def _normalize_empty_marker(text: str) -> str:
    return "" if text == "<empty>" else text


@when("I validate sqlite full-text search stop words list:")
def step_validate_sqlite_stop_words_list(context) -> None:
    values = [row["value"] if "value" in row.headings else row[0] for row in context.table]
    config = SqliteFullTextSearchRecipeConfig.model_validate({"stop_words": values})
    context.sqlite_stop_words = _resolve_stop_words(config.stop_words)
    context.validation_error = None


@when("I attempt to validate sqlite full-text search stop words list:")
def step_attempt_validate_sqlite_stop_words_list(context) -> None:
    values = [row["value"] if "value" in row.headings else row[0] for row in context.table]
    try:
        config = SqliteFullTextSearchRecipeConfig.model_validate({"stop_words": values})
        context.sqlite_stop_words = _resolve_stop_words(config.stop_words)
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to query a hybrid run without component runs")
def step_attempt_query_hybrid_without_components(context) -> None:
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    backend = HybridBackend()
    recipe = create_recipe_manifest(
        backend_id=backend.backend_id,
        name="hybrid-missing-components",
        config={
            "lexical_backend": "sqlite-full-text-search",
            "embedding_backend": "vector",
            "lexical_weight": 0.5,
            "embedding_weight": 0.5,
        },
    )
    run = create_run_manifest(corpus, recipe=recipe, stats={}, artifact_paths=[])
    budget = QueryBudget(
        max_total_items=5,
        max_total_characters=2000,
        max_items_per_source=5,
    )
    try:
        backend.query(corpus, run=run, query_text="alpha", budget=budget)
        context.validation_error = None
    except Exception as exc:
        context.validation_error = exc


@when('I compute a vector match span for text "{text}" with tokens "{tokens}"')
def step_compute_vector_match_span(context, text: str, tokens: str) -> None:
    text = _normalize_empty_marker(text)
    token_list = [token.strip() for token in tokens.split(",")]
    context.vector_match_span = _find_first_match(text, token_list)


@then("the vector match span is None")
def step_vector_match_span_is_none(context) -> None:
    assert context.vector_match_span is None


@then('the vector match span is "{span}"')
def step_vector_match_span_equals(context, span: str) -> None:
    start, end = span.split("..", 1)
    expected = (int(start), int(end))
    assert context.vector_match_span == expected


@then(
    'the vector snippet for text "{text}" with span "{span}" and max chars {max_chars:d} equals "{expected}"'
)
def step_vector_snippet_equals(
    context, text: str, span: str, max_chars: int, expected: str
) -> None:
    text = _normalize_empty_marker(text)
    expected = _normalize_empty_marker(expected)
    span_value = None
    if span.lower() != "none":
        start, end = span.split("..", 1)
        span_value = (int(start), int(end))
    snippet = _build_snippet(text, span_value, max_chars=max_chars)
    assert snippet == expected


@then('the sqlite stop words include "{token}"')
def step_sqlite_stop_words_include(context, token: str) -> None:
    stop_words = getattr(context, "sqlite_stop_words", None)
    assert isinstance(stop_words, set)
    assert token in stop_words


@then("the latest run recipe config includes:")
def step_latest_run_recipe_config_includes(context) -> None:
    run = context.last_run
    config = run.get("recipe", {}).get("config", {})
    for row in context.table:
        key = row["key"].strip() if "key" in row.headings else row[0].strip()
        value = row["value"].strip() if "value" in row.headings else row[1].strip()
        expected = _parse_expected_value(value)
        assert key in config, f"Missing recipe config key {key!r}"
        assert config[key] == expected


@then('the query evidence includes stage score "{stage}"')
def step_query_evidence_includes_stage_score(context, stage: str) -> None:
    evidence = context.last_query.get("evidence") or []
    for item in evidence:
        stage_scores = item.get("stage_scores")
        if isinstance(stage_scores, dict) and stage in stage_scores:
            return
    raise AssertionError(f"Missing stage score {stage!r} in evidence")


@then("the query stats include reranked_candidates {count:d}")
def step_query_stats_include_reranked_candidates(context, count: int) -> None:
    stats = context.last_query.get("stats") or {}
    assert stats.get("reranked_candidates") == count


@then('the query stats include fusion_weights "{weights}"')
def step_query_stats_include_fusion_weights(context, weights: str) -> None:
    stats = context.last_query.get("stats") or {}
    expected = _parse_weight_pairs(weights)
    actual = stats.get("fusion_weights")
    if isinstance(actual, dict):
        for key, value in expected.items():
            assert actual.get(key) == value
        return
    assert actual == weights
