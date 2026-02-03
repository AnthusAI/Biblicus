"""
Use case demo: short notes -> evidence -> context pack.

This demo is intentionally deterministic and requires no external services.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from biblicus.context import (
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_token_budget,
)
from biblicus.corpus import Corpus
from biblicus.models import QueryBudget
from biblicus.retrievers import get_retriever


def _prepare_corpus(*, corpus_path: Path, force: bool) -> Corpus:
    if (corpus_path / ".biblicus" / "config.json").is_file():
        corpus = Corpus.open(corpus_path)
        if force:
            corpus.purge(confirm=corpus.name)
        return corpus
    return Corpus.init(corpus_path, force=True)


def run_demo(*, corpus_path: Path, force: bool) -> Dict[str, object]:
    """
    Run the demo workflow and return a JSON-serializable payload.

    :param corpus_path: Path to the corpus directory to initialize/use.
    :type corpus_path: pathlib.Path
    :param force: Whether to purge the corpus before ingesting demo content.
    :type force: bool
    :return: JSON-serializable demo output including retrieved evidence and a fitted context pack.
    :rtype: dict[str, object]
    """
    corpus = _prepare_corpus(corpus_path=corpus_path, force=force)

    notes: List[tuple[str, str]] = [
        ("User name", "The user's name is Tactus Maximus."),
        ("Button style preference", "Primary button style preference: favorite color is magenta."),
        ("Style preference", "The user prefers concise answers."),
        ("Language preference", "The user dislikes idioms and abbreviations."),
        ("Engineering preference", "The user likes behavior-driven development."),
    ]
    for note_title, note_text in notes:
        corpus.ingest_note(note_text, title=note_title, tags=["use-case", "notes"])

    backend = get_retriever("scan")
    snapshot = backend.build_snapshot(
        corpus,
        configuration_name="Use case: notes to context pack",
        configuration={},
    )
    budget = QueryBudget(
        max_total_items=5, maximum_total_characters=4000, max_items_per_source=None
    )
    result = backend.query(
        corpus,
        snapshot=snapshot,
        query_text="Primary button style preference",
        budget=budget,
    )
    if not result.evidence:
        raise AssertionError("Expected non-empty evidence list from retrieval")

    policy = ContextPackPolicy(join_with="\n\n")
    context_pack = build_context_pack(result, policy=policy)
    fitted_context_pack = fit_context_pack_to_token_budget(
        context_pack,
        policy=policy,
        token_budget=TokenBudget(max_tokens=120),
    )

    if "magenta" not in fitted_context_pack.text.lower():
        raise AssertionError("Expected context pack to include the user's color preference")

    return {
        "corpus_path": str(corpus_path),
        "retriever_id": snapshot.configuration.retriever_id,
        "snapshot_id": snapshot.snapshot_id,
        "query_text": result.query_text,
        "evidence": [e.model_dump() for e in result.evidence],
        "context_pack_text": fitted_context_pack.text,
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build an argument parser for this demo script.

    :return: Parser for command-line arguments.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Use case demo: short notes -> evidence -> context pack."
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
    payload = run_demo(corpus_path=Path(args.corpus).resolve(), force=bool(args.force))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
