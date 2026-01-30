from __future__ import annotations

import json
from pathlib import Path

from behave import then, when

from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)


def _run_reference_from_context(context) -> str:
    extractor_id = context.last_extractor_id
    run_id = context.last_extraction_run_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(run_id, str) and run_id
    return f"{extractor_id}:{run_id}"


def _require_profiling_output(context) -> dict[str, object]:
    if not hasattr(context, "last_analysis_output"):
        result = getattr(context, "last_result", None)
        stderr = getattr(result, "stderr", "") if result is not None else ""
        raise AssertionError(f"Profiling output missing. stderr: {stderr}")
    return context.last_analysis_output


@when('I run a profiling analysis in corpus "{corpus_name}" using the latest extraction run')
def step_run_profiling_analysis_with_latest_extraction(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    run_ref = _run_reference_from_context(context)
    args = ["--corpus", str(corpus), "analyze", "profile", "--extraction-run", run_ref]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when('I run a profiling analysis in corpus "{corpus_name}"')
def step_run_profiling_analysis(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "analyze", "profile"]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when(
    'I run a profiling analysis in corpus "{corpus_name}" using recipe "{recipe_file}" and the latest extraction run'
)
def step_run_profiling_analysis_with_recipe(context, corpus_name: str, recipe_file: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    run_ref = _run_reference_from_context(context)
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "profile",
        "--recipe",
        str(recipe_path),
        "--extraction-run",
        run_ref,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when(
    'I run a profiling analysis in corpus "{corpus_name}" using recipe "{recipe_file}" without extraction run'
)
def step_run_profiling_analysis_with_recipe_without_extraction(
    context, corpus_name: str, recipe_file: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    recipe_path = Path(workdir) / recipe_file
    args = ["--corpus", str(corpus), "analyze", "profile", "--recipe", str(recipe_path)]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@then("the profiling output includes raw item total {count:d}")
def step_profiling_output_includes_raw_total(context, count: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    raw_items = report["raw_items"]
    assert raw_items["total_items"] == count


@then('the profiling output includes media type count "{media_type}" {count:d}')
def step_profiling_output_includes_media_type_count(context, media_type: str, count: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    raw_items = report["raw_items"]
    media_type_counts = raw_items["media_type_counts"]
    assert media_type_counts[media_type] == count


@then("the profiling output includes extracted source items {count:d}")
def step_profiling_output_includes_extracted_source_items(context, count: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    extracted_text = report["extracted_text"]
    assert extracted_text["source_items"] == count


@then("the profiling output includes extracted nonempty items {count:d}")
def step_profiling_output_includes_extracted_nonempty(context, count: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    extracted_text = report["extracted_text"]
    assert extracted_text["extracted_nonempty_items"] == count


@then("the profiling output includes extracted empty items {count:d}")
def step_profiling_output_includes_extracted_empty(context, count: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    extracted_text = report["extracted_text"]
    assert extracted_text["extracted_empty_items"] == count


@then("the profiling output includes extracted missing items {count:d}")
def step_profiling_output_includes_extracted_missing(context, count: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    extracted_text = report["extracted_text"]
    assert extracted_text["extracted_missing_items"] == count


@when('I create a profiling recipe file "{filename}" with:')
def step_create_profiling_recipe_file(context, filename: str) -> None:
    path = context.workdir / filename
    path.write_text(context.text, encoding="utf-8")


@then("the profiling output includes raw bytes distribution count {count:d}")
def step_profiling_output_raw_bytes_distribution_count(context, count: int) -> None:
    output = _require_profiling_output(context)
    distribution = output["report"]["raw_items"]["bytes_distribution"]
    assert distribution["count"] == count


@then("the profiling output includes extracted text distribution count {count:d}")
def step_profiling_output_extracted_text_distribution_count(context, count: int) -> None:
    output = _require_profiling_output(context)
    distribution = output["report"]["extracted_text"]["characters_distribution"]
    assert distribution["count"] == count


@then("the profiling output includes raw bytes percentiles {percentiles}")
def step_profiling_output_raw_bytes_percentiles(context, percentiles: str) -> None:
    output = _require_profiling_output(context)
    distribution = output["report"]["raw_items"]["bytes_distribution"]
    expected = {int(value.strip()) for value in percentiles.split(",") if value.strip()}
    actual = {entry["percentile"] for entry in distribution["percentiles"]}
    assert expected.issubset(actual)


@then("the profiling output includes extracted text percentiles {percentiles}")
def step_profiling_output_extracted_text_percentiles(context, percentiles: str) -> None:
    output = _require_profiling_output(context)
    distribution = output["report"]["extracted_text"]["characters_distribution"]
    expected = {int(value.strip()) for value in percentiles.split(",") if value.strip()}
    actual = {entry["percentile"] for entry in distribution["percentiles"]}
    assert expected.issubset(actual)


@then("the profiling output includes tagged items {count:d}")
def step_profiling_output_tagged_items(context, count: int) -> None:
    output = _require_profiling_output(context)
    tags = output["report"]["raw_items"]["tags"]
    assert tags["tagged_items"] == count


@then("the profiling output includes untagged items {count:d}")
def step_profiling_output_untagged_items(context, count: int) -> None:
    output = _require_profiling_output(context)
    tags = output["report"]["raw_items"]["tags"]
    assert tags["untagged_items"] == count


@then('the profiling output includes top tag "{tag}" with count {count:d}')
def step_profiling_output_top_tag(context, tag: str, count: int) -> None:
    output = _require_profiling_output(context)
    top_tags = output["report"]["raw_items"]["tags"]["top_tags"]
    matches = [entry for entry in top_tags if entry["tag"] == tag]
    assert matches, f"Missing tag {tag!r} in top tags"
    assert matches[0]["count"] == count
