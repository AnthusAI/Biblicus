from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest import mock

from behave import given, then, when
from pydantic import BaseModel, ConfigDict

from biblicus.corpus import Corpus
from biblicus.errors import ExtractionSnapshotFatalError
from biblicus.extraction import build_extraction_snapshot
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
        raise ExtractionSnapshotFatalError("Fatal extractor failure")


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _install_fake_tesseract_dependencies(context) -> None:
    if getattr(context, "_fake_tesseract_installed", False):
        return
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return
    except Exception:
        pass

    original_modules = {
        "pytesseract": sys.modules.get("pytesseract"),
        "PIL": sys.modules.get("PIL"),
        "PIL.Image": sys.modules.get("PIL.Image"),
    }
    context._fake_tesseract_original_modules = original_modules

    fake_pytesseract = types.ModuleType("pytesseract")

    class _Output:
        DICT = "DICT"

    def _image_to_data(*_args, **_kwargs) -> dict[str, list[str]]:
        return {"text": ["Hello", "World"], "conf": ["90", "95"]}

    def _get_tesseract_version() -> str:
        return "0.0"

    fake_pytesseract.Output = _Output
    fake_pytesseract.image_to_data = _image_to_data
    fake_pytesseract.get_tesseract_version = _get_tesseract_version
    sys.modules["pytesseract"] = fake_pytesseract

    fake_pil = types.ModuleType("PIL")
    fake_image_module = types.ModuleType("PIL.Image")

    class _FakeImage:
        def crop(self, _box) -> "_FakeImage":
            return self

    def _open(_path) -> _FakeImage:
        return _FakeImage()

    fake_image_module.open = _open
    fake_pil.Image = fake_image_module
    sys.modules["PIL"] = fake_pil
    sys.modules["PIL.Image"] = fake_image_module
    context._fake_tesseract_installed = True


def _ensure_fake_tesseract_for_extractor(context, extractor_id: str) -> None:
    if extractor_id == "ocr-tesseract":
        _install_fake_tesseract_dependencies(context)


def _ensure_fake_tesseract_for_steps(context, steps: list[dict[str, object]]) -> None:
    for step in steps:
        extractor_id = str(step.get("extractor_id", ""))
        if extractor_id == "ocr-tesseract":
            _install_fake_tesseract_dependencies(context)
            return


