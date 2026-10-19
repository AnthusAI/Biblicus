"""
Graph extraction commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from ..api import validate_request
from ..corpus import Corpus
from ..models import (
    parse_extraction_snapshot_reference,
)
from .common import (
    _add_common_corpus_arg,
    _open_corpus_from_arguments,
)


def cmd_graph_extract(arguments: argparse.Namespace) -> int:
    """
    Build a graph extraction snapshot for the corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import GraphExtractRequest, graph_extract

    corpus = _open_corpus_from_arguments(arguments)
    if arguments.extraction_snapshot:
        extraction_snapshot = parse_extraction_snapshot_reference(arguments.extraction_snapshot)
    else:
        extraction_snapshot = corpus.latest_extraction_snapshot_reference()
        if extraction_snapshot is None:
            raise ValueError("Graph extraction requires an extraction snapshot")
        print(
            "Warning: using latest extraction snapshot; pass --extraction-snapshot for reproducibility.",
            file=sys.stderr,
        )
    request = validate_request(
        GraphExtractRequest,
        "graph extract",
        corpus_path=str(corpus.root),
        extractor_id=arguments.extractor,
        extraction_snapshot=extraction_snapshot,
        configuration_name=arguments.configuration_name,
        configuration_paths=arguments.configuration or [],
        overrides=arguments.override,
        max_items=arguments.max_items,
        item_timeout_seconds=arguments.item_timeout_seconds,
        item_retry_attempts=arguments.item_retry_attempts,
        heartbeat_interval_seconds=arguments.heartbeat_interval_seconds,
    )
    manifest = graph_extract(request, progress_callback=_graph_extract_progress)
    print(manifest.model_dump_json(indent=2))
    return 0


def _graph_extract_progress(event: str, payload: Dict[str, Any]) -> None:
    if event == "starting":
        print(
            "[graph] starting snapshot "
            f"{payload['snapshot_id']} with {payload['items_total']} extraction items",
            file=sys.stderr,
            flush=True,
        )
    elif event == "processing":
        print(
            "[graph] processing "
            f"{payload['item_index']}/{payload['items_total']} item {payload['item_id']} "
            f"elapsedMs={payload.get('elapsed_ms', 0)}",
            file=sys.stderr,
            flush=True,
        )
    elif event == "heartbeat":
        print(
            "[graph] heartbeat "
            f"snapshot={payload['snapshot_id']} itemIndex={payload.get('item_index', 0)} "
            f"nodes={payload.get('nodes', 0)} edges={payload.get('edges', 0)} "
            f"skipped={payload.get('items_skipped', 0)} errored={payload.get('items_errored', 0)} "
            f"timeouts={payload.get('items_timed_out', 0)} elapsedMs={payload.get('elapsed_ms', 0)}",
            file=sys.stderr,
            flush=True,
        )
    elif event == "processed":
        message = (
            "[graph] processed "
            f"{payload['item_index']}/{payload['items_total']} "
            f"item {payload['item_id']} status={payload['status']} "
            f"nodes={payload['nodes']} edges={payload['edges']} "
            f"attempts={payload.get('attempts', 1)} durationMs={payload.get('duration_ms', 0)} "
            f"elapsedMs={payload.get('elapsed_ms', 0)}"
        )
        if payload.get("error_message"):
            message = f"{message} error={payload['error_message']}"
        if payload.get("error_reason"):
            message = f"{message} reason={payload['error_reason']}"
        print(message, file=sys.stderr, flush=True)
    elif event == "completed":
        print(
            "[graph] completed snapshot "
            f"{payload['snapshot_id']} processed={payload['items_processed']} "
            f"skipped={payload['items_skipped']} errored={payload['items_errored']} "
            f"timeouts={payload.get('items_timed_out', 0)} "
            f"nodes={payload['nodes']} edges={payload['edges']} elapsedMs={payload.get('elapsed_ms', 0)}",
            file=sys.stderr,
            flush=True,
        )


