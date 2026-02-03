from __future__ import annotations

import json
from pathlib import Path

from behave import then, when

from biblicus.corpus import Corpus
from biblicus.extraction_evaluation import ExtractionEvaluationItem, _resolve_item_id
from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)


def _run_reference_from_context(context) -> str:
    extractor_id = context.last_extractor_id
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    return f"{extractor_id}:{snapshot_id}"


def _require_extraction_evaluation_output(context) -> dict[str, object]:
    if not hasattr(context, "last_extraction_evaluation"):
        result = getattr(context, "last_result", None)
        stderr = getattr(result, "stderr", "") if result is not None else ""
        raise AssertionError(f"Extraction evaluation output missing. stderr: {stderr}")
    return context.last_extraction_evaluation


@when("I attempt to resolve an extraction evaluation item without locators")
def step_attempt_resolve_missing_locators(context) -> None:
    item = ExtractionEvaluationItem.model_construct(
        item_id=None,
        source_uri=None,
        expected_text="",
        kind="gold",
    )
    try:
        _resolve_item_id(item, catalog_items={})
    except ValueError as exc:
        context.last_exception = exc
        return
    raise AssertionError("Expected resolve to raise a ValueError")


@when(
    'I attempt to resolve an extraction evaluation item with source uri "{source_uri}" using catalog from corpus "{corpus_name}"'
)
def step_attempt_resolve_source_uri(context, source_uri: str, corpus_name: str) -> None:
    corpus_root = _corpus_path(context, corpus_name)
    corpus = Corpus.open(corpus_root)
    catalog = corpus.load_catalog()
    item = ExtractionEvaluationItem.model_construct(
        item_id=None,
        source_uri=source_uri,
        expected_text="",
        kind="gold",
    )
    try:
        _resolve_item_id(item, catalog_items=catalog.items)
    except ValueError as exc:
        context.last_exception = exc
        return
    raise AssertionError("Expected resolve to raise a ValueError")


@then('the extraction evaluation resolver error mentions "{message}"')
def step_extraction_eval_resolver_error_mentions(context, message: str) -> None:
    exc = getattr(context, "last_exception", None)
    assert exc is not None
    assert message in str(exc)


@when('I create an extraction evaluation dataset "{filename}" with expected texts:')
def step_create_extraction_evaluation_dataset(context, filename: str) -> None:
    if not hasattr(context, "ingested_ids"):
        raise AssertionError("No ingested item identifiers recorded")
    expected_texts = [row["expected_text"] for row in context.table]
    item_ids = context.ingested_ids[-len(expected_texts) :]
    if len(item_ids) != len(expected_texts):
        raise AssertionError("Not enough ingested item identifiers to build dataset")
    items = [
        {
            "item_id": item_id,
            "expected_text": expected_text,
            "kind": "gold",
        }
        for item_id, expected_text in zip(item_ids, expected_texts)
    ]
    dataset = {
        "schema_version": 1,
        "name": "extraction-evaluation-dataset",
        "description": "Behavior-driven development extraction dataset",
        "items": items,
    }
    path = context.workdir / filename
    path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")


@when('I create an extraction evaluation dataset file "{filename}" with:')
def step_create_extraction_evaluation_dataset_file(context, filename: str) -> None:
    path = context.workdir / filename
    path.write_text(context.text, encoding="utf-8")


@when(
    'I create an extraction evaluation dataset "{filename}" for the last ingested item in corpus "{corpus_name}" '
    'using source uri and expected text "{expected_text}"'
)
def step_create_extraction_evaluation_dataset_with_source_uri(
    context, filename: str, corpus_name: str, expected_text: str
) -> None:
    if not getattr(context, "last_ingest", None):
        raise AssertionError("No last ingested item recorded")
    corpus_root = _corpus_path(context, corpus_name)
    corpus = Corpus.open(corpus_root)
    item_id = context.last_ingest["id"]
    source_uri = corpus.get_item(item_id).source_uri
    dataset = {
        "schema_version": 1,
        "name": "source-uri-dataset",
        "description": "Dataset keyed by source uniform resource identifier",
        "items": [
            {
                "source_uri": source_uri,
                "expected_text": expected_text,
                "kind": "gold",
            }
        ],
    }
    path = context.workdir / filename
    path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")


@when(
    'I evaluate extraction snapshot in corpus "{corpus_name}" using dataset "{filename}" '
    "and the latest extraction snapshot"
)
def step_evaluate_extraction_with_run(context, corpus_name: str, filename: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    run_ref = _run_reference_from_context(context)
    dataset_path = context.workdir / filename
    args = [
        "--corpus",
        str(corpus),
        "extract",
        "evaluate",
        "--snapshot",
        run_ref,
        "--dataset",
        str(dataset_path),
    ]
    result = run_biblicus(context, args)
    context.last_result = result
    if result.returncode == 0:
        context.last_extraction_evaluation = _parse_json_output(result.stdout)


@when('I evaluate extraction snapshot in corpus "{corpus_name}" using dataset "{filename}"')
def step_evaluate_extraction_without_run(context, corpus_name: str, filename: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    dataset_path = context.workdir / filename
    args = [
        "--corpus",
        str(corpus),
        "extract",
        "evaluate",
        "--dataset",
        str(dataset_path),
    ]
    result = run_biblicus(context, args)
    context.last_result = result
    if result.returncode == 0:
        context.last_extraction_evaluation = _parse_json_output(result.stdout)


@then("the extraction evaluation metrics include coverage_present {count:d}")
def step_extraction_eval_coverage_present(context, count: int) -> None:
    output = _require_extraction_evaluation_output(context)
    metrics = output["metrics"]
    assert metrics["coverage_present"] == float(count)


@then("the extraction evaluation metrics include coverage_empty {count:d}")
def step_extraction_eval_coverage_empty(context, count: int) -> None:
    output = _require_extraction_evaluation_output(context)
    metrics = output["metrics"]
    assert metrics["coverage_empty"] == float(count)


@then("the extraction evaluation metrics include coverage_missing {count:d}")
def step_extraction_eval_coverage_missing(context, count: int) -> None:
    output = _require_extraction_evaluation_output(context)
    metrics = output["metrics"]
    assert metrics["coverage_missing"] == float(count)


@then("the extraction evaluation metrics include processable_fraction {expected:g}")
def step_extraction_eval_processable_fraction(context, expected: float) -> None:
    output = _require_extraction_evaluation_output(context)
    metrics = output["metrics"]
    assert metrics["processable_fraction"] == expected


@then("the extraction evaluation metrics include average_similarity {expected:g}")
def step_extraction_eval_average_similarity(context, expected: float) -> None:
    output = _require_extraction_evaluation_output(context)
    metrics = output["metrics"]
    assert metrics["average_similarity"] == expected
