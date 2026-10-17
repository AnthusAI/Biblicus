from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from behave import given, then, when

from biblicus.corpus import Corpus
from features.environment import run_biblicus
from features.steps.topic_modeling_steps import (
    _ensure_fake_bertopic_behavior,
    _install_fake_bertopic_module,
)


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _catalog_title_ids(context, corpus_name: str) -> Dict[str, str]:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    catalog = corpus.load_catalog()
    mapping: Dict[str, str] = {}
    for item in catalog.items.values():
        if item.title:
            mapping[item.title] = item.id
    return mapping


def _title_item_ids(context, corpus_name: str, raw_titles: str) -> List[str]:
    title_ids = _catalog_title_ids(context, corpus_name)
    values: List[str] = []
    for title in [entry.strip() for entry in raw_titles.split(";") if entry.strip()]:
        item_id = title_ids.get(title)
        if item_id is None:
            raise AssertionError(f"Missing item title {title!r}")
        values.append(item_id)
    return values


@given(
    'a topic classifier manifest "{manifest_file}" exists for corpus "{corpus_name}" with topics:'
)
def step_topic_classifier_manifest_exists(context, manifest_file: str, corpus_name: str) -> None:
    topics = []
    for row in context.table:
        topic_uid = row["topic_uid"].strip()
        topics.append(
            {
                "topic_uid": topic_uid,
                "display_name": row["display_name"].strip(),
                "description": f"Seed topic {topic_uid}",
                "seed_item_ids": _title_item_ids(context, corpus_name, row["seed_titles"]),
                "holdout_item_ids": _title_item_ids(
                    context,
                    corpus_name,
                    row["holdout_titles"] if "holdout_titles" in row.headings else "",
                ),
            }
        )
    payload = {
        "schema_version": 1,
        "classifier_id": "classifier-lab-v1",
        "display_name": "Classifier Lab v1",
        "description": "BDD topic classifier seed manifest.",
        "topics": topics,
        "unlabeled_policy": "use_minus_one",
    }
    path = context.workdir / manifest_file
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given(
    'an invalid topic classifier manifest "{manifest_file}" exists for corpus "{corpus_name}" with duplicate topic identifiers'
)
def step_invalid_topic_classifier_manifest_duplicate_uids(
    context, manifest_file: str, corpus_name: str
) -> None:
    title_ids = _catalog_title_ids(context, corpus_name)
    item_id = next(iter(title_ids.values()))
    payload = {
        "schema_version": 1,
        "classifier_id": "classifier-lab-v1",
        "display_name": "Classifier Lab v1",
        "description": "Invalid duplicate topic manifest.",
        "topics": [
            {
                "topic_uid": "duplicate-topic",
                "display_name": "Duplicate One",
                "description": "First duplicate topic.",
                "seed_item_ids": [item_id],
                "holdout_item_ids": [],
            },
            {
                "topic_uid": "duplicate-topic",
                "display_name": "Duplicate Two",
                "description": "Second duplicate topic.",
                "seed_item_ids": [item_id],
                "holdout_item_ids": [],
            },
        ],
        "unlabeled_policy": "use_minus_one",
    }
    path = context.workdir / manifest_file
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given('a topic classifier configuration "{configuration_file}" exists')
def step_topic_classifier_configuration_exists(context, configuration_file: str) -> None:
    payload = {
        "schema_version": 1,
        "text_source": {"min_text_characters": 1},
        "llm_extraction": {"enabled": False},
        "lexical_processing": {
            "enabled": False,
        },
        "bertopic_analysis": {
            "parameters": {"nr_topics": 4},
            "vectorizer": {"ngram_range": [1, 1], "stop_words": "english"},
        },
    }
    path = context.workdir / configuration_file
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given('fake BERTopic classification returns topic "{topic_id}" with score "{score}"')
def step_fake_bertopic_classification_returns(context, topic_id: str, score: str) -> None:
    behavior = _ensure_fake_bertopic_behavior(context)
    behavior.classification_topic_id = int(topic_id)
    behavior.classification_score = float(score)
    behavior.classification_probabilities = None


