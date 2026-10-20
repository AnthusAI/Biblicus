"""
Snapshot build, query, context pack, and evaluation commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from ..api import InvalidRequestError, validate_request
from ..context import (
    CharacterBudget,
    ContextBlockBuildRequest,
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_character_budget,
    fit_context_pack_to_token_budget,
)
from ..corpus import Corpus
from ..evaluation.retrieval import evaluate_snapshot, load_dataset
from ..models import (
    QueryBudget,
    RetrievalResult,
)
from ..retrievers import get_retriever
from . import common
from .common import (
    _add_common_corpus_arg,
    _add_dependency_flags,
    _dependency_mode,
    _open_corpus_from_arguments,
)


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
        offset=getattr(arguments, "offset", 0),
        maximum_total_characters=arguments.maximum_total_characters,
        max_items_per_source=arguments.max_items_per_source,
    )


def cmd_build(arguments: argparse.Namespace) -> int:
    """
    Build a retrieval snapshot for a retriever.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    retriever = get_retriever(arguments.retriever)

    base_config: Dict[str, object] = {}
    if getattr(arguments, "configuration", None):
        base_config = load_configuration_view(
            arguments.configuration,
            configuration_label="Configuration file",
            mapping_error_message="Retrieval snapshot configuration must be a mapping/object",
        )

    overrides = parse_dotted_overrides(arguments.override)
    configuration = apply_dotted_overrides(base_config, overrides)

    from ..workflow import build_plan_for_index

    dependency_mode = _dependency_mode(arguments)
    index_plan = build_plan_for_index(
        corpus,
        retriever_id=arguments.retriever,
        pipeline_config=None,
        index_config=configuration,
        load_handler_available=False,
    )
    common._execute_dependency_plan(
        index_plan,
        corpus=corpus,
        label="index",
        mode=dependency_mode,
    )

    snapshot = retriever.build_snapshot(
        corpus,
        configuration_name=arguments.configuration_name,
        configuration=configuration,
    )
    print(snapshot.model_dump_json(indent=2))
    return 0


def cmd_query(arguments: argparse.Namespace) -> int:
    """
    Execute a retrieval query.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import QueryRequest, query

    corpus = _open_corpus_from_arguments(arguments)
    snapshot_id = arguments.snapshot or corpus.latest_snapshot_id
    if not snapshot_id:
        from ..workflow import build_plan_for_query

        dependency_mode = _dependency_mode(arguments)
        retriever_id = arguments.retriever or "tf-vector"
        query_plan = build_plan_for_query(
            corpus,
            retriever_id=retriever_id,
            pipeline_config=None,
            index_config=None,
            load_handler_available=False,
        )
        common._execute_dependency_plan(
            query_plan,
            corpus=corpus,
            label="query",
            mode=dependency_mode,
        )
        snapshot_id = corpus.latest_snapshot_id
    query_text = arguments.query if arguments.query is not None else sys.stdin.read()
    request = validate_request(
        QueryRequest,
        "query",
        corpus_path=str(corpus.root),
        query_text=query_text,
        snapshot_id=snapshot_id,
        retriever_id=arguments.retriever,
        budget=_budget_from_args(arguments),
        reranker_id=getattr(arguments, "reranker_id", None),
        minimum_score=getattr(arguments, "minimum_score", None),
    )
    print(query(request).model_dump_json(indent=2))
    return 0


def cmd_context_pack_build(arguments: argparse.Namespace) -> int:
    """
    Build a context pack from a retrieval result.

    The retrieval result is read from standard input as JavaScript Object Notation.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    input_text = sys.stdin.read()
    if not input_text.strip():
        raise ValueError(
            "Context pack build requires a retrieval result JavaScript Object Notation on standard input"
        )
    retrieval_result = RetrievalResult.model_validate_json(input_text)
    join_with = bytes(arguments.join_with, "utf-8").decode("unicode_escape")
    policy = ContextPackPolicy(
        join_with=join_with,
        ordering=arguments.ordering,
        include_metadata=arguments.include_metadata,
    )
    context_pack = build_context_pack(retrieval_result, policy=policy)
    if arguments.max_tokens is not None:
        context_pack = fit_context_pack_to_token_budget(
            context_pack,
            policy=policy,
            token_budget=TokenBudget(max_tokens=int(arguments.max_tokens)),
        )
    if arguments.max_characters is not None:
        context_pack = fit_context_pack_to_character_budget(
            context_pack,
            policy=policy,
            character_budget=CharacterBudget(max_characters=int(arguments.max_characters)),
        )
    print(
        json.dumps(
            {
                "policy": policy.model_dump(),
                "context_pack": context_pack.model_dump(),
            },
            indent=2,
        )
    )
    return 0


