from __future__ import annotations

import json
from pathlib import Path

from behave import then, when

from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_ingest_output(stdout: str) -> str:
    parts = stdout.strip().splitlines()[-1].split("\t")
    if len(parts) != 3:
        raise AssertionError(f"Unexpected ingest output: {stdout!r}")
    return parts[0]


def _snapshot_reference_from_context(context) -> str:
    extractor_id = context.last_extractor_id
    snapshot_id = context.last_extraction_snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    return f"{extractor_id}:{snapshot_id}"


@when('I ingest topic modeling texts into corpus "{corpus_name}":')
def step_ingest_topic_modeling_texts(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    for row in context.table:
        result = run_biblicus(
            context,
            [
                "--corpus",
                str(corpus),
                "ingest",
                "--note",
                row["text"].strip(),
                "--title",
                row["title"].strip(),
            ],
        )
        assert result.returncode == 0, result.stderr
        item_id = _parse_ingest_output(result.stdout)
        context.ingested_ids.append(item_id)


@when(
    'I run a topic granularity sweep in corpus "{corpus_name}" using configuration "{configuration_file}" with target range "{target_range}" as markdown'
)
def step_run_topic_granularity_sweep_markdown(
    context, corpus_name: str, configuration_file: str, target_range: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    configuration_path = Path(context.workdir) / configuration_file
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "topic-granularity-sweep",
        "--configuration",
        str(configuration_path),
        "--extraction-snapshot",
        _snapshot_reference_from_context(context),
        "--target-topic-range",
        target_range,
        "--format",
        "markdown",
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_granularity_markdown = result.stdout
        latest_path = corpus / "analysis" / "topic-granularity-sweep" / "latest.json"
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        output_path = (
            corpus / "analysis" / "topic-granularity-sweep" / latest["snapshot_id"] / "output.json"
        )
        context.last_topic_granularity_output = json.loads(output_path.read_text(encoding="utf-8"))


@then("the granularity sweep output includes profiles:")
def step_granularity_sweep_includes_profiles(context) -> None:
    output = context.last_topic_granularity_output
    actual = {profile["profile"] for profile in output["profiles"]}
    expected = {row["profile"].strip() for row in context.table}
    assert expected.issubset(actual), output


@then("the granularity sweep selected topic count is between {minimum:d} and {maximum:d}")
def step_granularity_selected_count_between(context, minimum: int, maximum: int) -> None:
    output = context.last_topic_granularity_output
    profiles = {profile["profile"]: profile for profile in output["profiles"]}
    selected = profiles[output["selected_profile"]]
    assert minimum <= selected["topic_count"] <= maximum, output


@then('the granularity sweep markdown includes "{text}"')
def step_granularity_markdown_includes(context, text: str) -> None:
    markdown = getattr(context, "last_topic_granularity_markdown", "")
    assert text in markdown, markdown