@given('fake BERTopic classification returns topic "{topic_id}" with probabilities "{scores}"')
def step_fake_bertopic_classification_returns_probabilities(
    context, topic_id: str, scores: str
) -> None:
    behavior = _ensure_fake_bertopic_behavior(context)
    behavior.classification_topic_id = int(topic_id)
    behavior.classification_score = None
    probabilities: Dict[int, float] = {}
    for token in scores.split(","):
        if not token.strip():
            continue
        raw_topic_id, raw_score = token.split(":", 1)
        probabilities[int(raw_topic_id.strip())] = float(raw_score.strip())
    behavior.classification_probabilities = probabilities


@given("a fake BERTopic library assigns topics by document text with keywords:")
def step_fake_bertopic_assigns_topics_by_document_text(context) -> None:
    _install_fake_bertopic_module(context, use_fake_marker=True)
    behavior = _ensure_fake_bertopic_behavior(context)
    behavior.topic_assignments = []
    behavior.classification_probabilities = None
    behavior.classification_score = None
    behavior.topic_assignment_rules = []
    topic_keywords: Dict[int, List[tuple[str, float]]] = {}
    for row in context.table:
        phrase = row["text"].strip()
        topic_id = int(row["topic_id"].strip())
        behavior.topic_assignment_rules.append((phrase, topic_id))
        raw_keywords = row["keywords"].strip()
        keywords = [keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip()]
        topic_keywords[topic_id] = [
            (keyword, 1.0 - (index * 0.1)) for index, keyword in enumerate(keywords)
        ]
    behavior.topic_keywords = topic_keywords


