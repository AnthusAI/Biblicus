from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from behave import then, when

from features.environment import run_biblicus


def _parse_json_output(standard_output: str) -> Dict[str, Any]:
    return json.loads(standard_output)


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


@when('I create a retrieval build configuration file "{filename}" with:')
def step_create_retrieval_build_configuration_file(context, filename: str) -> None:
    path = context.workdir / filename
    path.write_text(context.text, encoding="utf-8")
    context.last_configuration_path = path


@when(
    'I build a "{retriever_id}" retrieval snapshot in corpus "{corpus_name}" using configuration file "{filename}"'
)
def step_build_snapshot_with_configuration_file(
    context, retriever_id: str, corpus_name: str, filename: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    configuration_path = (context.workdir / filename).resolve()
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(corpus),
            "build",
            "--retriever",
            retriever_id,
            "--configuration-name",
            "default",
            "--configuration",
            str(configuration_path),
        ],
    )
    assert result.returncode == 0, result.stderr
    context.last_snapshot = _parse_json_output(result.stdout)
    context.last_snapshot_id = context.last_snapshot.get("snapshot_id")


@then('the latest snapshot retriever id equals "{retriever_id}"')
def step_latest_snapshot_retriever_id_equals(context, retriever_id: str) -> None:
    assert context.last_snapshot is not None
    configuration = context.last_snapshot.get("configuration") or {}
    assert configuration.get("retriever_id") == retriever_id


@then('the latest snapshot configuration config includes "{key}" with value {value:d}')
def step_latest_snapshot_configuration_includes_int(context, key: str, value: int) -> None:
    assert context.last_snapshot is not None
    configuration = context.last_snapshot.get("configuration") or {}
    config = configuration.get("configuration") or {}
    assert config.get(key) == value
