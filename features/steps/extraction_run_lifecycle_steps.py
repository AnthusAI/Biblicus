from __future__ import annotations

import json
from pathlib import Path

from behave import then, when

from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _extractor_and_run_id(reference: str) -> tuple[str, str]:
    extractor_id, run_id = reference.split(":", 1)
    extractor_id = extractor_id.strip()
    run_id = run_id.strip()
    if not extractor_id or not run_id:
        raise ValueError("Extraction run reference must be extractor_id:run_id with non-empty parts")
    return extractor_id, run_id


def _remembered_reference(context, name: str) -> str:
    remembered = getattr(context, "remembered_extraction_run_references", {})
    value = remembered.get(name)
    assert isinstance(value, str) and value
    return value


@when('I list extraction runs in corpus "{corpus_name}"')
def step_list_extraction_runs(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "list"]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run_list = json.loads(result.stdout or "[]")


@when('I list extraction runs for extractor "{extractor_id}" in corpus "{corpus_name}"')
def step_list_extraction_runs_for_extractor(context, extractor_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "extract", "list", "--extractor-id", extractor_id]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_extraction_run_list = json.loads(result.stdout or "[]")


@then("the extraction run list is empty")
def step_extraction_run_list_is_empty(context) -> None:
    listed = getattr(context, "last_extraction_run_list", None)
    assert isinstance(listed, list)
    assert listed == []


@then('the extraction run list includes "{name}"')
def step_extraction_run_list_includes(context, name: str) -> None:
    expected = _remembered_reference(context, name)
    extractor_id, run_id = _extractor_and_run_id(expected)
    listed = getattr(context, "last_extraction_run_list", [])
    assert isinstance(listed, list)
    found = False
    for entry in listed:
        if not isinstance(entry, dict):
            continue
        if entry.get("extractor_id") == extractor_id and entry.get("run_id") == run_id:
            found = True
            break
    assert found, f"Expected run {expected} in list"


@then('the extraction run list does not include raw reference "{reference}"')
def step_extraction_run_list_does_not_include_raw_reference(context, reference: str) -> None:
    extractor_id, run_id = _extractor_and_run_id(reference)
    listed = getattr(context, "last_extraction_run_list", [])
    assert isinstance(listed, list)
    for entry in listed:
        if not isinstance(entry, dict):
            continue
        assert not (
            entry.get("extractor_id") == extractor_id and entry.get("run_id") == run_id
        ), f"Did not expect run {reference} in list"


@when('I show extraction run "{name}" in corpus "{corpus_name}"')
def step_show_extraction_run(context, name: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    reference = _remembered_reference(context, name)
    args = ["--corpus", str(corpus), "extract", "show", "--run", reference]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_shown_extraction_run = json.loads(result.stdout)


@then('the shown extraction run reference equals "{name}"')
def step_shown_extraction_run_reference_equals(context, name: str) -> None:
    expected = _remembered_reference(context, name)
    extractor_id, run_id = _extractor_and_run_id(expected)
    shown = getattr(context, "last_shown_extraction_run", None)
    assert isinstance(shown, dict)
    assert shown.get("run_id") == run_id
    recipe = shown.get("recipe")
    assert isinstance(recipe, dict)
    assert recipe.get("extractor_id") == extractor_id


@when('I delete extraction run "{name}" in corpus "{corpus_name}"')
def step_delete_extraction_run(context, name: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    reference = _remembered_reference(context, name)
    args = [
        "--corpus",
        str(corpus),
        "extract",
        "delete",
        "--run",
        reference,
        "--confirm",
        reference,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr


@when('I attempt to delete extraction run "{name}" in corpus "{corpus_name}" with confirm "{confirm}"')
def step_attempt_delete_extraction_run(context, name: str, corpus_name: str, confirm: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    reference = _remembered_reference(context, name)
    args = [
        "--corpus",
        str(corpus),
        "extract",
        "delete",
        "--run",
        reference,
        "--confirm",
        confirm,
    ]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@then('the extraction run artifacts for "{name}" do not exist under the corpus')
def step_extraction_run_artifacts_do_not_exist(context, name: str) -> None:
    reference = _remembered_reference(context, name)
    extractor_id, run_id = _extractor_and_run_id(reference)
    corpus = _corpus_path(context, "corpus")
    run_dir = corpus / ".biblicus" / "runs" / "extraction" / extractor_id / run_id
    assert not run_dir.exists(), run_dir
