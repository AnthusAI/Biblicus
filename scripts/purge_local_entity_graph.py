#!/usr/bin/env python3
"""
Purge local Biblicus entity graph artifacts for a corpus (Neo4j + snapshot dirs).

Does not touch cloud / Papyrus production records.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from biblicus.corpus import Corpus
from biblicus.graph.neo4j import create_neo4j_driver, resolve_neo4j_settings


def _purge_neo4j(*, corpus_uri: str, dry_run: bool) -> int:
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        with driver.session(database=settings.database) as session:
            count = session.run(
                """
                MATCH (n:GraphNode {corpus_id: $corpus_id})
                RETURN count(n) AS c
                """,
                corpus_id=corpus_uri,
            ).single()["c"]
            if dry_run:
                print(f"[dry-run] would delete {count} GraphNode rows for corpus_id={corpus_uri!r}")
                return count
            session.run(
                """
                MATCH (n:GraphNode {corpus_id: $corpus_id})
                DETACH DELETE n
                """,
                corpus_id=corpus_uri,
            )
            print(f"deleted {count} GraphNode rows for corpus_id={corpus_uri!r}")
            return count
    finally:
        driver.close()


def _purge_snapshot_dirs(*, graph_dir: Path, extractors: list[str], dry_run: bool) -> None:
    for extractor_id in extractors:
        extractor_dir = graph_dir / extractor_id
        if not extractor_dir.is_dir():
            print(f"skip missing {extractor_dir}")
            continue
        for child in extractor_dir.iterdir():
            if child.name == "latest.json":
                continue
            if child.is_dir():
                if dry_run:
                    print(f"[dry-run] would remove {child}")
                else:
                    shutil.rmtree(child)
                    print(f"removed {child}")
        latest = extractor_dir / "latest.json"
        if latest.is_file() and not dry_run:
            latest.unlink()
            print(f"removed {latest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        default="corpora/AI-ML-research",
        help="Corpus path (default: corpora/AI-ML-research)",
    )
    parser.add_argument(
        "--extractor",
        action="append",
        default=["ner-entities", "simple-entities"],
        help="Graph extractor snapshot dirs to purge (repeatable)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    corpus = Corpus.open(args.corpus)
    corpus_uri = corpus.uri
    graph_dir = corpus.root / "graph"
    _purge_neo4j(corpus_uri=corpus_uri, dry_run=args.dry_run)
    _purge_snapshot_dirs(graph_dir=graph_dir, extractors=list(args.extractor), dry_run=args.dry_run)
  # Drop stale local export bundles under analysis/ if present
    analysis_exports = corpus.root / "analysis" / "graph-exports"
    if analysis_exports.is_dir():
        for child in analysis_exports.iterdir():
            if dry_run:
                print(f"[dry-run] would remove {child}")
            else:
                shutil.rmtree(child) if child.is_dir() else child.unlink()
                print(f"removed {child}")
    print(json.dumps({"corpus_uri": corpus_uri, "status": "purged" if not args.dry_run else "dry-run"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
