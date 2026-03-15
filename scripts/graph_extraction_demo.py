"""
Run a minimal graph extraction demo against a corpus.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from biblicus.configuration import apply_dotted_overrides, load_configuration_view, parse_dotted_overrides
from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.graph.extraction import build_graph_snapshot
from biblicus.graph.neo4j import create_neo4j_driver, resolve_neo4j_settings
from biblicus.models import ExtractionSnapshotReference, parse_extraction_snapshot_reference

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _resolve_corpus(path: Path) -> Corpus:
    if (path / ".biblicus" / "config.json").is_file():
        return Corpus.open(path)
    raise ValueError("Corpus is not initialized. Run biblicus init first.")


def _resolve_extraction_snapshot(
    corpus: Corpus,
    *,
    snapshot_ref: str | None,
    build_if_missing: bool,
) -> ExtractionSnapshotReference:
    if snapshot_ref:
        return parse_extraction_snapshot_reference(snapshot_ref)
    latest = corpus.latest_extraction_snapshot_reference()
    if latest is not None:
        return latest
    if not build_if_missing:
        raise ValueError("No extraction snapshot found. Pass --extraction-snapshot or --build-extraction.")
    manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="graph-demo",
        configuration={
            "stages": [
                {"extractor_id": "pass-through-text", "config": {}},
                {"extractor_id": "select-text", "config": {}},
            ]
        },
    )
    return ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id=manifest.snapshot_id)


def _load_graph_configuration(
    *,
    configuration_paths: list[str] | None,
    overrides: list[str] | None,
) -> Dict[str, object]:
    base_config: Dict[str, object] = {}
    if configuration_paths:
        base_config = load_configuration_view(
            configuration_paths,
            configuration_label="Graph extraction configuration",
            mapping_error_message="Graph extraction configuration must be a mapping/object",
        )
    override_map = parse_dotted_overrides(overrides or [])
    return apply_dotted_overrides(base_config, override_map)


def _prepare_demo_items(corpus: Corpus) -> None:
    if corpus.list_items(limit=1):
        return
    corpus.ingest_note(
        "Alpha beta gamma. Graph extraction demo note.",
        title="Demo note one",
        tags=["graph", "demo"],
    )
    corpus.ingest_note(
        "Beta delta epsilon. Another demo item with overlap.",
        title="Demo note two",
        tags=["graph", "demo"],
    )
    corpus.ingest_note(
        "Gamma delta alpha. Final demo item for cooccurrence.",
        title="Demo note three",
        tags=["graph", "demo"],
    )


def _verify_neo4j_graph(*, corpus: Corpus, graph_id: str) -> Dict[str, int]:
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            node_result = session.run(
                "MATCH (n:GraphNode {corpus_id: $corpus_id, graph_id: $graph_id}) "
                "RETURN count(n) AS nodes",
                corpus_id=corpus.uri,
                graph_id=graph_id,
            )
            edge_result = session.run(
                "MATCH ()-[r:RELATED {corpus_id: $corpus_id, graph_id: $graph_id}]->() "
                "RETURN count(r) AS edges",
                corpus_id=corpus.uri,
                graph_id=graph_id,
            )
            nodes = int(node_result.single()["nodes"])
            edges = int(edge_result.single()["edges"])
            return {"nodes": nodes, "edges": edges}
    finally:
        driver.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a minimal graph extraction demo against a corpus.",
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to use.")
    parser.add_argument(
        "--extractor",
        default="cooccurrence",
        help="Graph extractor identifier (default: cooccurrence).",
    )
    parser.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference (extractor_id:snapshot_id).",
    )
    parser.add_argument(
        "--build-extraction",
        action="store_true",
        help="Build a basic extraction snapshot if none exists.",
    )
    parser.add_argument(
        "--prepare-demo",
        action="store_true",
        help="Ingest a few demo notes if the corpus is empty.",
    )
    parser.add_argument(
        "--configuration",
        action="append",
        default=None,
        help="Path to graph extraction configuration YAML (repeatable).",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=None,
        help="Override key=value pairs (repeatable, dotted keys supported).",
    )
    parser.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Query Neo4j to report node/edge counts for the new graph.",
    )

    args = parser.parse_args()
    corpus = _resolve_corpus(Path(args.corpus))
    if args.prepare_demo:
        _prepare_demo_items(corpus)
    extraction_snapshot = _resolve_extraction_snapshot(
        corpus,
        snapshot_ref=args.extraction_snapshot,
        build_if_missing=args.build_extraction,
    )
    configuration = _load_graph_configuration(
        configuration_paths=args.configuration,
        overrides=args.override,
    )
    manifest = build_graph_snapshot(
        corpus,
        extractor_id=args.extractor,
        configuration_name=args.configuration_name,
        configuration=configuration,
        extraction_snapshot=extraction_snapshot,
    )
    print(manifest.model_dump_json(indent=2))
    if args.verify:
        counts = _verify_neo4j_graph(corpus=corpus, graph_id=manifest.graph_id)
        print(json.dumps({"graph_counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
