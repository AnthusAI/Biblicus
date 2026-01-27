"""
Command-line interface for Biblicus.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import ValidationError

from .backends import get_backend
from .corpus import Corpus
from .evaluation import evaluate_run, load_dataset
from .models import QueryBudget
from .uris import corpus_ref_to_path


def _add_common_corpus_arg(parser: argparse.ArgumentParser) -> None:
    """
    Add the common --corpus argument to a parser.

    :param parser: Argument parser to modify.
    :type parser: argparse.ArgumentParser
    :return: None.
    :rtype: None
    """

    parser.add_argument(
        "--corpus",
        type=str,
        default=argparse.SUPPRESS,
        dest="corpus",
        help=(
            "Corpus path or uniform resource identifier (defaults to searching from the current working directory "
            "upward)."
        ),
    )


def cmd_init(arguments: argparse.Namespace) -> int:
    """
    Initialize a new corpus from command-line interface arguments.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """

    corpus_path = corpus_ref_to_path(arguments.path)
    corpus = Corpus.init(corpus_path, force=arguments.force)
    print(f"Initialized corpus at {corpus.root}")
    return 0


def _parse_tags(raw: Optional[str], raw_list: Optional[List[str]]) -> List[str]:
    """
    Parse and deduplicate tag strings.

    :param raw: Comma-separated tag string.
    :type raw: str or None
    :param raw_list: Repeated tag list.
    :type raw_list: list[str] or None
    :return: Deduplicated tag list.
    :rtype: list[str]
    """

    parsed_tags: List[str] = []
    if raw:
        parsed_tags.extend([tag.strip() for tag in raw.split(",") if tag.strip()])
    if raw_list:
        parsed_tags.extend([tag.strip() for tag in raw_list if tag.strip()])

    seen_tags = set()
    deduplicated_tags: List[str] = []
    for tag_value in parsed_tags:
        if tag_value not in seen_tags:
            seen_tags.add(tag_value)
            deduplicated_tags.append(tag_value)
    return deduplicated_tags


def cmd_ingest(arguments: argparse.Namespace) -> int:
    """
    Ingest items into a corpus from command-line interface arguments.

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

    results = []

    if arguments.note is not None or arguments.stdin:
        text = arguments.note if arguments.note is not None else sys.stdin.read()
        ingest_result = corpus.ingest_note(
            text,
            title=arguments.title,
            tags=tags,
            source_uri="stdin" if arguments.stdin else "text",
        )
        results.append(ingest_result)

    for source_path in arguments.files or []:
        results.append(corpus.ingest_source(source_path, tags=tags))

    if not results:
        print("Nothing to ingest: provide file paths, --note, or --stdin", file=sys.stderr)
        return 2

    for ingest_result in results:
        print(f"{ingest_result.item_id}\t{ingest_result.relpath}\t{ingest_result.sha256}")
    return 0


def cmd_list(arguments: argparse.Namespace) -> int:
    """
    List items from the corpus.

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
    items = corpus.list_items(limit=arguments.limit)
    for item in items:
        title = item.title or ""
        print(f"{item.id}\t{item.created_at}\t{item.relpath}\t{title}\t{','.join(item.tags)}")
    return 0


def cmd_show(arguments: argparse.Namespace) -> int:
    """
    Show an item from the corpus.

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
    item = corpus.get_item(arguments.id)
    print(item.model_dump_json(indent=2))
    return 0


def cmd_reindex(arguments: argparse.Namespace) -> int:
    """
    Rebuild the corpus catalog.

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
    stats = corpus.reindex()
    print(json.dumps(stats, indent=2, sort_keys=False))
    return 0


def cmd_purge(arguments: argparse.Namespace) -> int:
    """
    Purge all items and derived artifacts from a corpus.

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
    if arguments.confirm is None:
        raise ValueError(f"Purging is dangerous: pass --confirm {corpus.name!r} to proceed")
    corpus.purge(confirm=arguments.confirm)
    print(f"Purged corpus {corpus.root}")
    return 0


def _parse_config_pairs(pairs: Optional[List[str]]) -> Dict[str, object]:
    """
    Parse repeated key=value config pairs.

    :param pairs: Config pairs supplied via the command-line interface.
    :type pairs: list[str] or None
    :return: Parsed config mapping.
    :rtype: dict[str, object]
    :raises ValueError: If any entry is not key=value.
    """

    config: Dict[str, object] = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"Config values must be key=value (got {item!r})")
        key, raw = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Config keys must be non-empty")
        value: object = raw
        if raw.isdigit():
            value = int(raw)
        else:
            try:
                value = float(raw)
            except ValueError:
                value = raw
        config[key] = value
    return config


def _budget_from_args(arguments: argparse.Namespace) -> QueryBudget:
    """
    Build a QueryBudget from command-line interface arguments.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Query budget instance.
    :rtype: QueryBudget
    """

    return QueryBudget(
        max_total_items=arguments.max_total_items,
        max_total_characters=arguments.max_total_characters,
        max_items_per_source=arguments.max_items_per_source,
    )


def cmd_build(arguments: argparse.Namespace) -> int:
    """
    Build a retrieval run for a backend.

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
    backend = get_backend(arguments.backend)
    config = _parse_config_pairs(arguments.config)
    run = backend.build_run(corpus, recipe_name=arguments.recipe_name, config=config)
    print(run.model_dump_json(indent=2))
    return 0


def cmd_query(arguments: argparse.Namespace) -> int:
    """
    Execute a retrieval query.

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
    run_id = arguments.run or corpus.latest_run_id
    if not run_id:
        raise ValueError("No run identifier provided and no latest run is recorded for this corpus")
    run = corpus.load_run(run_id)
    if arguments.backend and arguments.backend != run.recipe.backend_id:
        raise ValueError(
            f"Backend mismatch: run uses {run.recipe.backend_id!r} but {arguments.backend!r} was requested"
        )
    backend = get_backend(run.recipe.backend_id)
    query_text = arguments.query if arguments.query is not None else sys.stdin.read()
    budget = _budget_from_args(arguments)
    result = backend.query(corpus, run=run, query_text=query_text, budget=budget)
    print(result.model_dump_json(indent=2))
    return 0


