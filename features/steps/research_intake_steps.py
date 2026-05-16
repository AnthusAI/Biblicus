from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import yaml
from behave import given, then, when

from biblicus.corpus import Corpus
from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _fixture_path(context, filename: str) -> Path:
    candidate = Path(filename)
    if candidate.is_absolute():
        return candidate
    workdir_path = (context.workdir / candidate).resolve()
    if workdir_path.exists():
        return workdir_path
    corpus_root = getattr(context, "last_corpus_root", None)
    if corpus_root is not None:
        return (corpus_root / candidate).resolve()
    return workdir_path


def _catalog_title_items(context, corpus_name: str) -> Dict[str, object]:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    return {item.title: item for item in corpus.load_catalog().items.values() if item.title}


def _research_intake_args(
    context,
    *,
    command: str,
    corpus_name: str,
    source_file: str,
    metadata_file: str,
) -> list[str]:
    return [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "research-intake",
        command,
        "--classifier",
        "classifier-lab-v1",
        "--configuration",
        str(_fixture_path(context, "research-intake.yml")),
        "--metadata-file",
        str(_fixture_path(context, metadata_file)),
        str(_fixture_path(context, source_file)),
    ]


@given('a research intake configuration "{configuration_file}" exists')
def step_research_intake_configuration_exists(context, configuration_file: str) -> None:
    payload = {
        "schema_version": 1,
        "required_fields": ["title", "abstract"],
        "metadata_text_fields": ["title", "abstract"],
        "accept_classifier_score": 0.6,
        "accept_corpus_similarity": 0.08,
        "reject_classifier_score": 0.2,
        "reject_corpus_similarity": 0.08,
        "nearest_evidence_count": 3,
    }
    _fixture_path(context, configuration_file).write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


