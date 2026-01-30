from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from behave import given, then, when

from biblicus.backends.scan import _build_snippet, _find_first_match
from biblicus.backends.sqlite_full_text_search import (
    SqliteFullTextSearchRecipeConfig,
    _build_full_text_search_index,
    _iter_chunks,
)
from biblicus.corpus import Corpus
from biblicus.evaluation import _run_artifact_bytes
from biblicus.models import Evidence, QueryBudget
from biblicus.retrieval import apply_budget
from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_json_output(standard_output: str) -> Dict[str, Any]:
    return json.loads(standard_output)


def _table_key_value(row) -> tuple[str, str]:
    if "key" in row.headings and "value" in row.headings:
        return row["key"].strip(), row["value"].strip()
    return row[0].strip(), row[1].strip()


def _parse_token_list(raw: str) -> List[str]:
    return [token for token in raw.split(",")]


def _parse_span(raw: str) -> Optional[tuple[int, int]]:
    if raw.lower() == "none":
        return None
    start, end = raw.split("..", 1)
    return int(start), int(end)


def _normalize_empty_text(text: str) -> str:
    return "" if text == "<empty>" else text


def _build_evidence_items(texts: Iterable[str]) -> List[Evidence]:
    evidence_items: List[Evidence] = []
    for index, text in enumerate(texts, start=1):
        evidence_items.append(
            Evidence(
                item_id=f"item-{index}",
                source_uri="source",
                media_type="text/plain",
                score=float(len(text)),
                rank=index,
                text=text,
                content_ref=None,
                span_start=None,
                span_end=None,
                stage="scan",
                recipe_id="recipe",
                run_id="run",
                hash=None,
            )
        )
    return evidence_items


@when('I build a "{backend}" retrieval run in corpus "{corpus_name}"')
def step_build_run(context, backend: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        ["--corpus", str(corpus), "build", "--backend", backend, "--recipe-name", "default"],
    )
    assert result.returncode == 0, result.stderr
    context.last_run = _parse_json_output(result.stdout)
    context.last_run_id = context.last_run.get("run_id")


@when('I build a "{backend}" retrieval run in corpus "{corpus_name}" with config:')
def step_build_run_with_config(context, backend: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "build", "--backend", backend, "--recipe-name", "default"]
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend(["--config", f"{key}={value}"])
    result = run_biblicus(context, args)
    assert result.returncode == 0, result.stderr
    context.last_run = _parse_json_output(result.stdout)
    context.last_run_id = context.last_run.get("run_id")


@when('I attempt to build a "{backend}" retrieval run in corpus "{corpus_name}" with config:')
def step_attempt_build_run_with_config(context, backend: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "build", "--backend", backend, "--recipe-name", "default"]
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend(["--config", f"{key}={value}"])
    context.last_result = run_biblicus(context, args)


@when('I query with the latest run for "{query_text}" and budget:')
def step_query_latest_run(context, query_text: str) -> None:
    assert context.last_run_id
    corpus = _corpus_path(context, "corpus")
    args = [
        "--corpus",
        str(corpus),
        "query",
        "--run",
        context.last_run_id,
        "--query",
        query_text,
    ]
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend([f"--{key.replace('_', '-')}", value])
    result = run_biblicus(context, args)
    assert result.returncode == 0, result.stderr
    context.last_query = _parse_json_output(result.stdout)


@when("I attempt to query the latest run with an invalid budget")
def step_query_latest_run_invalid_budget(context) -> None:
    assert context.last_run_id
    corpus = _corpus_path(context, "corpus")
    args = [
        "--corpus",
        str(corpus),
        "query",
        "--run",
        context.last_run_id,
        "--query",
        "test",
        "--max-total-items",
        "0",
        "--max-total-characters",
        "10",
        "--max-items-per-source",
        "1",
    ]
    run_biblicus(context, args)


@then('the query returns evidence with stage "{stage}"')
def step_query_returns_stage(context, stage: str) -> None:
    evidence = context.last_query.get("evidence") or []
    assert evidence
    assert all(item.get("stage") == stage for item in evidence)