def _table_key_value(row) -> tuple[str, str]:
    if "key" in row.headings and "value" in row.headings:
        return row["key"].strip(), row["value"].strip()
    return row[0].strip(), row[1].strip()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    cleaned = standard_output.strip()
    if cleaned.startswith("{") or cleaned.startswith("["):
        return json.loads(cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Expected JSON output but received: {standard_output}")
    return json.loads(cleaned[start : end + 1])


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


def _snapshot_reference_from_context(context) -> str:
    extractor_id = context.last_extractor_id
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    return f"{extractor_id}:{snapshot_id}"


@when('I build a "{extractor_id}" extraction snapshot in corpus "{corpus_name}" with config:')
def step_build_extraction_snapshot_with_config(
    context, extractor_id: str, corpus_name: str
) -> None:
    _ensure_fake_tesseract_for_extractor(context, extractor_id)
    corpus = _corpus_path(context, corpus_name)
    step_config: dict[str, object] = {}
    for row in context.table:
        key, value = _table_key_value(row)
        step_config[key] = value
    step_spec = _build_step_spec(extractor_id, step_config)
    args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot = _parse_json_output(result.stdout)
    context.last_extraction_snapshot_id = context.last_extraction_snapshot.get("snapshot_id")
    context.last_extractor_id = "pipeline"


@when('I build a "pipeline" extraction snapshot in corpus "{corpus_name}" with steps:')
def step_build_pipeline_extraction_snapshot(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    steps = _build_extractor_steps_from_table(context.table)
    _ensure_fake_tesseract_for_steps(context, steps)
    args = ["--corpus", str(corpus), "extract", "build"]
    for step in steps:
        extractor_id = str(step["extractor_id"])
        step_config = step["config"]
        assert isinstance(step_config, dict)
        step_spec = _build_step_spec(extractor_id, step_config)
        args.extend(["--step", step_spec])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot = _parse_json_output(result.stdout)
    context.last_extraction_snapshot_id = context.last_extraction_snapshot.get("snapshot_id")
    context.last_extractor_id = "pipeline"


@when('I build a "pipeline" extraction snapshot in corpus "{corpus_name}" using the configuration:')
def step_build_pipeline_extraction_snapshot_with_configuration(context, corpus_name: str) -> None:
    import yaml

    corpus = _corpus_path(context, corpus_name)
    configuration_data = yaml.safe_load(context.text)
    extractor_id = configuration_data["extractor_id"]
    config = configuration_data.get("config", {})
    steps = config.get("steps", [])
    _ensure_fake_tesseract_for_steps(context, steps)
    args = ["--corpus", str(corpus), "extract", "build"]
    for step in steps:
        step_extractor_id = str(step["extractor_id"])
        step_config = step.get("config", {})
        step_spec = _build_step_spec(step_extractor_id, step_config)
        args.extend(["--step", step_spec])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot = _parse_json_output(result.stdout)
    context.last_extraction_snapshot_id = context.last_extraction_snapshot.get("snapshot_id")
    context.last_extractor_id = "pipeline"


@when(
    'I build a "{extractor_id}" extraction snapshot in corpus "{corpus_name}" using the configuration:'
)
def step_build_non_pipeline_extraction_snapshot_with_configuration(
    context, extractor_id: str, corpus_name: str
) -> None:
    _ensure_fake_tesseract_for_extractor(context, extractor_id)
    import yaml

    corpus = _corpus_path(context, corpus_name)
    configuration_data = yaml.safe_load(context.text)
    config = configuration_data.get("config", {})
    step_spec = _build_step_spec(extractor_id, config)
    args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot = _parse_json_output(result.stdout)
    context.last_extraction_snapshot_id = context.last_extraction_snapshot.get("snapshot_id")
    context.last_extractor_id = "pipeline"


@when(
    'I build an "{extractor_id}" extraction snapshot in corpus "{corpus_name}" using the configuration:'
)
def step_build_non_pipeline_extraction_snapshot_with_configuration_an(
    context, extractor_id: str, corpus_name: str
) -> None:
    step_build_non_pipeline_extraction_snapshot_with_configuration(context, extractor_id, corpus_name)


@when('I build a "{extractor_id}" extraction snapshot in corpus "{corpus_name}"')
def step_build_extraction_snapshot(context, extractor_id: str, corpus_name: str) -> None:
    _ensure_fake_tesseract_for_extractor(context, extractor_id)
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "build", "--step", extractor_id]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot = _parse_json_output(result.stdout)
    context.last_extraction_snapshot_id = context.last_extraction_snapshot.get("snapshot_id")
    context.last_extractor_id = "pipeline"


@when('I build an "{extractor_id}" extraction snapshot in corpus "{corpus_name}"')
def step_build_extraction_snapshot_an(context, extractor_id: str, corpus_name: str) -> None:
    step_build_extraction_snapshot(context, extractor_id, corpus_name)


@when('I attempt to build a "{extractor_id}" extraction snapshot in corpus "{corpus_name}"')
def step_attempt_build_extraction_snapshot(context, extractor_id: str, corpus_name: str) -> None:
    _ensure_fake_tesseract_for_extractor(context, extractor_id)
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "build", "--step", extractor_id]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@when(
    'I attempt to build an extraction snapshot in corpus "{corpus_name}" using extractor "{extractor_id}" with step spec "{step_spec}"'
)
def step_attempt_build_extraction_snapshot_with_step_spec(
    context, corpus_name: str, extractor_id: str, step_spec: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    _ = extractor_id
    _ensure_fake_tesseract_for_extractor(context, extractor_id)
    args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@when(
    'I build an extraction snapshot in corpus "{corpus_name}" using extractor "{extractor_id}" with step spec "{step_spec}"'
)
def step_build_extraction_snapshot_with_step_spec(
    context, corpus_name: str, extractor_id: str, step_spec: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    _ = extractor_id
    _ensure_fake_tesseract_for_extractor(context, extractor_id)
    step_spec_unescaped = step_spec.replace('\\"', '"')
    args = ["--corpus", str(corpus), "extract", "build", "--step", step_spec_unescaped]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot = _parse_json_output(result.stdout)
    context.last_extraction_snapshot_id = context.last_extraction_snapshot.get("snapshot_id")
    context.last_extractor_id = "pipeline"


@when(
    'I attempt to build a "{extractor_id}" extraction snapshot in corpus "{corpus_name}" using the configuration:'
)
def step_attempt_build_extraction_snapshot_with_configuration(
    context, extractor_id: str, corpus_name: str
) -> None:
    _ensure_fake_tesseract_for_extractor(context, extractor_id)
    import yaml

    corpus = _corpus_path(context, corpus_name)
    configuration_data = yaml.safe_load(context.text)
    config = configuration_data.get("config", {})
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


@when('I attempt to build a "pipeline" extraction snapshot in corpus "{corpus_name}" with steps:')
def step_attempt_build_pipeline_extraction_snapshot(context, corpus_name: str) -> None:
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


@when('I remember the last extraction snapshot reference as "{name}"')
def step_remember_last_extraction_snapshot_reference(context, name: str) -> None:
    remembered = getattr(context, "remembered_extraction_snapshot_references", None)
    if remembered is None:
        remembered = {}
        context.remembered_extraction_snapshot_references = remembered
    remembered[name] = _snapshot_reference_from_context(context)


@then('the last extraction snapshot reference equals "{name}"')
def step_last_extraction_snapshot_reference_equals(context, name: str) -> None:
    remembered = getattr(context, "remembered_extraction_snapshot_references", {})
    expected = remembered.get(name)
    assert isinstance(expected, str) and expected
    assert _snapshot_reference_from_context(context) == expected


@then('the last extraction snapshot reference does not equal "{name}"')
def step_last_extraction_snapshot_reference_not_equals(context, name: str) -> None:
    remembered = getattr(context, "remembered_extraction_snapshot_references", {})
    expected = remembered.get(name)
    assert isinstance(expected, str) and expected
    assert _snapshot_reference_from_context(context) != expected


@then('the extraction snapshot artifacts exist under the corpus for extractor "{extractor_id}"')
def step_extraction_snapshot_artifacts_exist(context, extractor_id: str) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(snapshot_id, str) and snapshot_id
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    assert snapshot_dir.is_dir(), snapshot_dir
    manifest_path = snapshot_dir / "manifest.json"
    assert manifest_path.is_file(), manifest_path


@then("the extraction snapshot includes extracted text for all items")
def step_extraction_snapshot_includes_all_items(context) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert context.ingested_ids is not None and len(context.ingested_ids) > 0
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    for item_id in context.ingested_ids:
        text_path = snapshot_dir / "text" / f"{item_id}.txt"
        assert text_path.is_file(), f"Missing text file for item {item_id}: {text_path}"


@then("the extraction snapshot includes extracted text for the last ingested item")
def step_extraction_snapshot_includes_last_item(context) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    assert isinstance(item_id, str) and item_id
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path


@then("the extraction snapshot does not include extracted text for the last ingested item")
def step_extraction_snapshot_does_not_include_last_item(context) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert not text_path.exists()


@then('the extracted text for the last ingested item equals "{expected_text}"')
def step_extracted_text_equals(context, expected_text: str) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8").strip()
    assert text == expected_text, f"Expected: {expected_text!r}, Got: {text!r}"


@then("the extracted text for the last ingested item equals:")
def step_extracted_text_equals_multiline(context) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8").strip()
    expected_text = (context.text or "").strip()
    assert text == expected_text


@then("the extracted text for the last ingested item is empty")
def step_extracted_text_is_empty(context) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    corpus = _corpus_path(context, "corpus")
    extractor_id = context.last_extractor_id
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8")
    assert text.strip() == ""


@then('the extracted text for the item tagged "{tag}" is empty in the latest extraction snapshot')
def step_extracted_text_for_tagged_item_is_empty(context, tag: str) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8")
    assert text.strip() == ""


@then(
    'the extracted text for the item tagged "{tag}" is not empty in the latest extraction snapshot'
)
def step_extracted_text_for_tagged_item_is_not_empty(context, tag: str) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path
    text = text_path.read_text(encoding="utf-8")
    assert text.strip(), f'Extracted text for item tagged "{tag}" is empty'


@then('the extraction snapshot does not include extracted text for the item tagged "{tag}"')
def step_extraction_snapshot_does_not_include_tagged_item(context, tag: str) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert not text_path.exists(), text_path


@then('the extraction snapshot does not include any text for the item tagged "{tag}"')
def step_extraction_snapshot_does_not_include_any_text_for_tagged_item(
    context, tag: str
) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    if not text_path.exists():
        return
    text = text_path.read_text(encoding="utf-8")
    assert text.strip() == ""


@then('the extraction snapshot includes extracted text for the item tagged "{tag}"')
def step_extraction_snapshot_includes_extracted_text_for_tagged_item(context, tag: str) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    text_path = snapshot_dir / "text" / f"{item_id}.txt"
    assert text_path.is_file(), text_path


@then("the extraction snapshot stats include {key} {value:d}")
def step_extraction_snapshot_stats_include_int(context, key: str, value: int) -> None:
    assert context.last_extraction_snapshot is not None
    stats = context.last_extraction_snapshot.get("stats") or {}
    assert isinstance(stats, dict)
    assert stats.get(key) == value, stats


@then('the extraction snapshot item provenance uses extractor "{extractor_id}"')
def step_extraction_snapshot_item_provenance_extractor(context, extractor_id: str) -> None:
    assert context.last_extraction_snapshot is not None
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    items = context.last_extraction_snapshot.get("items") or []
    assert isinstance(items, list)
    matches = [
        entry for entry in items if isinstance(entry, dict) and entry.get("item_id") == item_id
    ]
    assert len(matches) == 1
    entry = matches[0]
    assert entry.get("final_producer_extractor_id") == extractor_id, entry


def _extraction_snapshot_item_entry_for_item_id(context, *, item_id: str) -> dict[str, object]:
    assert context.last_extraction_snapshot is not None
    items = context.last_extraction_snapshot.get("items") or []
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


@then("the extraction snapshot includes an errored result for the first ingested item")
def step_extraction_snapshot_first_item_errored(context) -> None:
    item_id = _ingested_item_id_at_index(context, 0)
    entry = _extraction_snapshot_item_entry_for_item_id(context, item_id=item_id)
    assert entry.get("status") == "errored", entry


@then("the extraction snapshot includes an errored result for the last ingested item")
def step_extraction_snapshot_last_item_errored(context) -> None:
    assert context.last_ingest is not None
    item_id = context.last_ingest["id"]
    entry = _extraction_snapshot_item_entry_for_item_id(context, item_id=item_id)
    assert entry.get("status") == "errored", entry


@then('the extraction snapshot error type for the first ingested item equals "{expected_type}"')
def step_extraction_snapshot_error_type_first_item(context, expected_type: str) -> None:
    item_id = _ingested_item_id_at_index(context, 0)
    entry = _extraction_snapshot_item_entry_for_item_id(context, item_id=item_id)
    assert entry.get("error_type") == expected_type, entry


@when('I attempt to build a non-pipeline extraction snapshot in corpus "{corpus_name}"')
def step_attempt_non_pipeline_extraction_snapshot(context, corpus_name: str) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    context.extraction_fatal_error = None
    try:
        build_extraction_snapshot(
            corpus,
            extractor_id="metadata-text",
            configuration_name="default",
            configuration={},
        )
    except Exception as exc:
        context.extraction_fatal_error = exc


@when(
    'I attempt to build a pipeline extraction snapshot in corpus "{corpus_name}" with a fatal extractor step'
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
            build_extraction_snapshot(
                corpus,
                extractor_id="pipeline",
                configuration_name="default",
                configuration={
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
        ExtractionSnapshotFatalError,
    ), f"Expected ExtractionSnapshotFatalError, got {context.extraction_fatal_error!r}"


@then('the fatal extraction error message includes "{message}"')
def step_fatal_extraction_error_message(context, message: str) -> None:
    assert message in str(context.extraction_fatal_error)


@then('the corpus has at least {count:d} extraction snapshots for extractor "{extractor_id}"')
def step_corpus_has_extraction_snapshots(context, count: int, extractor_id: str) -> None:
    corpus = _corpus_path(context, "corpus")
    extractor_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id
    assert extractor_dir.is_dir(), extractor_dir
    run_dirs = [path for path in extractor_dir.iterdir() if path.is_dir()]
    assert len(run_dirs) >= count


@then('the extraction snapshot includes metadata for the item tagged "{tag}"')
def step_extraction_snapshot_includes_metadata_for_tagged_item(context, tag: str) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    metadata_path = snapshot_dir / "metadata" / f"{item_id}.json"
    assert metadata_path.is_file(), f"Missing metadata file for item {item_id}: {metadata_path}"
    metadata = json.loads(metadata_path.read_text())
    assert isinstance(metadata, dict) and len(metadata) > 0, "Metadata is empty"


@then('the extraction snapshot does not include metadata for the item tagged "{tag}"')
def step_extraction_snapshot_does_not_include_metadata_for_tagged_item(context, tag: str) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    item_id = _first_item_id_tagged(context, tag)
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / ".biblicus" / "snapshots" / "extraction" / extractor_id / snapshot_id
    metadata_path = snapshot_dir / "metadata" / f"{item_id}.json"
    assert not metadata_path.exists() or (
        metadata_path.is_file() and json.loads(metadata_path.read_text()) == {}
    ), f"Metadata file exists and is not empty: {metadata_path}"


@when(
    'I build a "{retriever_id}" retrieval snapshot in corpus "{corpus_name}" using the latest extraction snapshot and config:'
)
def step_build_retrieval_snapshot_using_latest_extraction(
    context, retriever_id: str, corpus_name: str
) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id

    corpus = _corpus_path(context, corpus_name)
    args = [
        "--corpus",
        str(corpus),
        "build",
        "--retriever",
        retriever_id,
        "--configuration-name",
        "default",
    ]
    args.extend(["--config", f"extraction_snapshot={extractor_id}:{snapshot_id}"])
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend(["--config", f"{key}={value}"])
    result = run_biblicus(context, args)
    assert result.returncode == 0, result.stderr
    context.last_snapshot = _parse_json_output(result.stdout)
    context.last_snapshot_id = context.last_snapshot.get("snapshot_id")


@when(
    'I attempt to build a "{retriever_id}" retrieval snapshot in corpus "{corpus_name}" using the latest extraction snapshot and config:'
)
def step_attempt_build_retrieval_snapshot_using_latest_extraction(
    context, retriever_id: str, corpus_name: str
) -> None:
    snapshot_id = context.last_extraction_snapshot_id
    extractor_id = context.last_extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    assert isinstance(extractor_id, str) and extractor_id

    corpus = _corpus_path(context, corpus_name)
    args = [
        "--corpus",
        str(corpus),
        "build",
        "--retriever",
        retriever_id,
        "--configuration-name",
        "default",
    ]
    args.extend(["--config", f"extraction_snapshot={extractor_id}:{snapshot_id}"])
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend(["--config", f"{key}={value}"])
    context.last_result = run_biblicus(context, args)


@when(
    'I attempt to build a "{retriever_id}" retrieval snapshot in corpus "{corpus_name}" with extraction snapshot "{extraction_snapshot}"'
)
def step_attempt_build_retrieval_snapshot_with_extraction_snapshot(
    context, retriever_id: str, corpus_name: str, extraction_snapshot: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = [
        "--corpus",
        str(corpus),
        "build",
        "--retriever",
        retriever_id,
        "--configuration-name",
        "default",
    ]
    args.extend(["--config", f"extraction_snapshot={extraction_snapshot}"])
    context.last_result = run_biblicus(context, args)


@given('a configuration file "{filename}" exists with content:')
@when('a configuration file "{filename}" exists with content:')
def step_configuration_file_exists(context, filename: str) -> None:
    """Create a configuration file with the given content."""
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    path = Path(workdir) / filename
    path.write_text(context.text, encoding="utf-8")


@when(
    'I build an extraction snapshot in corpus "{corpus_name}" using configuration file "{configuration_file}"'
)
def step_build_extraction_snapshot_from_configuration_file(
    context, corpus_name: str, configuration_file: str
) -> None:
    """Build an extraction snapshot from a configuration file."""
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    configuration_path = Path(workdir) / configuration_file
    args = [
        "--corpus",
        str(corpus),
        "extract",
        "build",
        "--configuration",
        str(configuration_path),
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot = _parse_json_output(result.stdout)
    context.last_extraction_snapshot_id = context.last_extraction_snapshot.get("snapshot_id")
    # Extractor ID is in the configuration sub-object
    configuration = context.last_extraction_snapshot.get("configuration", {})
    context.last_extractor_id = configuration.get("extractor_id")


@when(
    'I attempt to build an extraction snapshot in corpus "{corpus_name}" using configuration file "{configuration_file}"'
)
def step_attempt_build_extraction_snapshot_from_configuration_file(
    context, corpus_name: str, configuration_file: str
) -> None:
    """Attempt to build an extraction snapshot from a configuration file without asserting success."""
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    configuration_path = Path(workdir) / configuration_file
    args = [
        "--corpus",
        str(corpus),
        "extract",
        "build",
        "--configuration",
        str(configuration_path),
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
