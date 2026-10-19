"""
Extraction snapshot commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from pydantic import ValidationError

from ..api import validate_request
from ..corpus import Corpus
from ..extraction import build_extraction_snapshot
from ..extraction_evaluation import (
    evaluate_extraction_snapshot,
    load_extraction_dataset,
    write_extraction_evaluation_result,
)
from ..models import (
    parse_extraction_snapshot_reference,
)
from . import common
from .common import (
    _add_common_corpus_arg,
    _add_dependency_flags,
    _default_extraction_max_workers,
    _dependency_mode,
)


def _parse_stage_spec(raw_stage: str) -> tuple[str, Dict[str, object]]:
    """
    Parse a pipeline stage specification.

    :param raw_stage: Stage spec in the form extractor_id or extractor_id:key=value,key=value.
    :type raw_stage: str
    :return: Tuple of extractor_id and config mapping.
    :rtype: tuple[str, dict[str, object]]
    :raises ValueError: If the stage spec is invalid.
    """
    raw_stage = raw_stage.strip()
    if not raw_stage:
        raise ValueError("Stage spec must be non-empty")
    if ":" not in raw_stage:
        return raw_stage, {}
    extractor_id, raw_pairs = raw_stage.split(":", 1)
    extractor_id = extractor_id.strip()
    if not extractor_id:
        raise ValueError("Stage spec must start with an extractor identifier")
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
            raise ValueError(f"Config values must be key=value (got {token!r})")
        key, value = token.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Config keys must be non-empty")
        config[key] = value
    return extractor_id, config


def cmd_extract_build(arguments: argparse.Namespace) -> int:
    """
    Build a text extraction snapshot for the corpus using a pipeline of extractors.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..configuration import load_configuration_view

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
                "stages": [
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
        # Build from --stage arguments
        raw_stages = list(arguments.stage or [])
        if not raw_stages:
            raise ValueError("Pipeline extraction requires at least one --stage")
        stages: List[Dict[str, object]] = []
        for raw_stage in raw_stages:
            stage_extractor_id, stage_config = _parse_stage_spec(raw_stage)
            stages.append({"extractor_id": stage_extractor_id, "config": stage_config})
        config = {"stages": stages}
        extractor_id = "pipeline"

    from ..workflow import build_plan_for_extract

    dependency_mode = _dependency_mode(arguments)
    resolved_max_workers = (
        int(arguments.max_workers)
        if arguments.max_workers is not None
        else _default_extraction_max_workers()
    )
    extract_plan = build_plan_for_extract(
        corpus,
        pipeline_config=config,
        load_handler_available=False,
        force=bool(arguments.force),
        max_workers=resolved_max_workers,
    )
    results = common._execute_dependency_plan(
        extract_plan,
        corpus=corpus,
        label="extract",
        mode=dependency_mode,
    )
    manifest = (
        results[-1]
        if results
        else build_extraction_snapshot(
            corpus,
            extractor_id=extractor_id,
            configuration_name=arguments.configuration_name,
            configuration=config,
            force=bool(arguments.force),
            max_workers=resolved_max_workers,
        )
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


def cmd_extract_url_text(arguments: argparse.Namespace) -> int:
    """
    Extract readable text from a source URL using the source-aware fetch strategy.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .. import url_text as url_text_module
    from ..api import UrlTextRequest, extract_url_text

    def print_failure_to_standard_error(error_payload: Dict[str, Any]) -> int:
        print(json.dumps({"status": "failed", "error": error_payload}, indent=2), file=sys.stderr)
        return 2

    try:
        payload = url_text_module.load_url_text_input_json(arguments.input_json)
    except ValueError as exc:
        return print_failure_to_standard_error({"code": "invalid_input_json", "message": str(exc)})

    source_uri = str(payload.get("source_uri") or "").strip()
    if not source_uri:
        return print_failure_to_standard_error(
            {"code": "missing_source_uri", "message": "source_uri is required"}
        )

    request = validate_request(
        UrlTextRequest,
        "extract url-text",
        source_uri=source_uri,
        reference_title=str(payload.get("reference_title") or ""),
        timeout_seconds=float(
            payload.get("timeout_seconds") or url_text_module.URL_TEXT_DEFAULT_TIMEOUT_SECONDS
        ),
    )
    try:
        output = extract_url_text(request)
    except url_text_module.UrlTextExtractionError as exc:
        return print_failure_to_standard_error(exc.to_dict())

    print(output.model_dump_json(indent=2, exclude_unset=True))
    return 0 if output.status == "ok" else 1


def cmd_extract_web_metadata(arguments: argparse.Namespace) -> int:
    """
    Extract reference metadata (title, authors, dates) from web HTML heuristics.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..api import WebMetadataRequest, extract_web_metadata
    from ..url_text import URL_TEXT_DEFAULT_TIMEOUT_SECONDS, load_url_text_input_json

    def print_failure_to_standard_error(error_payload: Dict[str, Any]) -> int:
        print(json.dumps({"status": "failed", "error": error_payload}, indent=2), file=sys.stderr)
        return 2

    try:
        payload = load_url_text_input_json(arguments.input_json)
    except ValueError as exc:
        return print_failure_to_standard_error({"code": "invalid_input_json", "message": str(exc)})

    source_uri = str(payload.get("source_uri") or "").strip()
    html_content = str(payload.get("html_content") or payload.get("html") or "").strip()
    if not html_content and not source_uri:
        return print_failure_to_standard_error(
            {"code": "missing_input", "message": "Provide source_uri and/or html_content."}
        )

    request = validate_request(
        WebMetadataRequest,
        "extract web-metadata",
        source_uri=source_uri,
        html_content=html_content,
        reference_title=str(payload.get("reference_title") or ""),
        use_llm_fallback=bool(arguments.use_llm_fallback or payload.get("use_llm_fallback")),
        model=str(payload.get("model") or ""),
        timeout_seconds=float(payload.get("timeout_seconds") or URL_TEXT_DEFAULT_TIMEOUT_SECONDS),
    )
    try:
        output = extract_web_metadata(request)
    except ValueError as exc:
        return print_failure_to_standard_error({"code": "web_metadata_failed", "message": str(exc)})

    print(output.model_dump_json(indent=2))
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


def register_extract_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the extract commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_extract = subparsers.add_parser(
        "extract", help="Work with text extraction snapshots for the corpus."
    )
    extract_sub = p_extract.add_subparsers(dest="extract_command", required=True)
    from ..web_transform import add_transform_commands

    add_transform_commands(subparsers, extract_sub)

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
        help="Path to YAML configuration file. If provided, --stage arguments are ignored.",
    )
    p_extract_build.add_argument(
        "--stage",
        action="append",
        default=None,
        help="Pipeline stage spec in the form extractor_id or extractor_id:key=value,key=value (repeatable).",
    )
    p_extract_build.add_argument(
        "--force",
        action="store_true",
        help="Reprocess items even if extraction artifacts already exist.",
    )
    p_extract_build.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help=(
            "Maximum number of concurrent extraction workers "
            "(defaults to BIBLICUS_EXTRACT_MAX_WORKERS or CPU count)."
        ),
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

    p_extract_url_text = extract_sub.add_parser(
        "url-text",
        help="Extract readable text from a source URL (web pages, PDFs, YouTube).",
    )
    p_extract_url_text.add_argument(
        "--input-json",
        default="-",
        help="JSON payload with source_uri and optional reference_title (default: stdin).",
    )
    p_extract_url_text.add_argument(
        "--format",
        choices=["json"],
        default="json",
        help="Output format (only json is supported).",
    )
    p_extract_url_text.set_defaults(func=cmd_extract_url_text)

    p_extract_web_metadata = extract_sub.add_parser(
        "web-metadata",
        help="Extract title, authors, and bibliography metadata from web HTML.",
    )
    p_extract_web_metadata.add_argument(
        "--input-json",
        default="-",
        help="JSON payload with source_uri and/or html_content (default: stdin).",
    )
    p_extract_web_metadata.add_argument(
        "--use-llm-fallback",
        action="store_true",
        help="Run LLM structured enrichment when heuristics are sparse.",
    )
    p_extract_web_metadata.set_defaults(func=cmd_extract_web_metadata)

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