@then("the query evidence count is {count:d}")
def step_query_evidence_count(context, count: int) -> None:
    evidence = context.last_query.get("evidence") or []
    assert len(evidence) == count


@then("the query evidence includes the last ingested item identifier")
def step_query_includes_last_ingested(context) -> None:
    assert context.last_ingest is not None
    evidence = context.last_query.get("evidence") or []
    ids = {item.get("item_id") for item in evidence}
    assert context.last_ingest["id"] in ids


@then("the latest run stats include text_items {count:d}")
def step_run_stats_text_items(context, count: int) -> None:
    stats = context.last_run.get("stats") or {}
    assert stats.get("text_items") == count


@then("the latest run stats include chunks {count:d}")
def step_run_stats_chunks(context, count: int) -> None:
    stats = context.last_run.get("stats") or {}
    assert stats.get("chunks") == count


@when('I create an evaluation dataset at "{filename}" with queries:')
def step_create_eval_dataset(context, filename: str) -> None:
    assert context.ingested_ids
    last_id = context.ingested_ids[-1]
    previous_id = (
        context.ingested_ids[-2] if len(context.ingested_ids) > 1 else context.ingested_ids[-1]
    )
    queries = []
    for idx, row in enumerate(context.table, start=1):
        query_text = row["query_text"] if "query_text" in row.headings else row[0]
        expected_key = row["expected_item"] if "expected_item" in row.headings else row[1]
        if expected_key == "last_ingested":
            expected_id = last_id
        elif expected_key == "previous_item":
            expected_id = previous_id
        else:
            expected_id = expected_key
        queries.append(
            {
                "query_id": f"q{idx}",
                "query_text": query_text,
                "expected_item_id": expected_id,
                "kind": "gold",
            }
        )
    dataset = {
        "schema_version": 1,
        "name": "behavior-driven-development-dataset",
        "description": "Behavior-driven development evaluation dataset",
        "queries": queries,
    }
    path = context.workdir / filename
    path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    context.dataset_path = path


@when('I evaluate the latest run with dataset "{filename}" and budget:')
def step_eval_latest_run(context, filename: str) -> None:
    assert context.last_run_id
    path = context.workdir / filename
    args = [
        "--corpus",
        str(_corpus_path(context, "corpus")),
        "eval",
        "--run",
        context.last_run_id,
        "--dataset",
        str(path),
    ]
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend([f"--{key.replace('_', '-')}", value])
    result = run_biblicus(context, args)
    assert result.returncode == 0, result.stderr
    context.last_eval = _parse_json_output(result.stdout)


@then("the evaluation reports mean reciprocal rank {expected:g}")
def step_eval_mean_reciprocal_rank(context, expected: float) -> None:
    metrics = context.last_eval.get("metrics") or {}
    assert metrics.get("mean_reciprocal_rank") == expected


@then("the evaluation reports hit_rate {expected:g}")
def step_eval_hit_rate(context, expected: float) -> None:
    metrics = context.last_eval.get("metrics") or {}
    assert metrics.get("hit_rate") == expected


@then("the evaluation system reports index_bytes greater than 0")
def step_eval_index_bytes(context) -> None:
    system = context.last_eval.get("system") or {}
    assert system.get("index_bytes", 0) > 0


@then("the evaluation system reports index_bytes {expected:g}")
def step_eval_index_bytes_value(context, expected: float) -> None:
    system = context.last_eval.get("system") or {}
    assert system.get("index_bytes") == expected


@when(
    'I create a source uniform resource identifier evaluation dataset at "{filename}" '
    'for query "{query_text}"'
)
def step_create_source_uri_dataset(context, filename: str, query_text: str) -> None:
    dataset = {
        "schema_version": 1,
        "name": "source-uniform-resource-identifier-dataset",
        "description": "Dataset keyed by source uniform resource identifier",
        "queries": [
            {
                "query_id": "q1",
                "query_text": query_text,
                "expected_source_uri": "text",
                "kind": "gold",
            }
        ],
    }
    path = context.workdir / filename
    path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    context.dataset_path = path


