"""
Command-line interface for Biblicus.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from pydantic import ValidationError

from .analysis import get_analysis_backend
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
from .errors import ExtractionSnapshotFatalError, IngestCollisionError
from .evaluation.retrieval import evaluate_snapshot, load_dataset
from .evidence_processing import apply_evidence_filter, apply_evidence_reranker
from .extraction import build_extraction_snapshot
from .extraction_evaluation import (
    evaluate_extraction_snapshot,
    load_extraction_dataset,
    write_extraction_evaluation_result,
)
from .models import QueryBudget, RetrievalResult, parse_extraction_snapshot_reference
from .retrievers import get_retriever
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

    try:
        if arguments.note is not None or arguments.stdin:
            text = arguments.note if arguments.note is not None else sys.stdin.read()
            ingest_result = corpus.ingest_note(
                text,
                title=arguments.title,
                tags=tags,
                source_uri=None if arguments.stdin else None,
            )
            results.append(ingest_result)

        for source_path in arguments.files or []:
            results.append(corpus.ingest_source(source_path, tags=tags))
    except IngestCollisionError as error:
        print(
            "Ingest failed: source already ingested\n"
            f"source_uri: {error.source_uri}\n"
            f"existing_item_id: {error.existing_item_id}\n"
            f"existing_relpath: {error.existing_relpath}",
            file=sys.stderr,
        )
        return 3

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


def _parse_config_pairs(pairs: Optional[Iterable[str]]) -> Dict[str, object]:
    """
    Parse key=value pairs into a configuration mapping.

    This is used by a few command-line options that accept repeated key=value items.
    Values are coerced to useful types in a predictable way:

    - JSON objects/arrays (leading ``{`` or ``[``) are parsed as JSON.
    - Whole numbers are parsed as integers.
    - Other numeric forms are parsed as floats.
    - Everything else remains a string.

    :param pairs: Iterable of key=value strings.
    :type pairs: Iterable[str] or None
    :return: Parsed configuration mapping.
    :rtype: dict[str, object]
    :raises ValueError: If any entry is not a key=value pair or values are invalid.
    """
    config: Dict[str, object] = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"Config values must be key=value (got {item!r})")
        key, raw = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Config keys must be non-empty")
        raw = raw.strip()
        value: object = raw
        if raw.startswith("{") or raw.startswith("["):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Config value must be valid JSON for key {key!r}") from exc
        elif raw.isdigit():
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
        offset=getattr(arguments, "offset", 0),
        maximum_total_characters=arguments.maximum_total_characters,
        max_items_per_source=arguments.max_items_per_source,
    )


def _add_dependency_flags(parser: argparse.ArgumentParser) -> None:
    """
    Add dependency execution flags to a subcommand parser.

    :param parser: Argument parser to extend.
    :type parser: argparse.ArgumentParser
    :return: None.
    :rtype: None
    """
    parser.add_argument(
        "--auto-deps",
        action="store_true",
        help="Automatically run dependency stages (load/extract/index) when needed.",
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Fail fast if dependency stages are required.",
    )


def _dependency_mode(arguments: argparse.Namespace) -> str:
    """
    Resolve dependency execution mode from CLI arguments.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Dependency mode (auto, none, or prompt).
    :rtype: str
    :raises ValueError: If conflicting flags are set.
    """
    auto_deps = bool(getattr(arguments, "auto_deps", False))
    no_deps = bool(getattr(arguments, "no_deps", False))
    if auto_deps and no_deps:
        raise ValueError("--auto-deps and --no-deps cannot be combined")
    if auto_deps:
        return "auto"
    if no_deps:
        return "none"
    if not sys.stdin.isatty():
        return "auto"
    return "prompt"


def _prompt_dependency_plan(plan, label: str) -> bool:
    pending = [task.kind for task in plan.tasks if task.status != "complete"]
    pending_summary = ", ".join(pending) if pending else "none"
    print(f"Dependencies required for {label}: {pending_summary}")
    response = input("Run dependencies now? [y/N]: ").strip().lower()
    return response in {"y", "yes"}


def _execute_dependency_plan(
    plan,
    *,
    corpus: Corpus,
    label: str,
    mode: str,
):
    from .workflow import Plan, build_default_handler_registry

    if plan.status == "complete":
        return []
    if plan.status == "blocked":
        raise ValueError(plan.root.reason or f"Dependencies blocked for {label}")
    if mode == "none":
        raise ValueError(f"Dependencies missing for {label}")
    if mode not in {"prompt", "auto"}:
        raise ValueError(f"Unsupported dependency mode: {mode}")
    if mode == "prompt" and not _prompt_dependency_plan(plan, label):
        raise ValueError(f"Dependencies declined for {label}")

    handler_registry = build_default_handler_registry(corpus)
    plan_to_execute = plan
    if getattr(plan.root, "kind", None) == "query":
        dependency_tasks = [task for task in plan.tasks if task.kind != "query"]
        if not dependency_tasks:
            return []
        plan_to_execute = Plan(
            tasks=dependency_tasks,
            root=dependency_tasks[-1],
            status="ready",
        )
    return plan_to_execute.execute(mode="auto", handler_registry=handler_registry)


def cmd_build(arguments: argparse.Namespace) -> int:
    """
    Build a retrieval snapshot for a retriever.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .configuration import (
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

    from .workflow import build_plan_for_index

    dependency_mode = _dependency_mode(arguments)
    index_plan = build_plan_for_index(
        corpus,
        retriever_id=arguments.retriever,
        pipeline_config=None,
        index_config=configuration,
        load_handler_available=False,
    )
    _execute_dependency_plan(
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


def cmd_extract_build(arguments: argparse.Namespace) -> int:
    """
    Build a text extraction snapshot for the corpus using a pipeline of extractors.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .configuration import load_configuration_view

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )

    # Load configuration from file if --configuration is provided
    if getattr(arguments, "configuration", None):
        configuration_data = load_configuration_view(
            arguments.configuration,
            configuration_label="Configuration file",
            mapping_error_message="Extraction configuration must be a mapping/object",
        )
        loaded_extractor_id = configuration_data.get("extractor_id", "pipeline")
        loaded_config = configuration_data.get("configuration", {})

        # If the configuration specifies a non-pipeline extractor, wrap it in a pipeline
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

    from .workflow import build_plan_for_extract

    dependency_mode = _dependency_mode(arguments)
    extract_plan = build_plan_for_extract(
        corpus,
        pipeline_config=config,
        load_handler_available=False,
    )
    results = _execute_dependency_plan(
        extract_plan,
        corpus=corpus,
        label="extract",
        mode=dependency_mode,
    )
    manifest = results[-1] if results else build_extraction_snapshot(
        corpus,
        extractor_id=extractor_id,
        configuration_name=arguments.configuration_name,
        configuration=config,
    )
    print(manifest.model_dump_json(indent=2))
    return 0


def cmd_extract_list(arguments: argparse.Namespace) -> int:
    """
    List extraction snapshots stored under the corpus.

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
    snapshots = corpus.list_extraction_snapshots(extractor_id=arguments.extractor_id)
    print(json.dumps([entry.model_dump() for entry in snapshots], indent=2))
    return 0


def cmd_extract_show(arguments: argparse.Namespace) -> int:
    """
    Show an extraction snapshot manifest.

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
    reference = parse_extraction_snapshot_reference(arguments.snapshot)
    manifest = corpus.load_extraction_snapshot_manifest(
        extractor_id=reference.extractor_id, snapshot_id=reference.snapshot_id
    )
    print(manifest.model_dump_json(indent=2))
    return 0


def cmd_extract_delete(arguments: argparse.Namespace) -> int:
    """
    Delete an extraction snapshot directory and its derived artifacts.

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
    if arguments.confirm != arguments.snapshot:
        raise ValueError("Refusing to delete extraction snapshot without an exact --confirm match.")
    reference = parse_extraction_snapshot_reference(arguments.snapshot)
    corpus.delete_extraction_snapshot(
        extractor_id=reference.extractor_id, snapshot_id=reference.snapshot_id
    )
    print(json.dumps({"deleted": True, "snapshot": arguments.snapshot}, indent=2))
    return 0


def cmd_extract_evaluate(arguments: argparse.Namespace) -> int:
    """
    Evaluate an extraction snapshot against a dataset.

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
    if arguments.snapshot:
        snapshot_ref = parse_extraction_snapshot_reference(arguments.snapshot)
    else:
        snapshot_ref = corpus.latest_extraction_snapshot_reference()
        if snapshot_ref is None:
            raise ValueError("Extraction evaluation requires an extraction snapshot")
        print(
            "Warning: using latest extraction snapshot; pass --snapshot for reproducibility.",
            file=sys.stderr,
        )

    dataset_path = Path(arguments.dataset)
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    try:
        dataset = load_extraction_dataset(dataset_path)
    except ValidationError as exc:
        raise ValueError(f"Invalid extraction dataset: {exc}") from exc

    snapshot = corpus.load_extraction_snapshot_manifest(
        extractor_id=snapshot_ref.extractor_id,
        snapshot_id=snapshot_ref.snapshot_id,
    )
    result = evaluate_extraction_snapshot(
        corpus=corpus,
        snapshot=snapshot,
        extractor_id=snapshot_ref.extractor_id,
        dataset=dataset,
    )
    write_extraction_evaluation_result(
        corpus=corpus, snapshot_id=snapshot.snapshot_id, result=result
    )
    print(result.model_dump_json(indent=2))
    return 0


def cmd_graph_extract(arguments: argparse.Namespace) -> int:
    """
    Build a graph extraction snapshot for the corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )
    from .graph.extraction import build_graph_snapshot

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )

    base_config: Dict[str, object] = {}
    if arguments.configuration is not None:
        base_config = load_configuration_view(
            arguments.configuration,
            configuration_label="Graph extraction configuration",
            mapping_error_message="Graph extraction configuration must be a mapping/object",
        )

    overrides = parse_dotted_overrides(arguments.override)
    configuration = apply_dotted_overrides(base_config, overrides)

    if arguments.extraction_snapshot:
        extraction_snapshot = parse_extraction_snapshot_reference(arguments.extraction_snapshot)
    else:
        extraction_snapshot = corpus.latest_extraction_snapshot_reference()
        if extraction_snapshot is None:
            raise ValueError("Graph extraction requires an extraction snapshot")
        print(
            "Warning: using latest extraction snapshot; pass --extraction-snapshot for reproducibility.",
            file=sys.stderr,
        )

    manifest = build_graph_snapshot(
        corpus,
        extractor_id=arguments.extractor,
        configuration_name=arguments.configuration_name,
        configuration=configuration,
        extraction_snapshot=extraction_snapshot,
    )
    print(manifest.model_dump_json(indent=2))
    return 0


def cmd_graph_list(arguments: argparse.Namespace) -> int:
    """
    List graph extraction snapshots stored under the corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .graph.extraction import list_graph_snapshots

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    snapshots = list_graph_snapshots(corpus, extractor_id=arguments.extractor_id)
    print(json.dumps([entry.model_dump() for entry in snapshots], indent=2))
    return 0


def cmd_graph_show(arguments: argparse.Namespace) -> int:
    """
    Show a graph snapshot manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .graph.extraction import load_graph_snapshot_manifest
    from .graph.models import parse_graph_snapshot_reference

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    reference = parse_graph_snapshot_reference(arguments.snapshot)
    manifest = load_graph_snapshot_manifest(
        corpus,
        extractor_id=reference.extractor_id,
        snapshot_id=reference.snapshot_id,
    )
    print(manifest.model_dump_json(indent=2))
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
    snapshot_id = arguments.snapshot or corpus.latest_snapshot_id
    if not snapshot_id:
        from .workflow import build_plan_for_query

        dependency_mode = _dependency_mode(arguments)
        retriever_id = arguments.retriever or "tf-vector"
        query_plan = build_plan_for_query(
            corpus,
            retriever_id=retriever_id,
            pipeline_config=None,
            index_config=None,
            load_handler_available=False,
        )
        _execute_dependency_plan(
            query_plan,
            corpus=corpus,
            label="query",
            mode=dependency_mode,
        )
        snapshot_id = corpus.latest_snapshot_id
    if not snapshot_id:
        raise ValueError(
            "No snapshot identifier provided and no latest snapshot is recorded for this corpus"
        )
    snapshot = corpus.load_snapshot(snapshot_id)
    if arguments.retriever and arguments.retriever != snapshot.configuration.retriever_id:
        raise ValueError(
            "Retriever mismatch: snapshot uses "
            f"{snapshot.configuration.retriever_id!r} but {arguments.retriever!r} was requested"
        )
    retriever = get_retriever(snapshot.configuration.retriever_id)
    query_text = arguments.query if arguments.query is not None else sys.stdin.read()
    budget = _budget_from_args(arguments)
    result = retriever.query(corpus, snapshot=snapshot, query_text=query_text, budget=budget)
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
    from .configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    configuration_data = load_configuration_view(
        arguments.configuration,
        configuration_label="Configuration file",
        mapping_error_message="Topic modeling configuration must be a mapping/object",
    )
    overrides = parse_dotted_overrides(arguments.override)
    configuration_data = apply_dotted_overrides(configuration_data, overrides)

    if arguments.extraction_snapshot:
        extraction_snapshot = parse_extraction_snapshot_reference(arguments.extraction_snapshot)
    else:
        extraction_snapshot = corpus.latest_extraction_snapshot_reference()
        if extraction_snapshot is None:
            raise ValueError("Topic analysis requires an extraction snapshot to supply text inputs")
        print(
            "Warning: using latest extraction snapshot; pass --extraction-snapshot for reproducibility.",
            file=sys.stderr,
        )

    backend = get_analysis_backend("topic-modeling")
    try:
        output = backend.run_analysis(
            corpus,
            configuration_name=arguments.configuration_name,
            configuration=configuration_data,
            extraction_snapshot=extraction_snapshot,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid topic modeling configuration: {exc}") from exc
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
    from .configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )

    configuration_data: dict[str, object] = {}
    if arguments.configuration is not None:
        configuration_data = load_configuration_view(
            arguments.configuration,
            configuration_label="Configuration file",
            mapping_error_message="Profiling configuration must be a mapping/object",
        )
        overrides = parse_dotted_overrides(arguments.override)
        configuration_data = apply_dotted_overrides(configuration_data, overrides)
    else:
        overrides = parse_dotted_overrides(arguments.override)
        if overrides:
            configuration_data = apply_dotted_overrides(configuration_data, overrides)

    if arguments.extraction_snapshot:
        extraction_snapshot = parse_extraction_snapshot_reference(arguments.extraction_snapshot)
    else:
        extraction_snapshot = corpus.latest_extraction_snapshot_reference()
        if extraction_snapshot is None:
            raise ValueError(
                "Profiling analysis requires an extraction snapshot to supply text inputs"
            )
        print(
            "Warning: using latest extraction snapshot; pass --extraction-snapshot for reproducibility.",
            file=sys.stderr,
        )

    backend = get_analysis_backend("profiling")
    try:
        output = backend.run_analysis(
            corpus,
            configuration_name=arguments.configuration_name,
            configuration=configuration_data,
            extraction_snapshot=extraction_snapshot,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid profiling configuration: {exc}") from exc
    print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_markov(arguments: argparse.Namespace) -> int:
    """
    Run Markov analysis for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .configuration import (
        apply_dotted_overrides,
        load_configuration_view,
        parse_dotted_overrides,
    )

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    configuration_data = load_configuration_view(
        arguments.configuration,
        configuration_label="Configuration file",
        mapping_error_message="Markov analysis configuration must be a mapping/object",
    )
    overrides = parse_dotted_overrides(arguments.override)
    configuration_data = apply_dotted_overrides(configuration_data, overrides)

    if arguments.extraction_snapshot:
        extraction_snapshot = parse_extraction_snapshot_reference(arguments.extraction_snapshot)
    else:
        extraction_snapshot = corpus.latest_extraction_snapshot_reference()
        if extraction_snapshot is None:
            raise ValueError(
                "Markov analysis requires an extraction snapshot to supply text inputs"
            )
        print(
            "Warning: using latest extraction snapshot; pass --extraction-snapshot for reproducibility.",
            file=sys.stderr,
        )

    backend = get_analysis_backend("markov")
    try:
        output = backend.run_analysis(
            corpus,
            configuration_name=arguments.configuration_name,
            configuration=configuration_data,
            extraction_snapshot=extraction_snapshot,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid Markov analysis configuration: {exc}") from exc
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

    p_build = sub.add_parser("build", help="Build a retrieval snapshot for the corpus.")
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

    p_extract = sub.add_parser(
        "extract", help="Work with text extraction snapshots for the corpus."
    )
    extract_sub = p_extract.add_subparsers(dest="extract_command", required=True)

    p_extract_build = extract_sub.add_parser("build", help="Build a text extraction snapshot.")
    _add_common_corpus_arg(p_extract_build)
    _add_dependency_flags(p_extract_build)
    p_extract_build.add_argument(
        "--configuration-name", default="default", help="Human-readable configuration name."
    )
    p_extract_build.add_argument(
        "--configuration",
        default=None,
        action="append",
        help="Path to YAML configuration file. If provided, --step arguments are ignored.",
    )
    p_extract_build.add_argument(
        "--step",
        action="append",
        default=None,
        help="Pipeline step spec in the form extractor_id or extractor_id:key=value,key=value (repeatable).",
    )
    p_extract_build.set_defaults(func=cmd_extract_build)

    p_extract_list = extract_sub.add_parser("list", help="List extraction snapshots.")
    _add_common_corpus_arg(p_extract_list)
    p_extract_list.add_argument(
        "--extractor-id",
        default=None,
        help="Optional extractor identifier filter (for example: pipeline).",
    )
    p_extract_list.set_defaults(func=cmd_extract_list)

    p_extract_show = extract_sub.add_parser("show", help="Show an extraction snapshot manifest.")
    _add_common_corpus_arg(p_extract_show)
    p_extract_show.add_argument(
        "--snapshot",
        required=True,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_extract_show.set_defaults(func=cmd_extract_show)

    p_extract_delete = extract_sub.add_parser(
        "delete", help="Delete an extraction snapshot directory."
    )
    _add_common_corpus_arg(p_extract_delete)
    p_extract_delete.add_argument(
        "--snapshot",
        required=True,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_extract_delete.add_argument(
        "--confirm",
        required=True,
        help="Type the exact extractor_id:snapshot_id to confirm deletion.",
    )
    p_extract_delete.set_defaults(func=cmd_extract_delete)

    p_extract_evaluate = extract_sub.add_parser(
        "evaluate", help="Evaluate an extraction snapshot against a dataset."
    )
    _add_common_corpus_arg(p_extract_evaluate)
    p_extract_evaluate.add_argument(
        "--snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id (defaults to latest snapshot).",
    )
    p_extract_evaluate.add_argument(
        "--dataset",
        required=True,
        help="Path to the extraction evaluation dataset JSON file.",
    )
    p_extract_evaluate.set_defaults(func=cmd_extract_evaluate)

    p_graph = sub.add_parser("graph", help="Run graph extraction pipelines for the corpus.")
    graph_sub = p_graph.add_subparsers(dest="graph_command", required=True)

    p_graph_extract = graph_sub.add_parser(
        "extract", help="Build a graph extraction snapshot."
    )
    _add_common_corpus_arg(p_graph_extract)
    p_graph_extract.add_argument(
        "--extractor",
        required=True,
        help="Graph extractor identifier (for example: cooccurrence).",
    )
    p_graph_extract.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id (defaults to latest snapshot).",
    )
    p_graph_extract.add_argument(
        "--configuration-name", default="default", help="Human-readable configuration name."
    )
    p_graph_extract.add_argument(
        "--configuration",
        default=None,
        action="append",
        help="Path to graph extraction configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_graph_extract.add_argument(
        "--override",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_graph_extract.set_defaults(func=cmd_graph_extract)

    p_graph_list = graph_sub.add_parser("list", help="List graph extraction snapshots.")
    _add_common_corpus_arg(p_graph_list)
    p_graph_list.add_argument(
        "--extractor-id",
        default=None,
        help="Optional graph extractor identifier filter (for example: cooccurrence).",
    )
    p_graph_list.set_defaults(func=cmd_graph_list)

    p_graph_show = graph_sub.add_parser(
        "show", help="Show a graph extraction snapshot manifest."
    )
    _add_common_corpus_arg(p_graph_show)
    p_graph_show.add_argument(
        "--snapshot",
        required=True,
        help="Graph snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_graph_show.set_defaults(func=cmd_graph_show)

    p_query = sub.add_parser("query", help="Run a retrieval query.")
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

    p_eval = sub.add_parser("eval", help="Evaluate a snapshot against a dataset.")
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
        "--configuration",
        required=True,
        action="append",
        help="Path to topic modeling configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_analyze_topics.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_analyze_topics.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    p_analyze_topics.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_analyze_topics.set_defaults(func=cmd_analyze_topics)

    p_analyze_profile = analyze_sub.add_parser("profile", help="Run profiling analysis.")
    _add_common_corpus_arg(p_analyze_profile)
    p_analyze_profile.add_argument(
        "--configuration",
        default=None,
        action="append",
        help="Optional profiling configuration YAML file. Repeatable; later files override earlier ones.",
    )
    p_analyze_profile.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_analyze_profile.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    p_analyze_profile.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_analyze_profile.set_defaults(func=cmd_analyze_profile)

    p_analyze_markov = analyze_sub.add_parser("markov", help="Run Markov analysis.")
    _add_common_corpus_arg(p_analyze_markov)
    p_analyze_markov.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to Markov analysis configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_analyze_markov.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_analyze_markov.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    p_analyze_markov.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_analyze_markov.set_defaults(func=cmd_analyze_markov)

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
        ExtractionSnapshotFatalError,
        NotImplementedError,
        ValidationError,
    ) as exception:
        message = exception.args[0] if getattr(exception, "args", None) else str(exception)
        print(str(message), file=sys.stderr)
        return 2
