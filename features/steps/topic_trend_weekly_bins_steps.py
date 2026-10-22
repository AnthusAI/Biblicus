from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from behave import given, then, when

from features.environment import run_biblicus

TRAILING_WINDOW_OUTPUT_FIELDS = {
    "schema_version",
    "analysis_id",
    "snapshot_id",
    "generated_at",
    "inputs",
    "as_of",
    "windows",
    "rank_window",
    "summary",
    "canonical_topics",
    "discovered_topics",
    "proposals",
    "artifact_paths",
    "warnings",
}


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


@given('the corpus "{corpus_name}" has dated items:')
def step_corpus_has_dated_items(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    for index, row in enumerate(context.table, start=1):
        item_id = f"{index:08d}-0000-4000-8000-000000000000"
        text = row["text"].strip()
        (corpus / f"{item_id}--item-{index}.txt").write_text(
            f"{text} item number {index}", encoding="utf-8"
        )
        lines = [f"title: Item {index}"]
        published_at = row["published_at"].strip()
        if published_at:
            lines.extend(["dates:", f'  published_at: "{published_at}"'])
        lines.extend(["biblicus:", f"  id: {item_id}", f"  source: urn:test:item-{index}"])
        (corpus / f"{item_id}--item-{index}.txt.biblicus.yml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )


def _run_topic_trends(context, corpus_name: str, extra: List[str]) -> None:
    corpus = _corpus_path(context, corpus_name)
    topic_modeling_snapshot_id = context.last_analysis_output["snapshot"]["snapshot_id"]
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "topic-trends",
        "--topic-modeling-snapshot",
        topic_modeling_snapshot_id,
        "--windows",
        "30d,90d,all",
        *extra,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_trends_output = json.loads(result.stdout)


@when(
    'I analyze topic trends in corpus "{corpus_name}" with weekly bins for {weeks:d} weeks as of "{as_of}"'
)
def step_trends_weekly(context, corpus_name: str, weeks: int, as_of: str) -> None:
    _run_topic_trends(
        context, corpus_name, ["--bin", "weekly", "--weeks", str(weeks), "--as-of", as_of]
    )


@when(
    'I analyze topic trends in corpus "{corpus_name}" with weekly bins and no week count as of "{as_of}"'
)
def step_trends_weekly_default_weeks(context, corpus_name: str, as_of: str) -> None:
    _run_topic_trends(context, corpus_name, ["--bin", "weekly", "--as-of", as_of])


@when(
    'I analyze topic trends in corpus "{corpus_name}" with a week count of {weeks:d} and no binning option'
)
def step_trends_weeks_without_bin(context, corpus_name: str, weeks: int) -> None:
    _run_topic_trends(context, corpus_name, ["--weeks", str(weeks)])


@when('I analyze topic trends in corpus "{corpus_name}" without a binning option as of "{as_of}"')
def step_trends_without_bin(context, corpus_name: str, as_of: str) -> None:
    _run_topic_trends(context, corpus_name, ["--as-of", as_of])


def _weekly_bins(context) -> Dict:
    bins = context.last_topic_trends_output["weekly_bins"]
    assert bins["bin"] == "weekly", bins
    return bins


def _discovered_counts(context, topic_id: int) -> Optional[List[int]]:
    for row in _weekly_bins(context)["discovered_topics"]:
        if row["topic_id"] == topic_id:
            return row["counts"]
    return None


@then('the weekly bins list {weeks:d} ISO weeks from "{first}" to "{last}"')
def step_weekly_bins_list_weeks(context, weeks: int, first: str, last: str) -> None:
    bins = _weekly_bins(context)
    assert bins["weeks"] == weeks, bins
    assert len(bins["iso_weeks"]) == weeks, bins
    assert len(bins["week_starts"]) == weeks, bins
    assert bins["iso_weeks"][0] == first, bins
    assert bins["iso_weeks"][-1] == last, bins


@then('discovered topic "{topic_id}" reports weekly counts "{counts}"')
def step_discovered_topic_weekly_counts(context, topic_id: str, counts: str) -> None:
    expected = [int(token) for token in counts.split(",")]
    actual = _discovered_counts(context, int(topic_id))
    assert actual == expected, (actual, expected)
    assert all(type(count) is int for count in actual), actual


@then('discovered topic "{topic_id}" reports {weeks:d} weekly counts that total {total:d}')
def step_discovered_topic_weekly_total(context, topic_id: str, weeks: int, total: int) -> None:
    actual = _discovered_counts(context, int(topic_id))
    assert len(actual) == weeks, actual
    assert sum(actual) == total, actual


@then("the weekly bins report {count:d} undated items")
def step_weekly_bins_undated(context, count: int) -> None:
    assert _weekly_bins(context)["undated_items"] == count, context.last_topic_trends_output


@then("the weekly counts of all discovered topics total {total:d}")
def step_weekly_counts_total(context, total: int) -> None:
    rows = _weekly_bins(context)["discovered_topics"]
    assert sum(sum(row["counts"]) for row in rows) == total, rows


@then("the topic trend output has no weekly bins")
def step_no_weekly_bins(context) -> None:
    assert "weekly_bins" not in context.last_topic_trends_output
    assert "weekly_bins" not in context.last_result.stdout


@then("the topic trend output has exactly the trailing-window fields")
def step_trailing_window_fields(context) -> None:
    output = context.last_topic_trends_output
    assert set(output) == TRAILING_WINDOW_OUTPUT_FIELDS, set(output)
    assert not {"bin", "weeks", "weekly_as_of"} & set(output["inputs"]), output["inputs"]
