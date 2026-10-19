"""
Shared helpers for the Biblicus command-line interface command groups.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

from ..corpus import Corpus
from ..extraction import load_or_build_extraction_snapshot
from ..models import (
    ExtractionSnapshotReference,
)


def _get_or_build_extraction_snapshot(
    *,
    corpus: Corpus,
    recipe_path: Path,
    analysis_label: str,
) -> ExtractionSnapshotReference:
    """
    Reuse the latest extraction snapshot when available, otherwise build one.

    This helper keeps the CLI logic small and is intentionally minimal: it falls
    back to the pipeline extractor with an empty configuration when no recipe is
    provided.
    """
    existing = corpus.latest_extraction_snapshot_reference(extractor_id="pipeline")
    if existing is not None:
        return existing

    extractor_id = "pipeline"
    config: Dict[str, object] = {}
    if recipe_path.exists():
        try:
            with recipe_path.open("r", encoding="utf-8") as handle:
                recipe_data = json.load(handle)
            extractor_id = recipe_data.get("extractor_id", extractor_id)
            config = recipe_data.get("config", config)
        except (OSError, json.JSONDecodeError):
            extractor_id = "pipeline"
            config = {}

    snapshot = corpus.extract(extractor_id=extractor_id, config=config, label=analysis_label)
    return ExtractionSnapshotReference(extractor_id=extractor_id, snapshot_id=snapshot.snapshot_id)


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


def _corpus_path_from_arguments(arguments: argparse.Namespace) -> str:
    """
    Resolve the corpus path or uniform resource identifier named by command-line interface arguments.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Explicit corpus reference, or the root of the corpus found from the working directory.
    :rtype: str
    """
    if getattr(arguments, "corpus", None):
        return str(arguments.corpus)
    return str(Corpus.find(Path.cwd()).root)


def _open_corpus_from_arguments(arguments: argparse.Namespace) -> Corpus:
    """
    Open the corpus named by command-line interface arguments.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Opened corpus.
    :rtype: Corpus
    """
    return Corpus.open(_corpus_path_from_arguments(arguments))


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


def _load_ingest_metadata_file(path: Path) -> Dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FileNotFoundError(f"Ingest metadata file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid ingest metadata file: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Ingest metadata file must be a mapping/object: {path}")
    return dict(payload)


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


def _default_extraction_recipe_path(corpus: Corpus, *, recipe_name: str = "default") -> Path:
    return corpus.root / "recipes" / "extraction" / f"{recipe_name}.yml"


def _default_extraction_max_workers() -> int:
    env_value = os.getenv("BIBLICUS_EXTRACT_MAX_WORKERS")
    if env_value:
        try:
            parsed = int(env_value)
        except ValueError as exc:
            raise ValueError("BIBLICUS_EXTRACT_MAX_WORKERS must be an integer >= 1") from exc
        if parsed < 1:
            raise ValueError("BIBLICUS_EXTRACT_MAX_WORKERS must be >= 1")
        return parsed
    cpu_count = os.cpu_count() or 1
    return max(4, cpu_count)


def _normalize_extraction_configuration(
    configuration_data: Dict[str, object],
) -> tuple[str, Dict[str, object], Optional[int]]:
    extractor_id = configuration_data.get("extractor_id", "pipeline")
    configuration = configuration_data.get("configuration", {})
    max_workers = configuration_data.get("max_workers")
    if configuration is None:
        configuration = {}
    if not isinstance(configuration, dict):
        raise ValueError("Extraction configuration must be a mapping/object")
    if not isinstance(extractor_id, str) or not extractor_id.strip():
        raise ValueError("Extraction configuration must include a non-empty extractor_id")
    extractor_id = extractor_id.strip()
    if max_workers is not None:
        if isinstance(max_workers, bool):
            raise ValueError("Extraction configuration max_workers must be an integer")
        try:
            max_workers = int(max_workers)
        except (TypeError, ValueError) as exc:
            raise ValueError("Extraction configuration max_workers must be an integer") from exc
        if max_workers < 1:
            raise ValueError("Extraction configuration max_workers must be >= 1")
    if extractor_id != "pipeline":
        return (
            "pipeline",
            {"stages": [{"extractor_id": extractor_id, "config": configuration}]},
            max_workers,
        )
    return "pipeline", configuration, max_workers


def _resolve_extraction_snapshot_for_analysis(
    *,
    corpus: Corpus,
    extraction_snapshot: Optional[str],
    analysis_label: str,
) -> "ExtractionSnapshotReference":
    from ..configuration import load_configuration_view
    from ..models import parse_extraction_snapshot_reference

    if extraction_snapshot:
        return parse_extraction_snapshot_reference(extraction_snapshot)

    recipe_path = _default_extraction_recipe_path(corpus)
    if recipe_path.is_file():
        latest_snapshot = corpus.latest_extraction_snapshot_reference(extractor_id="pipeline")
        if latest_snapshot is not None:
            manifest_path = (
                corpus.extraction_snapshot_dir(
                    extractor_id=latest_snapshot.extractor_id,
                    snapshot_id=latest_snapshot.snapshot_id,
                )
                / "manifest.json"
            )
            if manifest_path.is_file():
                print(
                    f"[extract] reusing snapshot {latest_snapshot.snapshot_id}",
                    file=sys.stderr,
                    flush=True,
                )
                return latest_snapshot
        print(
            f"{analysis_label}: using extraction recipe {recipe_path}",
            file=sys.stderr,
            flush=True,
        )
        configuration_data = load_configuration_view(
            [str(recipe_path)],
            configuration_label="Extraction recipe",
            mapping_error_message="Extraction recipe must be a mapping/object",
        )
        extractor_id, configuration, max_workers = _normalize_extraction_configuration(
            configuration_data
        )
        if max_workers is None:
            max_workers = _default_extraction_max_workers()
        configuration_name = recipe_path.stem
        manifest = load_or_build_extraction_snapshot(
            corpus,
            extractor_id=extractor_id,
            configuration_name=configuration_name,
            configuration=configuration,
            max_workers=max_workers,
        )
        return ExtractionSnapshotReference(
            extractor_id=extractor_id,
            snapshot_id=manifest.snapshot_id,
        )

    latest_snapshot = corpus.latest_extraction_snapshot_reference()
    if latest_snapshot is None:
        raise ValueError(
            f"{analysis_label} requires an extraction snapshot to supply text inputs. "
            f"Create an extraction recipe at {recipe_path} or pass --extraction-snapshot."
        )
    print(
        "Warning: using latest extraction snapshot; pass --extraction-snapshot for reproducibility.",
        file=sys.stderr,
    )
    return latest_snapshot


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
    from ..workflow import Plan, build_default_handler_registry

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
