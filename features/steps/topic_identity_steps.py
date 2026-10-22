from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from behave import given, then, when

from biblicus.retrieval import hash_text
from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_items(spec: str) -> List[str]:
    item_ids: List[str] = []
    for token in spec.split(","):
        token = token.strip()
        if "-" in token:
            low, high = token.split("-", 1)
            item_ids.extend(str(number) for number in range(int(low), int(high) + 1))
        else:
            item_ids.append(token)
    return item_ids


def _names(spec: str) -> List[str]:
    return [token.strip() for token in spec.split(",") if token.strip()]


@given(
    'topic modeling run "{run_id}" in corpus "{corpus_name}" created "{created_at}" has clusters:'
)
def step_topic_modeling_run_with_clusters(
    context, run_id: str, corpus_name: str, created_at: str
) -> None:
    payload = copy.deepcopy(context.last_analysis_output)
    label_source = payload["report"]["topics"][0]["label_source"]
    payload["snapshot"]["snapshot_id"] = run_id
    payload["snapshot"]["created_at"] = created_at
    payload["generated_at"] = created_at
    topics = []
    for row in context.table:
        item_ids = _parse_items(row["items"])
        keywords = _names(row["keywords"])
        topics.append(
            {
                "topic_id": int(row["topic_id"]),
                "label": f"Topic {row['topic_id'].strip()}",
                "label_source": label_source,
                "keywords": [
                    {"keyword": keyword, "score": 1.0 - index * 0.01}
                    for index, keyword in enumerate(keywords)
                ],
                "document_count": len(item_ids),
                "document_examples": [],
                "document_ids": item_ids,
            }
        )
    payload["report"]["topics"] = topics
    run_dir = _corpus_path(context, corpus_name) / "analysis" / "topic-modeling" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "output.json").write_text(json.dumps(payload), encoding="utf-8")


def _identify(
    context,
    *,
    corpus_name: str,
    run_id: str,
    previous: Optional[str] = None,
    threshold: Optional[str] = None,
    trends_snapshot: Optional[str] = None,
    output_format: str = "json",
) -> None:
    args = [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "analyze",
        "topic-identity",
        "--current",
        run_id,
        "--format",
        output_format,
    ]
    if previous is not None:
        args.extend(["--previous", previous])
    if threshold is not None:
        args.extend(["--threshold", threshold])
    if trends_snapshot is not None:
        args.extend(["--trends-snapshot", trends_snapshot])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if not hasattr(context, "identity_outputs"):
        context.identity_outputs = {}
        context.identity_stdout = {}
    if result.returncode != 0:
        return
    if output_format == "markdown":
        context.identity_markdown = result.stdout
        return
    context.identity_outputs[run_id] = json.loads(result.stdout)
    context.identity_stdout.setdefault(run_id, []).append(result.stdout)


@when('I identify clusters of run "{run_id}" in corpus "{corpus_name}" with no previous run')
def step_identify_first_run(context, run_id: str, corpus_name: str) -> None:
    _identify(context, corpus_name=corpus_name, run_id=run_id)


@when(
    'I identify clusters of run "{run_id}" in corpus "{corpus_name}" using threshold {threshold} and no previous run'
)
def step_identify_first_run_with_threshold(
    context, run_id: str, corpus_name: str, threshold: str
) -> None:
    _identify(context, corpus_name=corpus_name, run_id=run_id, threshold=threshold)


@when(
    'I identify clusters of run "{run_id}" in corpus "{corpus_name}" against previous run "{previous}" with threshold {threshold}'
)
def step_identify_with_previous(
    context, run_id: str, corpus_name: str, previous: str, threshold: str
) -> None:
    _identify(
        context, corpus_name=corpus_name, run_id=run_id, previous=previous, threshold=threshold
    )


@when(
    'I identify clusters of run "{run_id}" in corpus "{corpus_name}" against previous run "{previous}" as markdown'
)
def step_identify_with_previous_markdown(
    context, run_id: str, corpus_name: str, previous: str
) -> None:
    _identify(
        context,
        corpus_name=corpus_name,
        run_id=run_id,
        previous=previous,
        output_format="markdown",
    )


