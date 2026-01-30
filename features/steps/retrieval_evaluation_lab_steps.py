from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from behave import then, when


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)


def _expect_metric(metrics: dict[str, object], key: str, expected: float) -> None:
    actual = float(metrics[key])
    assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)


@when('I run the retrieval evaluation lab with corpus "{corpus_name}" and dataset "{dataset_name}"')
def step_run_retrieval_evaluation_lab(context, corpus_name: str, dataset_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    dataset_path = (context.workdir / dataset_name).resolve()
    result = subprocess.run(
        [
            "python3",
            "scripts/retrieval_evaluation_lab.py",
            "--corpus",
            str(corpus),
            "--dataset-path",
            str(dataset_path),
            "--force",
        ],
        cwd=context.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    context.last_result = result
    assert result.returncode == 0, result.stderr
    context.retrieval_lab_summary = _parse_json_output(result.stdout)


@then("the retrieval evaluation lab dataset file exists")
def step_retrieval_lab_dataset_exists(context) -> None:
    summary = context.retrieval_lab_summary
    dataset_path = Path(summary["dataset_path"])
    assert dataset_path.is_file()


@then("the retrieval evaluation lab output file exists")
def step_retrieval_lab_output_exists(context) -> None:
    summary = context.retrieval_lab_summary
    output_path = Path(summary["evaluation_output_path"])
    assert output_path.is_file()


@then("the retrieval evaluation lab metrics include hit_rate {expected:g}")
def step_retrieval_lab_hit_rate(context, expected: float) -> None:
    metrics = context.retrieval_lab_summary["metrics"]
    _expect_metric(metrics, "hit_rate", expected)


@then("the retrieval evaluation lab metrics include mean_reciprocal_rank {expected:g}")
def step_retrieval_lab_mean_reciprocal_rank(context, expected: float) -> None:
    metrics = context.retrieval_lab_summary["metrics"]
    _expect_metric(metrics, "mean_reciprocal_rank", expected)


@then("the retrieval evaluation lab metrics include precision_at_max_total_items {expected:g}")
def step_retrieval_lab_precision_at_max_total_items(context, expected: float) -> None:
    metrics = context.retrieval_lab_summary["metrics"]
    _expect_metric(metrics, "precision_at_max_total_items", expected)