@when(
    'I assess research intake candidate "{source_file}" in corpus "{corpus_name}" with metadata file "{metadata_file}"'
)
def step_assess_research_intake_candidate(
    context, source_file: str, corpus_name: str, metadata_file: str
) -> None:
    result = run_biblicus(
        context,
        _research_intake_args(
            context,
            command="assess",
            corpus_name=corpus_name,
            source_file=source_file,
            metadata_file=metadata_file,
        ),
        extra_env=getattr(context, "extra_env", None),
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_research_intake_output = json.loads(result.stdout)


@when(
    'I research-intake ingest candidate "{source_file}" in corpus "{corpus_name}" with metadata file "{metadata_file}"'
)
def step_research_intake_ingest_candidate(
    context, source_file: str, corpus_name: str, metadata_file: str
) -> None:
    args = _research_intake_args(
        context,
        command="ingest",
        corpus_name=corpus_name,
        source_file=source_file,
        metadata_file=metadata_file,
    )
    args.extend(["--source-uri", f"urn:test:{Path(source_file).stem}"])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_research_intake_output = json.loads(result.stdout)


@when('I list pending research intake items in corpus "{corpus_name}" as JSON')
def step_list_pending_research_intake(context, corpus_name: str) -> None:
    args = [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "research-intake",
        "pending",
        "--format",
        "json",
    ]
    result = run_biblicus(context, args)
    context.last_result = result
    if result.returncode == 0:
        context.last_research_intake_pending = json.loads(result.stdout)


@when('I ingest intake status item "{title}" with status "{status}" into corpus "{corpus_name}"')
def step_ingest_intake_status_item(context, title: str, status: str, corpus_name: str) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    corpus.ingest_item(
        f"{title} agent memory retrieval planning".encode("utf-8"),
        filename=f"{title.lower().replace(' ', '-')}.txt",
        media_type="text/plain",
        title=title,
        tags=["ai-ml-research"],
        metadata={
            "abstract": f"{title} abstract",
            "curation": {
                "intake_status": status,
                "intake_assessment": {"decision": status},
            },
        },
        source_uri=f"urn:test:{title.lower().replace(' ', '-')}",
    )
    corpus.reindex()


@when(
    'I decide research intake item titled "{title}" in corpus "{corpus_name}" as "{decision}" with topic "{topic_uid}"'
)
def step_decide_research_intake_item(
    context, title: str, corpus_name: str, decision: str, topic_uid: str
) -> None:
    item = _catalog_title_items(context, corpus_name)[title]
    args = [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "research-intake",
        "decide",
        "--item-id",
        item.id,
        "--decision",
        decision,
        "--topic-uid",
        topic_uid,
    ]
    result = run_biblicus(context, args)
    context.last_result = result
    if result.returncode == 0:
        context.last_research_intake_output = json.loads(result.stdout)


@when(
    'I decide research intake item titled "{title}" in corpus "{corpus_name}" as "{decision}" with topic "{topic_uid}" adding tags {tags_json}'
)
def step_decide_research_intake_item_with_tags(
    context, title: str, corpus_name: str, decision: str, topic_uid: str, tags_json: str
) -> None:
    item = _catalog_title_items(context, corpus_name)[title]
    tags = json.loads(tags_json)
    assert isinstance(tags, list), tags
    args = [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "research-intake",
        "decide",
        "--item-id",
        item.id,
        "--decision",
        decision,
        "--topic-uid",
        topic_uid,
    ]
    for tag in tags:
        args.extend(["--tags-add", str(tag)])
    result = run_biblicus(context, args)
    context.last_result = result
    if result.returncode == 0:
        context.last_research_intake_output = json.loads(result.stdout)


@when(
    'I decide research intake item titled "{title}" in corpus "{corpus_name}" as "{decision}" with delete'
)
def step_decide_research_intake_item_with_delete(
    context, title: str, corpus_name: str, decision: str
) -> None:
    item = _catalog_title_items(context, corpus_name)[title]
    args = [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "research-intake",
        "decide",
        "--item-id",
        item.id,
        "--decision",
        decision,
        "--delete",
    ]
    result = run_biblicus(context, args)
    context.last_result = result
    if result.returncode == 0:
        context.last_research_intake_output = json.loads(result.stdout)


@then('the research intake decision is "{decision}"')
def step_research_intake_decision_is(context, decision: str) -> None:
    payload = context.last_research_intake_output
    assert payload["decision"] == decision, payload


@then('corpus "{corpus_name}" has {count:d} catalog items')
def step_corpus_has_catalog_items(context, corpus_name: str, count: int) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    assert len(corpus.load_catalog().items) == count


@then('the ingested research intake item has curation status "{status}"')
def step_ingested_research_intake_item_has_status(context, status: str) -> None:
    item_id = context.last_research_intake_output.get("item_id")
    assert item_id, context.last_research_intake_output
    corpus_path = Path(context.last_research_intake_output["corpus_path"])
    item = Corpus.open(corpus_path).get_item(item_id)
    assert item.metadata["curation"]["intake_status"] == status, item.metadata
    assert item.metadata["curation"]["intake_assessment"]["decision"] == status, item.metadata


@then('the research intake pending list includes title "{title}"')
def step_research_intake_pending_list_includes_title(context, title: str) -> None:
    payload = context.last_research_intake_pending
    titles = {item["title"] for item in payload["items"]}
    assert title in titles, payload


@then('the research intake pending list does not include title "{title}"')
def step_research_intake_pending_list_does_not_include_title(context, title: str) -> None:
    payload = context.last_research_intake_pending
    titles = {item["title"] for item in payload["items"]}
    assert title not in titles, payload


@then("the topic modeling text collection has {count:d} documents")
def step_topic_modeling_text_collection_has_documents(context, count: int) -> None:
    payload = context.last_analysis_output
    assert payload["report"]["text_collection"]["documents"] == count, payload


@then('item titled "{title}" in corpus "{corpus_name}" has curation status "{status}"')
def step_item_titled_has_curation_status(
    context, title: str, corpus_name: str, status: str
) -> None:
    item = _catalog_title_items(context, corpus_name)[title]
    assert item.metadata["curation"]["intake_status"] == status, item.metadata


@then('item titled "{title}" in corpus "{corpus_name}" has tags including {tags_json}')
def step_item_titled_has_tags_including(
    context, title: str, corpus_name: str, tags_json: str
) -> None:
    item = _catalog_title_items(context, corpus_name)[title]
    expected = json.loads(tags_json)
    assert isinstance(expected, list), expected
    tags = item.tags
    for tag in expected:
        assert tag in tags, (tag, tags)
