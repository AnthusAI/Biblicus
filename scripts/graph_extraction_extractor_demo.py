"""
Run a narrative graph extraction demo for a specific extractor.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.graph.extraction import build_graph_snapshot
from biblicus.graph.neo4j import create_neo4j_driver, resolve_neo4j_settings
from biblicus.models import ExtractionSnapshotReference

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


EXTRACTOR_CONFIGS = {
    "simple-entities": {
        "schema_version": 1,
        "min_entity_length": 3,
        "max_entity_words": 4,
        "include_item_node": True,
    },
    "cooccurrence": {
        "schema_version": 1,
        "window_size": 4,
        "min_cooccurrence": 2,
    },
    "ner-entities": {
        "schema_version": 1,
        "model": "en_core_web_sm",
        "min_entity_length": 3,
        "include_item_node": True,
    },
    "dependency-relations": {
        "schema_version": 1,
        "model": "en_core_web_sm",
        "min_entity_length": 3,
        "include_item_node": True,
    },
}


def _configure_logger(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")
    return logging.getLogger("biblicus.graph_demo")


def _log_phase(logger: logging.Logger, title: str) -> None:
    logger.info("")
    logger.info(title)


def _download_wikipedia(*, corpus_path: Path, limit: int, force: bool) -> Dict[str, int]:
    from scripts.download_wikipedia import download_wikipedia_corpus

    return download_wikipedia_corpus(corpus_path=corpus_path, limit=limit, force=force)


def _build_extraction_snapshot(corpus: Corpus, configuration_name: str) -> ExtractionSnapshotReference:
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


def _build_graph_configuration(extractor_id: str, overrides: Dict[str, object]) -> Dict[str, object]:
    base = EXTRACTOR_CONFIGS.get(extractor_id)
    if base is None:
        raise ValueError(f"Unknown extractor '{extractor_id}'.")
    config = dict(base)
    config.update(overrides)
    return config


def _query_counts(
    *, corpus_id: str, graph_id: str, extraction_snapshot: str
) -> Dict[str, int]:
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            node_result = session.run(
                "MATCH (n:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot}) RETURN count(n) AS nodes",
                corpus_id=corpus_id,
                graph_id=graph_id,
                extraction_snapshot=extraction_snapshot,
            )
            edge_result = session.run(
                "MATCH ()-[r:RELATED {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot}]->() RETURN count(r) AS edges",
                corpus_id=corpus_id,
                graph_id=graph_id,
                extraction_snapshot=extraction_snapshot,
            )
            return {
                "nodes": int(node_result.single()["nodes"]),
                "edges": int(edge_result.single()["edges"]),
            }
    finally:
        driver.close()


def _sample_entities(
    *,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
    item_id: Optional[str],
    limit: int,
) -> List[str]:
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            params = {
                "corpus_id": corpus_id,
                "graph_id": graph_id,
                "extraction_snapshot": extraction_snapshot,
                "limit": limit,
            }
            item_clause = ""
            if item_id is not None:
                item_clause = "WHERE n.item_id = $item_id"
                params["item_id"] = item_id
            result = session.run(
                "MATCH (n:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot, node_type: 'entity'}) "
                + item_clause
                + " RETURN DISTINCT n.label AS label ORDER BY n.label LIMIT $limit",
                **params,
            )
            return [row["label"] for row in result]
    finally:
        driver.close()


def _sample_terms(
    *,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
    item_id: Optional[str],
    limit: int,
) -> List[str]:
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            params = {
                "corpus_id": corpus_id,
                "graph_id": graph_id,
                "extraction_snapshot": extraction_snapshot,
                "limit": limit,
            }
            item_clause = ""
            if item_id is not None:
                item_clause = "WHERE n.item_id = $item_id"
                params["item_id"] = item_id
            result = session.run(
                "MATCH (n:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot, node_type: 'term'}) "
                + item_clause
                + " RETURN DISTINCT n.label AS label ORDER BY n.label LIMIT $limit",
                **params,
            )
            return [row["label"] for row in result]
    finally:
        driver.close()


def _sample_edges(
    *,
    corpus_id: str,
    graph_id: str,
    extraction_snapshot: str,
    item_id: Optional[str],
    limit: int,
) -> List[Tuple[str, str, str, str, str]]:
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            params = {
                "corpus_id": corpus_id,
                "graph_id": graph_id,
                "extraction_snapshot": extraction_snapshot,
                "limit": limit,
            }
            item_clause = ""
            if item_id is not None:
                item_clause = "WHERE src.item_id = $item_id AND dst.item_id = $item_id"
                params["item_id"] = item_id
            result = session.run(
                "MATCH (src:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot})"
                "-[r:RELATED {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot}]->"
                "(dst:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id, "
                "extraction_snapshot_id: $extraction_snapshot}) "
                + item_clause
                + " RETURN src.node_type AS src_type, src.label AS src, r.edge_type AS edge_type, "
                "dst.node_type AS dst_type, dst.label AS dst ORDER BY src.label, dst.label LIMIT $limit",
                **params,
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


def _load_text_preview(
    corpus: Corpus, extraction_snapshot: ExtractionSnapshotReference, relpath: str, limit: int
) -> str:
    snapshot_dir = corpus.extraction_snapshot_dir(
        extractor_id=extraction_snapshot.extractor_id,
        snapshot_id=extraction_snapshot.snapshot_id,
    )
    text_path = snapshot_dir / relpath
    text = text_path.read_text(encoding="utf-8") if text_path.is_file() else ""
    return text[:limit].strip()


def _write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_demo(arguments: argparse.Namespace, logger: logging.Logger) -> Dict[str, object]:
    corpus_path = Path(arguments.corpus).resolve()

    if arguments.skip_download:
        _log_phase(logger, "Phase 1: Reuse existing corpus")
        ingestion_stats = {"ingested": 0, "skipped": 0}
        logger.info("Skipped download; using existing corpus at %s.", corpus_path)
    else:
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
    graph_config = _build_graph_configuration(arguments.extractor, arguments.override)
    manifest = build_graph_snapshot(
        corpus,
        extractor_id=arguments.extractor,
        configuration_name=arguments.graph_configuration_name,
        configuration=graph_config,
        extraction_snapshot=extraction_snapshot,
    )
    logger.info("Graph snapshot: %s", manifest.snapshot_id)
    logger.info("Graph id: %s", manifest.graph_id)

    counts = _query_counts(
        corpus_id=corpus.uri,
        graph_id=manifest.graph_id,
        extraction_snapshot=extraction_snapshot.as_string(),
    )

    _log_phase(logger, "Phase 4: Graph report")
    logger.info("Graph counts: %s nodes, %s edges", counts["nodes"], counts["edges"])

    if arguments.extractor == "cooccurrence":
        term_samples = _sample_terms(
            corpus_id=corpus.uri,
            graph_id=manifest.graph_id,
            extraction_snapshot=extraction_snapshot.as_string(),
            item_id=None,
            limit=arguments.sample_entities,
        )
        logger.info("Sample terms: %s", ", ".join(term_samples) if term_samples else "none")
    else:
        entity_samples = _sample_entities(
            corpus_id=corpus.uri,
            graph_id=manifest.graph_id,
            extraction_snapshot=extraction_snapshot.as_string(),
            item_id=None,
            limit=arguments.sample_entities,
        )
        logger.info("Sample entities: %s", ", ".join(entity_samples) if entity_samples else "none")

    edges = _sample_edges(
        corpus_id=corpus.uri,
        graph_id=manifest.graph_id,
        extraction_snapshot=extraction_snapshot.as_string(),
        item_id=None,
        limit=arguments.sample_edges,
    )
    if edges:
        edge_lines = [
            f"{src_type}:{src} -[{edge_type}]-> {dst_type}:{dst}"
            for src_type, src, edge_type, dst_type, dst in edges
        ]
        logger.info("Sample edges: %s", " | ".join(edge_lines))
    else:
        logger.info("Sample edges: none")

    _log_phase(logger, "Phase 5: Item walkthroughs")
    extraction_manifest = corpus.load_extraction_snapshot_manifest(
        extractor_id=extraction_snapshot.extractor_id,
        snapshot_id=extraction_snapshot.snapshot_id,
    )
    for item_result in list(extraction_manifest.items)[: arguments.sample_items]:
        item = corpus.get_item(item_result.item_id)
        logger.info("Item: %s (%s)", item.id, item.title)
        preview = ""
        if item_result.final_text_relpath:
            preview = _load_text_preview(
                corpus,
                extraction_snapshot,
                item_result.final_text_relpath,
                arguments.preview_characters,
            )
        logger.info("Input preview: %s", preview or "none")
        if arguments.extractor == "cooccurrence":
            terms = _sample_terms(
                corpus_id=corpus.uri,
                graph_id=manifest.graph_id,
                extraction_snapshot=extraction_snapshot.as_string(),
                item_id=item.id,
                limit=arguments.sample_entities,
            )
            logger.info("Terms: %s", ", ".join(terms) if terms else "none")
        else:
            entities = _sample_entities(
                corpus_id=corpus.uri,
                graph_id=manifest.graph_id,
                extraction_snapshot=extraction_snapshot.as_string(),
                item_id=item.id,
                limit=arguments.sample_entities,
            )
            logger.info("Entities: %s", ", ".join(entities) if entities else "none")
        item_edges = _sample_edges(
            corpus_id=corpus.uri,
            graph_id=manifest.graph_id,
            extraction_snapshot=extraction_snapshot.as_string(),
            item_id=item.id,
            limit=arguments.sample_edges,
        )
        if item_edges:
            item_edge_lines = [
                f"{src_type}:{src} -[{edge_type}]-> {dst_type}:{dst}"
                for src_type, src, edge_type, dst_type, dst in item_edges
            ]
            logger.info("Edges: %s", " | ".join(item_edge_lines))
        else:
            logger.info("Edges: none")

    report = {
        "corpus": str(corpus_path),
        "ingestion": ingestion_stats,
        "extraction_snapshot": extraction_snapshot.as_string(),
        "graph_snapshot": manifest.snapshot_id,
        "graph_id": manifest.graph_id,
        "graph_counts": counts,
    }
    if arguments.report_path:
        report_text = json.dumps(report, indent=2)
        _write_report(Path(arguments.report_path), report_text + "\n")

    return report


def _parse_overrides(values: Iterable[str]) -> Dict[str, object]:
    config: Dict[str, object] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"Overrides must be key=value (got {raw!r})")
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.isdigit():
            config[key] = int(value)
        else:
            try:
                config[key] = float(value)
            except ValueError:
                config[key] = value
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a narrative graph extraction demo for a specific extractor."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--extractor", required=True, help="Graph extractor identifier.")
    parser.add_argument("--limit", type=int, default=5, help="Number of Wikipedia pages to download.")
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading Wikipedia and reuse the existing corpus.",
    )
    parser.add_argument(
        "--extraction-configuration-name",
        default="demo",
        help="Human-readable extraction configuration label.",
    )
    parser.add_argument(
        "--graph-configuration-name",
        default="demo",
        help="Human-readable graph configuration label.",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        help="Override config key=value pairs.",
    )
    parser.add_argument(
        "--sample-items",
        type=int,
        default=2,
        help="Number of items to narrate.",
    )
    parser.add_argument(
        "--sample-entities",
        type=int,
        default=5,
        help="Number of entities or terms to sample.",
    )
    parser.add_argument(
        "--sample-edges",
        type=int,
        default=5,
        help="Number of edges to sample.",
    )
    parser.add_argument(
        "--preview-characters",
        type=int,
        default=220,
        help="Number of input characters to show per item.",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Optional report output path.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.override = _parse_overrides(args.override)
    logger = _configure_logger(args.verbose)
    run_demo(args, logger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