@when(
    'I train a topic classifier in corpus "{corpus_name}" using manifest "{manifest_file}" and configuration "{configuration_file}"'
)
def step_train_topic_classifier(
    context,
    corpus_name: str,
    manifest_file: str,
    configuration_file: str,
) -> None:
    corpus = _corpus_path(context, corpus_name)
    snapshot_ref = f"{context.last_extractor_id}:{context.last_extraction_snapshot_id}"
    args = [
        "--corpus",
        str(corpus),
        "topic-classifier",
        "train",
        "--manifest",
        str(context.workdir / manifest_file),
        "--configuration",
        str(context.workdir / configuration_file),
        "--configuration-name",
        "bdd-topic-classifier",
        "--extraction-snapshot",
        snapshot_ref,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_output = json.loads(result.stdout)


@when(
    'I classify item titled "{title}" in corpus "{corpus_name}" using classifier "{classifier_id}" with review threshold "{review_threshold}"'
)
def step_classify_topic_classifier_item(
    context,
    title: str,
    corpus_name: str,
    classifier_id: str,
    review_threshold: str,
) -> None:
    item_id = _catalog_title_ids(context, corpus_name)[title]
    corpus = _corpus_path(context, corpus_name)
    args = [
        "--corpus",
        str(corpus),
        "topic-classifier",
        "classify",
        "--classifier",
        classifier_id,
        "--item-id",
        item_id,
        "--review-threshold",
        review_threshold,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_prediction = json.loads(result.stdout)


@when(
    'I classify item titled "{title}" in corpus "{corpus_name}" using classifier "{classifier_id}" with top-k "{top_k}" and review threshold "{review_threshold}"'
)
def step_classify_topic_classifier_item_with_top_k(
    context,
    title: str,
    corpus_name: str,
    classifier_id: str,
    review_threshold: str,
    top_k: str,
) -> None:
    item_id = _catalog_title_ids(context, corpus_name)[title]
    corpus = _corpus_path(context, corpus_name)
    args = [
        "--corpus",
        str(corpus),
        "topic-classifier",
        "classify",
        "--classifier",
        classifier_id,
        "--item-id",
        item_id,
        "--review-threshold",
        review_threshold,
        "--top-k",
        top_k,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_prediction = json.loads(result.stdout)


@when(
    'I project classifier "{classifier_id}" from corpus "{authority_corpus_name}" onto item titled "{title}" in corpus "{target_corpus_name}" with review threshold "{review_threshold}"'
)
def step_project_topic_classifier_item(
    context,
    classifier_id: str,
    authority_corpus_name: str,
    title: str,
    target_corpus_name: str,
    review_threshold: str,
) -> None:
    item_id = _catalog_title_ids(context, target_corpus_name)[title]
    snapshot_ref = f"{context.last_extractor_id}:{context.last_extraction_snapshot_id}"
    args = [
        "topic-classifier",
        "project",
        "--classifier-corpus",
        str(_corpus_path(context, authority_corpus_name)),
        "--target-corpus",
        str(_corpus_path(context, target_corpus_name)),
        "--classifier",
        classifier_id,
        "--extraction-snapshot",
        snapshot_ref,
        "--item-id",
        item_id,
        "--review-threshold",
        review_threshold,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_projection = json.loads(result.stdout)


@when(
    'I project classifier "{classifier_id}" from corpus "{authority_corpus_name}" onto item titled "{title}" in corpus "{target_corpus_name}" as markdown with top-k "{top_k}"'
)
def step_project_topic_classifier_item_markdown(
    context,
    classifier_id: str,
    authority_corpus_name: str,
    title: str,
    target_corpus_name: str,
    top_k: str,
) -> None:
    item_id = _catalog_title_ids(context, target_corpus_name)[title]
    snapshot_ref = f"{context.last_extractor_id}:{context.last_extraction_snapshot_id}"
    args = [
        "topic-classifier",
        "project",
        "--classifier-corpus",
        str(_corpus_path(context, authority_corpus_name)),
        "--target-corpus",
        str(_corpus_path(context, target_corpus_name)),
        "--classifier",
        classifier_id,
        "--extraction-snapshot",
        snapshot_ref,
        "--item-id",
        item_id,
        "--top-k",
        top_k,
        "--format",
        "markdown",
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result


@when(
    'I record projection of classifier "{classifier_id}" from corpus "{authority_corpus_name}" onto item titled "{title}" in corpus "{target_corpus_name}"'
)
def step_record_topic_classifier_projection(
    context,
    classifier_id: str,
    authority_corpus_name: str,
    title: str,
    target_corpus_name: str,
) -> None:
    item_id = _catalog_title_ids(context, target_corpus_name)[title]
    snapshot_ref = f"{context.last_extractor_id}:{context.last_extraction_snapshot_id}"
    args = [
        "topic-classifier",
        "project",
        "--classifier-corpus",
        str(_corpus_path(context, authority_corpus_name)),
        "--target-corpus",
        str(_corpus_path(context, target_corpus_name)),
        "--classifier",
        classifier_id,
        "--extraction-snapshot",
        snapshot_ref,
        "--item-id",
        item_id,
        "--record",
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_projection = json.loads(result.stdout)


@when(
    'I project classifier "{classifier_id}" from corpus "{authority_corpus_name}" onto all items in corpus "{target_corpus_name}"'
)
def step_project_topic_classifier_all_items(
    context,
    classifier_id: str,
    authority_corpus_name: str,
    target_corpus_name: str,
) -> None:
    snapshot_ref = f"{context.last_extractor_id}:{context.last_extraction_snapshot_id}"
    args = [
        "topic-classifier",
        "project",
        "--classifier-corpus",
        str(_corpus_path(context, authority_corpus_name)),
        "--target-corpus",
        str(_corpus_path(context, target_corpus_name)),
        "--classifier",
        classifier_id,
        "--extraction-snapshot",
        snapshot_ref,
        "--all",
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_projection = json.loads(result.stdout)


@when(
    'I project classifier "{classifier_id}" from corpus "{authority_corpus_name}" onto items titled "{titles}" in corpus "{target_corpus_name}"'
)
def step_project_topic_classifier_repeated_items(
    context,
    classifier_id: str,
    authority_corpus_name: str,
    titles: str,
    target_corpus_name: str,
) -> None:
    title_ids = _catalog_title_ids(context, target_corpus_name)
    snapshot_ref = f"{context.last_extractor_id}:{context.last_extraction_snapshot_id}"
    args = [
        "topic-classifier",
        "project",
        "--classifier-corpus",
        str(_corpus_path(context, authority_corpus_name)),
        "--target-corpus",
        str(_corpus_path(context, target_corpus_name)),
        "--classifier",
        classifier_id,
        "--extraction-snapshot",
        snapshot_ref,
    ]
    for title in [entry.strip() for entry in titles.split(";") if entry.strip()]:
        args.extend(["--item-id", title_ids[title]])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_projection = json.loads(result.stdout)


@when(
    'I project classifier "{classifier_id}" from corpus "{authority_corpus_name}" onto all items and item id "{item_id}" in corpus "{target_corpus_name}"'
)
def step_project_topic_classifier_ambiguous_selection(
    context,
    classifier_id: str,
    authority_corpus_name: str,
    item_id: str,
    target_corpus_name: str,
) -> None:
    args = [
        "topic-classifier",
        "project",
        "--classifier-corpus",
        str(_corpus_path(context, authority_corpus_name)),
        "--target-corpus",
        str(_corpus_path(context, target_corpus_name)),
        "--classifier",
        classifier_id,
        "--extraction-snapshot",
        "pipeline:example-snapshot",
        "--all",
        "--item-id",
        item_id,
    ]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@when(
    'I project classifier "{classifier_id}" from corpus "{authority_corpus_name}" onto item titled "{title}" in corpus "{target_corpus_name}" with missing extraction snapshot'
)
def step_project_topic_classifier_missing_extraction_snapshot(
    context,
    classifier_id: str,
    authority_corpus_name: str,
    title: str,
    target_corpus_name: str,
) -> None:
    item_id = _catalog_title_ids(context, target_corpus_name)[title]
    args = [
        "topic-classifier",
        "project",
        "--classifier-corpus",
        str(_corpus_path(context, authority_corpus_name)),
        "--target-corpus",
        str(_corpus_path(context, target_corpus_name)),
        "--classifier",
        classifier_id,
        "--extraction-snapshot",
        "pipeline:missing-snapshot",
        "--item-id",
        item_id,
    ]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@when(
    'I review candidate items in corpus "{corpus_name}" using classifier "{classifier_id}" with candidate tag "{candidate_tag}" and proposed topic "{proposed_topic_uid}"'
)
def step_review_topic_classifier_candidate_batch(
    context,
    corpus_name: str,
    classifier_id: str,
    candidate_tag: str,
    proposed_topic_uid: str,
) -> None:
    corpus = _corpus_path(context, corpus_name)
    snapshot_ref = f"{context.last_extractor_id}:{context.last_extraction_snapshot_id}"
    topic_modeling_snapshot_id = context.last_analysis_output["snapshot"]["snapshot_id"]
    args = [
        "--corpus",
        str(corpus),
        "topic-classifier",
        "review-batch",
        "--classifier",
        classifier_id,
        "--extraction-snapshot",
        snapshot_ref,
        "--topic-modeling-snapshot",
        topic_modeling_snapshot_id,
        "--candidate-tag",
        candidate_tag,
        "--proposed-topic-uid",
        proposed_topic_uid,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_batch_review = json.loads(result.stdout)


@when(
    'I draft topic classifier manifest "{output_file}" from "{base_file}" with topic "{topic_uid}" using seed title "{seed_title}"'
)
def step_draft_topic_classifier_manifest(
    context,
    output_file: str,
    base_file: str,
    topic_uid: str,
    seed_title: str,
) -> None:
    item_id = _catalog_title_ids(context, "draft-lab")[seed_title]
    args = [
        "topic-classifier",
        "draft-manifest",
        "--base-manifest",
        str(context.workdir / base_file),
        "--output",
        str(context.workdir / output_file),
        "--topic-uid",
        topic_uid,
        "--topic-display-name",
        "Automated Scientific Discovery",
        "--topic-description",
        "Reviewed articles about agents and systems that automate scientific research.",
        "--seed-item-id",
        item_id,
    ]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    context.last_result = result
    if result.returncode == 0:
        context.last_topic_classifier_draft_manifest = json.loads(result.stdout)


@then(
    'the fake BERTopic training labels contain {count_a:d} label "{label_a}", {count_b:d} label "{label_b}", and {count_c:d} labels "{label_c}"'
)
def step_fake_bertopic_training_labels_contain(
    context,
    count_a: int,
    label_a: str,
    count_b: int,
    label_b: str,
    count_c: int,
    label_c: str,
) -> None:
    behavior = _ensure_fake_bertopic_behavior(context)
    counts = Counter(str(label) for label in behavior.last_y)
    assert counts[label_a] == count_a, behavior.last_y
    assert counts[label_b] == count_b, behavior.last_y
    assert counts[label_c] == count_c, behavior.last_y


@then(
    'the fake BERTopic training labels contain {count_a:d} label "{label_a}", {count_b:d} labels "{label_b}", and {count_c:d} labels "{label_c}"'
)
def step_fake_bertopic_training_labels_contain_plural_middle(
    context,
    count_a: int,
    label_a: str,
    count_b: int,
    label_b: str,
    count_c: int,
    label_c: str,
) -> None:
    step_fake_bertopic_training_labels_contain(
        context,
        count_a,
        label_a,
        count_b,
        label_b,
        count_c,
        label_c,
    )


@then('the topic classifier map links topic "{topic_uid}" to BERTopic topics "{topic_ids}"')
def step_topic_classifier_map_links_topic(context, topic_uid: str, topic_ids: str) -> None:
    topic_map_path = Path(context.last_topic_classifier_output["topic_map_path"])
    payload = json.loads(topic_map_path.read_text(encoding="utf-8"))
    topic = next(entry for entry in payload["topics"] if entry["topic_uid"] == topic_uid)
    expected = [int(token.strip()) for token in topic_ids.split(",") if token.strip()]
    assert topic["bertopic_topic_ids"] == expected, payload


@then('the topic classifier map reports discovered BERTopic topic "{topic_id}"')
def step_topic_classifier_map_reports_discovered(context, topic_id: str) -> None:
    topic_map_path = Path(context.last_topic_classifier_output["topic_map_path"])
    payload = json.loads(topic_map_path.read_text(encoding="utf-8"))
    discovered = {int(entry["bertopic_topic_id"]) for entry in payload["discovered"]}
    assert int(topic_id) in discovered, payload


@then(
    'the topic classifier prediction has topic_uid "{topic_uid}" and review_recommended "{review_recommended}"'
)
def step_topic_classifier_prediction_has_review_status(
    context, topic_uid: str, review_recommended: str
) -> None:
    prediction = context.last_topic_classifier_prediction
    assert prediction["topic_uid"] == topic_uid, prediction
    expected_review = review_recommended.lower() == "true"
    assert prediction["review_recommended"] is expected_review, prediction


@then(
    'the topic classifier prediction has no primary topic and review_recommended "{review_recommended}"'
)
def step_topic_classifier_prediction_has_no_primary_topic(context, review_recommended: str) -> None:
    prediction = context.last_topic_classifier_prediction
    assert prediction["topic_uid"] is None, prediction
    assert prediction["display_name"] is None, prediction
    expected_review = review_recommended.lower() == "true"
    assert prediction["review_recommended"] is expected_review, prediction


@then('the topic classifier prediction has ranked candidates "{topic_uids}"')
def step_topic_classifier_prediction_has_ranked_candidates(context, topic_uids: str) -> None:
    prediction = context.last_topic_classifier_prediction
    expected = [token.strip() for token in topic_uids.split(",") if token.strip()]
    actual = [candidate["topic_uid"] for candidate in prediction["topic_candidates"]]
    assert actual == expected, prediction


@then("the topic classifier projection includes {count:d} item")
@then("the topic classifier projection includes {count:d} items")
def step_topic_classifier_projection_count(context, count: int) -> None:
    payload = context.last_topic_classifier_projection
    assert payload["summary"]["projected_items"] == count, payload
    assert len(payload["items"]) == count, payload


@then("the topic classifier projection skips {count:d} item")
@then("the topic classifier projection skips {count:d} items")
def step_topic_classifier_projection_skipped_count(context, count: int) -> None:
    payload = context.last_topic_classifier_projection
    assert payload["summary"]["skipped_items"] == count, payload
    assert len(payload["skipped_items"]) == count, payload


@then(
    'the topic classifier projection skipped item titled "{title}" reason includes "{expected_text}"'
)
def step_topic_classifier_projection_skipped_reason(
    context, title: str, expected_text: str
) -> None:
    payload = context.last_topic_classifier_projection
    for skipped_item in payload["skipped_items"]:
        if skipped_item["title"] == title:
            assert expected_text in skipped_item["reason"], skipped_item
            return
    raise AssertionError(f"Missing skipped projection item titled {title!r}")


@then(
    'the topic classifier projection item titled "{title}" has topic_uid "{topic_uid}" and review_recommended "{review_recommended}"'
)
def step_topic_classifier_projection_item_has_review_status(
    context, title: str, topic_uid: str, review_recommended: str
) -> None:
    item = _projection_item_by_title(context.last_topic_classifier_projection, title)
    assert item["topic_uid"] == topic_uid, item
    expected_review = review_recommended.lower() == "true"
    assert item["review_recommended"] is expected_review, item


@then(
    'the target corpus "{target_corpus_name}" has a recorded projection for item titled "{title}" using authority corpus "{authority_corpus_name}"'
)
def step_target_corpus_has_recorded_projection(
    context, target_corpus_name: str, title: str, authority_corpus_name: str
) -> None:
    item_id = _catalog_title_ids(context, target_corpus_name)[title]
    record = _recorded_projection_for_item(context, target_corpus_name, item_id)
    assert record is not None
    assert record["item_id"] == item_id, record
    assert (
        record["classifier_corpus_uri"] == _corpus_path(context, authority_corpus_name).as_uri()
    ), record
    assert record["target_corpus_uri"] == _corpus_path(context, target_corpus_name).as_uri(), record
    assert record["recorded"] is True, record


@then(
    'the target corpus "{target_corpus_name}" recorded projection for item titled "{title}" has ranked candidates "{topic_uids}"'
)
def step_recorded_projection_has_ranked_candidates(
    context, target_corpus_name: str, title: str, topic_uids: str
) -> None:
    item_id = _catalog_title_ids(context, target_corpus_name)[title]
    record = _recorded_projection_for_item(context, target_corpus_name, item_id)
    assert record is not None
    expected = [token.strip() for token in topic_uids.split(",") if token.strip()]
    actual = [candidate["topic_uid"] for candidate in record["topic_candidates"]]
    assert actual == expected, record


@then(
    'the authority corpus "{authority_corpus_name}" has no recorded projection for item titled "{title}"'
)
def step_authority_corpus_has_no_recorded_projection(
    context, authority_corpus_name: str, title: str
) -> None:
    for corpus_path in context.workdir.iterdir():
        if not corpus_path.is_dir():
            continue
        try:
            item_id = _catalog_title_ids(context, corpus_path.name).get(title)
        except FileNotFoundError:
            continue
        if item_id is None:
            continue
        record = _recorded_projection_for_item(context, authority_corpus_name, item_id)
        assert record is None, record


@then("the topic classifier batch review includes {count:d} candidate item")
@then("the topic classifier batch review includes {count:d} candidate items")
def step_topic_classifier_batch_review_count(context, count: int) -> None:
    payload = context.last_topic_classifier_batch_review
    assert payload["summary"]["candidate_items"] == count, payload
    assert len(payload["items"]) == count, payload


@then(
    'the topic classifier batch review item titled "{title}" has proposed topic "{proposed_topic_uid}" and unsupervised topic "{topic_id}"'
)
def step_topic_classifier_batch_review_item_has_topics(
    context,
    title: str,
    proposed_topic_uid: str,
    topic_id: str,
) -> None:
    payload = context.last_topic_classifier_batch_review
    item = _batch_review_item_by_title(payload, title)
    assert item["proposed_topic_uid"] == proposed_topic_uid, item
    assert item["unsupervised_topic_id"] == int(topic_id), item


@then('the topic classifier batch review summary flag "{flag}" is "{expected}"')
def step_topic_classifier_batch_review_flag(context, flag: str, expected: str) -> None:
    payload = context.last_topic_classifier_batch_review
    flags = payload["summary"]["topic_management_flags"]
    expected_value = expected.lower() == "true"
    assert flags[flag] is expected_value, payload


@then('topic classifier manifest "{manifest_file}" does not list item titled "{title}" as a seed')
def step_topic_classifier_manifest_does_not_list_seed(
    context, manifest_file: str, title: str
) -> None:
    item_id = _find_title_item_id(context, title)
    payload = _load_manifest_payload(context, manifest_file)
    seed_ids = {
        seed_item_id for topic in payload["topics"] for seed_item_id in topic["seed_item_ids"]
    }
    assert item_id not in seed_ids, payload


@then('topic classifier manifest "{manifest_file}" includes topic "{topic_uid}"')
def step_topic_classifier_manifest_includes_topic(
    context, manifest_file: str, topic_uid: str
) -> None:
    payload = _load_manifest_payload(context, manifest_file)
    topic_uids = {topic["topic_uid"] for topic in payload["topics"]}
    assert topic_uid in topic_uids, payload


@then('topic classifier manifest "{manifest_file}" does not include topic "{topic_uid}"')
def step_topic_classifier_manifest_does_not_include_topic(
    context, manifest_file: str, topic_uid: str
) -> None:
    payload = _load_manifest_payload(context, manifest_file)
    topic_uids = {topic["topic_uid"] for topic in payload["topics"]}
    assert topic_uid not in topic_uids, payload


@then('the AI-ML research canonical topic classifier manifest does not include topic "{topic_uid}"')
def step_ai_ml_research_manifest_does_not_include_topic(context, topic_uid: str) -> None:
    path = (
        Path.cwd()
        / "corpora"
        / "AI-ML-research"
        / "metadata"
        / "topic-classifiers"
        / "ai-ml-research"
        / "seed-manifest.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    topic_uids = {topic["topic_uid"] for topic in payload["topics"]}
    assert topic_uid not in topic_uids, payload


@then('standard output includes "{expected}"')
def step_standard_output_includes(context, expected: str) -> None:
    assert expected in context.last_result.stdout, context.last_result.stdout


def _batch_review_item_by_title(payload: dict[str, object], title: str) -> dict[str, object]:
    for item in payload["items"]:
        if item["title"] == title:
            return item
    raise AssertionError(f"Missing batch review item titled {title!r}")


def _projection_item_by_title(payload: dict[str, object], title: str) -> dict[str, object]:
    for item in payload["items"]:
        if item["title"] == title:
            return item
    raise AssertionError(f"Missing projected item titled {title!r}")


def _recorded_projection_for_item(
    context, corpus_name: str, item_id: str
) -> Optional[dict[str, object]]:
    path = (
        _corpus_path(context, corpus_name)
        / "metadata"
        / "topic-classifiers"
        / "classifier-lab-v1"
        / "predictions.jsonl"
    )
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("item_id") == item_id:
            return payload
    return None


def _find_title_item_id(context, title: str) -> Optional[str]:
    for corpus_path in context.workdir.iterdir():
        if not corpus_path.is_dir():
            continue
        metadata_path = corpus_path / "metadata" / "catalog.json"
        if not metadata_path.is_file():
            continue
        corpus = Corpus.open(corpus_path)
        for item in corpus.load_catalog().items.values():
            if item.title == title:
                return item.id
    raise AssertionError(f"Missing item title {title!r}")


def _load_manifest_payload(context, manifest_file: str) -> dict[str, object]:
    path = context.workdir / manifest_file
    return json.loads(path.read_text(encoding="utf-8"))
