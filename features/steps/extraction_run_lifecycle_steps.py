from __future__ import annotations

import json
from pathlib import Path

from behave import then, when

from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _extractor_and_snapshot_id(reference: str) -> tuple[str, str]:
    extractor_id, snapshot_id = reference.split(":", 1)
    extractor_id = extractor_id.strip()
    snapshot_id = snapshot_id.strip()
    if not extractor_id or not snapshot_id:
        raise ValueError(
            "Extraction snapshot reference must be extractor_id:snapshot_id with non-empty parts"
        )
    return extractor_id, snapshot_id


def _remembered_reference(context, name: str) -> str:
    remembered = getattr(context, "remembered_extraction_snapshot_references", {})
    value = remembered.get(name)
    assert isinstance(value, str) and value
    return value


@when('I list extraction snapshots in corpus "{corpus_name}"')
def step_list_extraction_snapshots(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "list"]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot_list = json.loads(result.stdout or "[]")


@when('I list extraction snapshots for extractor "{extractor_id}" in corpus "{corpus_name}"')
def step_list_extraction_snapshots_for_extractor(
    context, extractor_id: str, corpus_name: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "list", "--extractor-id", extractor_id]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_snapshot_list = json.loads(result.stdout or "[]")


@then("the extraction snapshot list is empty")
def step_extraction_snapshot_list_is_empty(context) -> None:
    listed = getattr(context, "last_extraction_snapshot_list", None)
    assert isinstance(listed, list)
    assert listed == []


@then('the extraction snapshot list includes "{name}"')
def step_extraction_snapshot_list_includes(context, name: str) -> None:
    expected = _remembered_reference(context, name)
    extractor_id, snapshot_id = _extractor_and_snapshot_id(expected)
    listed = getattr(context, "last_extraction_snapshot_list", [])
    assert isinstance(listed, list)
    found = False
    for entry in listed:
        if not isinstance(entry, dict):
            continue
        if entry.get("extractor_id") == extractor_id and entry.get("snapshot_id") == snapshot_id:
            found = True
            break
    assert found, f"Expected snapshot {expected} in list"


@then('the extraction snapshot list does not include raw reference "{reference}"')
def step_extraction_snapshot_list_does_not_include_raw_reference(context, reference: str) -> None:
    extractor_id, snapshot_id = _extractor_and_snapshot_id(reference)
    listed = getattr(context, "last_extraction_snapshot_list", [])
    assert isinstance(listed, list)
    for entry in listed:
        if not isinstance(entry, dict):
            continue
        assert not (
            entry.get("extractor_id") == extractor_id and entry.get("snapshot_id") == snapshot_id
        ), f"Did not expect snapshot {reference} in list"


@when('I show extraction snapshot "{name}" in corpus "{corpus_name}"')
def step_show_extraction_snapshot(context, name: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    reference = _remembered_reference(context, name)
    args = ["--corpus", str(corpus), "extract", "show", "--snapshot", reference]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_shown_extraction_snapshot = json.loads(result.stdout)


@then('the shown extraction snapshot reference equals "{name}"')
def step_shown_extraction_snapshot_reference_equals(context, name: str) -> None:
    expected = _remembered_reference(context, name)
    extractor_id, snapshot_id = _extractor_and_snapshot_id(expected)
    shown = getattr(context, "last_shown_extraction_snapshot", None)
    assert isinstance(shown, dict)
    assert shown.get("snapshot_id") == snapshot_id
    configuration = shown.get("configuration")
    assert isinstance(configuration, dict)
    assert configuration.get("extractor_id") == extractor_id


@when('I delete extraction snapshot "{name}" in corpus "{corpus_name}"')
def step_delete_extraction_snapshot(context, name: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    reference = _remembered_reference(context, name)
    args = [
        "--corpus",
        str(corpus),
        "extract",
        "delete",
        "--snapshot",
        reference,
        "--confirm",
        reference,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr


@when(
    'I attempt to delete extraction snapshot "{name}" in corpus "{corpus_name}" with confirm "{confirm}"'
)
def step_attempt_delete_extraction_snapshot(
    context, name: str, corpus_name: str, confirm: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    reference = _remembered_reference(context, name)
    args = [
        "--corpus",
        str(corpus),
        "extract",
        "delete",
        "--snapshot",
        reference,
        "--confirm",
        confirm,
    ]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@then('the extraction snapshot artifacts for "{name}" do not exist under the corpus')
def step_extraction_snapshot_artifacts_do_not_exist(context, name: str) -> None:
    reference = _remembered_reference(context, name)
    extractor_id, snapshot_id = _extractor_and_snapshot_id(reference)
    corpus = _corpus_path(context, "corpus")
    snapshot_dir = corpus / "extracted" / extractor_id / snapshot_id
    assert not snapshot_dir.exists(), snapshot_dir