@when(
    'I identify clusters of run "{run_id}" in corpus "{corpus_name}" with topic trends snapshot "{snapshot_id}"'
)
def step_identify_with_named_trends_snapshot(
    context, run_id: str, corpus_name: str, snapshot_id: str
) -> None:
    _identify(context, corpus_name=corpus_name, run_id=run_id, trends_snapshot=snapshot_id)


@when(
    'I identify clusters of run "{run_id}" in corpus "{corpus_name}" with the topic trends snapshot'
)
def step_identify_with_latest_trends_snapshot(context, run_id: str, corpus_name: str) -> None:
    _identify(
        context,
        corpus_name=corpus_name,
        run_id=run_id,
        trends_snapshot=context.last_topic_trends_output["snapshot_id"],
    )


@when(
    'I identify clusters of the latest topic analysis in corpus "{corpus_name}" with the topic trends snapshot'
)
def step_identify_latest_analysis_with_trends(context, corpus_name: str) -> None:
    _identify(
        context,
        corpus_name=corpus_name,
        run_id=context.last_analysis_output["snapshot"]["snapshot_id"],
        trends_snapshot=context.last_topic_trends_output["snapshot_id"],
    )


def _cluster(context, run_id: str, topic_id: str) -> Dict[str, Any]:
    for cluster in context.identity_outputs[run_id]["clusters"]:
        if cluster["topic_id"] == int(topic_id):
            return cluster
    raise AssertionError(f"No cluster for topic {topic_id} in run {run_id}")


def _uids(context, run_id: str, topics: str) -> List[str]:
    return sorted(_cluster(context, run_id, topic)["uid"] for topic in _names(topics))


@then(
    'cluster of topic "{topic_id}" in run "{run_id}" has the uid of topic "{previous_topic_id}" in run "{previous_run_id}"'
)
def step_cluster_has_uid_of(
    context, topic_id: str, run_id: str, previous_topic_id: str, previous_run_id: str
) -> None:
    current = _cluster(context, run_id, topic_id)["uid"]
    previous = _cluster(context, previous_run_id, previous_topic_id)["uid"]
    assert current == previous, (current, previous)


@then('cluster of topic "{topic_id}" in run "{run_id}" has event "{event}"')
def step_cluster_has_event(context, topic_id: str, run_id: str, event: str) -> None:
    assert _cluster(context, run_id, topic_id)["event"] == event


@then(
    'cluster of topic "{topic_id}" in run "{run_id}" has predecessors from run "{previous_run_id}" topics "{topics}"'
)
def step_cluster_has_predecessors(
    context, topic_id: str, run_id: str, previous_run_id: str, topics: str
) -> None:
    actual = _cluster(context, run_id, topic_id)["predecessor_uids"]
    assert actual == _uids(context, previous_run_id, topics), actual


@then(
    'cluster of topic "{topic_id}" in run "{run_id}" has successors from run "{successor_run_id}" topics "{topics}"'
)
def step_cluster_has_successors(
    context, topic_id: str, run_id: str, successor_run_id: str, topics: str
) -> None:
    actual = _cluster(context, run_id, topic_id)["successor_uids"]
    assert actual == _uids(context, successor_run_id, topics), actual


@then(
    'cluster of topic "{topic_id}" in run "{run_id}" has a uid derived from the run identifier and topic identifier'
)
def step_cluster_uid_is_derived(context, topic_id: str, run_id: str) -> None:
    expected = "cl-" + hash_text(f"{run_id}:{topic_id}")[:12]
    assert _cluster(context, run_id, topic_id)["uid"] == expected


@then(
    'cluster of topic "{topic_id}" in run "{run_id}" has a new uid not used in run "{previous_run_id}"'
)
def step_cluster_has_new_uid(context, topic_id: str, run_id: str, previous_run_id: str) -> None:
    previous = {cluster["uid"] for cluster in context.identity_outputs[previous_run_id]["clusters"]}
    assert _cluster(context, run_id, topic_id)["uid"] not in previous


@then('cluster of topic "{topic_id}" in run "{run_id}" has first seen "{first_seen}"')
def step_cluster_first_seen(context, topic_id: str, run_id: str, first_seen: str) -> None:
    assert _cluster(context, run_id, topic_id)["first_seen"] == first_seen


