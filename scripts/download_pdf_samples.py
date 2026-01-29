"""
Download a small Portable Document Format corpus for integration testing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from biblicus.corpus import Corpus


DEFAULT_PDF_URLS = [
    "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "https://commons.wikimedia.org/wiki/Special:FilePath/Example.pdf",
    "https://commons.wikimedia.org/wiki/Special:FilePath/Test.pdf",
]


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


def download_pdf_samples(
    *,
    corpus_path: Path,
    urls: List[str],
    force: bool,
    tags: List[str],
) -> Dict[str, int]:
    """
    Download Portable Document Format sample files into a corpus.

    The repository does not include downloaded files. This script is intended for
    local integration tests and demos.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param urls: List of Portable Document Format URLs to download.
    :type urls: list[str]
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param tags: Tags to associate with ingested items.
    :type tags: list[str]
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """

    corpus = _prepare_corpus(corpus_path, force=force)
    ingested = 0
    failed = 0
    for url in urls:
        try:
            corpus.ingest_source(url, tags=tags, source_uri=url)
            ingested += 1
        except Exception:
            failed += 1
    corpus.reindex()
    return {"ingested": ingested, "failed": failed}


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """

    parser = argparse.ArgumentParser(
        description="Download Portable Document Format samples into Biblicus."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--url",
        action="append",
        default=None,
        help="Portable Document Format URL to download (repeatable).",
    )
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=None,
        help="Tag to apply to ingested items (repeatable).",
    )
    return parser


def main() -> int:
    """
    Entry point for the Portable Document Format download script.

    :return: Exit code.
    :rtype: int
    """

    parser = build_parser()
    args = parser.parse_args()
    urls = args.url or list(DEFAULT_PDF_URLS)
    tags = args.tag or ["pdf"]
    stats = download_pdf_samples(
        corpus_path=Path(args.corpus).resolve(),
        urls=urls,
        force=bool(args.force),
        tags=tags,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
