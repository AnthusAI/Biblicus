"""
Programmatic Wikipedia demo for Biblicus retrieval and context packs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import quote
from urllib.request import Request, urlopen

from biblicus.backends import get_backend
from biblicus.context import (
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_token_budget,
)
from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_run
from biblicus.models import QueryBudget


DEFAULT_TITLES = [
    "Retrieval-augmented generation",
    "Information retrieval",
    "Vector database",
    "Knowledge base",
    "Semantic search",
    "Search engine",
]


def fetch_wikipedia_summary(title: str) -> Tuple[str, str, str]:
    """
    Fetch a Wikipedia summary for a page title.

    :param title: Wikipedia page title.
    :type title: str
    :return: Tuple of extract text, page uniform resource locator, and resolved title.
    :rtype: tuple[str, str, str]
    """
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    request = Request(url, headers={"User-Agent": "biblicus/0"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    extract = payload.get("extract") or ""
    resolved_title = payload.get("title") or title
    content_urls = payload.get("content_urls") or {}
    desktop_urls = content_urls.get("desktop") or {}
    page_url = desktop_urls.get("page") or f"https://en.wikipedia.org/wiki/{quote(resolved_title)}"
    return extract, page_url, resolved_title


def prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for the demo.

    :param path: Corpus path.
    :type path: Path
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :return: Corpus instance.
    :rtype: Corpus
    :raises ValueError: If the target path is non-empty without force.
    """
    if (path / ".biblicus" / "config.json").is_file():
        corpus = Corpus.open(path)
        if force:
            corpus.purge(confirm=corpus.name)
        return corpus
    if path.exists() and any(path.iterdir()) and not force:
        raise ValueError("Target corpus directory is not empty. Use --force to initialize anyway.")
    return Corpus.init(path, force=True)


def ingest_wikipedia_summaries(
    corpus: Corpus, titles: Iterable[str]
) -> Dict[str, int]:
    """
    Ingest Wikipedia summaries as notes in a corpus.

    :param corpus: Corpus to receive notes.
    :type corpus: Corpus
    :param titles: Wikipedia page titles.
    :type titles: Iterable[str]
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """
    ingested = 0
    skipped = 0
    for title in titles:
        extract, page_url, resolved_title = fetch_wikipedia_summary(title)
        if not extract.strip():
            skipped += 1
            continue
        corpus.ingest_note(
            extract,
            title=resolved_title,
            tags=["wikipedia", "rag-demo"],
            source_uri=page_url,
        )
        ingested += 1
    corpus.reindex()
    return {"ingested": ingested, "skipped": skipped}


def run_demo(*, corpus_path: Path, limit: int, force: bool, query: str) -> Dict[str, object]:
    """
    Run the end-to-end Wikipedia demo.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param limit: Number of titles to ingest.
    :type limit: int
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param query: Retrieval query text.
    :type query: str
    :return: Summary output including query results and context pack text.
    :rtype: dict[str, object]
    """
    corpus = prepare_corpus(corpus_path, force=force)
    titles = DEFAULT_TITLES[:limit]
    ingest_stats = ingest_wikipedia_summaries(corpus, titles)

    extraction_manifest = build_extraction_run(
        corpus,
        extractor_id="pipeline",
        recipe_name="Wikipedia demo extraction",
        config={"steps": [{"extractor_id": "pass-through-text", "config": {}}]},
    )

    backend = get_backend("sqlite-full-text-search")
    run = backend.build_run(
        corpus,
        recipe_name="Wikipedia demo retrieval",
        config={
            "extraction_run": f"pipeline:{extraction_manifest.run_id}",
            "chunk_size": 220,
            "chunk_overlap": 40,
            "snippet_characters": 160,
        },
    )
    budget = QueryBudget(max_total_items=5, max_total_characters=1600, max_items_per_source=1)
    retrieval_result = backend.query(corpus, run=run, query_text=query, budget=budget)

    policy = ContextPackPolicy(join_with="\n\n")
    context_pack = build_context_pack(retrieval_result, policy=policy)
    token_budget = TokenBudget(max_tokens=400)
    fitted_context_pack = fit_context_pack_to_token_budget(
        context_pack,
        policy=policy,
        token_budget=token_budget,
    )

    return {
        "ingest_stats": ingest_stats,
        "extraction_run_id": extraction_manifest.run_id,
        "retrieval_run_id": run.run_id,
        "query_text": query,
        "evidence": [evidence.model_dump() for evidence in retrieval_result.evidence],
        "context_pack_text": fitted_context_pack.text,
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Run the Wikipedia retrieval demo.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--limit", type=int, default=5, help="Number of Wikipedia pages to download."
    )
    parser.add_argument(
        "--force", action="store_true", help="Purge existing corpus content."
    )
    parser.add_argument(
        "--query",
        default="retrieval augmented generation",
        help="Query text to run against the corpus.",
    )
    return parser


def main() -> int:
    """
    Entry point for the Wikipedia retrieval demo.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    output = run_demo(
        corpus_path=Path(args.corpus).resolve(),
        limit=args.limit,
        force=args.force,
        query=args.query,
    )
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
