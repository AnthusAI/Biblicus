from __future__ import annotations

import json
from pathlib import Path

from behave import then, when

from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _table_key_value(row) -> tuple[str, str]:
    if "key" in row.headings and "value" in row.headings:
        return row["key"].strip(), row["value"].strip()
    return row[0].strip(), row[1].strip()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)

def _build_extractor_steps_from_table(table) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    for row in table:
        extractor_id = (row["extractor_id"] if "extractor_id" in row.headings else row[0]).strip()
        raw_config = row["config_json"] if "config_json" in row.headings else (row[1] if len(row) > 1 else "{}")
        config = json.loads(raw_config) if raw_config else {}
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise ValueError("Extractor step config_json must parse to an object")
        steps.append({"extractor_id": extractor_id, "config": config})
    return steps


@when('I build a "{extractor_id}" extraction run in corpus "{corpus_name}" with config:')
def step_build_extraction_run_with_config(context, extractor_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "--extractor", extractor_id]
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend(["--config", f"{key}={value}"])
    result = run_biblicus(context, args)
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = extractor_id


@when('I build a "cascade" extraction run in corpus "{corpus_name}" with steps:')
def step_build_cascade_extraction_run(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    steps = _build_extractor_steps_from_table(context.table)
    args = ["--corpus", str(corpus), "extract", "--extractor", "cascade"]
    for step in steps:
        extractor_id = str(step["extractor_id"])
        step_config = step["config"]
        assert isinstance(step_config, dict)
        if not step_config:
            args.extend(["--step", extractor_id])
            continue
        inline_pairs = ",".join(f"{key}={value}" for key, value in step_config.items())
        args.extend(["--step", f"{extractor_id}:{inline_pairs}"])
    result = run_biblicus(context, args)
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = "cascade"


@when('I build a "{extractor_id}" extraction run in corpus "{corpus_name}"')
def step_build_extraction_run(context, extractor_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "--extractor", extractor_id]
    result = run_biblicus(context, args)
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = extractor_id


@when('I attempt to build a "{extractor_id}" extraction run in corpus "{corpus_name}"')
def step_attempt_build_extraction_run(context, extractor_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "--extractor", extractor_id]
    context.last_result = run_biblicus(context, args)


@when('I attempt to build an extraction run in corpus "{corpus_name}" using extractor "{extractor_id}" with step spec "{step_spec}"')
def step_attempt_build_extraction_run_with_step_spec(context, corpus_name: str, extractor_id: str, step_spec: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "--extractor", extractor_id, "--step", step_spec]
    context.last_result = run_biblicus(context, args)


@then('the extraction run artifacts exist under the corpus for extractor "{extractor_id}"')
def step_extraction_run_artifacts_exist(context, extractor_id: str) -> None:
    run_id = context.last_extraction_run_id
    assert isinstance(run_id, str) and run_id
    corpus = _corpus_path(context, "corpus")
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    assert run_dir.is_dir(), run_dir
    manifest_path = run_dir / "manifest.json"
    assert manifest_path.is_file(), manifest_path


@then("the extraction run includes extracted text for the last ingested item")
def step_extraction_run_includes_last_item(context) -> None:
    run_id = context.last_extraction_run_id
    assert isinstance(run_id, str) and run_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    assert isinstance(item_id, str) and item_id
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path


@then("the extraction run does not include extracted text for the last ingested item")
def step_extraction_run_does_not_include_last_item(context) -> None:
    run_id = context.last_extraction_run_id
    assert isinstance(run_id, str) and run_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert not text_path.exists()


@then('the extracted text for the last ingested item equals "{expected_text}"')
def step_extracted_text_equals(context, expected_text: str) -> None:
    run_id = context.last_extraction_run_id
    assert isinstance(run_id, str) and run_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8").strip()
    assert text == expected_text


@then("the extracted text for the last ingested item equals:")
def step_extracted_text_equals_multiline(context) -> None:
    run_id = context.last_extraction_run_id
    assert isinstance(run_id, str) and run_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8").strip()
    expected_text = (context.text or "").strip()
    assert text == expected_text


@then("the extracted text for the last ingested item is empty")
def step_extracted_text_is_empty(context) -> None:
    run_id = context.last_extraction_run_id
    assert isinstance(run_id, str) and run_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8")
    assert text.strip() == ""


@then("the extraction run stats include {key} {value:d}")
def step_extraction_run_stats_include_int(context, key: str, value: int) -> None:
    assert context.last_extraction_run is not None
    stats = context.last_extraction_run.get("stats") or {}
    assert isinstance(stats, dict)
    assert stats.get(key) == value, stats


@then('the extraction run item provenance uses extractor "{extractor_id}"')
def step_extraction_run_item_provenance_extractor(context, extractor_id: str) -> None:
    assert context.last_extraction_run is not None
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    items = context.last_extraction_run.get("items") or []
    assert isinstance(items, list)
    matches = [entry for entry in items if isinstance(entry, dict) and entry.get("item_id") == item_id]
    assert len(matches) == 1
    entry = matches[0]
    assert entry.get("producer_extractor_id") == extractor_id, entry


@then('the corpus has at least {count:d} extraction runs for extractor "{extractor_id}"')
def step_corpus_has_extraction_runs(context, count: int, extractor_id: str) -> None:
    corpus = _corpus_path(context, "corpus")
    extractor_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id
    assert extractor_dir.is_dir(), extractor_dir
    run_dirs = [path for path in extractor_dir.iterdir() if path.is_dir()]
    assert len(run_dirs) >= count


@when('I build a "{backend}" retrieval run in corpus "{corpus_name}" using the latest extraction run and config:')
def step_build_retrieval_run_using_latest_extraction(context, backend: str, corpus_name: str) -> None:
    run_id = context.last_extraction_run_id
    extractor_id = context.last_extractor_id
    assert isinstance(run_id, str) and run_id
    assert isinstance(extractor_id, str) and extractor_id

    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "build", "--backend", backend, "--recipe-name", "default"]
    args.extend(["--config", f"extraction_run={extractor_id}:{run_id}"])
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend(["--config", f"{key}={value}"])
    result = run_biblicus(context, args)
    assert result.returncode == 0, result.stderr
    context.last_run = _parse_json_output(result.stdout)
    context.last_run_id = context.last_run.get("run_id")


@when(
    'I attempt to build a "{backend}" retrieval run in corpus "{corpus_name}" with extraction run "{extraction_run}"'
)
def step_attempt_build_retrieval_run_with_extraction_run(context, backend: str, corpus_name: str, extraction_run: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "build", "--backend", backend, "--recipe-name", "default"]
    args.extend(["--config", f"extraction_run={extraction_run}"])
    context.last_result = run_biblicus(context, args)
