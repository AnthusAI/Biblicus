from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import yaml
from behave import then, when

from biblicus.corpus import Corpus
from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


@when(
    'I analyze topic trends in corpus "{corpus_name}" using classifier "{classifier_id}" with windows "{windows}" as of "{as_of}"'
)
def step_analyze_topic_trends(
    context,
    corpus_name: str,
    classifier_id: str,
    windows: str,
    as_of: str,
) -> None:
    corpus = _corpus_path(context, corpus_name)
    topic_modeling_snapshot_id = context.last_analysis_output["snapshot"]["snapshot_id"]
    args = [
        "--corpus",
        str(corpus),
        "analyze",
        "topic-trends",
        "--topic-modeling-snapshot",
        topic_modeling_snapshot_id,
        "--classifier",
        classifier_id,
        "--windows",
        windows,
        "--as-of",
        as_of,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_trends_output = json.loads(result.stdout)


@when(
    'I analyze topic trends in corpus "{corpus_name}" without classifier with windows "{windows}" as of "{as_of}" as markdown'
)
def step_analyze_topic_trends_without_classifier_markdown(
    context,
    corpus_name: str,
    windows: str,
    as_of: str,
) -> None:
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
        windows,
        "--as-of",
        as_of,
        "--format",
        "markdown",
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_trends_markdown = result.stdout
        latest_path = corpus / "analysis" / "topic-governance" / "latest.json"
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        output_path = (
            corpus / "analysis" / "topic-governance" / latest["snapshot_id"] / "output.json"
        )
        context.last_topic_trends_output = json.loads(output_path.read_text(encoding="utf-8"))


@when('I migrate publication dates in corpus "{corpus_name}"')
def step_migrate_publication_dates(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        ["--corpus", str(corpus), "migrate-publication-dates"],
        extra_env=getattr(context, "extra_env", None),
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_publication_date_migration = json.loads(result.stdout)


@then("the topic trend output excludes {count:d} undated item")
@then("the topic trend output excludes {count:d} undated items")
def step_topic_trend_excludes_undated(context, count: int) -> None:
    output = context.last_topic_trends_output
    assert output["summary"]["undated_items"] == count, output
    assert any("dates.published_at" in warning for warning in output["warnings"]), output


@then(
    'the topic trend output ranks discovered topic "{first_topic_id}" above discovered topic "{second_topic_id}" for window "{window}"'
)
def step_topic_trend_ranks_discovered_topics(
    context,
    first_topic_id: str,
    second_topic_id: str,
    window: str,
) -> None:
    output = context.last_topic_trends_output
    ranks: Dict[int, int] = {
        int(row["topic_id"]): int(row["rank"]) for row in output["discovered_topics"]
    }
    assert ranks[int(first_topic_id)] < ranks[int(second_topic_id)], output
    assert output["rank_window"] == window, output


@then("the topic trend output includes canonical and discovered rankings")
def step_topic_trend_includes_rankings(context) -> None:
    output = context.last_topic_trends_output
    assert isinstance(output["canonical_topics"], list), output
    assert isinstance(output["discovered_topics"], list), output
    assert output["canonical_topics"], output
    assert output["discovered_topics"], output


@then('the topic trend output includes a governance proposal for topic "{topic_uid}"')
def step_topic_trend_includes_governance_proposal(context, topic_uid: str) -> None:
    output = context.last_topic_trends_output
    proposals = {proposal["payload"]["topic_uid"]: proposal for proposal in output["proposals"]}
    assert topic_uid in proposals, output
    assert proposals[topic_uid]["status"] == "proposed", proposals[topic_uid]
    assert proposals[topic_uid]["proposal_kind"] == "new-topic", proposals[topic_uid]
    proposals_path = Path(output["artifact_paths"]["proposals"])
    assert proposals_path.is_file(), output


@then('the topic trend Markdown includes label "{label}" for topic "{topic_id}"')
def step_topic_trend_markdown_includes_label(context, label: str, topic_id: str) -> None:
    markdown = getattr(context, "last_topic_trends_markdown", "")
    assert label in markdown, markdown
    assert topic_id in markdown, markdown


@then('the governance proposal for topic "{topic_uid}" has display name "{display_name}"')
def step_governance_proposal_display_name(context, topic_uid: str, display_name: str) -> None:
    output = context.last_topic_trends_output
    proposals = {proposal["payload"]["topic_uid"]: proposal for proposal in output["proposals"]}
    assert topic_uid in proposals, output
    assert proposals[topic_uid]["payload"]["display_name"] == display_name, proposals[topic_uid]


@then('the catalog item titled "{title}" has dates field "{field}" "{value}"')
def step_catalog_item_has_dates_field(context, title: str, field: str, value: str) -> None:
    for corpus_path in context.workdir.iterdir():
        if not corpus_path.is_dir():
            continue
        metadata_path = corpus_path / "metadata" / "catalog.json"
        if not metadata_path.is_file():
            continue
        corpus = Corpus.open(corpus_path)
        for item in corpus.load_catalog().items.values():
            if item.title == title:
                dates = item.dates.model_dump(mode="json") if item.dates is not None else {}
                assert dates.get(field) == value, dates
                return
    raise AssertionError(f"Missing catalog item titled {title!r}")


@then('the sidecar for raw file "{raw_filename}" omits top-level metadata key "{metadata_key}"')
def step_raw_file_sidecar_omits_key(context, raw_filename: str, metadata_key: str) -> None:
    for corpus_path in context.workdir.iterdir():
        if not corpus_path.is_dir():
            continue
        sidecar_path = corpus_path / f"{raw_filename}.biblicus.yml"
        if sidecar_path.is_file():
            payload = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
            assert metadata_key not in payload, payload
            return
    raise AssertionError(f"Missing sidecar for raw file {raw_filename!r}")
