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

from .analysis import get_analysis_backend
from .backends import get_backend
from .context import (
    CharacterBudget,
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_character_budget,
    fit_context_pack_to_token_budget,
)
from .corpus import Corpus
from .crawl import CrawlRequest, crawl_into_corpus
from .errors import ExtractionRunFatalError
from .evaluation import evaluate_run, load_dataset
from .evidence_processing import apply_evidence_filter, apply_evidence_reranker
from .extraction import build_extraction_run
from .models import QueryBudget, RetrievalResult, parse_extraction_run_reference
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


def cmd_import_tree(arguments: argparse.Namespace) -> int:
    """
    Import a folder tree into a corpus.

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
    stats = corpus.import_tree(Path(arguments.path), tags=tags)
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


def _parse_step_spec(raw_step: str) -> tuple[str, Dict[str, object]]:
    """
    Parse a pipeline step specification.

    :param raw_step: Step spec in the form extractor_id or extractor_id:key=value,key=value.
    :type raw_step: str
    :return: Tuple of extractor_id and config mapping.
    :rtype: tuple[str, dict[str, object]]
    :raises ValueError: If the step spec is invalid.
    """
    raw_step = raw_step.strip()
    if not raw_step:
        raise ValueError("Step spec must be non-empty")
    if ":" not in raw_step:
        return raw_step, {}
    extractor_id, raw_pairs = raw_step.split(":", 1)
    extractor_id = extractor_id.strip()
    if not extractor_id:
        raise ValueError("Step spec must start with an extractor identifier")
    config: Dict[str, object] = {}
    raw_pairs = raw_pairs.strip()
    if not raw_pairs:
        return extractor_id, {}

    tokens = []
    current_token = []
    brace_depth = 0
    bracket_depth = 0
    in_quotes = False
    escape_next = False

    for char in raw_pairs:
        if escape_next:
            current_token.append(char)
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            current_token.append(char)
            continue

        if char == '"' and brace_depth == 0 and bracket_depth == 0:
            in_quotes = not in_quotes
            current_token.append(char)
            continue

        if not in_quotes:
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
            elif char == "[":
                bracket_depth += 1
            elif char == "]":
                bracket_depth -= 1
            elif char == "," and brace_depth == 0 and bracket_depth == 0:
                tokens.append("".join(current_token).strip())
                current_token = []
                continue

        current_token.append(char)

    if current_token:
        tokens.append("".join(current_token).strip())

    for token in tokens:
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"Step config values must be key=value (got {token!r})")
        key, value = token.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Step config keys must be non-empty")
        config[key] = value
    return extractor_id, config


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


def cmd_extract_build(arguments: argparse.Namespace) -> int:
    """
    Build a text extraction run for the corpus using a pipeline of extractors.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    import yaml

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )

    # Load recipe from file if --recipe is provided
    if getattr(arguments, "recipe", None):
        recipe_path = Path(arguments.recipe)
        if not recipe_path.exists():
            raise FileNotFoundError(f"Recipe file not found: {recipe_path}")
        with open(recipe_path, "r", encoding="utf-8") as f:
            recipe_data = yaml.safe_load(f)
        loaded_extractor_id = recipe_data.get("extractor_id", "pipeline")
        loaded_config = recipe_data.get("config", {})

        # If the recipe specifies a non-pipeline extractor, wrap it in a pipeline
        if loaded_extractor_id != "pipeline":
            extractor_id = "pipeline"
            config = {
                "steps": [
                    {
                        "extractor_id": loaded_extractor_id,
                        "config": loaded_config,
                    }
                ]
            }
        else:
            extractor_id = loaded_extractor_id
            config = loaded_config
    else:
        # Build from --step arguments
        raw_steps = list(arguments.step or [])
        if not raw_steps:
            raise ValueError("Pipeline extraction requires at least one --step")
        steps: List[Dict[str, object]] = []
        for raw_step in raw_steps:
            step_extractor_id, step_config = _parse_step_spec(raw_step)
            steps.append({"extractor_id": step_extractor_id, "config": step_config})
        config = {"steps": steps}
        extractor_id = "pipeline"

    manifest = build_extraction_run(
        corpus,
        extractor_id=extractor_id,
        recipe_name=arguments.recipe_name,
        config=config,
    )
    print(manifest.model_dump_json(indent=2))
    return 0


def cmd_extract_list(arguments: argparse.Namespace) -> int:
    """
    List extraction runs stored under the corpus.

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
    runs = corpus.list_extraction_runs(extractor_id=arguments.extractor_id)
    print(json.dumps([entry.model_dump() for entry in runs], indent=2))
    return 0


def cmd_extract_show(arguments: argparse.Namespace) -> int:
    """
    Show an extraction run manifest.

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
    reference = parse_extraction_run_reference(arguments.run)
    manifest = corpus.load_extraction_run_manifest(
        extractor_id=reference.extractor_id, run_id=reference.run_id
    )
    print(manifest.model_dump_json(indent=2))
    return 0


