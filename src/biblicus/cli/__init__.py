"""
Command-line interface for Biblicus.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from pydantic import ValidationError

from ..errors import ExtractionSnapshotFatalError, RemoteSourceDependencyError
from .analyze import register_analyze_commands
from .benchmark import register_benchmark_commands
from .corpus import register_corpus_commands
from .crawl import register_crawl_commands
from .dashboard import register_dashboard_commands
from .extract import register_extract_commands
from .graph import register_graph_commands
from .research_intake import register_research_intake_commands
from .retrieval import register_build_commands, register_query_commands
from .steering import register_steering_commands
from .taxonomy_ontology import register_taxonomy_ontology_commands
from .topic_classifier import register_topic_classifier_commands


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser instance.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="biblicus",
        description="Biblicus command-line interface (minimum viable product)",
    )
    parser.add_argument(
        "--corpus",
        type=str,
        default=None,
        dest="corpus",
        help=(
            "Corpus path or uniform resource identifier (defaults to searching from the current working directory "
            "upward). "
            "Can be provided before or after the subcommand."
        ),
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    register_corpus_commands(subparsers)
    register_build_commands(subparsers)
    register_extract_commands(subparsers)
    register_graph_commands(subparsers)
    register_taxonomy_ontology_commands(subparsers)
    register_query_commands(subparsers)
    register_crawl_commands(subparsers)
    register_steering_commands(subparsers)
    register_research_intake_commands(subparsers)
    register_topic_classifier_commands(subparsers)
    register_analyze_commands(subparsers)
    register_benchmark_commands(subparsers)
    register_dashboard_commands(subparsers)

    return parser


def main(argument_list: Optional[List[str]] = None) -> int:
    """
    Entry point for the Biblicus command-line interface.

    :param argument_list: Optional command-line interface arguments.
    :type argument_list: list[str] or None
    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    arguments = parser.parse_args(argument_list)
    try:
        return int(arguments.func(arguments))
    except (
        FileNotFoundError,
        FileExistsError,
        KeyError,
        ValueError,
        ExtractionSnapshotFatalError,
        RemoteSourceDependencyError,
        NotImplementedError,
        ValidationError,
    ) as exception:
        message = exception.args[0] if getattr(exception, "args", None) else str(exception)
        print(str(message), file=sys.stderr)
        return 2
