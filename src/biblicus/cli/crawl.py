"""
Website crawl command for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..corpus import Corpus
from ..crawl import CrawlRequest, crawl_into_corpus
from .common import (
    _add_common_corpus_arg,
    _parse_tags,
)


def cmd_crawl(arguments: argparse.Namespace) -> int:
    """
    Crawl a website prefix into a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    tags = _parse_tags(arguments.tags, arguments.tag)
    request = CrawlRequest(
        root_url=arguments.root_url,
        allowed_prefix=arguments.allowed_prefix,
        max_items=arguments.max_items,
        tags=tags,
    )
    result = crawl_into_corpus(corpus=corpus, request=request)
    print(result.model_dump_json(indent=2))
    return 0


def register_crawl_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the crawl commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_crawl = subparsers.add_parser("crawl", help="Crawl a website prefix into the corpus.")
    _add_common_corpus_arg(p_crawl)
    p_crawl.add_argument(
        "--root-url", required=True, help="Root uniform resource locator to fetch."
    )
    p_crawl.add_argument(
        "--allowed-prefix",
        required=True,
        help="Uniform resource locator prefix that limits which links are eligible for crawl.",
    )
    p_crawl.add_argument(
        "--max-items", type=int, default=50, help="Maximum number of items to store."
    )
    p_crawl.add_argument(
        "--tags", default=None, help="Comma-separated tags to apply to stored items."
    )
    p_crawl.add_argument("--tag", action="append", help="Repeatable tag to apply to stored items.")
    p_crawl.set_defaults(func=cmd_crawl)
