from __future__ import annotations

import contextlib
import io
import json
import runpy
import sys
from pathlib import Path
from typing import Any, Dict

from behave import then, when

MIGRATION_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "migrate_catalog_extensions.py"
)


def _catalog_file(context, corpus_name: str) -> Path:
    return (context.workdir / corpus_name).resolve() / "metadata" / "catalog.json"


def _read_catalog(context, corpus_name: str) -> Dict[str, Any]:
    return json.loads(_catalog_file(context, corpus_name).read_text(encoding="utf-8"))


def _write_catalog(context, corpus_name: str, catalog: Dict[str, Any]) -> None:
    _catalog_file(context, corpus_name).write_text(
        json.dumps(catalog, indent=2) + "\n", encoding="utf-8"
    )


def _last_item(catalog: Dict[str, Any], context) -> Dict[str, Any]:
    return catalog["items"][context.ingested_ids[-1]]


@when(
    "I add the top-level catalog item field \"{field_name}\" with value '{value_json}' "
    'to the last ingested item in corpus "{corpus_name}"'
)
def step_add_top_level_catalog_item_field(
    context, field_name: str, value_json: str, corpus_name: str
) -> None:
    catalog = _read_catalog(context, corpus_name)
    _last_item(catalog, context)[field_name] = json.loads(value_json)
    _write_catalog(context, corpus_name, catalog)


@when(
    "I set the catalog item metadata field \"{field_name}\" to '{value_json}' "
    'on the last ingested item in corpus "{corpus_name}"'
)
def step_set_catalog_item_metadata_field(
    context, field_name: str, value_json: str, corpus_name: str
) -> None:
    catalog = _read_catalog(context, corpus_name)
    _last_item(catalog, context).setdefault("metadata", {})[field_name] = json.loads(value_json)
    _write_catalog(context, corpus_name, catalog)


def _run_migration(context, corpus_name: str, extra_arguments: list[str]) -> None:
    corpus_path = str((context.workdir / corpus_name).resolve())
    standard_output = io.StringIO()
    previous_argv = sys.argv
    sys.argv = [str(MIGRATION_SCRIPT_PATH), corpus_path, *extra_arguments]
    exit_code = 0
    try:
        with contextlib.redirect_stdout(standard_output):
            runpy.run_path(str(MIGRATION_SCRIPT_PATH), run_name="__main__")
    except SystemExit as exit_signal:
        exit_code = int(exit_signal.code or 0)
    finally:
        sys.argv = previous_argv
    context.migration_exit_code = exit_code
    context.migration_output = standard_output.getvalue()


@when('I run the catalog extension migration on corpus "{corpus_name}"')
def step_run_catalog_extension_migration(context, corpus_name: str) -> None:
    _run_migration(context, corpus_name, [])


@when('I run the catalog extension migration on corpus "{corpus_name}" with the dry run flag')
def step_run_catalog_extension_migration_dry_run(context, corpus_name: str) -> None:
    _run_migration(context, corpus_name, ["--dry-run"])


@when('I remember the catalog file content of corpus "{corpus_name}"')
def step_remember_catalog_file_content(context, corpus_name: str) -> None:
    context.remembered_catalog_content = _catalog_file(context, corpus_name).read_text(
        encoding="utf-8"
    )


@then('the migration succeeds and reports "{text}"')
def step_migration_succeeds_and_reports(context, text: str) -> None:
    assert context.migration_exit_code == 0, context.migration_output
    assert text in context.migration_output, context.migration_output


@then('the catalog file content of corpus "{corpus_name}" is unchanged')
def step_catalog_file_content_unchanged(context, corpus_name: str) -> None:
    current = _catalog_file(context, corpus_name).read_text(encoding="utf-8")
    assert current == context.remembered_catalog_content


@then('no temporary catalog file exists in corpus "{corpus_name}"')
def step_no_temporary_catalog_file(context, corpus_name: str) -> None:
    temporary = _catalog_file(context, corpus_name).with_suffix(".json.tmp")
    assert not temporary.exists()


@then(
    'the catalog item metadata field "{field_name}" of the last ingested item in corpus '
    "\"{corpus_name}\" equals '{value_json}'"
)
def step_catalog_item_metadata_field_equals(
    context, field_name: str, corpus_name: str, value_json: str
) -> None:
    item = _last_item(_read_catalog(context, corpus_name), context)
    assert field_name not in item
    assert item["metadata"][field_name] == json.loads(value_json)
