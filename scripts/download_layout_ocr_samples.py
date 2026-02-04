"""
Download sample documents with complex layouts for layout-aware OCR testing.

This script downloads public domain multi-column SCANNED documents suitable for
demonstrating layout-aware OCR capabilities.

NOTE: Many arXiv papers are born-digital (have selectable text) and are NOT
suitable for OCR testing. We need actual scanned images.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from biblicus.corpus import Corpus

# Public domain SCANNED multi-column documents
# These are actual image-based PDFs without text layers
DEFAULT_LAYOUT_SAMPLES = [
    # Internet Archive - Scanned academic papers from 1980s-1990s
    {
        "url": "https://archive.org/download/ERIC_ED299828/ERIC_ED299828.pdf",
        "tags": ["scanned", "two-column", "academic", "eric"],
        "description": "ERIC Educational Research Document (scanned, 1988)",
    },
    # TODO: Add more verified scanned sources
    # Requirements:
    # - Must be actual scans (no text layer)
    # - Multi-column layout
    # - Public domain or open access
    # - Stable URLs that won't break
]


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for layout OCR sample downloads.

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


def download_layout_ocr_samples(
    *,
    corpus_path: Path,
    samples: List[Dict[str, object]],
    force: bool,
    additional_tags: List[str],
) -> Dict[str, int]:
    """
    Download layout OCR sample files into a corpus.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param samples: List of sample definitions with url, tags, and metadata.
    :type samples: list[dict]
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param additional_tags: Additional tags to apply to all items.
    :type additional_tags: list[str]
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """
    corpus = _prepare_corpus(corpus_path, force=force)
    ingested = 0
    failed = 0
    skipped = 0

    for sample in samples:
        url = sample["url"]
        tags = list(sample.get("tags", [])) + additional_tags
        is_optional = sample.get("optional", False)

        try:
            print(f"Downloading: {sample.get('description', url)}")
            corpus.ingest_source(url, tags=tags, source_uri=url)
            ingested += 1
            print("  ✓ Success")
        except Exception as e:
            if is_optional:
                print(f"  ⊘ Skipped (optional): {e}")
                skipped += 1
            else:
                print(f"  ✗ Failed: {e}")
                failed += 1

    corpus.reindex()
    return {"ingested": ingested, "failed": failed, "skipped": skipped}


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Download multi-column documents for layout-aware OCR demos and tests."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--url",
        action="append",
        default=None,
        help="Custom URL to download (repeatable). If not specified, uses default samples.",
    )
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=None,
        help="Additional tag to apply to ingested items (repeatable).",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Include optional samples that may not always be available.",
    )
    return parser


def main() -> int:
    """
    Entry point for the layout OCR sample download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.url:
        # Custom URLs provided
        samples = [{"url": url, "tags": ["custom"]} for url in args.url]
    else:
        # Use default samples
        samples = [
            s
            for s in DEFAULT_LAYOUT_SAMPLES
            if not s.get("optional", False) or args.include_optional
        ]

    additional_tags = args.tag or ["layout-ocr-sample"]

    stats = download_layout_ocr_samples(
        corpus_path=Path(args.corpus).resolve(),
        samples=samples,
        force=bool(args.force),
        additional_tags=additional_tags,
    )

    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