def cmd_eval(arguments: argparse.Namespace) -> int:
    """
    Evaluate a retrieval run against a dataset.

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
    run_id = arguments.run or corpus.latest_run_id
    if not run_id:
        raise ValueError("No run identifier provided and no latest run is recorded for this corpus")
    run = corpus.load_run(run_id)
    dataset = load_dataset(Path(arguments.dataset))
    budget = _budget_from_args(arguments)
    result = evaluate_run(corpus=corpus, run=run, dataset=dataset, budget=budget)
    print(result.model_dump_json(indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser instance.
    :rtype: argparse.ArgumentParser
    """

    parser = argparse.ArgumentParser(
        prog="biblicus",
        description="Biblicus command-line interface (minimum viable product)",
    )
    parser.add_argument(
        "--corpus",
        type=str,
        default=None,
        dest="corpus",
        help=(
            "Corpus path or uniform resource identifier (defaults to searching from the current working directory "
            "upward). "
            "Can be provided before or after the subcommand."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize a new corpus at PATH.")
    p_init.add_argument("path", help="Corpus path or file:// uniform resource identifier.")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing config if present.")
    p_init.set_defaults(func=cmd_init)

    p_ingest = sub.add_parser("ingest", help="Ingest file(s) and/or text into the corpus.")
    _add_common_corpus_arg(p_ingest)
    p_ingest.add_argument("files", nargs="*", help="File paths to ingest.")
    p_ingest.add_argument("--note", default=None, help="Ingest a literal note as Markdown text.")
    p_ingest.add_argument("--stdin", action="store_true", help="Read text to ingest from standard input.")
    p_ingest.add_argument("--title", default=None, help="Optional title (for --note/--stdin).")
    p_ingest.add_argument("--tags", default=None, help="Comma-separated tags.")
    p_ingest.add_argument("--tag", action="append", help="Repeatable tag.")
    p_ingest.set_defaults(func=cmd_ingest)

    p_list = sub.add_parser("list", help="List recently ingested items.")
    _add_common_corpus_arg(p_list)
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show metadata for an item identifier.")
    _add_common_corpus_arg(p_show)
    p_show.add_argument("id", help="Item identifier (universally unique identifier).")
    p_show.set_defaults(func=cmd_show)

    p_reindex = sub.add_parser("reindex", help="Rebuild/refresh the corpus catalog from the on-disk corpus.")
    _add_common_corpus_arg(p_reindex)
    p_reindex.set_defaults(func=cmd_reindex)

    p_purge = sub.add_parser("purge", help="Delete all items and derived files (requires confirmation).")
    _add_common_corpus_arg(p_purge)
    p_purge.add_argument(
        "--confirm",
        default=None,
        help="Type the corpus name (directory basename) to confirm purging.",
    )
    p_purge.set_defaults(func=cmd_purge)

    p_build = sub.add_parser("build", help="Build a retrieval backend run for the corpus.")
    _add_common_corpus_arg(p_build)
    p_build.add_argument(
        "--backend",
        required=True,
        help="Backend identifier (for example, scan, sqlite-full-text-search).",
    )
    p_build.add_argument("--recipe-name", default="default", help="Human-readable recipe name.")
    p_build.add_argument(
        "--config",
        action="append",
        default=None,
        help="Backend config as key=value (repeatable).",
    )
    p_build.set_defaults(func=cmd_build)

    p_query = sub.add_parser("query", help="Run a retrieval query.")
    _add_common_corpus_arg(p_query)
    p_query.add_argument("--run", default=None, help="Run identifier (defaults to latest run).")
    p_query.add_argument("--backend", default=None, help="Validate backend identifier.")
    p_query.add_argument("--query", default=None, help="Query text (defaults to standard input).")
    p_query.add_argument("--max-total-items", type=int, default=5)
    p_query.add_argument("--max-total-characters", type=int, default=2000)
    p_query.add_argument("--max-items-per-source", type=int, default=5)
    p_query.set_defaults(func=cmd_query)

    p_eval = sub.add_parser("eval", help="Evaluate a run against a dataset.")
    _add_common_corpus_arg(p_eval)
    p_eval.add_argument("--run", default=None, help="Run identifier (defaults to latest run).")
    p_eval.add_argument(
        "--dataset",
        required=True,
        help="Path to dataset JavaScript Object Notation file.",
    )
    p_eval.add_argument("--max-total-items", type=int, default=5)
    p_eval.add_argument("--max-total-characters", type=int, default=2000)
    p_eval.add_argument("--max-items-per-source", type=int, default=5)
    p_eval.set_defaults(func=cmd_eval)

    return parser


def main(argument_list: Optional[List[str]] = None) -> int:
    """
    Entry point for the Biblicus command-line interface.

    :param argument_list: Optional command-line interface arguments.
    :type argument_list: list[str] or None
    :return: Exit code.
    :rtype: int
    """

    parser = build_parser()
    arguments = parser.parse_args(argument_list)
    try:
        return int(arguments.func(arguments))
    except (
        FileNotFoundError,
        FileExistsError,
        KeyError,
        ValueError,
        NotImplementedError,
        ValidationError,
    ) as exception:
        message = exception.args[0] if getattr(exception, "args", None) else str(exception)
        print(str(message), file=sys.stderr)
        return 2