@given('I create an empty evaluation dataset at "{filename}"')
@when('I create an empty evaluation dataset at "{filename}"')
def step_create_empty_dataset(context, filename: str) -> None:
    dataset = {
        "schema_version": 1,
        "name": "empty-dataset",
        "description": "Empty evaluation dataset",
        "queries": [],
    }
    path = context.workdir / filename
    path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    context.dataset_path = path


@when("I delete the latest run artifacts")
def step_delete_latest_run_artifacts(context) -> None:
    assert context.last_run_id
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    run = corpus.load_run(context.last_run_id)
    for relpath in run.artifact_paths:
        path = corpus.root / relpath
        if path.exists():
            path.unlink()


@when("I measure the latest run artifact bytes")
def step_measure_latest_run_artifacts(context) -> None:
    assert context.last_run_id
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    run = corpus.load_run(context.last_run_id)
    context.latest_run_bytes = _run_artifact_bytes(corpus, run)


@then("the run artifact bytes are {count:d}")
def step_run_artifact_bytes(context, count: int) -> None:
    assert context.latest_run_bytes == count


@when('I attempt to query the latest run with backend "{backend}"')
def step_query_latest_run_backend_mismatch(context, backend: str) -> None:
    assert context.last_run_id
    corpus = _corpus_path(context, "corpus")
    args = [
        "--corpus",
        str(corpus),
        "query",
        "--run",
        context.last_run_id,
        "--backend",
        backend,
        "--query",
        "test",
    ]
    context.last_result = run_biblicus(context, args)


@when('I compute a scan match span for text "{text}" and tokens "{tokens}"')
def step_compute_scan_span(context, text: str, tokens: str) -> None:
    token_list = _parse_token_list(tokens)
    context.scan_span = _find_first_match(text, token_list)


@then('the scan match span is "{span}"')
def step_scan_span_is(context, span: str) -> None:
    expected_span = _parse_span(span)
    assert context.scan_span == expected_span


@when('I build a scan snippet from text "{text}" with span "{span}" and max chars {max_chars:d}')
def step_build_scan_snippet(context, text: str, span: str, max_chars: int) -> None:
    parsed_span = _parse_span(span)
    normalized_text = _normalize_empty_text(text)
    context.scan_snippet = _build_snippet(normalized_text, parsed_span, max_chars=max_chars)


@then('the scan snippet is "{snippet}"')
def step_scan_snippet_is(context, snippet: str) -> None:
    expected = _normalize_empty_text(snippet)
    assert context.scan_snippet == expected


