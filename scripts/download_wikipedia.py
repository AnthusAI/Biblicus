"""
Download a small Wikipedia corpus for integration testing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote
from urllib.request import Request, urlopen

from biblicus.corpus import Corpus


DEFAULT_TITLES = [
    "Ada Lovelace",
    "Alan Turing",
    "Grace Hopper",
    "Claude Shannon",
    "Alonzo Church",
    "John McCarthy (computer scientist)",
    "Edsger W. Dijkstra",
    "Donald Knuth",
    "Barbara Liskov",
    "Niklaus Wirth",
    "John von Neumann",
    "George Boole",
    "Kurt Godel",
    "Noam Chomsky",
    "Marvin Minsky",
    "Herbert A. Simon",
    "E. F. Codd",
    "Ken Thompson",
    "Dennis Ritchie",
    "Brian Kernighan",
    "Tim Berners-Lee",
    "Vint Cerf",
    "Leslie Lamport",
    "Ivan Sutherland",
    "Radia Perlman",
]


def _fetch_summary(title: str) -> Tuple[str, str, str]:
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


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for integration downloads.

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


def download_wikipedia_corpus(*, corpus_path: Path, limit: int, force: bool) -> Dict[str, int]:
    """
    Download Wikipedia summaries into a corpus.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param limit: Number of pages to download.
    :type limit: int
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """

    corpus = _prepare_corpus(corpus_path, force=force)
    titles = DEFAULT_TITLES[:limit]
    ingested = 0
    skipped = 0
    for title in titles:
        extract, page_url, resolved_title = _fetch_summary(title)
        if not extract.strip():
            skipped += 1
            continue
        corpus.ingest_note(extract, title=resolved_title, tags=["wikipedia"], source_uri=page_url)
        ingested += 1
    corpus.reindex()
    return {"ingested": ingested, "skipped": skipped}


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Download a Wikipedia corpus into Biblicus.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--limit", type=int, default=5, help="Number of pages to download.")
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    return parser


def main() -> int:
    """
    Entry point for the Wikipedia download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    stats = download_wikipedia_corpus(
        corpus_path=Path(args.corpus).resolve(),
        limit=args.limit,
        force=args.force,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
