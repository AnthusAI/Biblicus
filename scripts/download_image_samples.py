"""
Download a small image corpus for integration testing.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

from biblicus.corpus import Corpus

DEFAULT_IMAGE_URLS = [
    "https://commons.wikimedia.org/wiki/Special:FilePath/Hello_world.png",
    "https://commons.wikimedia.org/wiki/Special:FilePath/Example.jpg",
]

_BLANK_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0bIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _blank_portable_network_graphics_bytes() -> bytes:
    """
    Return a deterministic blank Portable Network Graphics payload.

    This is used to ensure integration tests always include an image item with no text.

    :return: Portable Network Graphics bytes.
    :rtype: bytes
    """

    return _BLANK_PNG_BYTES


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


def download_image_samples(
    *,
    corpus_path: Path,
    urls: List[str],
    force: bool,
    tags: List[str],
    delay_seconds: float,
) -> Dict[str, int]:
    """
    Download image sample files into a corpus.

    The repository does not include downloaded files. This script is intended for local integration tests and demos.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param urls: List of image URLs to download.
    :type urls: list[str]
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param tags: Base tags to associate with ingested items.
    :type tags: list[str]
    :param delay_seconds: Delay between downloads to reduce rate limiting.
    :type delay_seconds: float
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """

    corpus = _prepare_corpus(corpus_path, force=force)
    ingested = 0
    failed = 0

    corpus.ingest_item(
        _blank_portable_network_graphics_bytes(),
        filename="blank.png",
        media_type="image/png",
        source_uri="generated:blank.png",
        tags=[*tags, "image-without-text"],
    )
    ingested += 1

    for url in urls:
        try:
            extra_tags: list[str] = []
            lower = url.lower()
            if "hello_world" in lower:
                extra_tags = ["image-with-text"]
            elif "example.jpg" in lower:
                extra_tags = ["image-jpeg-sample"]
            corpus.ingest_source(url, tags=[*tags, *extra_tags], source_uri=url)
            ingested += 1
        except Exception:
            failed += 1
        time.sleep(delay_seconds)
    corpus.reindex()
    return {"ingested": ingested, "failed": failed}


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """

    parser = argparse.ArgumentParser(description="Download image samples into Biblicus.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--url",
        action="append",
        default=None,
        help="Image URL to download (repeatable).",
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
    parser.add_argument(
        "--delay-seconds",
        default="0.5",
        help="Delay between downloads to reduce rate limiting.",
    )
    return parser


def main() -> int:
    """
    Entry point for the image download script.

    :return: Exit code.
    :rtype: int
    """

    parser = build_parser()
    args = parser.parse_args()
    urls = args.url or list(DEFAULT_IMAGE_URLS)
    tags = args.tag or ["image", "integration"]
    stats = download_image_samples(
        corpus_path=Path(args.corpus).resolve(),
        urls=urls,
        force=bool(args.force),
        tags=tags,
        delay_seconds=float(args.delay_seconds),
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