@when(
    'I split text "{text}" into sqlite chunks with size {chunk_size:d} and overlap {chunk_overlap:d}'
)
def step_split_sqlite_chunks(context, text: str, chunk_size: int, chunk_overlap: int) -> None:
    normalized_text = _normalize_empty_text(text)
    context.sqlite_chunks = list(
        _iter_chunks(normalized_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    )


@then("the sqlite chunk count is {count:d}")
def step_sqlite_chunk_count(context, count: int) -> None:
    assert len(context.sqlite_chunks) == count


@when('I rebuild a SQLite full-text search index for corpus "{corpus_name}" at "{relative_path}"')
def step_rebuild_sqlite_full_text_search(context, corpus_name: str, relative_path: str) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    db_path = corpus.root / relative_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text("stale", encoding="utf-8")
    config = SqliteFullTextSearchRecipeConfig(chunk_size=5, chunk_overlap=2, snippet_characters=120)
    stats = _build_full_text_search_index(
        db_path=db_path,
        corpus=corpus,
        items=corpus.load_catalog().items.values(),
        recipe_config=config,
        extraction_reference=None,
    )
    context.sqlite_full_text_search_path = db_path
    context.sqlite_full_text_search_stats = stats


@then("the SQLite full-text search index file exists")
def step_sqlite_full_text_search_index_exists(context) -> None:
    assert context.sqlite_full_text_search_path.exists()


@when("I apply a budget with no per-source or character limits")
def step_apply_budget_without_limits(context) -> None:
    evidence = _build_evidence_items(["alpha", "beta", "gamma"])
    budget = QueryBudget(max_total_items=2, max_total_characters=None, max_items_per_source=None)
    context.budgeted_evidence = apply_budget(evidence, budget)


@then("the budget returns {count:d} evidence items")
def step_budget_count(context, count: int) -> None:
    assert len(context.budgeted_evidence) == count


@then('the budget returns evidence ranks "{ranks}"')
def step_budget_ranks(context, ranks: str) -> None:
    expected = [int(value) for value in ranks.split(",")]
    observed = [item.rank for item in context.budgeted_evidence]
    assert observed == expected


@when('I create an invalid evaluation dataset at "{filename}" for query "{query_text}"')
def step_create_invalid_dataset(context, filename: str, query_text: str) -> None:
    dataset = {
        "schema_version": 1,
        "name": "invalid-dataset",
        "description": "Missing expectation fields",
        "queries": [
            {
                "query_id": "q1",
                "query_text": query_text,
                "kind": "gold",
            }
        ],
    }
    path = context.workdir / filename
    path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    context.dataset_path = path


@when('I create an evaluation dataset at "{filename}" with schema version {schema_version:d}')
def step_create_dataset_with_schema_version(context, filename: str, schema_version: int) -> None:
    dataset = {
        "schema_version": schema_version,
        "name": "schema-version-dataset",
        "description": "Dataset with custom schema version",
        "queries": [
            {
                "query_id": "q1",
                "query_text": "alpha",
                "expected_item_id": "placeholder",
                "kind": "gold",
            }
        ],
    }
    path = context.workdir / filename
    path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    context.dataset_path = path


@when('I attempt to evaluate the latest run with dataset "{filename}"')
def step_eval_latest_run_invalid_dataset(context, filename: str) -> None:
    assert context.last_run_id
    path = context.workdir / filename
    args = [
        "--corpus",
        str(_corpus_path(context, "corpus")),
        "eval",
        "--run",
        context.last_run_id,
        "--dataset",
        str(path),
        "--max-total-items",
        "3",
        "--max-total-characters",
        "2000",
        "--max-items-per-source",
        "5",
    ]
    run_biblicus(context, args)


@when('I download a Wikipedia corpus into "{corpus_name}"')
def step_download_wikipedia_corpus(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = subprocess.run(
        ["python3", "scripts/download_wikipedia.py", "--corpus", str(corpus), "--limit", "5"],
        cwd=context.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@when('I download a Portable Document Format corpus into "{corpus_name}"')
def step_download_pdf_corpus(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = subprocess.run(
        ["python3", "scripts/download_pdf_samples.py", "--corpus", str(corpus), "--force"],
        cwd=context.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@when('I download a mixed corpus into "{corpus_name}"')
def step_download_mixed_corpus(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = subprocess.run(
        ["python3", "scripts/download_mixed_samples.py", "--corpus", str(corpus), "--force"],
        cwd=context.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@when('I download an audio corpus into "{corpus_name}"')
def step_download_audio_corpus(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = subprocess.run(
        ["python3", "scripts/download_audio_samples.py", "--corpus", str(corpus), "--force"],
        cwd=context.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@when('I download an image corpus into "{corpus_name}"')
def step_download_image_corpus(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = subprocess.run(
        ["python3", "scripts/download_image_samples.py", "--corpus", str(corpus), "--force"],
        cwd=context.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@then("the corpus contains at least {count:d} items")
def step_corpus_contains_items(context, count: int) -> None:
    catalog = Corpus.open(_corpus_path(context, "corpus")).load_catalog()
    assert len(catalog.items) >= count


@then('the corpus contains at least {count:d} item with media type "{media_type}"')
@then('the corpus contains at least {count:d} items with media type "{media_type}"')
def step_corpus_contains_items_with_media_type(context, count: int, media_type: str) -> None:
    catalog = Corpus.open(_corpus_path(context, "corpus")).load_catalog()
    matching = [item for item in catalog.items.values() if item.media_type == media_type]
    assert len(matching) >= count


@then('the corpus contains at least {count:d} item tagged "{tag}"')
@then('the corpus contains at least {count:d} items tagged "{tag}"')
def step_corpus_contains_items_with_tag(context, count: int, tag: str) -> None:
    catalog = Corpus.open(_corpus_path(context, "corpus")).load_catalog()
    matching = [item for item in catalog.items.values() if tag in item.tags]
    assert len(matching) >= count
