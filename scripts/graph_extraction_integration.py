"""
Run a repeatable graph extraction integration workflow on Wikipedia.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.graph.extraction import build_graph_snapshot
from biblicus.graph.neo4j import create_neo4j_driver, resolve_neo4j_settings
from biblicus.models import ExtractionSnapshotReference

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _configure_logger(verbose: bool) -> logging.Logger:
    """
    Configure the integration logger.

    :param verbose: Whether to use debug logging.
    :type verbose: bool
    :return: Configured logger.
    :rtype: logging.Logger
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")
    return logging.getLogger("biblicus.graph_integration")


def _log_phase(logger: logging.Logger, title: str, detail: Optional[str] = None) -> None:
    """
    Log a phase banner for the integration workflow.

    :param logger: Logger instance.
    :type logger: logging.Logger
    :param title: Phase title.
    :type title: str
    :param detail: Optional detail line.
    :type detail: str or None
    :return: None.
    :rtype: None
    """
    logger.info("")
    logger.info(title)
    if detail:
        logger.info(detail)


def _download_wikipedia(*, corpus_path: Path, limit: int, force: bool) -> Dict[str, int]:
    """
    Download a small Wikipedia corpus for integration.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param limit: Number of pages to download.
    :type limit: int
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """
    from scripts.download_wikipedia import download_wikipedia_corpus

    return download_wikipedia_corpus(corpus_path=corpus_path, limit=limit, force=force)


def _build_extraction_snapshot(corpus: Corpus, configuration_name: str) -> ExtractionSnapshotReference:
    """
    Build a minimal extraction snapshot for graph extraction.

    :param corpus: Corpus to process.
    :type corpus: Corpus
    :param configuration_name: Human-readable configuration label.
    :type configuration_name: str
    :return: Extraction snapshot reference.
    :rtype: ExtractionSnapshotReference
    """
    extraction_config = {
        "steps": [
            {"extractor_id": "pass-through-text", "config": {}},
            {"extractor_id": "select-text", "config": {}},
        ]
    }
    manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name=configuration_name,
        configuration=extraction_config,
    )
    return ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id=manifest.snapshot_id)


def _build_graph_configuration(arguments: argparse.Namespace) -> Dict[str, object]:
    """
    Build the simple-entities graph configuration.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :return: Configuration mapping.
    :rtype: dict[str, object]
    """
    return {
        "schema_version": 1,
        "min_entity_length": arguments.min_entity_length,
        "max_entity_words": arguments.max_entity_words,
        "include_item_node": arguments.include_item_node,
    }


def _build_story_summary(
    *,
    corpus_path: Path,
    ingestion_stats: Dict[str, int],
    extraction_snapshot: ExtractionSnapshotReference,
    graph_id: str,
    graph_snapshot: str,
    graph_counts: Optional[Dict[str, int]],
    sample_entities: Sequence[str],
) -> str:
    """
    Build a narrative summary for the integration run.

    :param corpus_path: Corpus path used for the run.
    :type corpus_path: Path
    :param ingestion_stats: Ingestion statistics.
    :type ingestion_stats: dict[str, int]
    :param extraction_snapshot: Extraction snapshot reference.
    :type extraction_snapshot: ExtractionSnapshotReference
    :param graph_id: Graph identifier.
    :type graph_id: str
    :param graph_snapshot: Graph snapshot identifier.
    :type graph_snapshot: str
    :param graph_counts: Optional Neo4j counts.
    :type graph_counts: dict[str, int] or None
    :param sample_entities: Sample entity labels.
    :type sample_entities: Sequence[str]
    :return: Narrative summary text.
    :rtype: str
    """
    entity_preview = ", ".join(sample_entities) if sample_entities else "no entities sampled"
    counts_text = "counts unavailable"
    if graph_counts is not None:
        counts_text = f"{graph_counts.get('nodes', 0)} nodes and {graph_counts.get('edges', 0)} edges"
    return (
        "In this run, Biblicus downloaded "
        f"{ingestion_stats.get('ingested', 0)} Wikipedia items into {corpus_path}, "
        f"built extraction snapshot {extraction_snapshot.as_string()}, "
        f"and materialized graph snapshot {graph_snapshot} "
        f"as graph {graph_id}. Neo4j reports {counts_text}. "
        f"Sample entities include {entity_preview}."
    )