def cmd_context_pack_build_blocks(arguments: argparse.Namespace) -> int:
    """
    Build a context pack from ordered context blocks.

    The build request is read from standard input as JavaScript Object Notation.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import context_pack_build_blocks

    input_text = sys.stdin.read()
    if not input_text.strip():
        raise InvalidRequestError(
            "Context block build requires a context-block request JavaScript Object Notation on standard input"
        )
    request = ContextBlockBuildRequest.model_validate_json(input_text)
    result = context_pack_build_blocks(request)
    print(json.dumps(result.model_dump(), indent=2))
    return 0


def cmd_eval(arguments: argparse.Namespace) -> int:
    """
    Evaluate a retrieval snapshot against a dataset.

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
    snapshot_id = arguments.snapshot or corpus.latest_snapshot_id
    if not snapshot_id:
        raise ValueError(
            "No snapshot identifier provided and no latest snapshot is recorded for this corpus"
        )
    snapshot = corpus.load_snapshot(snapshot_id)
    dataset = load_dataset(Path(arguments.dataset))
    budget = _budget_from_args(arguments)
    result = evaluate_snapshot(corpus=corpus, snapshot=snapshot, dataset=dataset, budget=budget)
    print(result.model_dump_json(indent=2))
    return 0


def register_build_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the snapshot build command on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_build = subparsers.add_parser("build", help="Build a retrieval snapshot for the corpus.")
    _add_common_corpus_arg(p_build)
    _add_dependency_flags(p_build)
    p_build.add_argument(
        "--retriever",
        required=True,
        help="Retriever identifier (for example, scan, sqlite-full-text-search).",
    )
    p_build.add_argument(
        "--configuration-name", default="default", help="Human-readable configuration name."
    )
    p_build.add_argument(
        "--configuration",
        default=None,
        action="append",
        help="Path to YAML configuration file (repeatable). If provided, files are composed in precedence order.",
    )
    p_build.add_argument(
        "--override",
        "--config",
        action="append",
        default=None,
        help="Configuration override as key=value (repeatable). Dotted keys create nested config mappings.",
    )
    p_build.set_defaults(func=cmd_build)


def register_query_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the query, context pack, and evaluation commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_query = subparsers.add_parser("query", help="Run a retrieval query.")
    _add_common_corpus_arg(p_query)
    _add_dependency_flags(p_query)
    p_query.add_argument(
        "--snapshot", default=None, help="Snapshot identifier (defaults to latest snapshot)."
    )
    p_query.add_argument("--retriever", default=None, help="Validate retriever identifier.")
    p_query.add_argument("--query", default=None, help="Query text (defaults to standard input).")
    p_query.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip this many ranked candidates before selecting evidence (pagination).",
    )
    p_query.add_argument("--max-total-items", type=int, default=5)
    p_query.add_argument("--maximum-total-characters", type=int, default=2000)
    p_query.add_argument("--max-items-per-source", type=int, default=5)
    p_query.add_argument(
        "--reranker-id",
        default=None,
        help="Optional reranker identifier to apply after retrieval (for example: rerank-longest-text).",
    )
    p_query.add_argument(
        "--minimum-score",
        type=float,
        default=None,
        help="Optional minimum score threshold to filter evidence after retrieval.",
    )
    p_query.set_defaults(func=cmd_query, typed_command="query")

    p_context_pack = subparsers.add_parser(
        "context-pack", help="Build context pack text from evidence."
    )
    context_pack_sub = p_context_pack.add_subparsers(dest="context_pack_command", required=True)

    p_context_pack_build = context_pack_sub.add_parser(
        "build", help="Build a context pack from a retrieval result JavaScript Object Notation."
    )
    p_context_pack_build.add_argument(
        "--join-with",
        default="\\n\\n",
        help="Separator between evidence blocks (escape sequences supported, default is two newlines).",
    )
    p_context_pack_build.add_argument(
        "--ordering",
        choices=["rank", "score", "source"],
        default="rank",
        help="Evidence ordering policy (rank, score, source).",
    )
    p_context_pack_build.add_argument(
        "--include-metadata",
        action="store_true",
        help="Include evidence metadata in each context pack block.",
    )
    p_context_pack_build.add_argument(
        "--max-tokens",
        default=None,
        type=int,
        help="Optional token budget for the final context pack using the naive-whitespace tokenizer.",
    )
    p_context_pack_build.add_argument(
        "--max-characters",
        default=None,
        type=int,
        help="Optional character budget for the final context pack.",
    )
    p_context_pack_build.set_defaults(func=cmd_context_pack_build)

    p_context_pack_build_blocks = context_pack_sub.add_parser(
        "build-blocks",
        help="Build a budgeted context pack from ordered context blocks in JavaScript Object Notation.",
    )
    p_context_pack_build_blocks.set_defaults(func=cmd_context_pack_build_blocks, typed_command="context-pack build-blocks")

    p_eval = subparsers.add_parser("eval", help="Evaluate a snapshot against a dataset.")
    _add_common_corpus_arg(p_eval)
    p_eval.add_argument(
        "--snapshot", default=None, help="Snapshot identifier (defaults to latest snapshot)."
    )
    p_eval.add_argument(
        "--dataset",
        required=True,
        help="Path to dataset JavaScript Object Notation file.",
    )
    p_eval.add_argument("--max-total-items", type=int, default=5)
    p_eval.add_argument("--maximum-total-characters", type=int, default=2000)
    p_eval.add_argument("--max-items-per-source", type=int, default=5)
    p_eval.set_defaults(func=cmd_eval)
