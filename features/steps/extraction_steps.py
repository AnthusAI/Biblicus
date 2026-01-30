from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from behave import given, then, when
from pydantic import BaseModel, ConfigDict

from biblicus.corpus import Corpus
from biblicus.errors import ExtractionRunFatalError
from biblicus.extraction import build_extraction_run
from biblicus.extractors import get_extractor as resolve_extractor
from biblicus.extractors.base import TextExtractor
from biblicus.models import CatalogItem, ExtractionStepOutput
from features.environment import run_biblicus


class _FatalExtractorConfig(BaseModel):
    """
    Configuration model for the fatal extractor test double.
    """

    model_config = ConfigDict(extra="forbid")


class _FatalExtractor(TextExtractor):
    """
    Extractor test double that raises a fatal extraction error.
    """

    extractor_id = "fatal-text"

    def validate_config(self, config: dict[str, object]) -> BaseModel:
        return _FatalExtractorConfig.model_validate(config)

    def extract_text(
        self,
        *,
        corpus: Corpus,
        item: CatalogItem,
        config: BaseModel,
        previous_extractions: list[ExtractionStepOutput],
    ) -> None:
        _ = corpus
        _ = item
        _ = config
        _ = previous_extractions
        raise ExtractionRunFatalError("Fatal extractor failure")


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
        raw_config = (
            row["config_json"]
            if "config_json" in row.headings
            else (row[1] if len(row) > 1 else "{}")
        )
        config = json.loads(raw_config) if raw_config else {}
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise ValueError("Extractor step config_json must parse to an object")
        steps.append({"extractor_id": extractor_id, "config": config})
    return steps


def _build_step_spec(extractor_id: str, config: dict[str, object]) -> str:
    import json

    if not config:
        return extractor_id

    # Only JSON-encode complex types (lists, dicts), not simple strings/numbers
    def encode_value(v: object) -> str:
        if isinstance(v, (list, dict)):
            return json.dumps(v)
        return str(v)

    inline_pairs = ",".join(f"{key}={encode_value(value)}" for key, value in config.items())
    return f"{extractor_id}:{inline_pairs}"


def _run_reference_from_context(context) -> str:
    extractor_id = context.last_extractor_id
    run_id = context.last_extraction_run_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(run_id, str) and run_id
    return f"{extractor_id}:{run_id}"


