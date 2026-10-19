"""
Analysis commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pydantic import ValidationError

from ..analysis import get_analysis_backend
from ..api import validate_request
from ..corpus import Corpus
from .common import (
    _add_common_corpus_arg,
    _corpus_path_from_arguments,
    _resolve_extraction_snapshot_for_analysis,
)


def cmd_analyze_topics(arguments: argparse.Namespace) -> int:
    """
    Run topic modeling analysis for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    configuration_data = load_configuration_view(
        arguments.configuration,
        configuration_label="Configuration file",
        mapping_error_message="Topic modeling configuration must be a mapping/object",
    )
    overrides = parse_dotted_overrides(arguments.override)
    configuration_data = apply_dotted_overrides(configuration_data, overrides)

    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Topic analysis",
    )

    backend = get_analysis_backend("topic-modeling")
    try:
        output = backend.run_analysis(
            corpus,
            configuration_name=arguments.configuration_name,
            configuration=configuration_data,
            extraction_snapshot=extraction_snapshot,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid topic modeling configuration: {exc}") from exc
    print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_topic_trends(arguments: argparse.Namespace) -> int:
    """
    Run temporal topic intelligence for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import TopicTrendsRequest, analyze_topic_trends
    from ..topic_trends import topic_trends_markdown

    windows = [token.strip() for token in arguments.windows.split(",") if token.strip()]
    request = validate_request(
        TopicTrendsRequest,
        "analyze topic-trends",
        corpus_path=_corpus_path_from_arguments(arguments),
        topic_modeling_snapshot_id=arguments.topic_modeling_snapshot,
        classifier_id=arguments.classifier,
        windows=windows,
        as_of=arguments.as_of,
        rank_window=arguments.rank_window,
    )
    output = analyze_topic_trends(request)
    if arguments.format == "markdown":
        print(topic_trends_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_topic_granularity_sweep(arguments: argparse.Namespace) -> int:
    """
    Run a topic granularity sweep for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )
    from ..topic_granularity import (
        run_topic_granularity_sweep,
        topic_granularity_sweep_markdown,
    )

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    configuration_data = load_configuration_view(
        arguments.configuration,
        configuration_label="Configuration file",
        mapping_error_message="Topic modeling configuration must be a mapping/object",
    )
    overrides = parse_dotted_overrides(arguments.override)
    configuration_data = apply_dotted_overrides(configuration_data, overrides)
    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Topic granularity sweep",
    )
    output = run_topic_granularity_sweep(
        corpus=corpus,
        configuration_name=arguments.configuration_name,
        configuration=configuration_data,
        extraction_snapshot=extraction_snapshot,
        target_topic_range=arguments.target_topic_range,
    )
    if arguments.format == "markdown":
        print(topic_granularity_sweep_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_topic_context(arguments: argparse.Namespace) -> int:
    """
    Generate a research-agent topic context report for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import TopicContextRequest, analyze_topic_context
    from ..topic_context import topic_context_markdown

    request = validate_request(
        TopicContextRequest,
        "analyze topic-context",
        corpus_path=_corpus_path_from_arguments(arguments),
        topic_modeling_snapshot_id=arguments.topic_modeling_snapshot,
        max_topics=arguments.max_topics,
        examples_per_topic=arguments.examples_per_topic,
        summary_model=arguments.summary_model,
        include_outlier=arguments.include_outlier,
    )
    output = analyze_topic_context(request)
    if arguments.format == "markdown":
        print(topic_context_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_profile(arguments: argparse.Namespace) -> int:
    """
    Run profiling analysis for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )

    configuration_data: dict[str, object] = {}
    if arguments.configuration is not None:
        configuration_data = load_configuration_view(
            arguments.configuration,
            configuration_label="Configuration file",
            mapping_error_message="Profiling configuration must be a mapping/object",
        )
        overrides = parse_dotted_overrides(arguments.override)
        configuration_data = apply_dotted_overrides(configuration_data, overrides)
    else:
        overrides = parse_dotted_overrides(arguments.override)
        if overrides:
            configuration_data = apply_dotted_overrides(configuration_data, overrides)

    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Profiling analysis",
    )

    backend = get_analysis_backend("profiling")
    try:
        output = backend.run_analysis(
            corpus,
            configuration_name=arguments.configuration_name,
            configuration=configuration_data,
            extraction_snapshot=extraction_snapshot,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid profiling configuration: {exc}") from exc
    print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_markov(arguments: argparse.Namespace) -> int:
    """
    Run Markov analysis for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    configuration_data = load_configuration_view(
        arguments.configuration,
        configuration_label="Configuration file",
        mapping_error_message="Markov analysis configuration must be a mapping/object",
    )
    overrides = parse_dotted_overrides(arguments.override)
    configuration_data = apply_dotted_overrides(configuration_data, overrides)

    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Markov analysis",
    )

    backend = get_analysis_backend("markov")
    try:
        output = backend.run_analysis(
            corpus,
            configuration_name=arguments.configuration_name,
            configuration=configuration_data,
            extraction_snapshot=extraction_snapshot,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid Markov analysis configuration: {exc}") from exc
    print(output.model_dump_json(indent=2))
    return 0


def register_analyze_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the analyze commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_analyze = subparsers.add_parser("analyze", help="Run analysis pipelines for the corpus.")
    analyze_sub = p_analyze.add_subparsers(dest="analyze_command", required=True)

    p_analyze_topics = analyze_sub.add_parser("topics", help="Run topic modeling analysis.")
    _add_common_corpus_arg(p_analyze_topics)
    p_analyze_topics.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to topic modeling configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_analyze_topics.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_analyze_topics.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    p_analyze_topics.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_analyze_topics.set_defaults(func=cmd_analyze_topics)

    p_analyze_topic_granularity = analyze_sub.add_parser(
        "topic-granularity-sweep",
        help="Compare topic modeling granularity profiles and label the selected profile.",
    )
    _add_common_corpus_arg(p_analyze_topic_granularity)
    p_analyze_topic_granularity.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to topic modeling configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_analyze_topic_granularity.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_analyze_topic_granularity.add_argument(
        "--configuration-name",
        default="granularity-sweep",
        help="Human-readable configuration name.",
    )
    p_analyze_topic_granularity.add_argument(
        "--extraction-snapshot",
        required=True,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_analyze_topic_granularity.add_argument(
        "--target-topic-range",
        default="10:20",
        help="Target non-outlier topic count range in min:max form.",
    )
    p_analyze_topic_granularity.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_analyze_topic_granularity.set_defaults(func=cmd_analyze_topic_granularity_sweep)

    p_analyze_topic_context = analyze_sub.add_parser(
        "topic-context", help="Generate Markdown or JSON topic context for research agents."
    )
    _add_common_corpus_arg(p_analyze_topic_context)
    p_analyze_topic_context.add_argument(
        "--topic-modeling-snapshot",
        required=True,
        help="Topic modeling snapshot identifier to summarize.",
    )
    p_analyze_topic_context.add_argument(
        "--max-topics",
        type=int,
        default=20,
        help="Maximum non-outlier topic buckets to include.",
    )
    p_analyze_topic_context.add_argument(
        "--examples-per-topic",
        type=int,
        default=3,
        help="Maximum representative examples per topic.",
    )
    p_analyze_topic_context.add_argument(
        "--summary-model",
        default=None,
        help="Optional OpenAI model for topic guidance and missing example summaries.",
    )
    p_analyze_topic_context.add_argument(
        "--include-outlier",
        action="store_true",
        help="Include BERTopic outlier topic -1 in the report.",
    )
    p_analyze_topic_context.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format.",
    )
    p_analyze_topic_context.set_defaults(func=cmd_analyze_topic_context)

    p_analyze_topic_trends = analyze_sub.add_parser(
        "topic-trends", help="Run publication-date topic trend analysis."
    )
    _add_common_corpus_arg(p_analyze_topic_trends)
    p_analyze_topic_trends.add_argument(
        "--topic-modeling-snapshot",
        required=True,
        help="Topic modeling snapshot identifier to analyze.",
    )
    p_analyze_topic_trends.add_argument(
        "--classifier",
        default=None,
        help="Optional topic classifier identifier for canonical topic coverage.",
    )
    p_analyze_topic_trends.add_argument(
        "--windows",
        default="30d,90d,1y,all",
        help="Comma-separated publication windows such as 30d,90d,1y,all.",
    )
    p_analyze_topic_trends.add_argument(
        "--as-of",
        default=None,
        help="Publication date anchor for trend windows. Defaults to latest dates.published_at.",
    )
    p_analyze_topic_trends.add_argument(
        "--rank-window",
        default="90d",
        help="Window used to rank topics. Must be included in --windows.",
    )
    p_analyze_topic_trends.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_analyze_topic_trends.set_defaults(func=cmd_analyze_topic_trends)

    p_analyze_profile = analyze_sub.add_parser("profile", help="Run profiling analysis.")
    _add_common_corpus_arg(p_analyze_profile)
    p_analyze_profile.add_argument(
        "--configuration",
        default=None,
        action="append",
        help="Optional profiling configuration YAML file. Repeatable; later files override earlier ones.",
    )
    p_analyze_profile.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_analyze_profile.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    p_analyze_profile.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_analyze_profile.set_defaults(func=cmd_analyze_profile)

    p_analyze_markov = analyze_sub.add_parser("markov", help="Run Markov analysis.")
    _add_common_corpus_arg(p_analyze_markov)
    p_analyze_markov.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to Markov analysis configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_analyze_markov.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_analyze_markov.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    p_analyze_markov.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_analyze_markov.set_defaults(func=cmd_analyze_markov)

    # -----------------------------------------------------------------
    # benchmark subcommand group
    # -----------------------------------------------------------------