def cmd_extract_delete(arguments: argparse.Namespace) -> int:
    """
    Delete an extraction run directory and its derived artifacts.

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
    if arguments.confirm != arguments.run:
        raise ValueError("Refusing to delete extraction run without an exact --confirm match.")
    reference = parse_extraction_run_reference(arguments.run)
    corpus.delete_extraction_run(extractor_id=reference.extractor_id, run_id=reference.run_id)
    print(json.dumps({"deleted": True, "run": arguments.run}, indent=2))
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
    processed_evidence = result.evidence
    if getattr(arguments, "reranker_id", None):
        processed_evidence = apply_evidence_reranker(
            reranker_id=arguments.reranker_id,
            query_text=result.query_text,
            evidence=processed_evidence,
        )
    if getattr(arguments, "minimum_score", None) is not None:
        processed_evidence = apply_evidence_filter(
            filter_id="filter-minimum-score",
            query_text=result.query_text,
            evidence=processed_evidence,
            config={"minimum_score": float(arguments.minimum_score)},
        )
    if processed_evidence is not result.evidence:
        result = result.model_copy(update={"evidence": processed_evidence})
    print(result.model_dump_json(indent=2))
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


def cmd_analyze_topics(arguments: argparse.Namespace) -> int:
    """
    Run topic modeling analysis for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    import yaml

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    recipe_path = Path(arguments.recipe)
    if not recipe_path.is_file():
        raise FileNotFoundError(f"Recipe file not found: {recipe_path}")
    recipe_data = yaml.safe_load(recipe_path.read_text(encoding="utf-8")) or {}
    if not isinstance(recipe_data, dict):
        raise ValueError("Topic modeling recipe must be a mapping/object")

    if arguments.extraction_run:
        extraction_run = parse_extraction_run_reference(arguments.extraction_run)
    else:
        extraction_run = corpus.latest_extraction_run_reference()
        if extraction_run is None:
            raise ValueError("Topic analysis requires an extraction run to supply text inputs")
        print(
            "Warning: using latest extraction run; pass --extraction-run for reproducibility.",
            file=sys.stderr,
        )

    backend = get_analysis_backend("topic-modeling")
    try:
        output = backend.run_analysis(
            corpus,
            recipe_name=arguments.recipe_name,
            config=recipe_data,
            extraction_run=extraction_run,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid topic modeling recipe: {exc}") from exc
    print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_profile(arguments: argparse.Namespace) -> int:
    """
    Run profiling analysis for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    import yaml

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )

    recipe_data: dict[str, object] = {}
    if arguments.recipe is not None:
        recipe_path = Path(arguments.recipe)
        if not recipe_path.is_file():
            raise FileNotFoundError(f"Recipe file not found: {recipe_path}")
        recipe_raw = yaml.safe_load(recipe_path.read_text(encoding="utf-8")) or {}
        if not isinstance(recipe_raw, dict):
            raise ValueError("Profiling recipe must be a mapping/object")
        recipe_data = recipe_raw

    if arguments.extraction_run:
        extraction_run = parse_extraction_run_reference(arguments.extraction_run)
    else:
        extraction_run = corpus.latest_extraction_run_reference()
        if extraction_run is None:
            raise ValueError("Profiling analysis requires an extraction run to supply text inputs")
        print(
            "Warning: using latest extraction run; pass --extraction-run for reproducibility.",
            file=sys.stderr,
        )

    backend = get_analysis_backend("profiling")
    try:
        output = backend.run_analysis(
            corpus,
            recipe_name=arguments.recipe_name,
            config=recipe_data,
            extraction_run=extraction_run,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid profiling recipe: {exc}") from exc
    print(output.model_dump_json(indent=2))
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
    p_init.add_argument(
        "--force", action="store_true", help="Overwrite existing config if present."
    )
    p_init.set_defaults(func=cmd_init)

    p_ingest = sub.add_parser("ingest", help="Ingest file(s) and/or text into the corpus.")
    _add_common_corpus_arg(p_ingest)
    p_ingest.add_argument("files", nargs="*", help="File paths to ingest.")
    p_ingest.add_argument("--note", default=None, help="Ingest a literal note as Markdown text.")
    p_ingest.add_argument(
        "--stdin", action="store_true", help="Read text to ingest from standard input."
    )
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

    p_reindex = sub.add_parser(
        "reindex", help="Rebuild/refresh the corpus catalog from the on-disk corpus."
    )
    _add_common_corpus_arg(p_reindex)
    p_reindex.set_defaults(func=cmd_reindex)

    p_import_tree = sub.add_parser("import-tree", help="Import a folder tree into the corpus.")
    _add_common_corpus_arg(p_import_tree)
    p_import_tree.add_argument("path", help="Folder tree root to import.")
    p_import_tree.add_argument(
        "--tags", default=None, help="Comma-separated tags to apply to imported items."
    )
    p_import_tree.add_argument(
        "--tag", action="append", help="Repeatable tag to apply to imported items."
    )
    p_import_tree.set_defaults(func=cmd_import_tree)

    p_purge = sub.add_parser(
        "purge", help="Delete all items and derived files (requires confirmation)."
    )
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

    p_extract = sub.add_parser("extract", help="Work with text extraction runs for the corpus.")
    extract_sub = p_extract.add_subparsers(dest="extract_command", required=True)

    p_extract_build = extract_sub.add_parser("build", help="Build a text extraction run.")
    _add_common_corpus_arg(p_extract_build)
    p_extract_build.add_argument(
        "--recipe-name", default="default", help="Human-readable recipe name."
    )
    p_extract_build.add_argument(
        "--recipe",
        default=None,
        help="Path to YAML recipe file. If provided, --step arguments are ignored.",
    )
    p_extract_build.add_argument(
        "--step",
        action="append",
        default=None,
        help="Pipeline step spec in the form extractor_id or extractor_id:key=value,key=value (repeatable).",
    )
    p_extract_build.set_defaults(func=cmd_extract_build)

    p_extract_list = extract_sub.add_parser("list", help="List extraction runs.")
    _add_common_corpus_arg(p_extract_list)
    p_extract_list.add_argument(
        "--extractor-id",
        default=None,
        help="Optional extractor identifier filter (for example: pipeline).",
    )
    p_extract_list.set_defaults(func=cmd_extract_list)

    p_extract_show = extract_sub.add_parser("show", help="Show an extraction run manifest.")
    _add_common_corpus_arg(p_extract_show)
    p_extract_show.add_argument(
        "--run",
        required=True,
        help="Extraction run reference in the form extractor_id:run_id.",
    )
    p_extract_show.set_defaults(func=cmd_extract_show)

    p_extract_delete = extract_sub.add_parser("delete", help="Delete an extraction run directory.")
    _add_common_corpus_arg(p_extract_delete)
    p_extract_delete.add_argument(
        "--run",
        required=True,
        help="Extraction run reference in the form extractor_id:run_id.",
    )
    p_extract_delete.add_argument(
        "--confirm",
        required=True,
        help="Type the exact extractor_id:run_id to confirm deletion.",
    )
    p_extract_delete.set_defaults(func=cmd_extract_delete)

    p_query = sub.add_parser("query", help="Run a retrieval query.")
    _add_common_corpus_arg(p_query)
    p_query.add_argument("--run", default=None, help="Run identifier (defaults to latest run).")
    p_query.add_argument("--backend", default=None, help="Validate backend identifier.")
    p_query.add_argument("--query", default=None, help="Query text (defaults to standard input).")
    p_query.add_argument("--max-total-items", type=int, default=5)
    p_query.add_argument("--max-total-characters", type=int, default=2000)
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
    p_query.set_defaults(func=cmd_query)

    p_context_pack = sub.add_parser("context-pack", help="Build context pack text from evidence.")
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

    p_crawl = sub.add_parser("crawl", help="Crawl a website prefix into the corpus.")
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

    p_analyze = sub.add_parser("analyze", help="Run analysis pipelines for the corpus.")
    analyze_sub = p_analyze.add_subparsers(dest="analyze_command", required=True)

    p_analyze_topics = analyze_sub.add_parser("topics", help="Run topic modeling analysis.")
    _add_common_corpus_arg(p_analyze_topics)
    p_analyze_topics.add_argument(
        "--recipe",
        required=True,
        help="Path to topic modeling recipe YAML.",
    )
    p_analyze_topics.add_argument(
        "--recipe-name",
        default="default",
        help="Human-readable recipe name.",
    )
    p_analyze_topics.add_argument(
        "--extraction-run",
        default=None,
        help="Extraction run reference in the form extractor_id:run_id.",
    )
    p_analyze_topics.set_defaults(func=cmd_analyze_topics)

    p_analyze_profile = analyze_sub.add_parser("profile", help="Run profiling analysis.")
    _add_common_corpus_arg(p_analyze_profile)
    p_analyze_profile.add_argument(
        "--recipe",
        default=None,
        help="Optional profiling recipe YAML file.",
    )
    p_analyze_profile.add_argument(
        "--recipe-name",
        default="default",
        help="Human-readable recipe name.",
    )
    p_analyze_profile.add_argument(
        "--extraction-run",
        default=None,
        help="Extraction run reference in the form extractor_id:run_id.",
    )
    p_analyze_profile.set_defaults(func=cmd_analyze_profile)

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
        ExtractionRunFatalError,
        NotImplementedError,
        ValidationError,
    ) as exception:
        message = exception.args[0] if getattr(exception, "args", None) else str(exception)
        print(str(message), file=sys.stderr)
        return 2