@when('I build a "{extractor_id}" extraction run in corpus "{corpus_name}" with config:')
def step_build_extraction_run_with_config(context, extractor_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    step_config: dict[str, object] = {}
    for row in context.table:
        key, value = _table_key_value(row)
        step_config[key] = value
    step_spec = _build_step_spec(extractor_id, step_config)
    args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = "pipeline"


@when('I build a "pipeline" extraction run in corpus "{corpus_name}" with steps:')
def step_build_pipeline_extraction_run(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    steps = _build_extractor_steps_from_table(context.table)
    args = ["--corpus", str(corpus), "extract", "build"]
    for step in steps:
        extractor_id = str(step["extractor_id"])
        step_config = step["config"]
        assert isinstance(step_config, dict)
        step_spec = _build_step_spec(extractor_id, step_config)
        args.extend(["--step", step_spec])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = "pipeline"


@when('I build a "pipeline" extraction run in corpus "{corpus_name}" using the recipe:')
def step_build_pipeline_extraction_run_with_recipe(context, corpus_name: str) -> None:
    import yaml

    corpus = _corpus_path(context, corpus_name)
    recipe = yaml.safe_load(context.text)
    extractor_id = recipe["extractor_id"]
    config = recipe.get("config", {})
    steps = config.get("steps", [])
    args = ["--corpus", str(corpus), "extract", "build"]
    for step in steps:
        step_extractor_id = str(step["extractor_id"])
        step_config = step.get("config", {})
        step_spec = _build_step_spec(step_extractor_id, step_config)
        args.extend(["--step", step_spec])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = extractor_id


@when('I build a "{extractor_id}" extraction run in corpus "{corpus_name}" using the recipe:')
def step_build_non_pipeline_extraction_run_with_recipe(
    context, extractor_id: str, corpus_name: str
) -> None:
    import yaml

    corpus = _corpus_path(context, corpus_name)
    recipe = yaml.safe_load(context.text)
    config = recipe.get("config", {})
    step_spec = _build_step_spec(extractor_id, config)
    args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = "pipeline"


@when('I build a "{extractor_id}" extraction run in corpus "{corpus_name}"')
def step_build_extraction_run(context, extractor_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "build", "--step", extractor_id]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = "pipeline"


@when('I attempt to build a "{extractor_id}" extraction run in corpus "{corpus_name}"')
def step_attempt_build_extraction_run(context, extractor_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "build", "--step", extractor_id]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@when(
    'I attempt to build an extraction run in corpus "{corpus_name}" using extractor "{extractor_id}" with step spec "{step_spec}"'
)
def step_attempt_build_extraction_run_with_step_spec(
    context, corpus_name: str, extractor_id: str, step_spec: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    _ = extractor_id
    args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@when(
    'I build an extraction run in corpus "{corpus_name}" using extractor "{extractor_id}" with step spec "{step_spec}"'
)
def step_build_extraction_run_with_step_spec(
    context, corpus_name: str, extractor_id: str, step_spec: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    _ = extractor_id
    step_spec_unescaped = step_spec.replace('\\"', '"')
    args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec_unescaped]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    context.last_extractor_id = "pipeline"


@when(
    'I attempt to build a "{extractor_id}" extraction run in corpus "{corpus_name}" using the recipe:'
)
def step_attempt_build_extraction_run_with_recipe(
    context, extractor_id: str, corpus_name: str
) -> None:
    import yaml

    corpus = _corpus_path(context, corpus_name)
    recipe = yaml.safe_load(context.text)
    config = recipe.get("config", {})
    steps = config.get("steps", []) if "steps" in config else []
    if steps:
        args = ["--corpus", str(corpus), "extract", "build"]
        for step in steps:
            step_extractor_id = str(step["extractor_id"])
            step_config = step.get("config", {})
            step_spec = _build_step_spec(step_extractor_id, step_config)
            args.extend(["--step", step_spec])
    else:
        step_spec = _build_step_spec(extractor_id, config)
        args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@when('I attempt to build a "pipeline" extraction run in corpus "{corpus_name}" with steps:')
def step_attempt_build_pipeline_extraction_run(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    steps = _build_extractor_steps_from_table(context.table)
    args = ["--corpus", str(corpus), "extract", "build"]
    for step in steps:
        extractor_id = str(step["extractor_id"])
        step_config = step["config"]
        assert isinstance(step_config, dict)
        step_spec = _build_step_spec(extractor_id, step_config)
        args.extend(["--step", step_spec])
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@when('I remember the last extraction run reference as "{name}"')
def step_remember_last_extraction_run_reference(context, name: str) -> None:
    remembered = getattr(context, "remembered_extraction_run_references", None)
    if remembered is None:
        remembered = {}
        context.remembered_extraction_run_references = remembered
    remembered[name] = _run_reference_from_context(context)


@then('the last extraction run reference equals "{name}"')
def step_last_extraction_run_reference_equals(context, name: str) -> None:
    remembered = getattr(context, "remembered_extraction_run_references", {})
    expected = remembered.get(name)
    assert isinstance(expected, str) and expected
    assert _run_reference_from_context(context) == expected


@then('the last extraction run reference does not equal "{name}"')
def step_last_extraction_run_reference_not_equals(context, name: str) -> None:
    remembered = getattr(context, "remembered_extraction_run_references", {})
    expected = remembered.get(name)
    assert isinstance(expected, str) and expected
    assert _run_reference_from_context(context) != expected


@then('the extraction run artifacts exist under the corpus for extractor "{extractor_id}"')
def step_extraction_run_artifacts_exist(context, extractor_id: str) -> None:
    run_id = context.last_extraction_run_id
    assert isinstance(run_id, str) and run_id
    corpus = _corpus_path(context, "corpus")
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    assert run_dir.is_dir(), run_dir
    manifest_path = run_dir / "manifest.json"
    assert manifest_path.is_file(), manifest_path


@then("the extraction run includes extracted text for all items")
def step_extraction_run_includes_all_items(context) -> None:
    run_id = context.last_extraction_run_id
    assert isinstance(run_id, str) and run_id
    assert context.ingested_ids is not None and len(context.ingested_ids) > 0
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    for item_id in context.ingested_ids:
        text_path = run_dir / "text" / f"{item_id}.txt"
        assert text_path.is_file(), f"Missing text file for item {item_id}: {text_path}"


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
    assert text == expected_text, f"Expected: {expected_text!r}, Got: {text!r}"


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


@then('the extracted text for the item tagged "{tag}" is empty in the latest extraction run')
def step_extracted_text_for_tagged_item_is_empty(context, tag: str) -> None:
    run_id = context.last_extraction_run_id
    extractor_id = context.last_extractor_id
    assert isinstance(run_id, str) and run_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8")
    assert text.strip() == ""


@then('the extracted text for the item tagged "{tag}" is not empty in the latest extraction run')
def step_extracted_text_for_tagged_item_is_not_empty(context, tag: str) -> None:
    run_id = context.last_extraction_run_id
    extractor_id = context.last_extractor_id
    assert isinstance(run_id, str) and run_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8")
    assert text.strip(), f'Extracted text for item tagged "{tag}" is empty'


@then('the extraction run does not include extracted text for the item tagged "{tag}"')
def step_extraction_run_does_not_include_tagged_item(context, tag: str) -> None:
    run_id = context.last_extraction_run_id
    extractor_id = context.last_extractor_id
    assert isinstance(run_id, str) and run_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert not text_path.exists(), text_path


@then('the extraction run includes extracted text for the item tagged "{tag}"')
def step_extraction_run_includes_extracted_text_for_tagged_item(context, tag: str) -> None:
    run_id = context.last_extraction_run_id
    extractor_id = context.last_extractor_id
    assert isinstance(run_id, str) and run_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    text_path = run_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path


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
    matches = [
        entry for entry in items if isinstance(entry, dict) and entry.get("item_id") == item_id
    ]
    assert len(matches) == 1
    entry = matches[0]
    assert entry.get("final_producer_extractor_id") == extractor_id, entry


def _extraction_run_item_entry_for_item_id(context, *, item_id: str) -> dict[str, object]:
    assert context.last_extraction_run is not None
    items = context.last_extraction_run.get("items") or []
    assert isinstance(items, list)
    matches = [
        entry for entry in items if isinstance(entry, dict) and entry.get("item_id") == item_id
    ]
    assert len(matches) == 1
    return matches[0]


def _ingested_item_id_at_index(context, index: int) -> str:
    ingested = getattr(context, "ingested_ids", None)
    assert isinstance(ingested, list)
    assert len(ingested) > index
    value = ingested[index]
    assert isinstance(value, str) and value
    return value


def _first_item_id_tagged(context, tag: str) -> str:
    corpus = Corpus.open(_corpus_path(context, "corpus"))
    catalog = corpus.load_catalog()
    matching = [item for item in catalog.items.values() if tag in item.tags]
    assert matching, f'No catalog items tagged "{tag}"'
    return matching[0].id


@then("the extraction run includes an errored result for the first ingested item")
def step_extraction_run_first_item_errored(context) -> None:
    item_id = _ingested_item_id_at_index(context, 0)
    entry = _extraction_run_item_entry_for_item_id(context, item_id=item_id)
    assert entry.get("status") == "errored", entry


@then("the extraction run includes an errored result for the last ingested item")
def step_extraction_run_last_item_errored(context) -> None:
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    entry = _extraction_run_item_entry_for_item_id(context, item_id=item_id)
    assert entry.get("status") == "errored", entry


@then('the extraction run error type for the first ingested item equals "{expected_type}"')
def step_extraction_run_error_type_first_item(context, expected_type: str) -> None:
    item_id = _ingested_item_id_at_index(context, 0)
    entry = _extraction_run_item_entry_for_item_id(context, item_id=item_id)
    assert entry.get("error_type") == expected_type, entry


@when('I attempt to build a non-pipeline extraction run in corpus "{corpus_name}"')
def step_attempt_non_pipeline_extraction_run(context, corpus_name: str) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    context.extraction_fatal_error = None
    try:
        build_extraction_run(
            corpus,
            extractor_id="metadata-text",
            recipe_name="default",
            config={},
        )
    except Exception as exc:
        context.extraction_fatal_error = exc


@when(
    'I attempt to build a pipeline extraction run in corpus "{corpus_name}" with a fatal extractor step'
)
def step_attempt_pipeline_with_fatal_extractor(context, corpus_name: str) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))

    def _resolve_extractor(extractor_id: str) -> TextExtractor:
        if extractor_id == _FatalExtractor.extractor_id:
            return _FatalExtractor()
        return resolve_extractor(extractor_id)

    context.extraction_fatal_error = None
    with mock.patch("biblicus.extraction.get_extractor", side_effect=_resolve_extractor):
        try:
            build_extraction_run(
                corpus,
                extractor_id="pipeline",
                recipe_name="default",
                config={
                    "steps": [
                        {"extractor_id": _FatalExtractor.extractor_id, "config": {}},
                    ]
                },
            )
        except Exception as exc:
            context.extraction_fatal_error = exc


@then("a fatal extraction error is raised")
def step_fatal_extraction_error_raised(context) -> None:
    assert isinstance(
        context.extraction_fatal_error,
        ExtractionRunFatalError,
    ), f"Expected ExtractionRunFatalError, got {context.extraction_fatal_error!r}"


@then('the fatal extraction error message includes "{message}"')
def step_fatal_extraction_error_message(context, message: str) -> None:
    assert message in str(context.extraction_fatal_error)


@then('the corpus has at least {count:d} extraction runs for extractor "{extractor_id}"')
def step_corpus_has_extraction_runs(context, count: int, extractor_id: str) -> None:
    corpus = _corpus_path(context, "corpus")
    extractor_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id
    assert extractor_dir.is_dir(), extractor_dir
    run_dirs = [path for path in extractor_dir.iterdir() if path.is_dir()]
    assert len(run_dirs) >= count


@when(
    'I build a "{backend}" retrieval run in corpus "{corpus_name}" using the latest extraction run and config:'
)
def step_build_retrieval_run_using_latest_extraction(
    context, backend: str, corpus_name: str
) -> None:
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
def step_attempt_build_retrieval_run_with_extraction_run(
    context, backend: str, corpus_name: str, extraction_run: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "build", "--backend", backend, "--recipe-name", "default"]
    args.extend(["--config", f"extraction_run={extraction_run}"])
    context.last_result = run_biblicus(context, args)


@given('a recipe file "{filename}" exists with content:')
@when('a recipe file "{filename}" exists with content:')
def step_recipe_file_exists(context, filename: str) -> None:
    """Create a recipe file with the given content."""
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    path = Path(workdir) / filename
    path.write_text(context.text, encoding="utf-8")


@when('I build an extraction run in corpus "{corpus_name}" using recipe file "{recipe_file}"')
def step_build_extraction_run_from_recipe_file(context, corpus_name: str, recipe_file: str) -> None:
    """Build an extraction run from a recipe file."""
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    args = ["--corpus", str(corpus), "extract", "build", "--recipe", str(recipe_path)]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run = _parse_json_output(result.stdout)
    context.last_extraction_run_id = context.last_extraction_run.get("run_id")
    # Extractor ID is in the recipe sub-object
    recipe = context.last_extraction_run.get("recipe", {})
    context.last_extractor_id = recipe.get("extractor_id")


@when(
    'I attempt to build an extraction run in corpus "{corpus_name}" using recipe file "{recipe_file}"'
)
def step_attempt_build_extraction_run_from_recipe_file(
    context, corpus_name: str, recipe_file: str
) -> None:
    """Attempt to build an extraction run from a recipe file without asserting success."""
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    args = ["--corpus", str(corpus), "extract", "build", "--recipe", str(recipe_path)]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
