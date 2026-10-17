from __future__ import annotations

import json
from pathlib import Path

from behave import then, when

from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _load_latest_topic_context_output(corpus: Path) -> dict[str, object]:
    latest_path = corpus / "analysis" / "topic-context" / "latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    output_path = corpus / "analysis" / "topic-context" / latest["snapshot_id"] / "output.json"
    return json.loads(output_path.read_text(encoding="utf-8"))


@when(
    'I generate a topic context report in corpus "{corpus_name}" with max topics {max_topics:d} and {examples_per_topic:d} example as markdown'
)
@when(
    'I generate a topic context report in corpus "{corpus_name}" with max topics {max_topics:d} and {examples_per_topic:d} examples as markdown'
)
def step_generate_topic_context_markdown(
    context,
    corpus_name: str,
    max_topics: int,
    examples_per_topic: int,
) -> None:
    corpus = _corpus_path(context, corpus_name)
    topic_modeling_snapshot_id = context.last_analysis_output["snapshot"]["snapshot_id"]
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "topic-context",
        "--topic-modeling-snapshot",
        topic_modeling_snapshot_id,
        "--max-topics",
        str(max_topics),
        "--examples-per-topic",
        str(examples_per_topic),
        "--format",
        "markdown",
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    assert result.returncode == 0, result.stderr
    if result.returncode == 0:
        context.last_topic_context_markdown = result.stdout
        context.last_topic_context_output = _load_latest_topic_context_output(corpus)


@when(
    'I generate a summarized topic context report in corpus "{corpus_name}" using summary model "{summary_model}" with max topics {max_topics:d} and {examples_per_topic:d} examples as markdown'
)
def step_generate_topic_context_markdown_with_summary_model(
    context,
    corpus_name: str,
    summary_model: str,
    max_topics: int,
    examples_per_topic: int,
) -> None:
    corpus = _corpus_path(context, corpus_name)
    topic_modeling_snapshot_id = context.last_analysis_output["snapshot"]["snapshot_id"]
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "topic-context",
        "--topic-modeling-snapshot",
        topic_modeling_snapshot_id,
        "--summary-model",
        summary_model,
        "--max-topics",
        str(max_topics),
        "--examples-per-topic",
        str(examples_per_topic),
        "--format",
        "markdown",
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    assert result.returncode == 0, result.stderr
    if result.returncode == 0:
        context.last_topic_context_markdown = result.stdout
        context.last_topic_context_output = _load_latest_topic_context_output(corpus)


@then("the topic context output includes {count:d} topic")
@then("the topic context output includes {count:d} topics")
def step_topic_context_output_includes_topic_count(context, count: int) -> None:
    output = context.last_topic_context_output
    assert len(output["topics"]) == count, output


@then('the topic context Markdown includes "{text}"')
def step_topic_context_markdown_includes(context, text: str) -> None:
    markdown = getattr(context, "last_topic_context_markdown", "")
    assert text in markdown, markdown


@then('the topic context Markdown does not include "{text}"')
def step_topic_context_markdown_omits(context, text: str) -> None:
    markdown = getattr(context, "last_topic_context_markdown", "")
    assert text not in markdown, markdown


@then('the topic context output example "{title}" uses text source "{text_source}"')
def step_topic_context_example_uses_text_source(
    context,
    title: str,
    text_source: str,
) -> None:
    output = context.last_topic_context_output
    for topic in output["topics"]:
        for example in topic["examples"]:
            if example["title"] == title:
                assert example["text_source"] == text_source, example
                return
    raise AssertionError(f"Missing topic context example titled {title!r}")