def cmd_graph_list(arguments: argparse.Namespace) -> int:
    """
    List graph extraction snapshots stored under the corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..graph.extraction import list_graph_snapshots

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    snapshots = list_graph_snapshots(corpus, extractor_id=arguments.extractor_id)
    print(json.dumps([entry.model_dump() for entry in snapshots], indent=2))
    return 0


def cmd_graph_show(arguments: argparse.Namespace) -> int:
    """
    Show a graph snapshot manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..graph.extraction import load_graph_snapshot_manifest
    from ..graph.models import parse_graph_snapshot_reference

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    reference = parse_graph_snapshot_reference(arguments.snapshot)
    manifest = load_graph_snapshot_manifest(
        corpus,
        extractor_id=reference.extractor_id,
        snapshot_id=reference.snapshot_id,
    )
    print(manifest.model_dump_json(indent=2))
    return 0


def cmd_graph_export(arguments: argparse.Namespace) -> int:
    """
    Export graph snapshot nodes and edges from Neo4j as portable JSON.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..graph.extraction import export_graph_snapshot
    from ..graph.models import parse_graph_snapshot_reference

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    reference = parse_graph_snapshot_reference(arguments.snapshot)
    payload = export_graph_snapshot(corpus, snapshot=reference)
    output = payload.model_dump_json(indent=2)
    if arguments.output:
        Path(arguments.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


def register_graph_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the graph commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_graph = subparsers.add_parser("graph", help="Run graph extraction pipelines for the corpus.")
    graph_sub = p_graph.add_subparsers(dest="graph_command", required=True)

    p_graph_extract = graph_sub.add_parser("extract", help="Build a graph extraction snapshot.")
    _add_common_corpus_arg(p_graph_extract)
    p_graph_extract.add_argument(
        "--extractor",
        required=True,
        help="Graph extractor identifier (for example: cooccurrence).",
    )
    p_graph_extract.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id (defaults to latest snapshot).",
    )
    p_graph_extract.add_argument(
        "--configuration-name", default="default", help="Human-readable configuration name."
    )
    p_graph_extract.add_argument(
        "--configuration",
        default=None,
        action="append",
        help="Path to graph extraction configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_graph_extract.add_argument(
        "--override",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_graph_extract.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Maximum number of extraction items to process for bounded validation runs.",
    )
    p_graph_extract.add_argument(
        "--item-timeout-seconds",
        type=float,
        default=60.0,
        help="Per-item extraction timeout in seconds (<=0 disables timeout).",
    )
    p_graph_extract.add_argument(
        "--item-retry-attempts",
        type=int,
        default=0,
        help="Retries per item after timeout/error before recording item error.",
    )
    p_graph_extract.add_argument(
        "--heartbeat-interval-seconds",
        type=float,
        default=10.0,
        help="Progress heartbeat interval in seconds (<=0 disables heartbeat events).",
    )
    p_graph_extract.set_defaults(func=cmd_graph_extract, typed_command="graph extract")

    p_graph_list = graph_sub.add_parser("list", help="List graph extraction snapshots.")
    _add_common_corpus_arg(p_graph_list)
    p_graph_list.add_argument(
        "--extractor-id",
        default=None,
        help="Optional graph extractor identifier filter (for example: cooccurrence).",
    )
    p_graph_list.set_defaults(func=cmd_graph_list)

    p_graph_show = graph_sub.add_parser("show", help="Show a graph extraction snapshot manifest.")
    _add_common_corpus_arg(p_graph_show)
    p_graph_show.add_argument(
        "--snapshot",
        required=True,
        help="Graph snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_graph_show.set_defaults(func=cmd_graph_show)

    p_graph_export = graph_sub.add_parser(
        "export", help="Export graph snapshot nodes and edges from Neo4j."
    )
    _add_common_corpus_arg(p_graph_export)
    p_graph_export.add_argument(
        "--snapshot",
        required=True,
        help="Graph snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_graph_export.add_argument(
        "--output",
        default=None,
        help="Optional output JSON path (defaults to stdout).",
    )
    p_graph_export.set_defaults(func=cmd_graph_export)
