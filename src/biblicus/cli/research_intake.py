"""
Research intake commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from ..corpus import Corpus
from .common import (
    _add_common_corpus_arg,
    _load_ingest_metadata_file,
    _parse_tags,
)


def _load_research_intake_configuration(paths: List[str]) -> object:
    from ..configuration import load_configuration_view
    from ..research_intake import ResearchIntakeConfiguration

    payload = load_configuration_view(
        paths,
        configuration_label="Research intake configuration",
        mapping_error_message="Research intake configuration must be a mapping/object",
    )
    return ResearchIntakeConfiguration.model_validate(payload)


def cmd_research_intake_assess(arguments: argparse.Namespace) -> int:
    """
    Assess a research-agent candidate without ingesting it.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..research_intake import assess_research_intake_candidate

    corpus = Corpus.open(arguments.corpus) if arguments.corpus else Corpus.find(Path.cwd())
    metadata = _load_ingest_metadata_file(Path(arguments.metadata_file))
    configuration = _load_research_intake_configuration(arguments.configuration)
    output = assess_research_intake_candidate(
        corpus=corpus,
        classifier_id=arguments.classifier,
        source_path=Path(arguments.source),
        metadata=metadata,
        configuration=configuration,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_research_intake_ingest(arguments: argparse.Namespace) -> int:
    """
    Assess and conditionally ingest a research-agent candidate.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..research_intake import ingest_research_intake_candidate

    corpus = Corpus.open(arguments.corpus) if arguments.corpus else Corpus.find(Path.cwd())
    metadata = _load_ingest_metadata_file(Path(arguments.metadata_file))
    configuration = _load_research_intake_configuration(arguments.configuration)
    output = ingest_research_intake_candidate(
        corpus=corpus,
        classifier_id=arguments.classifier,
        source_path=Path(arguments.source),
        metadata=metadata,
        configuration=configuration,
        source_uri=arguments.source_uri,
        media_type=arguments.media_type,
        tags=_parse_tags(arguments.tags, arguments.tag),
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_research_intake_pending(arguments: argparse.Namespace) -> int:
    """
    List research-agent intake items awaiting review.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..research_intake import (
        list_pending_research_intake_items,
        research_intake_pending_markdown,
    )

    corpus = Corpus.open(arguments.corpus) if arguments.corpus else Corpus.find(Path.cwd())
    output = list_pending_research_intake_items(corpus=corpus)
    if arguments.format == "markdown":
        print(research_intake_pending_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_research_intake_decide(arguments: argparse.Namespace) -> int:
    """
    Apply a human decision to an existing research intake item.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..research_intake import decide_research_intake_item

    corpus = Corpus.open(arguments.corpus) if arguments.corpus else Corpus.find(Path.cwd())
    output = decide_research_intake_item(
        corpus=corpus,
        item_id=arguments.item_id,
        decision=arguments.decision,
        topic_uid=arguments.topic_uid,
        tags_add=getattr(arguments, "tags_add", None) or [],
        tags_remove=getattr(arguments, "tags_remove", None) or [],
        delete=bool(getattr(arguments, "delete", False)),
    )
    print(output.model_dump_json(indent=2))
    return 0


def register_research_intake_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the research intake commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_research_intake = subparsers.add_parser(
        "research-intake", help="Assess and manage research-agent intake candidates."
    )
    research_intake_sub = p_research_intake.add_subparsers(
        dest="research_intake_command", required=True
    )

    p_research_intake_assess = research_intake_sub.add_parser(
        "assess", help="Assess a local candidate without ingesting it."
    )
    _add_common_corpus_arg(p_research_intake_assess)
    p_research_intake_assess.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_research_intake_assess.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to research intake configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_research_intake_assess.add_argument(
        "--metadata-file",
        required=True,
        help="YAML or JSON candidate metadata object.",
    )
    p_research_intake_assess.add_argument("source", help="Local candidate file path.")
    p_research_intake_assess.set_defaults(func=cmd_research_intake_assess)

    p_research_intake_ingest = research_intake_sub.add_parser(
        "ingest", help="Assess a local candidate and ingest it when accepted or pending."
    )
    _add_common_corpus_arg(p_research_intake_ingest)
    p_research_intake_ingest.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_research_intake_ingest.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to research intake configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_research_intake_ingest.add_argument(
        "--metadata-file",
        required=True,
        help="YAML or JSON candidate metadata object.",
    )
    p_research_intake_ingest.add_argument(
        "--source-uri",
        default=None,
        help="Explicit source uniform resource identifier for accepted or pending ingest.",
    )
    p_research_intake_ingest.add_argument(
        "--media-type",
        default=None,
        help="Explicit media type for accepted or pending ingest.",
    )
    p_research_intake_ingest.add_argument("--tags", default=None, help="Comma-separated tags.")
    p_research_intake_ingest.add_argument(
        "--tag", action="append", help="Repeatable tag to apply to accepted or pending ingest."
    )
    p_research_intake_ingest.add_argument("source", help="Local candidate file path.")
    p_research_intake_ingest.set_defaults(func=cmd_research_intake_ingest)

    p_research_intake_pending = research_intake_sub.add_parser(
        "pending", help="List research intake items awaiting review."
    )
    _add_common_corpus_arg(p_research_intake_pending)
    p_research_intake_pending.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_research_intake_pending.set_defaults(func=cmd_research_intake_pending)

    p_research_intake_decide = research_intake_sub.add_parser(
        "decide", help="Apply a human decision to an existing intake item."
    )
    _add_common_corpus_arg(p_research_intake_decide)
    p_research_intake_decide.add_argument(
        "--item-id",
        required=True,
        help="Pending item identifier.",
    )
    p_research_intake_decide.add_argument(
        "--decision",
        required=True,
        choices=["accept", "reject"],
        help="Human intake decision.",
    )
    p_research_intake_decide.add_argument(
        "--topic-uid",
        default=None,
        help="Reviewed topic identity for accepted items.",
    )
    p_research_intake_decide.add_argument(
        "--tags-add",
        action="append",
        default=None,
        help="Repeatable tag to add during the decision.",
    )
    p_research_intake_decide.add_argument(
        "--tags-remove",
        action="append",
        default=None,
        help="Repeatable tag to remove during the decision.",
    )
    p_research_intake_decide.add_argument(
        "--delete",
        action="store_true",
        help="Delete the item files when rejecting (reject-only).",
    )
    p_research_intake_decide.set_defaults(func=cmd_research_intake_decide)
