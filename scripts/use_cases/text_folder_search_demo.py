"""
Use case demo: folder of text files -> extraction -> indexing -> retrieval evidence.

This demo uses bundled demo text files and runs without external services.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.models import QueryBudget
from biblicus.retrievers import get_retriever


def _prepare_corpus(*, corpus_path: Path, force: bool) -> Corpus:
    if (corpus_path / ".biblicus" / "config.json").is_file():
        corpus = Corpus.open(corpus_path)
        if force:
            corpus.purge(confirm=corpus.name)
        return corpus
    return Corpus.init(corpus_path, force=True)


def _demo_source_files(repo_root: Path) -> List[Path]:
    items_dir = repo_root / "datasets" / "retrieval_lab" / "items"
    return sorted(items_dir.glob("*.txt"))


def run_demo(*, repo_root: Path, corpus_path: Path, force: bool) -> Dict[str, object]:
    """
    Run the demo workflow and return a JSON-serializable payload.

    :param repo_root: Repository root path used to locate bundled demo data.
    :type repo_root: pathlib.Path
    :param corpus_path: Path to the corpus directory to initialize/use.
    :type corpus_path: pathlib.Path
    :param force: Whether to purge the corpus before ingesting demo content.
    :type force: bool
    :return: JSON-serializable demo output including retrieved evidence.
    :rtype: dict[str, object]
    """
    corpus = _prepare_corpus(corpus_path=corpus_path, force=force)

    ingested_item_ids: List[str] = []
    for source_path in _demo_source_files(repo_root):
        ingest_result = corpus.ingest_source(
            str(source_path),
            tags=["use-case", "retrieval-lab"],
            source_uri=source_path.resolve().as_uri(),
            allow_external=True,
        )
        ingested_item_ids.append(ingest_result.item_id)
    corpus.reindex()

    extraction_manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="Use case: pass-through text",
        configuration={"stages": [{"extractor_id": "pass-through-text", "config": {}}]},
    )

    backend = get_retriever("sqlite-full-text-search")
    run = backend.build_snapshot(
        corpus,
        configuration_name="Use case: sqlite full text search",
        configuration={
            "chunk_size": 200,
            "chunk_overlap": 50,
            "snippet_characters": 120,
            "extraction_snapshot": f"pipeline:{extraction_manifest.snapshot_id}",
        },
    )
    budget = QueryBudget(max_total_items=5, maximum_total_characters=10000, max_items_per_source=5)
    result = backend.query(
        corpus,
        snapshot=run,
        query_text="Beta unique signal for retrieval lab",
        budget=budget,
    )
    if not result.evidence:
        raise AssertionError("Expected non-empty evidence list from retrieval")

    return {
        "corpus_path": str(corpus_path),
        "retriever_id": run.configuration.retriever_id,
        "extraction_snapshot_id": extraction_manifest.snapshot_id,
        "retrieval_snapshot_id": run.snapshot_id,
        "ingested_item_ids": ingested_item_ids,
        "query_text": result.query_text,
        "evidence": [e.model_dump() for e in result.evidence],
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build an argument parser for this demo script.

    :return: Parser for command-line arguments.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Use case demo: folder of text files -> extraction -> indexing -> retrieval."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path.")
    parser.add_argument("--force", action="store_true", help="Purge corpus before running.")
    return parser


def main() -> int:
    """
    Command-line entrypoint.

    :return: Exit code.
    :rtype: int
    """
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parent.parent.parent
    payload = run_demo(
        repo_root=repo_root,
        corpus_path=Path(args.corpus).resolve(),
        force=bool(args.force),
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