def _write_story_report(*, path: Path, content: str) -> None:
    """
    Write a Markdown story report.

    :param path: Output path.
    :type path: Path
    :param content: Markdown content.
    :type content: str
    :return: None.
    :rtype: None
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _query_graph_counts(
    *,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
) -> Dict[str, int]:
    """
    Query Neo4j for node and edge counts.

    :param corpus_id: Corpus identifier.
    :type corpus_id: str
    :param graph_id: Graph identifier.
    :type graph_id: str
    :return: Node and edge counts.
    :rtype: dict[str, int]
    """
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            node_result = session.run(
                "MATCH (n:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot}) "
                "RETURN count(n) AS nodes",
                corpus_id=corpus_id,
                graph_id=graph_id,
                extraction_snapshot=extraction_snapshot,
            )
            edge_result = session.run(
                "MATCH ()-[r:RELATED {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot}]->() "
                "RETURN count(r) AS edges",
                corpus_id=corpus_id,
                graph_id=graph_id,
                extraction_snapshot=extraction_snapshot,
            )
            nodes = int(node_result.single()["nodes"])
            edges = int(edge_result.single()["edges"])
            return {"nodes": nodes, "edges": edges}
    finally:
        driver.close()


def _sample_entities_for_item(
    *,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
    item_id: str,
    limit: int,
) -> List[str]:
    """
    Sample entity labels for a single item.

    :param corpus_id: Corpus identifier.
    :type corpus_id: str
    :param graph_id: Graph identifier.
    :type graph_id: str
    :param item_id: Corpus item identifier.
    :type item_id: str
    :param limit: Maximum number of labels to return.
    :type limit: int
    :return: Sample entity labels.
    :rtype: list[str]
    """
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            result = session.run(
                "MATCH (n:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot, item_id: $item_id, node_type: 'entity'}) "
                "RETURN n.label AS label ORDER BY n.label LIMIT $limit",
                corpus_id=corpus_id,
                graph_id=graph_id,
                extraction_snapshot=extraction_snapshot,
                item_id=item_id,
                limit=limit,
            )
            return [row["label"] for row in result]
    finally:
        driver.close()


def _sample_edges_for_item(
    *,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
    item_id: str,
    limit: int,
) -> List[Tuple[str, str, str, str, str]]:
    """
    Sample edges for a single item.

    :param corpus_id: Corpus identifier.
    :type corpus_id: str
    :param graph_id: Graph identifier.
    :type graph_id: str
    :param item_id: Corpus item identifier.
    :type item_id: str
    :param limit: Maximum number of edges to return.
    :type limit: int
    :return: Sample edges as (source, type, target).
    :rtype: list[tuple[str, str, str]]
    """
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            result = session.run(
                "MATCH (src:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot, item_id: $item_id})"
                "-[r:RELATED {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot, item_id: $item_id}]->"
                "(dst:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot, item_id: $item_id}) "
                "RETURN src.node_type AS src_type, src.label AS src, r.edge_type AS edge_type, "
                "dst.node_type AS dst_type, dst.label AS dst "
                "ORDER BY src.label, dst.label LIMIT $limit",
                corpus_id=corpus_id,
                graph_id=graph_id,
                extraction_snapshot=extraction_snapshot,
                item_id=item_id,
                limit=limit,
            )
            return [
                (
                    row["src_type"],
                    row["src"],
                    row["edge_type"],
                    row["dst_type"],
                    row["dst"],
                )
                for row in result
            ]
    finally:
        driver.close()


def _sample_entity_labels(
    *,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
    limit: int,
) -> List[str]:
    """
    Sample a few entity labels from Neo4j.

    :param corpus_id: Corpus identifier.
    :type corpus_id: str
    :param graph_id: Graph identifier.
    :type graph_id: str
    :param limit: Maximum number of labels to return.
    :type limit: int
    :return: Sample entity labels.
    :rtype: list[str]
    """
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            result = session.run(
                "MATCH (n:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot, node_type: 'entity'}) "
                "RETURN n.label AS label ORDER BY n.label LIMIT $limit",
                corpus_id=corpus_id,
                graph_id=graph_id,
                extraction_snapshot=extraction_snapshot,
                limit=limit,
            )
            return [row["label"] for row in result]
    finally:
        driver.close()


def run_integration(arguments: argparse.Namespace, logger: logging.Logger) -> Dict[str, object]:
    """
    Execute the graph extraction integration workflow.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :param logger: Logger instance.
    :type logger: logging.Logger
    :return: Summary of the workflow results.
    :rtype: dict[str, object]
    """
    corpus_path = Path(arguments.corpus).resolve()

    _log_phase(logger, "Phase 1: Download Wikipedia corpus")
    ingestion_stats = _download_wikipedia(
        corpus_path=corpus_path,
        limit=arguments.limit,
        force=arguments.force,
    )
    logger.info("Downloaded %s items (skipped %s).", ingestion_stats["ingested"], ingestion_stats["skipped"])

    corpus = Corpus.open(corpus_path)

    _log_phase(logger, "Phase 2: Build extraction snapshot")
    extraction_snapshot = _build_extraction_snapshot(
        corpus, configuration_name=arguments.extraction_configuration_name
    )
    logger.info("Extraction snapshot: %s", extraction_snapshot.as_string())

    _log_phase(logger, "Phase 3: Build graph snapshot")
    graph_config = _build_graph_configuration(arguments)
    manifest = build_graph_snapshot(
        corpus,
        extractor_id="simple-entities",
        configuration_name=arguments.graph_configuration_name,
        configuration=graph_config,
        extraction_snapshot=extraction_snapshot,
    )
    logger.info("Graph snapshot: %s", manifest.snapshot_id)
    logger.info("Graph id: %s", manifest.graph_id)

    summary: Dict[str, object] = {
        "corpus": str(corpus_path),
        "ingestion": ingestion_stats,
        "extraction_snapshot": extraction_snapshot.as_string(),
        "graph_snapshot": manifest.snapshot_id,
        "graph_id": manifest.graph_id,
        "graph_stats": manifest.stats,
    }

    counts: Optional[Dict[str, int]] = None
    if arguments.verify:
        _log_phase(logger, "Phase 4: Verify Neo4j materialization")
        counts = _query_graph_counts(
            corpus_id=corpus.uri,
            graph_id=manifest.graph_id,
            extraction_snapshot=extraction_snapshot.as_string(),
        )
        logger.info("Graph counts: %s nodes, %s edges", counts["nodes"], counts["edges"])
        summary["neo4j_counts"] = counts
        labels = _sample_entity_labels(
            corpus_id=corpus.uri,
            graph_id=manifest.graph_id,
            extraction_snapshot=extraction_snapshot.as_string(),
            limit=arguments.sample_entities,
        )
        logger.info("Sample entities: %s", ", ".join(labels) if labels else "none")
        summary["sample_entities"] = labels

    story_summary = _build_story_summary(
        corpus_path=corpus_path,
        ingestion_stats=ingestion_stats,
        extraction_snapshot=extraction_snapshot,
        graph_id=manifest.graph_id,
        graph_snapshot=manifest.snapshot_id,
        graph_counts=counts,
        sample_entities=summary.get("sample_entities", []),
    )

    if arguments.story:
        _log_phase(logger, "Phase 5: Story highlights")
        logger.info(story_summary)
        extraction_manifest = corpus.load_extraction_snapshot_manifest(
            extractor_id=extraction_snapshot.extractor_id,
            snapshot_id=extraction_snapshot.snapshot_id,
        )
        item_samples = list(extraction_manifest.items)[: arguments.sample_items]
        for item_result in item_samples:
            item = corpus.get_item(item_result.item_id)
            text_length = 0
            if item_result.final_text_relpath:
                text_path = corpus.extraction_snapshot_dir(
                    extractor_id=extraction_snapshot.extractor_id,
                    snapshot_id=extraction_snapshot.snapshot_id,
                ) / item_result.final_text_relpath
                if text_path.is_file():
                    text_length = len(text_path.read_text(encoding="utf-8"))
            logger.info("Item %s (%s) extracted text length: %s", item.id, item.title, text_length)
            if arguments.verify:
                entities = _sample_entities_for_item(
                    corpus_id=corpus.uri,
                    graph_id=manifest.graph_id,
                    extraction_snapshot=extraction_snapshot.as_string(),
                    item_id=item.id,
                    limit=arguments.sample_entities,
                )
                edges = _sample_edges_for_item(
                    corpus_id=corpus.uri,
                    graph_id=manifest.graph_id,
                    extraction_snapshot=extraction_snapshot.as_string(),
                    item_id=item.id,
                    limit=arguments.sample_edges,
                )
                logger.info("Item %s entities: %s", item.id, ", ".join(entities) if entities else "none")
                if edges:
                    edge_lines = [
                        f"{src_type}:{src} -[{edge_type}]-> {dst_type}:{dst}"
                        for src_type, src, edge_type, dst_type, dst in edges
                    ]
                    logger.info("Item %s edges: %s", item.id, " | ".join(edge_lines))
                else:
                    logger.info("Item %s edges: none", item.id)

    if arguments.report_path:
        report_lines = [
            "# Graph extraction integration report",
            "",
            story_summary,
            "",
            "## What worked",
            "",
            "- Wikipedia corpus downloaded and ingested.",
            "- Extraction snapshot built successfully.",
            "- Graph snapshot materialized to Neo4j.",
        ]
        if counts is not None:
            report_lines.extend(
                [
                    f"- Neo4j reports {counts.get('nodes', 0)} nodes and {counts.get('edges', 0)} edges.",
                ]
            )
        report_lines.extend(
            [
                "",
                "## What did not work",
                "",
                "- No known failures observed in this run.",
                "",
                "## Next steps",
                "",
                "- Decide whether to store graph properties as native Neo4j maps or JSON strings.",
                "- Add a graph-aware retriever that consumes the materialized graph.",
                "- Expand integration runs with a larger corpus for richer graphs.",
                "",
                "## Run details",
                "",
                f"- Corpus: `{corpus_path}`",
                f"- Extraction snapshot: `{extraction_snapshot.as_string()}`",
                f"- Graph snapshot: `{manifest.snapshot_id}`",
                f"- Graph id: `{manifest.graph_id}`",
            ]
        )
        if counts is not None:
            report_lines.extend(
                [
                    f"- Neo4j nodes: `{counts.get('nodes', 0)}`",
                    f"- Neo4j edges: `{counts.get('edges', 0)}`",
                ]
            )
        if summary.get("sample_entities"):
            report_lines.extend(
                [
                    "",
                    "## Sample entities",
                    "",
                    ", ".join(summary["sample_entities"]),
                ]
            )
        _write_story_report(path=Path(arguments.report_path).resolve(), content="\n".join(report_lines) + "\n")

    return summary


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Run a repeatable graph extraction integration workflow."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--limit", type=int, default=5, help="Number of Wikipedia pages to download.")
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    parser.add_argument(
        "--min-entity-length",
        type=int,
        default=3,
        help="Minimum character length for entities.",
    )
    parser.add_argument(
        "--max-entity-words",
        type=int,
        default=4,
        help="Maximum words per entity span.",
    )
    parser.add_argument(
        "--no-item-node",
        action="store_false",
        dest="include_item_node",
        help="Exclude item nodes and mentions edges.",
    )
    parser.add_argument(
        "--graph-configuration-name",
        default="simple-entities",
        help="Human-readable graph configuration label.",
    )
    parser.add_argument(
        "--extraction-configuration-name",
        default="integration",
        help="Human-readable extraction configuration label.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Query Neo4j for counts and sample entities.",
    )
    parser.add_argument(
        "--sample-entities",
        type=int,
        default=5,
        help="Number of entity labels to sample when verifying.",
    )
    parser.add_argument(
        "--sample-items",
        type=int,
        default=2,
        help="Number of items to narrate in story output.",
    )
    parser.add_argument(
        "--sample-edges",
        type=int,
        default=3,
        help="Number of edges to sample per narrated item.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Optional Markdown report output path.",
    )
    parser.add_argument(
        "--no-story",
        action="store_false",
        dest="story",
        help="Disable story highlights.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.set_defaults(include_item_node=True, story=True)
    return parser


def main() -> int:
    """
    Entry point for the integration script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    logger = _configure_logger(args.verbose)
    output = run_integration(args, logger)
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
