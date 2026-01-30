from __future__ import annotations

import json
import subprocess
from pathlib import Path

from behave import then, when


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)


@when(
    'I run the extraction evaluation lab with corpus "{corpus_name}" and dataset "{dataset_name}"'
)
def step_run_extraction_evaluation_lab(context, corpus_name: str, dataset_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    dataset_path = (context.workdir / dataset_name).resolve()
    result = subprocess.run(
        [
            "python3",
            "scripts/extraction_evaluation_lab.py",
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
    context.extraction_lab_summary = _parse_json_output(result.stdout)


@then("the extraction evaluation lab dataset file exists")
def step_extraction_lab_dataset_exists(context) -> None:
    summary = context.extraction_lab_summary
    dataset_path = Path(summary["dataset_path"])
    assert dataset_path.is_file()


@then("the extraction evaluation lab output file exists")
def step_extraction_lab_output_exists(context) -> None:
    summary = context.extraction_lab_summary
    output_path = Path(summary["evaluation_output_path"])
    assert output_path.is_file()


@then("the extraction evaluation lab metrics include coverage_present {count:d}")
def step_extraction_lab_coverage_present(context, count: int) -> None:
    metrics = context.extraction_lab_summary["metrics"]
    assert metrics["coverage_present"] == float(count)


@then("the extraction evaluation lab metrics include coverage_empty {count:d}")
def step_extraction_lab_coverage_empty(context, count: int) -> None:
    metrics = context.extraction_lab_summary["metrics"]
    assert metrics["coverage_empty"] == float(count)


@then("the extraction evaluation lab metrics include coverage_missing {count:d}")
def step_extraction_lab_coverage_missing(context, count: int) -> None:
    metrics = context.extraction_lab_summary["metrics"]
    assert metrics["coverage_missing"] == float(count)


@then("the extraction evaluation lab metrics include processable_fraction {expected:g}")
def step_extraction_lab_processable_fraction(context, expected: float) -> None:
    metrics = context.extraction_lab_summary["metrics"]
    assert metrics["processable_fraction"] == expected


@then("the extraction evaluation lab metrics include average_similarity {expected:g}")
def step_extraction_lab_average_similarity(context, expected: float) -> None:
    metrics = context.extraction_lab_summary["metrics"]
    assert metrics["average_similarity"] == expected
