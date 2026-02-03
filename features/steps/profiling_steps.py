from __future__ import annotations

import json
from pathlib import Path

from behave import then, when

from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)


def _snapshot_reference_from_context(context) -> str:
    extractor_id = context.last_extractor_id
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    return f"{extractor_id}:{snapshot_id}"


def _require_profiling_output(context) -> dict[str, object]:
    if not hasattr(context, "last_analysis_output"):
        result = getattr(context, "last_result", None)
        stderr = getattr(result, "stderr", "") if result is not None else ""
        raise AssertionError(f"Profiling output missing. stderr: {stderr}")
    return context.last_analysis_output


@when(
    'I snapshot a profiling analysis in corpus "{corpus_name}" using the latest extraction snapshot'
)
def step_run_profiling_analysis_with_latest_extraction(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    snapshot_ref = _snapshot_reference_from_context(context)
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "profile",
        "--extraction-snapshot",
        snapshot_ref,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when('I snapshot a profiling analysis in corpus "{corpus_name}"')
def step_run_profiling_analysis(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "analyze", "profile"]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when(
    'I snapshot a profiling analysis in corpus "{corpus_name}" using configuration "{configuration_file}" '
    "and the latest extraction snapshot"
)
def step_run_profiling_analysis_with_configuration(
    context, corpus_name: str, configuration_file: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    configuration_path = Path(workdir) / configuration_file
    snapshot_ref = _snapshot_reference_from_context(context)
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "profile",
        "--configuration",
        str(configuration_path),
        "--extraction-snapshot",
        snapshot_ref,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when(
    'I snapshot a profiling analysis in corpus "{corpus_name}" using configuration "{configuration_file}" '
    "without extraction snapshot"
)
def step_run_profiling_analysis_without_extraction_snapshot(
    context, corpus_name: str, configuration_file: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    configuration_path = Path(workdir) / configuration_file
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "profile",
        "--configuration",
        str(configuration_path),
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when(
    'I snapshot a profiling analysis in corpus "{corpus_name}" using configurations "{configuration_files}" '
    "and the latest extraction snapshot with config overrides:"
)
def step_run_profiling_analysis_with_recipes_and_overrides(
    context, corpus_name: str, configuration_files: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    configuration_paths = []
    for token in configuration_files.split(","):
        token = token.strip()
        if not token:
            continue
        configuration_paths.append(str(Path(workdir) / token))
    snapshot_ref = _snapshot_reference_from_context(context)
    args = ["--corpus", str(corpus), "analyze", "profile"]
    for configuration_path in configuration_paths:
        args.extend(["--configuration", configuration_path])
    for row in context.table:
        key = str(row["key"]).strip()
        value = str(row["value"]).strip()
        args.extend(["--override", f"{key}={value}"])
    args.extend(["--extraction-snapshot", snapshot_ref])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@when(
    'I snapshot a profiling analysis in corpus "{corpus_name}" using the latest extraction snapshot with config overrides:'
)
def step_run_profiling_analysis_with_overrides_only(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    snapshot_ref = _snapshot_reference_from_context(context)
    args = ["--corpus", str(corpus), "analyze", "profile"]
    for row in context.table:
        key = str(row["key"]).strip()
        value = str(row["value"]).strip()
        args.extend(["--override", f"{key}={value}"])
    args.extend(["--extraction-snapshot", snapshot_ref])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_analysis_output = _parse_json_output(result.stdout)


@then("the profiling analysis report includes sample_size {value:d}")
def step_profiling_analysis_report_includes_sample_size(context, value: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    assert report["sample_size"] == value


@then("the profiling analysis report includes min_text_characters {value:d}")
def step_profiling_analysis_report_includes_min_text_characters(context, value: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    assert report["min_text_characters"] == value


@when(
    'I snapshot a profiling analysis in corpus "{corpus_name}" using configuration "{configuration_file}" '
    "without an extraction snapshot"
)
def step_run_profiling_analysis_with_recipe_without_extraction(
    context, corpus_name: str, configuration_file: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    workdir = getattr(context, "workdir", None)
    assert workdir is not None
    configuration_path = Path(workdir) / configuration_file
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "profile",
        "--configuration",
        str(configuration_path),
    ]
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


@then("the profiling analysis output includes percentile {percentile:d}")
def step_profiling_analysis_output_includes_percentile(context, percentile: int) -> None:
    output = _require_profiling_output(context)
    report = output["report"]
    extracted_text = report["extracted_text"]
    distribution = extracted_text["characters_distribution"]
    percentiles = distribution.get("percentiles", [])
    values = {entry.get("percentile") for entry in percentiles}
    assert percentile in values


@when('I create a profiling configuration file "{filename}" with:')
def step_create_profiling_configuration_file(context, filename: str) -> None:
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
