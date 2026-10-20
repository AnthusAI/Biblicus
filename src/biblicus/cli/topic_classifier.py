"""
Topic classifier commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from ..api import validate_request
from ..corpus import Corpus
from ..models import (
    parse_extraction_snapshot_reference,
)
from .common import (
    _add_common_corpus_arg,
    _open_corpus_from_arguments,
    _parse_tags,
    _resolve_extraction_snapshot_for_analysis,
)


def cmd_topic_classifier_train(arguments: argparse.Namespace) -> int:
    """
    Train a topic classifier model version.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import TopicClassifierTrainRequest, topic_classifier_train

    corpus = _open_corpus_from_arguments(arguments)
    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Topic classifier training",
    )
    request = validate_request(
        TopicClassifierTrainRequest,
        "topic-classifier train",
        corpus_path=str(corpus.root),
        manifest_path=arguments.manifest,
        configuration_paths=arguments.configuration,
        overrides=arguments.override,
        configuration_name=arguments.configuration_name,
        extraction_snapshot=extraction_snapshot,
    )
    print(topic_classifier_train(request).model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_classify(arguments: argparse.Namespace) -> int:
    """
    Classify an existing corpus item with a topic classifier.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..topic_classifier import classify_topic_classifier_item

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = classify_topic_classifier_item(
        corpus=corpus,
        classifier_id=arguments.classifier,
        item_id=arguments.item_id,
        review_threshold=arguments.review_threshold,
        top_k=arguments.top_k,
        record=False,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_project(arguments: argparse.Namespace) -> int:
    """
    Project a topic classifier from an authority corpus onto a target corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import TopicClassifierProjectRequest, topic_classifier_project

    request = validate_request(
        TopicClassifierProjectRequest,
        "topic-classifier project",
        classifier_corpus_path=arguments.classifier_corpus,
        target_corpus_path=arguments.target_corpus,
        classifier_id=arguments.classifier,
        extraction_snapshot=parse_extraction_snapshot_reference(arguments.extraction_snapshot),
        project_all=arguments.project_all,
        item_ids=arguments.item_id or [],
        review_threshold=arguments.review_threshold,
        top_k=arguments.top_k,
        record=arguments.record,
    )
    output = topic_classifier_project(request)
    if arguments.format == "markdown":
        print(_topic_classifier_projection_markdown(output.model_dump(mode="json")))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_ingest_classify(arguments: argparse.Namespace) -> int:
    """
    Ingest one source and classify it with a topic classifier.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..topic_classifier import ingest_and_classify_topic_classifier_item

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    tags = _parse_tags(arguments.tags, arguments.tag)
    output = ingest_and_classify_topic_classifier_item(
        corpus=corpus,
        classifier_id=arguments.classifier,
        source=arguments.source,
        tags=tags,
        review_threshold=arguments.review_threshold,
        top_k=arguments.top_k,
        record=arguments.record,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_review_batch(arguments: argparse.Namespace) -> int:
    """
    Build a blind batch review table for candidate topic classifier items.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..models import parse_extraction_snapshot_reference
    from ..topic_classifier import build_topic_classifier_batch_review

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = build_topic_classifier_batch_review(
        corpus=corpus,
        classifier_id=arguments.classifier,
        extraction_snapshot=parse_extraction_snapshot_reference(arguments.extraction_snapshot),
        topic_modeling_snapshot_id=arguments.topic_modeling_snapshot,
        candidate_tag=arguments.candidate_tag,
        proposed_topic_uid=arguments.proposed_topic_uid,
        review_threshold=arguments.review_threshold,
        record=arguments.record,
    )
    if arguments.format == "markdown":
        print(_topic_classifier_batch_review_markdown(output.model_dump(mode="json")))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_draft_manifest(arguments: argparse.Namespace) -> int:
    """
    Draft a reviewed seed manifest without mutating the baseline manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..topic_classifier import draft_topic_classifier_manifest

    output = draft_topic_classifier_manifest(
        base_manifest_path=Path(arguments.base_manifest),
        output_path=Path(arguments.output),
        classifier_id=arguments.classifier_id,
        display_name=arguments.display_name,
        description=arguments.description,
        topic_uid=arguments.topic_uid,
        topic_display_name=arguments.topic_display_name,
        topic_description=arguments.topic_description,
        seed_item_ids=arguments.seed_item_id or [],
        holdout_item_ids=arguments.holdout_item_id or [],
    )
    print(output.model_dump_json(indent=2))
    return 0


def _topic_classifier_batch_review_markdown(payload: Dict[str, Any]) -> str:
    """
    Render a topic classifier batch review payload as a Markdown table.

    :param payload: Batch review payload.
    :type payload: dict[str, Any]
    :return: Markdown report.
    :rtype: str
    """
    lines = [
        f"# Topic Classifier Batch Review: {payload['classifier_id']}",
        "",
        f"- Model version: `{payload['model_version']}`",
        f"- Candidate items: {payload['summary']['candidate_items']}",
        f"- Review recommended: {payload['summary']['review_recommended_items']}",
        "",
        "| Item ID | Title | Proposed | Classifier Topic | Score | Review | Discovery Topic | Keywords | Decision |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["items"]:
        keywords = ", ".join(
            str(keyword.get("keyword", "")) for keyword in item.get("unsupervised_keywords", [])[:5]
        )
        score = item.get("classifier_score")
        score_text = "" if score is None else f"{float(score):.3f}"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["item_id"]),
                    _markdown_table_cell(item.get("title") or ""),
                    _markdown_table_cell(item.get("proposed_topic_uid") or ""),
                    _markdown_table_cell(item.get("classifier_topic_uid") or "discovered"),
                    score_text,
                    str(item["review_recommended"]).lower(),
                    (
                        ""
                        if item.get("unsupervised_topic_id") is None
                        else str(item["unsupervised_topic_id"])
                    ),
                    _markdown_table_cell(keywords),
                    _markdown_table_cell(item.get("reviewer_decision") or "pending"),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _topic_classifier_projection_markdown(payload: Dict[str, Any]) -> str:
    """
    Render a topic classifier projection payload as a Markdown table.

    :param payload: Projection payload.
    :type payload: dict[str, Any]
    :return: Markdown report.
    :rtype: str
    """
    lines = [
        f"# Topic Classifier Projection: {payload['classifier_id']}",
        "",
        f"- Model version: `{payload['model_version']}`",
        f"- Classifier corpus: `{payload['classifier_corpus_uri']}`",
        f"- Target corpus: `{payload['target_corpus_uri']}`",
        f"- Projected items: {payload['summary']['projected_items']}",
        f"- Skipped items: {payload['summary']['skipped_items']}",
        f"- Review recommended: {payload['summary']['review_recommended_items']}",
        "",
        "| Item ID | Title | Topic | Score | Review | Candidates | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["items"]:
        score = item.get("score")
        score_text = "" if score is None else f"{float(score):.3f}"
        candidates = _topic_classifier_candidates_markdown(item.get("topic_candidates") or [])
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["item_id"]),
                    _markdown_table_cell(item.get("title") or ""),
                    _markdown_table_cell(item.get("topic_uid") or "review"),
                    score_text,
                    str(item["review_recommended"]).lower(),
                    _markdown_table_cell(candidates),
                    _markdown_table_cell(item.get("source_uri") or ""),
                ]
            )
            + " |"
        )
    if payload.get("skipped_items"):
        lines.extend(
            [
                "",
                "## Skipped Items",
                "",
                "| Item ID | Title | Reason |",
                "| --- | --- | --- |",
            ]
        )
        for item in payload["skipped_items"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(item["item_id"]),
                        _markdown_table_cell(item.get("title") or ""),
                        _markdown_table_cell(item["reason"]),
                    ]
                )
                + " |"
            )
    return "\n".join(lines)


def _topic_classifier_candidates_markdown(candidates: object) -> str:
    """
    Render ranked topic candidates for a compact Markdown table cell.

    :param candidates: Candidate payloads.
    :type candidates: object
    :return: Compact ranked candidate text.
    :rtype: str
    """
    if not isinstance(candidates, list):
        return ""
    values: List[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        label = str(candidate.get("topic_uid") or "discovered")
        score = candidate.get("score")
        score_text = "" if score is None else f" {float(score):.3f}"
        values.append(f"{label}{score_text}")
    return "; ".join(values)


def _markdown_table_cell(value: str) -> str:
    """
    Escape text for a Markdown table cell.

    :param value: Cell value.
    :type value: str
    :return: Escaped cell value.
    :rtype: str
    """
    return value.replace("|", "\\|").replace("\n", " ")


def register_topic_classifier_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the topic classifier commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_topic_classifier = subparsers.add_parser(
        "topic-classifier", help="Train and use semi-supervised topic classifiers."
    )
    topic_classifier_sub = p_topic_classifier.add_subparsers(
        dest="topic_classifier_command", required=True
    )

    p_topic_classifier_train = topic_classifier_sub.add_parser(
        "train", help="Train a topic classifier model version."
    )
    _add_common_corpus_arg(p_topic_classifier_train)
    p_topic_classifier_train.add_argument(
        "--manifest",
        required=True,
        help="Path to topic classifier seed-manifest.json.",
    )
    p_topic_classifier_train.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to topic classifier configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_topic_classifier_train.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_topic_classifier_train.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    p_topic_classifier_train.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_topic_classifier_train.set_defaults(func=cmd_topic_classifier_train, typed_command="topic-classifier train")

    p_topic_classifier_classify = topic_classifier_sub.add_parser(
        "classify", help="Classify an existing corpus item."
    )
    _add_common_corpus_arg(p_topic_classifier_classify)
    p_topic_classifier_classify.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_topic_classifier_classify.add_argument(
        "--item-id",
        required=True,
        help="Corpus item identifier to classify.",
    )
    p_topic_classifier_classify.add_argument(
        "--review-threshold",
        type=float,
        default=0.35,
        help="Minimum confidence score before review is recommended.",
    )
    p_topic_classifier_classify.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum ranked topic candidates to include.",
    )
    p_topic_classifier_classify.set_defaults(func=cmd_topic_classifier_classify)

    p_topic_classifier_project = topic_classifier_sub.add_parser(
        "project",
        help="Project a classifier from an authority corpus onto a target corpus.",
    )
    p_topic_classifier_project.add_argument(
        "--classifier-corpus",
        required=True,
        help="Corpus path or uniform resource identifier containing classifier artifacts.",
    )
    p_topic_classifier_project.add_argument(
        "--target-corpus",
        required=True,
        help="Corpus path or uniform resource identifier containing target items.",
    )
    p_topic_classifier_project.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_topic_classifier_project.add_argument(
        "--extraction-snapshot",
        required=True,
        help="Target corpus extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_topic_classifier_project.add_argument(
        "--all",
        action="store_true",
        dest="project_all",
        help="Project the classifier onto every target corpus item.",
    )
    p_topic_classifier_project.add_argument(
        "--item-id",
        action="append",
        default=[],
        help="Repeatable target item identifier to project.",
    )
    p_topic_classifier_project.add_argument(
        "--review-threshold",
        type=float,
        default=0.35,
        help="Minimum confidence score before review is recommended.",
    )
    p_topic_classifier_project.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum ranked topic candidates to include.",
    )
    p_topic_classifier_project.add_argument(
        "--record",
        action="store_true",
        help="Persist projection predictions as audit records in the target corpus.",
    )
    p_topic_classifier_project.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_topic_classifier_project.set_defaults(func=cmd_topic_classifier_project, typed_command="topic-classifier project")

    p_topic_classifier_ingest = topic_classifier_sub.add_parser(
        "ingest-classify", help="Ingest one source and classify it immediately."
    )
    _add_common_corpus_arg(p_topic_classifier_ingest)
    p_topic_classifier_ingest.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_topic_classifier_ingest.add_argument(
        "--review-threshold",
        type=float,
        default=0.35,
        help="Minimum confidence score before review is recommended.",
    )
    p_topic_classifier_ingest.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum ranked topic candidates to include.",
    )
    p_topic_classifier_ingest.add_argument(
        "--record",
        action="store_true",
        help="Persist the prediction as an audit record.",
    )
    p_topic_classifier_ingest.add_argument("--tags", default=None, help="Comma-separated tags.")
    p_topic_classifier_ingest.add_argument(
        "--tag", action="append", help="Repeatable tag to apply to the ingested item."
    )
    p_topic_classifier_ingest.add_argument("source", help="Path or URL to ingest and classify.")
    p_topic_classifier_ingest.set_defaults(func=cmd_topic_classifier_ingest_classify)

    p_topic_classifier_review = topic_classifier_sub.add_parser(
        "review-batch",
        help="Review blind candidate items against classifier and discovery outputs.",
    )
    _add_common_corpus_arg(p_topic_classifier_review)
    p_topic_classifier_review.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_topic_classifier_review.add_argument(
        "--extraction-snapshot",
        required=True,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_topic_classifier_review.add_argument(
        "--topic-modeling-snapshot",
        required=True,
        help="Exploratory topic modeling snapshot identifier.",
    )
    p_topic_classifier_review.add_argument(
        "--candidate-tag",
        default=None,
        help="Candidate tag required for included items.",
    )
    p_topic_classifier_review.add_argument(
        "--proposed-topic-uid",
        default=None,
        help="Candidate proposed topic identity required for included items.",
    )
    p_topic_classifier_review.add_argument(
        "--review-threshold",
        type=float,
        default=0.35,
        help="Minimum confidence score before review is recommended.",
    )
    p_topic_classifier_review.add_argument(
        "--record",
        action="store_true",
        help="Persist classifier predictions as audit records.",
    )
    p_topic_classifier_review.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_topic_classifier_review.set_defaults(func=cmd_topic_classifier_review_batch)

    p_topic_classifier_draft = topic_classifier_sub.add_parser(
        "draft-manifest", help="Draft a reviewed seed manifest without changing the baseline."
    )
    p_topic_classifier_draft.add_argument(
        "--base-manifest",
        required=True,
        help="Existing seed manifest to copy.",
    )
    p_topic_classifier_draft.add_argument(
        "--output",
        required=True,
        help="Destination path for the drafted seed manifest.",
    )
    p_topic_classifier_draft.add_argument(
        "--classifier-id",
        default=None,
        help="Optional classifier identifier override. Omit to preserve the base classifier identity.",
    )
    p_topic_classifier_draft.add_argument(
        "--display-name",
        default=None,
        help="Optional display name override. Omit to preserve the base display name.",
    )
    p_topic_classifier_draft.add_argument(
        "--description",
        default=None,
        help="Optional description override. Omit to preserve the base description.",
    )
    p_topic_classifier_draft.add_argument(
        "--topic-uid", required=True, help="Topic identity to add."
    )
    p_topic_classifier_draft.add_argument(
        "--topic-display-name",
        required=True,
        help="Human-readable topic label.",
    )
    p_topic_classifier_draft.add_argument(
        "--topic-description",
        required=True,
        help="Reviewed topic definition.",
    )
    p_topic_classifier_draft.add_argument(
        "--seed-item-id",
        action="append",
        required=True,
        help="Reviewed seed item identifier. Repeat for multiple seeds.",
    )
    p_topic_classifier_draft.add_argument(
        "--holdout-item-id",
        action="append",
        default=[],
        help="Reviewed holdout item identifier. Repeat for multiple holdouts.",
    )
    p_topic_classifier_draft.set_defaults(func=cmd_topic_classifier_draft_manifest)
