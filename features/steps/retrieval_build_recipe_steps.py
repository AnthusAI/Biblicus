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


@when('I create a retrieval build recipe file "{filename}" with:')
def step_create_retrieval_build_recipe_file(context, filename: str) -> None:
    path = context.workdir / filename
    path.write_text(context.text, encoding="utf-8")
    context.last_recipe_path = path


@when(
    'I build a "{backend}" retrieval run in corpus "{corpus_name}" using recipe file "{filename}"'
)
def step_build_run_with_recipe_file(context, backend: str, corpus_name: str, filename: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    recipe = (context.workdir / filename).resolve()
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(corpus),
            "build",
            "--backend",
            backend,
            "--recipe-name",
            "default",
            "--recipe",
            str(recipe),
        ],
    )
    assert result.returncode == 0, result.stderr
    context.last_run = _parse_json_output(result.stdout)
    context.last_run_id = context.last_run.get("run_id")


@then('the latest run backend id equals "{backend_id}"')
def step_latest_run_backend_id_equals(context, backend_id: str) -> None:
    assert context.last_run is not None
    recipe = context.last_run.get("recipe") or {}
    assert recipe.get("backend_id") == backend_id


@then('the latest run recipe config includes "{key}" with value {value:d}')
def step_latest_run_recipe_config_includes_int(context, key: str, value: int) -> None:
    assert context.last_run is not None
    recipe = context.last_run.get("recipe") or {}
    config = recipe.get("config") or {}
    assert config.get(key) == value