@then(
    'cluster of topic "{topic_id}" in run "{run_id}" lists {count:d} member items sorted by item identifier'
)
def step_cluster_member_items(context, topic_id: str, run_id: str, count: int) -> None:
    cluster = _cluster(context, run_id, topic_id)
    assert cluster["member_item_count"] == count, cluster
    assert cluster["member_item_ids"] == sorted(cluster["member_item_ids"])
    assert len(cluster["member_item_ids"]) == count


@then('cluster of topic "{topic_id}" in run "{run_id}" has top terms "{terms}"')
def step_cluster_top_terms(context, topic_id: str, run_id: str, terms: str) -> None:
    assert _cluster(context, run_id, topic_id)["top_terms"] == _names(terms)


@then('run "{run_id}" has no previous run and no gone clusters')
def step_run_has_no_previous(context, run_id: str) -> None:
    output = context.identity_outputs[run_id]
    assert output["previous_run_id"] is None, output
    assert output["gone"] == [], output


@then('run "{run_id}" reports no gone clusters')
def step_run_reports_no_gone(context, run_id: str) -> None:
    assert context.identity_outputs[run_id]["gone"] == []


@then('run "{run_id}" reports gone clusters from run "{previous_run_id}" topics "{topics}"')
def step_run_reports_gone(context, run_id: str, previous_run_id: str, topics: str) -> None:
    gone = context.identity_outputs[run_id]["gone"]
    assert sorted(entry["uid"] for entry in gone) == _uids(context, previous_run_id, topics), gone
    assert all(entry["last_seen_run_id"] == previous_run_id for entry in gone), gone


@then('run "{run_id}" event counts are "{counts}"')
def step_run_event_counts(context, run_id: str, counts: str) -> None:
    expected = {}
    for token in counts.split(","):
        name, value = token.split()
        expected[name] = int(value)
    assert context.identity_outputs[run_id]["event_counts"] == expected


@then('the two identity reports of run "{run_id}" are identical')
def step_identity_reports_identical(context, run_id: str) -> None:
    history = context.identity_stdout[run_id]
    assert len(history) >= 2, history
    assert history[-1] == history[-2]


@then(
    'run "{run_id}" reports {documents:d} documents, {outliers:d} outlier documents and {clusters:d} cluster'
)
def step_run_reports_corpus_size(
    context, run_id: str, documents: int, outliers: int, clusters: int
) -> None:
    output = context.identity_outputs[run_id]
    assert output["document_count"] == documents, output
    assert output["outlier_document_count"] == outliers, output
    assert output["cluster_count"] == clusters, output


@then('run "{run_id}" has no cluster for the outlier topic')
def step_run_has_no_outlier_cluster(context, run_id: str) -> None:
    assert all(
        cluster["topic_id"] != -1 for cluster in context.identity_outputs[run_id]["clusters"]
    )


@then(
    'the identity Markdown lists cluster of topic "{topic_id}" in run "{run_id}" with event "{event}"'
)
def step_identity_markdown_lists_cluster(context, topic_id: str, run_id: str, event: str) -> None:
    first_run_cluster = context.identity_outputs["run-a"]["clusters"][0]["uid"]
    matching = [
        line for line in context.identity_markdown.splitlines() if f"`{first_run_cluster}`" in line
    ]
    assert matching and f"| {event} |" in matching[0], context.identity_markdown


@then('the identity report lists {weeks:d} ISO weeks from "{first}" to "{last}"')
def step_identity_report_iso_weeks(context, weeks: int, first: str, last: str) -> None:
    run_id = context.last_analysis_output["snapshot"]["snapshot_id"]
    iso_weeks = context.identity_outputs[run_id]["series_iso_weeks"]
    assert len(iso_weeks) == weeks, iso_weeks
    assert iso_weeks[0] == first and iso_weeks[-1] == last, iso_weeks


@then('the latest topic analysis cluster of topic "{topic_id}" has weekly series "{series}"')
def step_latest_cluster_weekly_series(context, topic_id: str, series: str) -> None:
    run_id = context.last_analysis_output["snapshot"]["snapshot_id"]
    cluster = _cluster(context, run_id, topic_id)
    assert cluster["weekly_series"] == [int(token) for token in series.split(",")], cluster
