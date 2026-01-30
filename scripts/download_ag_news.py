"""
Download the AG News dataset into a Biblicus corpus.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from biblicus.corpus import Corpus

LABELS = ["World", "Sports", "Business", "Sci/Tech"]


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for dataset downloads.

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


def _count_existing_ag_news_items(corpus: Corpus) -> int:
    """
    Count existing AG News items in the corpus.

    :param corpus: Corpus instance to inspect.
    :type corpus: Corpus
    :return: Count of existing AG News items.
    :rtype: int
    """
    catalog = corpus.load_catalog()
    return sum(1 for item in catalog.items.values() if "ag_news" in item.tags)


def download_ag_news_corpus(
    *, corpus_path: Path, split: str, limit: int, force: bool, resume: bool
) -> Dict[str, int]:
    """
    Download AG News samples into a corpus.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param split: Dataset split to load.
    :type split: str
    :param limit: Maximum number of samples to ingest.
    :type limit: int
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "AG News download requires the datasets library. "
            "Install with: python3 -m pip install 'biblicus[datasets]'"
        ) from exc

    corpus = _prepare_corpus(corpus_path, force=force)
    existing = 0
    if resume and not force:
        existing = _count_existing_ag_news_items(corpus)
        if existing >= limit:
            return {"ingested": 0, "skipped": 0, "existing": existing, "target": limit}
    dataset = load_dataset("ag_news", split=split)
    ingested = 0
    skipped = 0
    remaining = max(0, limit - existing)
    for index, record in enumerate(dataset):
        if index < existing:
            continue
        if ingested >= remaining:
            break
        text = (record.get("text") or "").strip()
        if not text:
            skipped += 1
            continue
        label_value = record.get("label")
        label_name = LABELS[label_value] if isinstance(label_value, int) else "unknown"
        title = f"AG News {split} {index}"
        tags = ["ag_news", f"label:{label_name}"]
        corpus.ingest_note(text, title=title, tags=tags)
        ingested += 1
    corpus.reindex()
    return {"ingested": ingested, "skipped": skipped, "existing": existing, "target": limit}


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Download AG News into Biblicus.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--split", default="train", help="Dataset split to ingest.")
    parser.add_argument("--limit", type=int, default=1000, help="Number of rows to ingest.")
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip items already ingested into the corpus.",
    )
    return parser


def main() -> int:
    """
    Entry point for the AG News download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    stats = download_ag_news_corpus(
        corpus_path=Path(args.corpus).resolve(),
        split=args.split,
        limit=args.limit,
        force=args.force,
        resume=args.resume,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
