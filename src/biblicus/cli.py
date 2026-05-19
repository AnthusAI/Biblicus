"""
Command-line interface for Biblicus.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from pydantic import ValidationError

from .analysis import get_analysis_backend
from .collections import load_collection_config, pull_collection
from .context import (
    CharacterBudget,
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_character_budget,
    fit_context_pack_to_token_budget,
)
from .corpus import Corpus
from .corpus_audit import build_corpus_audit, corpus_audit_markdown
from .crawl import CrawlRequest, crawl_into_corpus
from .errors import ExtractionSnapshotFatalError, IngestCollisionError, RemoteSourceDependencyError
from .evaluation.retrieval import evaluate_snapshot, load_dataset
from .evidence_processing import apply_evidence_filter, apply_evidence_reranker
from .extraction import build_extraction_snapshot, load_or_build_extraction_snapshot
from .extraction_evaluation import (
    evaluate_extraction_snapshot,
    load_extraction_dataset,
    write_extraction_evaluation_result,
)
from .migration import migrate_layout
from .models import (
    CorpusConfig,
    ExtractionSnapshotReference,
    QueryBudget,
    RemoteCorpusSourceConfig,
    RetrievalResult,
    parse_extraction_snapshot_reference,
)
from .pipelines import run_pipeline_recipe
from .retrievers import get_retriever
from .steering import (
    build_steering_artifact_inventory,
    build_steering_export,
    render_steering_seed_manifest,
)
from .steering_proposals import (
    build_steering_graph_signal_bundle,
    load_steering_proposal_bundle,
    record_steering_proposal_bundle,
)
from .uris import corpus_ref_to_path


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
        except Exception:
            pass

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


def cmd_migrate_layout(arguments: argparse.Namespace) -> int:
    """
    Migrate a legacy corpus layout to the current layout.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    corpus_path = corpus_ref_to_path(arguments.path)
    stats = migrate_layout(corpus_root=corpus_path, force=arguments.force)
    print(json.dumps(stats, indent=2))
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


def _metadata_tags(metadata: Dict[str, Any]) -> List[str]:
    raw_tags = metadata.get("tags")
    if raw_tags is None:
        return []
    if isinstance(raw_tags, str):
        return [raw_tags] if raw_tags.strip() else []
    if isinstance(raw_tags, list):
        return [entry for entry in raw_tags if isinstance(entry, str) and entry.strip()]
    raise ValueError("Ingest metadata tags must be a string or list of strings")


def _metadata_with_import_rationale(
    metadata: Dict[str, Any], import_rationale: Optional[str]
) -> Dict[str, Any]:
    """
    Add optional import rationale metadata.

    :param metadata: Existing metadata mapping.
    :type metadata: dict[str, Any]
    :param import_rationale: Optional rationale explaining why the item belongs in the corpus.
    :type import_rationale: str or None
    :return: Metadata with curation.import_rationale when provided.
    :rtype: dict[str, Any]
    :raises ValueError: If curation metadata is malformed.
    """
    if import_rationale is None:
        return dict(metadata)
    rationale = import_rationale.strip()
    if not rationale:
        raise ValueError("Import rationale must not be blank")
    updated_metadata = dict(metadata)
    raw_curation = updated_metadata.get("curation")
    if raw_curation is None:
        curation: Dict[str, Any] = {}
    elif isinstance(raw_curation, dict):
        curation = dict(raw_curation)
    else:
        raise ValueError("Ingest metadata curation must be a mapping/object")
    curation["import_rationale"] = rationale
    updated_metadata["curation"] = curation
    return updated_metadata


def _validate_ingest_date_value(value: str, field_name: str) -> str:
    """
    Validate a canonical ingest date or timestamp value.

    :param value: User-supplied date value.
    :type value: str
    :param field_name: Canonical dates field name.
    :type field_name: str
    :return: The original stripped date value.
    :rtype: str
    :raises ValueError: If the value is not a date or International Organization for Standardization timestamp.
    """
    candidate = value.strip()
    if not candidate:
        raise ValueError(f"{field_name} must not be blank")
    try:
        date.fromisoformat(candidate)
        return candidate
    except ValueError:
        pass
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return candidate
    except ValueError as exc:
        raise ValueError(f"{field_name} must be YYYY-MM-DD or a full ISO 8601 timestamp") from exc


def _apply_ingest_date_overrides(
    *,
    metadata: Dict[str, Any],
    published_at: Optional[str],
    updated_at: Optional[str],
    retrieved_at: Optional[str],
) -> Dict[str, Any]:
    """
    Apply command-line date overrides to canonical ingest metadata.

    :param metadata: Metadata loaded from the ingest metadata file.
    :type metadata: dict[str, Any]
    :param published_at: Optional publication date override.
    :type published_at: str or None
    :param updated_at: Optional update date override.
    :type updated_at: str or None
    :param retrieved_at: Optional retrieval timestamp override.
    :type retrieved_at: str or None
    :return: Metadata with canonical nested date fields.
    :rtype: dict[str, Any]
    :raises ValueError: If date metadata is malformed.
    """
    metadata_for_ingest = dict(metadata)
    legacy_date_fields = [
        field for field in ("published", "updated") if field in metadata_for_ingest
    ]
    if legacy_date_fields:
        joined_fields = ", ".join(legacy_date_fields)
        raise ValueError(
            f"Use dates.published_at or dates.updated_at instead of top-level {joined_fields}"
        )

    raw_dates = metadata_for_ingest.get("dates")
    if raw_dates is None:
        dates: Dict[str, Any] = {}
    elif isinstance(raw_dates, dict):
        dates = dict(raw_dates)
    else:
        raise ValueError("Ingest metadata dates must be a mapping/object")

    raw_date_provenance = metadata_for_ingest.get("date_provenance")
    if raw_date_provenance is None:
        date_provenance: Dict[str, Any] = {}
    elif isinstance(raw_date_provenance, dict):
        date_provenance = dict(raw_date_provenance)
    else:
        raise ValueError("Ingest metadata date_provenance must be a mapping/object")

    overrides = {
        "published_at": published_at,
        "updated_at": updated_at,
        "retrieved_at": retrieved_at,
    }
    for field_name, value in overrides.items():
        if value is None:
            continue
        dates[field_name] = _validate_ingest_date_value(value, field_name)
        date_provenance[field_name] = "cli-argument"

    if dates:
        metadata_for_ingest["dates"] = dates
    elif "dates" in metadata_for_ingest:
        metadata_for_ingest.pop("dates")
    if date_provenance:
        metadata_for_ingest["date_provenance"] = date_provenance
    elif "date_provenance" in metadata_for_ingest:
        metadata_for_ingest.pop("date_provenance")
    return metadata_for_ingest


def _standard_ingest_local_item(
    *,
    corpus: Corpus,
    source_path: str,
    tags: List[str],
    metadata: Dict[str, Any],
    title: Optional[str],
    source_uri: Optional[str],
    media_type: Optional[str],
    published_at: Optional[str],
    updated_at: Optional[str],
    retrieved_at: Optional[str],
) -> object:
    if "://" in source_path:
        raise ValueError("Standard metadata ingest requires a local file path")
    path = Path(source_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Ingest source file not found: {path}")
    metadata_for_ingest = _apply_ingest_date_overrides(
        metadata=metadata,
        published_at=published_at,
        updated_at=updated_at,
        retrieved_at=retrieved_at,
    )
    metadata_for_ingest.pop("tags", None)
    metadata_title = metadata_for_ingest.pop("title", None)
    metadata_media_type = metadata_for_ingest.pop("media_type", None)
    resolved_title = title
    if resolved_title is None and isinstance(metadata_title, str) and metadata_title.strip():
        resolved_title = metadata_title.strip()
    resolved_media_type = media_type
    if resolved_media_type is None and isinstance(metadata_media_type, str):
        resolved_media_type = metadata_media_type.strip() or None
    if resolved_media_type is None:
        guessed_media_type, _ = mimetypes.guess_type(path.name)
        resolved_media_type = guessed_media_type or "application/octet-stream"
    resolved_tags = _parse_tags(None, [*tags, *_metadata_tags(metadata)])
    resolved_source_uri = source_uri or path.as_uri()
    return corpus.ingest_item(
        path.read_bytes(),
        filename=path.name,
        media_type=resolved_media_type,
        title=resolved_title,
        tags=resolved_tags,
        metadata=metadata_for_ingest,
        source_uri=resolved_source_uri,
    )


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
    metadata_path = getattr(arguments, "metadata_file", None)
    source_uri = getattr(arguments, "source_uri", None)
    media_type = getattr(arguments, "media_type", None)
    import_rationale = getattr(arguments, "import_rationale", None)
    published_at = getattr(arguments, "published_at", None)
    updated_at = getattr(arguments, "updated_at", None)
    retrieved_at = getattr(arguments, "retrieved_at", None)
    standard_item_ingest = bool(
        metadata_path or source_uri or media_type or published_at or updated_at or retrieved_at
    )

    results = []

    try:
        if standard_item_ingest:
            if arguments.note is not None or arguments.stdin:
                raise ValueError("Standard metadata ingest requires a local file path")
            files = list(arguments.files or [])
            if len(files) != 1:
                raise ValueError("Standard metadata ingest requires exactly one local file path")
            loaded_metadata = (
                _load_ingest_metadata_file(Path(metadata_path)) if metadata_path else {}
            )
            metadata = _metadata_with_import_rationale(loaded_metadata, import_rationale)
            results.append(
                _standard_ingest_local_item(
                    corpus=corpus,
                    source_path=files[0],
                    tags=tags,
                    metadata=metadata,
                    title=arguments.title,
                    source_uri=source_uri,
                    media_type=media_type,
                    published_at=published_at,
                    updated_at=updated_at,
                    retrieved_at=retrieved_at,
                )
            )
        else:
            if arguments.note is not None or arguments.stdin:
                text = arguments.note if arguments.note is not None else sys.stdin.read()
                ingest_result = corpus.ingest_note(
                    text,
                    title=arguments.title,
                    tags=tags,
                    metadata=_metadata_with_import_rationale({}, import_rationale),
                    source_uri=None if arguments.stdin else None,
                )
                results.append(ingest_result)

            for source_path in arguments.files or []:
                results.append(
                    corpus.ingest_source(
                        source_path,
                        tags=tags,
                        metadata=_metadata_with_import_rationale({}, import_rationale),
                    )
                )
    except IngestCollisionError as error:
        if error.collision_key is not None:
            print(
                "Ingest failed: item already ingested\n"
                f"source_uri: {error.source_uri}\n"
                f"matching_key: {error.collision_key}\n"
                f"existing_item_id: {error.existing_item_id}\n"
                f"existing_relpath: {error.existing_relpath}",
                file=sys.stderr,
            )
            return 3
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


def cmd_corpus_audit(arguments: argparse.Namespace) -> int:
    """
    Build a read-only curation audit for a corpus.

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
    try:
        output = build_corpus_audit(
            corpus=corpus,
            required_tags=arguments.required_tag,
            forbidden_tags=arguments.forbid_tag,
            extraction_snapshot=arguments.extraction_snapshot,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Corpus audit failed: {exc}", file=sys.stderr)
        return 2
    if arguments.format == "markdown":
        print(corpus_audit_markdown(output, top=arguments.top), end="")
    else:
        print(output.model_dump_json(indent=2))
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


def cmd_source_set(arguments: argparse.Namespace) -> int:
    """
    Configure a remote source for a corpus.

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
    config_path = corpus.meta_dir / "config.json"
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    config = CorpusConfig.model_validate(config_data)
    source_payload = {
        "kind": arguments.kind,
        "profile": arguments.profile,
        "name": arguments.name,
        "bucket": arguments.bucket,
        "container": arguments.container,
        "prefix": arguments.prefix or "",
        "folder_url": arguments.folder_url,
    }
    remote_source = RemoteCorpusSourceConfig.model_validate(source_payload)
    updated = config.model_copy(update={"source": remote_source})
    config_path.write_text(updated.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(remote_source.model_dump_json(indent=2))
    return 0


def cmd_source_show(arguments: argparse.Namespace) -> int:
    """
    Show the configured remote source.

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
    if corpus.config is None or corpus.config.source is None:
        raise ValueError("Remote source is not configured for this corpus.")
    print(corpus.config.source.model_dump_json(indent=2))
    return 0


def cmd_source_pull(arguments: argparse.Namespace) -> int:
    """
    Pull the configured remote source into the corpus.

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
    result = corpus.pull_source()
    print(result.model_dump_json(indent=2))
    return 0


def cmd_collection_show(arguments: argparse.Namespace) -> int:
    """
    Show the configured collection metadata.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    collection_root = Path(arguments.collection)
    config = load_collection_config(collection_root)
    print(config.model_dump_json(indent=2))
    return 0


def cmd_collection_pull(arguments: argparse.Namespace) -> int:
    """
    Pull a remote collection into local corpora.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    collection_root = Path(arguments.collection)
    result = pull_collection(collection_root)
    print(result.model_dump_json(indent=2))
    return 0


def cmd_pipeline_run(arguments: argparse.Namespace) -> int:
    """
    Run a pipeline recipe.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    result = run_pipeline_recipe(Path(arguments.recipe))
    print(
        json.dumps(
            {
                "corpora": result.corpora,
                "extraction_snapshot_ids": result.extraction_snapshot_ids,
                "retrieval_snapshot_ids": result.retrieval_snapshot_ids,
            },
            indent=2,
        )
    )
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
    from .configuration import load_configuration_view
    from .models import parse_extraction_snapshot_reference

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

    from .workflow import build_plan_for_extract

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
    results = _execute_dependency_plan(
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
        max_items=arguments.max_items,
        progress_callback=_graph_extract_progress,
    )
    print(manifest.model_dump_json(indent=2))
    return 0


def _graph_extract_progress(event: str, payload: Dict[str, Any]) -> None:
    if event == "starting":
        print(
            "[graph] starting snapshot "
            f"{payload['snapshot_id']} with {payload['items_total']} extraction items",
            file=sys.stderr,
            flush=True,
        )
    elif event == "processing":
        print(
            "[graph] processing "
            f"{payload['item_index']}/{payload['items_total']} item {payload['item_id']}",
            file=sys.stderr,
            flush=True,
        )
    elif event == "processed":
        message = (
            "[graph] processed "
            f"{payload['item_index']}/{payload['items_total']} "
            f"item {payload['item_id']} status={payload['status']} "
            f"nodes={payload['nodes']} edges={payload['edges']}"
        )
        if payload.get("error_message"):
            message = f"{message} error={payload['error_message']}"
        print(message, file=sys.stderr, flush=True)
    elif event == "completed":
        print(
            "[graph] completed snapshot "
            f"{payload['snapshot_id']} processed={payload['items_processed']} "
            f"skipped={payload['items_skipped']} errored={payload['items_errored']} "
            f"nodes={payload['nodes']} edges={payload['edges']}",
            file=sys.stderr,
            flush=True,
        )


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


def cmd_graph_export(arguments: argparse.Namespace) -> int:
    """
    Export a graph snapshot's Neo4j records as portable JSON.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .graph.extraction import export_graph_snapshot
    from .graph.models import parse_graph_snapshot_reference

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    snapshot = parse_graph_snapshot_reference(arguments.snapshot)
    exported = export_graph_snapshot(corpus, snapshot=snapshot)
    payload = exported.model_dump(mode="json")
    if arguments.output:
        output_path = Path(arguments.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_taxonomy_record(arguments: argparse.Namespace) -> int:
    """
    Record an accepted taxonomy manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .taxonomy import record_taxonomy_manifest

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = record_taxonomy_manifest(corpus=corpus, input_path=Path(arguments.input))
    print(output.model_dump_json(indent=2))
    return 0


def cmd_taxonomy_discover(arguments: argparse.Namespace) -> int:
    """
    Discover candidate child taxonomy nodes under accepted root topics.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .steering_feedback import load_steering_feedback
    from .taxonomy import discover_taxonomy_children, taxonomy_discovery_markdown

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Taxonomy discovery",
    )
    steering_feedback = (
        load_steering_feedback(Path(arguments.steering_feedback))
        if arguments.steering_feedback
        else None
    )
    output = discover_taxonomy_children(
        corpus=corpus,
        classifier_id=arguments.classifier,
        extraction_snapshot=extraction_snapshot,
        steering_feedback=steering_feedback,
    )
    if arguments.format == "markdown":
        print(taxonomy_discovery_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_ontology_record(arguments: argparse.Namespace) -> int:
    """
    Record an accepted ontology manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .ontology import record_ontology_manifest

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = record_ontology_manifest(corpus=corpus, input_path=Path(arguments.input))
    print(output.model_dump_json(indent=2))
    return 0


def cmd_ontology_apply(arguments: argparse.Namespace) -> int:
    """
    Apply accepted taxonomy and ontology assertions to a graph snapshot.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .ontology import apply_ontology_to_graph

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = apply_ontology_to_graph(
        corpus=corpus,
        taxonomy_snapshot_id=arguments.taxonomy,
        ontology_snapshot_id=arguments.relationships,
        graph_snapshot=arguments.graph_snapshot,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_ontology_query(arguments: argparse.Namespace) -> int:
    """
    Query accepted ontology assertions.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .ontology import query_ontology_assertions

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = query_ontology_assertions(
        corpus=corpus,
        ontology_snapshot_id=arguments.relationships,
        source_ref=arguments.source_ref,
        relationship_uid=arguments.relationship,
        direction=arguments.direction,
    )
    print(output.model_dump_json(indent=2))
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


def cmd_steering_export(arguments: argparse.Namespace) -> int:
    """
    Export a stable steering bundle for an external application.

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
    bundle = build_steering_export(
        corpus=corpus,
        classifier_id=arguments.classifier,
        topic_governance_snapshot_id=arguments.topic_governance_snapshot,
    )
    print(bundle.model_dump_json(indent=2))
    return 0


def cmd_steering_artifacts(arguments: argparse.Namespace) -> int:
    """
    List stable artifact references for an external steering worker.

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
    inventory = build_steering_artifact_inventory(corpus)
    print(inventory.model_dump_json(indent=2))
    return 0


def cmd_steering_render_seed_manifest(arguments: argparse.Namespace) -> int:
    """
    Render an accepted steering topic set as a Biblicus seed manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    output = render_steering_seed_manifest(
        input_path=Path(arguments.input),
        output_path=Path(arguments.output),
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_steering_graph_signals(arguments: argparse.Namespace) -> int:
    """
    Emit topic-informed graph steering signals.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .steering_feedback import load_steering_feedback

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    steering_feedback = (
        load_steering_feedback(Path(arguments.steering_feedback))
        if arguments.steering_feedback
        else None
    )
    bundle = build_steering_graph_signal_bundle(
        corpus=corpus,
        classifier_id=arguments.classifier,
        graph_snapshot=arguments.graph_snapshot,
        steering_feedback=steering_feedback,
    )
    print(bundle.model_dump_json(indent=2))
    return 0


def cmd_steering_proposals_validate(arguments: argparse.Namespace) -> int:
    """
    Validate an externally authored steering proposal bundle.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    bundle = load_steering_proposal_bundle(Path(arguments.input))
    print(bundle.model_dump_json(indent=2))
    return 0


def cmd_steering_proposals_record(arguments: argparse.Namespace) -> int:
    """
    Record an externally authored steering proposal bundle.

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
    output = record_steering_proposal_bundle(
        corpus=corpus,
        input_path=Path(arguments.input),
    )
    print(output.model_dump_json(indent=2))
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

    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Topic analysis",
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


def cmd_analyze_topic_trends(arguments: argparse.Namespace) -> int:
    """
    Run temporal topic intelligence for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .topic_trends import build_topic_trends, topic_trends_markdown

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    windows = [token.strip() for token in arguments.windows.split(",") if token.strip()]
    output = build_topic_trends(
        corpus=corpus,
        topic_modeling_snapshot_id=arguments.topic_modeling_snapshot,
        classifier_id=arguments.classifier,
        windows=windows,
        as_of=arguments.as_of,
        rank_window=arguments.rank_window,
    )
    if arguments.format == "markdown":
        print(topic_trends_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_topic_granularity_sweep(arguments: argparse.Namespace) -> int:
    """
    Run a topic granularity sweep for a corpus.

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
    from .topic_granularity import (
        run_topic_granularity_sweep,
        topic_granularity_sweep_markdown,
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
    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Topic granularity sweep",
    )
    output = run_topic_granularity_sweep(
        corpus=corpus,
        configuration_name=arguments.configuration_name,
        configuration=configuration_data,
        extraction_snapshot=extraction_snapshot,
        target_topic_range=arguments.target_topic_range,
    )
    if arguments.format == "markdown":
        print(topic_granularity_sweep_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_analyze_topic_context(arguments: argparse.Namespace) -> int:
    """
    Generate a research-agent topic context report for a corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .topic_context import build_topic_context, topic_context_markdown

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = build_topic_context(
        corpus=corpus,
        topic_modeling_snapshot_id=arguments.topic_modeling_snapshot,
        max_topics=arguments.max_topics,
        examples_per_topic=arguments.examples_per_topic,
        summary_model=arguments.summary_model,
        include_outlier=arguments.include_outlier,
    )
    if arguments.format == "markdown":
        print(topic_context_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_migrate_publication_dates(arguments: argparse.Namespace) -> int:
    """
    Migrate legacy publication date metadata into the canonical dates block.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .topic_trends import migrate_publication_dates

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = migrate_publication_dates(corpus=corpus)
    print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_train(arguments: argparse.Namespace) -> int:
    """
    Train a topic classifier model version.

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
    from .topic_classifier import train_topic_classifier

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    configuration_data = load_configuration_view(
        arguments.configuration,
        configuration_label="Topic classifier configuration",
        mapping_error_message="Topic classifier configuration must be a mapping/object",
    )
    overrides = parse_dotted_overrides(arguments.override)
    configuration_data = apply_dotted_overrides(configuration_data, overrides)
    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Topic classifier training",
    )
    output = train_topic_classifier(
        corpus=corpus,
        manifest_path=Path(arguments.manifest).resolve(),
        configuration_name=arguments.configuration_name,
        configuration=configuration_data,
        extraction_snapshot=extraction_snapshot,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_classify(arguments: argparse.Namespace) -> int:
    """
    Classify an existing corpus item with a topic classifier.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .topic_classifier import classify_topic_classifier_item

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = classify_topic_classifier_item(
        corpus=corpus,
        classifier_id=arguments.classifier,
        item_id=arguments.item_id,
        review_threshold=arguments.review_threshold,
        top_k=arguments.top_k,
        record=False,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_project(arguments: argparse.Namespace) -> int:
    """
    Project a topic classifier from an authority corpus onto a target corpus.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .models import parse_extraction_snapshot_reference
    from .topic_classifier import project_topic_classifier_items

    classifier_corpus = Corpus.open(arguments.classifier_corpus)
    target_corpus = Corpus.open(arguments.target_corpus)
    output = project_topic_classifier_items(
        classifier_corpus=classifier_corpus,
        target_corpus=target_corpus,
        classifier_id=arguments.classifier,
        extraction_snapshot=parse_extraction_snapshot_reference(arguments.extraction_snapshot),
        project_all=arguments.project_all,
        item_ids=arguments.item_id or [],
        review_threshold=arguments.review_threshold,
        top_k=arguments.top_k,
        record=arguments.record,
    )
    payload = output.model_dump(mode="json")
    if arguments.format == "markdown":
        print(_topic_classifier_projection_markdown(payload))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_ingest_classify(arguments: argparse.Namespace) -> int:
    """
    Ingest one source and classify it with a topic classifier.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .topic_classifier import ingest_and_classify_topic_classifier_item

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    tags = _parse_tags(arguments.tags, arguments.tag)
    output = ingest_and_classify_topic_classifier_item(
        corpus=corpus,
        classifier_id=arguments.classifier,
        source=arguments.source,
        tags=tags,
        review_threshold=arguments.review_threshold,
        top_k=arguments.top_k,
        record=arguments.record,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_review_batch(arguments: argparse.Namespace) -> int:
    """
    Build a blind batch review table for candidate topic classifier items.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .models import parse_extraction_snapshot_reference
    from .topic_classifier import build_topic_classifier_batch_review

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = build_topic_classifier_batch_review(
        corpus=corpus,
        classifier_id=arguments.classifier,
        extraction_snapshot=parse_extraction_snapshot_reference(arguments.extraction_snapshot),
        topic_modeling_snapshot_id=arguments.topic_modeling_snapshot,
        candidate_tag=arguments.candidate_tag,
        proposed_topic_uid=arguments.proposed_topic_uid,
        review_threshold=arguments.review_threshold,
        record=arguments.record,
    )
    if arguments.format == "markdown":
        print(_topic_classifier_batch_review_markdown(output.model_dump(mode="json")))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_topic_classifier_draft_manifest(arguments: argparse.Namespace) -> int:
    """
    Draft a reviewed seed manifest without mutating the baseline manifest.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .topic_classifier import draft_topic_classifier_manifest

    output = draft_topic_classifier_manifest(
        base_manifest_path=Path(arguments.base_manifest),
        output_path=Path(arguments.output),
        classifier_id=arguments.classifier_id,
        display_name=arguments.display_name,
        description=arguments.description,
        topic_uid=arguments.topic_uid,
        topic_display_name=arguments.topic_display_name,
        topic_description=arguments.topic_description,
        seed_item_ids=arguments.seed_item_id or [],
        holdout_item_ids=arguments.holdout_item_id or [],
    )
    print(output.model_dump_json(indent=2))
    return 0


def _load_research_intake_configuration(paths: List[str]) -> object:
    from .configuration import load_configuration_view
    from .research_intake import ResearchIntakeConfiguration

    payload = load_configuration_view(
        paths,
        configuration_label="Research intake configuration",
        mapping_error_message="Research intake configuration must be a mapping/object",
    )
    return ResearchIntakeConfiguration.model_validate(payload)


def cmd_research_intake_assess(arguments: argparse.Namespace) -> int:
    """
    Assess a research-agent candidate without ingesting it.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .research_intake import assess_research_intake_candidate

    corpus = Corpus.open(arguments.corpus) if arguments.corpus else Corpus.find(Path.cwd())
    metadata = _load_ingest_metadata_file(Path(arguments.metadata_file))
    configuration = _load_research_intake_configuration(arguments.configuration)
    output = assess_research_intake_candidate(
        corpus=corpus,
        classifier_id=arguments.classifier,
        source_path=Path(arguments.source),
        metadata=metadata,
        configuration=configuration,
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_research_intake_ingest(arguments: argparse.Namespace) -> int:
    """
    Assess and conditionally ingest a research-agent candidate.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .research_intake import ingest_research_intake_candidate

    corpus = Corpus.open(arguments.corpus) if arguments.corpus else Corpus.find(Path.cwd())
    metadata = _load_ingest_metadata_file(Path(arguments.metadata_file))
    configuration = _load_research_intake_configuration(arguments.configuration)
    output = ingest_research_intake_candidate(
        corpus=corpus,
        classifier_id=arguments.classifier,
        source_path=Path(arguments.source),
        metadata=metadata,
        configuration=configuration,
        source_uri=arguments.source_uri,
        media_type=arguments.media_type,
        tags=_parse_tags(arguments.tags, arguments.tag),
    )
    print(output.model_dump_json(indent=2))
    return 0


def cmd_research_intake_pending(arguments: argparse.Namespace) -> int:
    """
    List research-agent intake items awaiting review.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .research_intake import (
        list_pending_research_intake_items,
        research_intake_pending_markdown,
    )

    corpus = Corpus.open(arguments.corpus) if arguments.corpus else Corpus.find(Path.cwd())
    output = list_pending_research_intake_items(corpus=corpus)
    if arguments.format == "markdown":
        print(research_intake_pending_markdown(output))
    else:
        print(output.model_dump_json(indent=2))
    return 0


def cmd_research_intake_decide(arguments: argparse.Namespace) -> int:
    """
    Apply a human decision to an existing research intake item.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .research_intake import decide_research_intake_item

    corpus = Corpus.open(arguments.corpus) if arguments.corpus else Corpus.find(Path.cwd())
    output = decide_research_intake_item(
        corpus=corpus,
        item_id=arguments.item_id,
        decision=arguments.decision,
        topic_uid=arguments.topic_uid,
        tags_add=getattr(arguments, "tags_add", None) or [],
        tags_remove=getattr(arguments, "tags_remove", None) or [],
        delete=bool(getattr(arguments, "delete", False)),
    )
    print(output.model_dump_json(indent=2))
    return 0


def _topic_classifier_batch_review_markdown(payload: Dict[str, Any]) -> str:
    """
    Render a topic classifier batch review payload as a Markdown table.

    :param payload: Batch review payload.
    :type payload: dict[str, Any]
    :return: Markdown report.
    :rtype: str
    """
    lines = [
        f"# Topic Classifier Batch Review: {payload['classifier_id']}",
        "",
        f"- Model version: `{payload['model_version']}`",
        f"- Candidate items: {payload['summary']['candidate_items']}",
        f"- Review recommended: {payload['summary']['review_recommended_items']}",
        "",
        "| Item ID | Title | Proposed | Classifier Topic | Score | Review | Discovery Topic | Keywords | Decision |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["items"]:
        keywords = ", ".join(
            str(keyword.get("keyword", "")) for keyword in item.get("unsupervised_keywords", [])[:5]
        )
        score = item.get("classifier_score")
        score_text = "" if score is None else f"{float(score):.3f}"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["item_id"]),
                    _markdown_table_cell(item.get("title") or ""),
                    _markdown_table_cell(item.get("proposed_topic_uid") or ""),
                    _markdown_table_cell(item.get("classifier_topic_uid") or "discovered"),
                    score_text,
                    str(item["review_recommended"]).lower(),
                    (
                        ""
                        if item.get("unsupervised_topic_id") is None
                        else str(item["unsupervised_topic_id"])
                    ),
                    _markdown_table_cell(keywords),
                    _markdown_table_cell(item.get("reviewer_decision") or "pending"),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _topic_classifier_projection_markdown(payload: Dict[str, Any]) -> str:
    """
    Render a topic classifier projection payload as a Markdown table.

    :param payload: Projection payload.
    :type payload: dict[str, Any]
    :return: Markdown report.
    :rtype: str
    """
    lines = [
        f"# Topic Classifier Projection: {payload['classifier_id']}",
        "",
        f"- Model version: `{payload['model_version']}`",
        f"- Classifier corpus: `{payload['classifier_corpus_uri']}`",
        f"- Target corpus: `{payload['target_corpus_uri']}`",
        f"- Projected items: {payload['summary']['projected_items']}",
        f"- Skipped items: {payload['summary']['skipped_items']}",
        f"- Review recommended: {payload['summary']['review_recommended_items']}",
        "",
        "| Item ID | Title | Topic | Score | Review | Candidates | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["items"]:
        score = item.get("score")
        score_text = "" if score is None else f"{float(score):.3f}"
        candidates = _topic_classifier_candidates_markdown(item.get("topic_candidates") or [])
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["item_id"]),
                    _markdown_table_cell(item.get("title") or ""),
                    _markdown_table_cell(item.get("topic_uid") or "review"),
                    score_text,
                    str(item["review_recommended"]).lower(),
                    _markdown_table_cell(candidates),
                    _markdown_table_cell(item.get("source_uri") or ""),
                ]
            )
            + " |"
        )
    if payload.get("skipped_items"):
        lines.extend(
            [
                "",
                "## Skipped Items",
                "",
                "| Item ID | Title | Reason |",
                "| --- | --- | --- |",
            ]
        )
        for item in payload["skipped_items"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(item["item_id"]),
                        _markdown_table_cell(item.get("title") or ""),
                        _markdown_table_cell(item["reason"]),
                    ]
                )
                + " |"
            )
    return "\n".join(lines)


def _topic_classifier_candidates_markdown(candidates: object) -> str:
    """
    Render ranked topic candidates for a compact Markdown table cell.

    :param candidates: Candidate payloads.
    :type candidates: object
    :return: Compact ranked candidate text.
    :rtype: str
    """
    if not isinstance(candidates, list):
        return ""
    values: List[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        label = str(candidate.get("topic_uid") or "discovered")
        score = candidate.get("score")
        score_text = "" if score is None else f" {float(score):.3f}"
        values.append(f"{label}{score_text}")
    return "; ".join(values)


def _markdown_table_cell(value: str) -> str:
    """
    Escape text for a Markdown table cell.

    :param value: Cell value.
    :type value: str
    :return: Escaped cell value.
    :rtype: str
    """
    return value.replace("|", "\\|").replace("\n", " ")


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

    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Profiling analysis",
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

    extraction_snapshot = _resolve_extraction_snapshot_for_analysis(
        corpus=corpus,
        extraction_snapshot=arguments.extraction_snapshot,
        analysis_label="Markov analysis",
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


# -----------------------------------------------------------------
# Benchmark commands
# -----------------------------------------------------------------


def cmd_benchmark_download(arguments: argparse.Namespace) -> int:
    """
    Download benchmark datasets.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    import subprocess

    if isinstance(arguments.datasets, str):
        datasets = [d.strip() for d in arguments.datasets.split(",")]
    else:
        datasets = [str(d).strip() for d in arguments.datasets]
    corpus_dir = Path(arguments.corpus_dir)
    count = arguments.count
    force = arguments.force

    print("=" * 70)
    print("BIBLICUS BENCHMARK DATASET DOWNLOAD")
    print("=" * 70)

    for dataset in datasets:
        print(f"\nDownloading {dataset}...")

        if dataset == "funsd":
            corpus_path = corpus_dir / "funsd_benchmark"
            cmd = ["python", "scripts/download_funsd_samples.py", "--corpus", str(corpus_path)]
            if count:
                cmd.extend(["--count", str(count)])
            if force:
                cmd.append("--force")

        elif dataset == "sroie":
            corpus_path = corpus_dir / "sroie_benchmark"
            cmd = ["python", "scripts/download_sroie_samples.py", "--corpus", str(corpus_path)]
            if count:
                cmd.extend(["--count", str(count)])
            if force:
                cmd.append("--force")

        elif dataset == "scanned-arxiv":
            print("  NOTICE: scanned-arxiv dataset is not yet available.")
            print("          The HuggingFace dataset lacks actual scanned images.")
            print("          This category is pending a suitable dataset source.")
            continue

        else:
            print(f"  Unknown dataset: {dataset}")
            continue

        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"  ERROR: Failed to download {dataset}")
        else:
            print(f"  Downloaded {dataset} to {corpus_path}")

    return 0


def cmd_benchmark_run(arguments: argparse.Namespace) -> int:
    """
    Run benchmark evaluation.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from .evaluation.benchmark_runner import BenchmarkConfig, BenchmarkRunner

    config_path = Path(arguments.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Benchmark configuration not found: {config_path}")

    config = BenchmarkConfig.load(config_path)

    # Override pipelines if specified
    if arguments.pipelines:
        config.pipelines = [Path(p.strip()) for p in arguments.pipelines.split(",")]

    runner = BenchmarkRunner(config)

    # Run specific category or all
    if arguments.category:
        if arguments.category not in config.categories:
            raise ValueError(
                f"Unknown category: {arguments.category}. "
                f"Available: {', '.join(config.categories.keys())}"
            )
        cat_config = config.categories[arguments.category]
        result = runner.run_category(cat_config)
        print(f"\n{arguments.category.upper()} Results:")
        print(
            f"  Best pipeline: {result.best_pipeline} ({result.best_score:.3f} {result.primary_metric})"
        )
    else:
        result = runner.run_all()
        result.print_summary()

        # Save results
        output_path = (
            Path(arguments.output)
            if arguments.output
            else Path(f"results/benchmark_{config.benchmark_name}.json")
        )
        result.to_json(output_path)
        print(f"\nResults saved to: {output_path}")

        # Also generate markdown report
        md_path = output_path.with_suffix(".md")
        result.to_markdown(md_path)
        print(f"Markdown report: {md_path}")

    return 0


def cmd_benchmark_report(arguments: argparse.Namespace) -> int:
    """
    Generate benchmark report from results.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    import glob
    import json

    input_pattern = arguments.input
    output_path = Path(arguments.output)

    # Find all matching result files
    result_files = glob.glob(input_pattern)
    if not result_files:
        raise FileNotFoundError(f"No result files found matching: {input_pattern}")

    print(f"Generating report from {len(result_files)} result file(s)...")

    # For now, just use the first/latest result file
    # TODO: Merge multiple results for comparison
    result_path = Path(sorted(result_files)[-1])

    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Generate markdown report
    lines = [
        "# Biblicus Document Understanding Benchmark Results",
        "",
        f"**Source:** {result_path.name}",
        f"**Benchmark:** {data.get('benchmark_name', 'unknown')}",
        f"**Date:** {data.get('timestamp', 'unknown')}",
        "",
        "## Summary",
        "",
    ]

    categories = data.get("categories", {})
    if categories:
        lines.extend(
            [
                "| Category | Dataset | Docs | Best Pipeline | Score |",
                "|----------|---------|------|---------------|-------|",
            ]
        )
        for cat_name, cat_data in categories.items():
            lines.append(
                f"| {cat_name.title()} | {cat_data.get('dataset', '')} | "
                f"{cat_data.get('documents_evaluated', 0)} | "
                f"{cat_data.get('best_pipeline', '')} | "
                f"{cat_data.get('best_score', 0):.3f} |"
            )

    recommendations = data.get("recommendations", {})
    if recommendations:
        lines.extend(["", "## Recommendations", ""])
        for rec_type, pipeline in recommendations.items():
            lines.append(f"- **{rec_type.replace('_', ' ').title()}:** {pipeline}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report generated: {output_path}")
    return 0


def cmd_benchmark_status(arguments: argparse.Namespace) -> int:
    """
    Show status of benchmark datasets.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    corpus_dir = Path(arguments.corpus_dir)

    print("=" * 70)
    print("BIBLICUS BENCHMARK DATASET STATUS")
    print("=" * 70)

    datasets = [
        ("funsd", "funsd_benchmark", "funsd_ground_truth"),
        ("sroie", "sroie_benchmark", "sroie_ground_truth"),
        # ("scanned-arxiv", "scanned_arxiv_benchmark", "scanned_arxiv_ground_truth"),  # Pending - need dataset with images
    ]

    for name, corpus_name, gt_subdir in datasets:
        corpus_path = corpus_dir / corpus_name
        status = "NOT DOWNLOADED"
        doc_count = 0

        if corpus_path.exists():
            # Check both .biblicus (standard) and metadata (legacy) locations
            meta_dir = corpus_path / ".biblicus"
            if not meta_dir.exists():
                meta_dir = corpus_path / "metadata"

            config_file = meta_dir / "config.json"
            gt_dir = meta_dir / gt_subdir

            if config_file.exists():
                status = "DOWNLOADED"
                if gt_dir.exists():
                    doc_count = len(list(gt_dir.glob("*.txt")))
                    status = f"READY ({doc_count} docs)"

        print(f"  {name:15} {status}")

    print()
    print("To download datasets:")
    print("  biblicus benchmark download --datasets funsd,sroie")

    return 0


def cmd_dashboard_sync(arguments: argparse.Namespace) -> int:
    """Sync corpus catalog to Amplify dashboard backend."""
    from .sync.amplify_publisher import AmplifyPublisher

    corpus = (
        Corpus.open(arguments.corpus) if getattr(arguments, "corpus", None) else Corpus.discover()
    )

    # Create publisher
    publisher = AmplifyPublisher(corpus.name)

    print(f"Syncing {corpus.name} to dashboard backend...")

    # Create corpus record if it doesn't exist
    try:
        publisher.create_corpus()
        print("✓ Corpus record created/verified")
    except Exception as e:
        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
            print(f"✗ Failed to create corpus: {e}", file=sys.stderr)
            return 1

    # Sync catalog
    try:
        result = publisher.sync_catalog(corpus.catalog_path, force=arguments.force)

        if result.skipped:
            print(f"✓ Catalog unchanged (hash: {result.hash[:8]}...)")
        else:
            print(
                f"✓ Synced: {result.created} created, {result.updated} updated, {result.deleted} deleted"
            )

        if result.errors:
            print(f"⚠ {len(result.errors)} errors occurred:", file=sys.stderr)
            for error in result.errors[:5]:
                print(f"  - {error}", file=sys.stderr)
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more", file=sys.stderr)
            return 1

        return 0
    except Exception as e:
        print(f"✗ Sync failed: {e}", file=sys.stderr)
        return 1


def cmd_dashboard_configure(arguments: argparse.Namespace) -> int:
    """Configure Amplify backend credentials."""
    from pathlib import Path

    # Save configuration to ~/.biblicus/amplify.env
    config_dir = Path.home() / ".biblicus"
    config_dir.mkdir(exist_ok=True)

    config_path = config_dir / "amplify.env"

    config_content = f"""# Amplify Dashboard Backend Configuration
AMPLIFY_APPSYNC_ENDPOINT={arguments.endpoint}
AMPLIFY_API_KEY={arguments.api_key}
AMPLIFY_S3_BUCKET={arguments.bucket}
AWS_REGION={arguments.region}
"""

    config_path.write_text(config_content)
    print(f"✓ Configuration saved to {config_path}")
    print()
    print("Auto-sync will now work automatically after extraction/ingest.")
    print("Set AMPLIFY_AUTO_SYNC_CATALOG=false to disable auto-sync.")

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

    p_migrate = sub.add_parser(
        "migrate-layout", help="Migrate a legacy corpus layout to the current layout."
    )
    p_migrate.add_argument("path", help="Corpus path or file:// uniform resource identifier.")
    p_migrate.add_argument(
        "--force", action="store_true", help="Overwrite existing paths if present."
    )
    p_migrate.set_defaults(func=cmd_migrate_layout)

    p_migrate_dates = sub.add_parser(
        "migrate-publication-dates",
        help="Move legacy publication metadata into dates.published_at and dates.updated_at.",
    )
    _add_common_corpus_arg(p_migrate_dates)
    p_migrate_dates.set_defaults(func=cmd_migrate_publication_dates)

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
    p_ingest.add_argument(
        "--metadata-file",
        default=None,
        help="YAML or JSON metadata object for standard single-item ingest.",
    )
    p_ingest.add_argument(
        "--import-rationale",
        default=None,
        help="Optional explanation of why the item belongs in the corpus.",
    )
    p_ingest.add_argument(
        "--source-uri",
        default=None,
        help="Explicit source uniform resource identifier for standard single-item ingest.",
    )
    p_ingest.add_argument(
        "--media-type",
        default=None,
        help="Explicit media type for standard single-item ingest.",
    )
    p_ingest.add_argument(
        "--published-at",
        default=None,
        help="Publication date for canonical metadata dates.published_at.",
    )
    p_ingest.add_argument(
        "--updated-at",
        default=None,
        help="Update date for canonical metadata dates.updated_at.",
    )
    p_ingest.add_argument(
        "--retrieved-at",
        default=None,
        help="Retrieval timestamp for canonical metadata dates.retrieved_at.",
    )
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

    p_corpus = sub.add_parser("corpus", help="Inspect and audit corpora.")
    corpus_sub = p_corpus.add_subparsers(dest="corpus_command", required=True)
    p_corpus_audit = corpus_sub.add_parser(
        "audit", help="Run a read-only curation audit for a corpus."
    )
    _add_common_corpus_arg(p_corpus_audit)
    p_corpus_audit.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format.",
    )
    p_corpus_audit.add_argument(
        "--required-tag",
        action="append",
        default=[],
        help="Tag expected on every item. Repeatable.",
    )
    p_corpus_audit.add_argument(
        "--forbid-tag",
        action="append",
        default=[],
        help="Tag expected on no item. Repeatable.",
    )
    p_corpus_audit.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Optional extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_corpus_audit.add_argument(
        "--top",
        type=int,
        default=20,
        help="Maximum facet rows to show in Markdown output.",
    )
    p_corpus_audit.set_defaults(func=cmd_corpus_audit)

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

    p_source = sub.add_parser("source", help="Manage remote corpus sources.")
    source_sub = p_source.add_subparsers(dest="source_command", required=True)

    p_source_set = source_sub.add_parser("set", help="Configure the remote source for a corpus.")
    _add_common_corpus_arg(p_source_set)
    p_source_set.add_argument("--kind", required=True, choices=["s3", "azure-blob", "google-drive"])
    p_source_set.add_argument("--profile", required=True, help="Source profile name.")
    p_source_set.add_argument(
        "--name", default=None, help="Local storage namespace for the source."
    )
    p_source_set.add_argument("--bucket", default=None, help="S3 bucket name.")
    p_source_set.add_argument("--container", default=None, help="Azure Blob container name.")
    p_source_set.add_argument(
        "--folder-url", default=None, help="Google Drive folder URL (for google-drive sources)."
    )
    p_source_set.add_argument("--prefix", default=None, help="Optional remote prefix to mirror.")
    p_source_set.set_defaults(func=cmd_source_set)

    p_source_show = source_sub.add_parser("show", help="Show the configured remote source.")
    _add_common_corpus_arg(p_source_show)
    p_source_show.set_defaults(func=cmd_source_show)

    p_source_pull = source_sub.add_parser("pull", help="Mirror the remote source into the corpus.")
    _add_common_corpus_arg(p_source_pull)
    p_source_pull.set_defaults(func=cmd_source_pull)

    p_collection = sub.add_parser("collection", help="Manage remote collections.")
    collection_sub = p_collection.add_subparsers(dest="collection_command", required=True)
    p_collection_show = collection_sub.add_parser("show", help="Show the collection config.")
    p_collection_show.add_argument("--collection", required=True, help="Collection root path.")
    p_collection_show.set_defaults(func=cmd_collection_show)
    p_collection_pull = collection_sub.add_parser("pull", help="Mirror a remote collection.")
    p_collection_pull.add_argument("--collection", required=True, help="Collection root path.")
    p_collection_pull.set_defaults(func=cmd_collection_pull)

    p_pipeline = sub.add_parser("pipeline", help="Run pipeline recipes.")
    pipeline_sub = p_pipeline.add_subparsers(dest="pipeline_command", required=True)
    p_pipeline_run = pipeline_sub.add_parser("run", help="Run a pipeline recipe.")
    p_pipeline_run.add_argument("--recipe", required=True, help="Pipeline recipe path.")
    p_pipeline_run.set_defaults(func=cmd_pipeline_run)

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

    p_graph_extract = graph_sub.add_parser("extract", help="Build a graph extraction snapshot.")
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
    p_graph_extract.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Maximum number of extraction items to process for bounded validation runs.",
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

    p_graph_show = graph_sub.add_parser("show", help="Show a graph extraction snapshot manifest.")
    _add_common_corpus_arg(p_graph_show)
    p_graph_show.add_argument(
        "--snapshot",
        required=True,
        help="Graph snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_graph_show.set_defaults(func=cmd_graph_show)

    p_graph_export = graph_sub.add_parser(
        "export",
        help="Export graph snapshot nodes and edges as portable JSON.",
    )
    _add_common_corpus_arg(p_graph_export)
    p_graph_export.add_argument(
        "--snapshot",
        required=True,
        help="Graph snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_graph_export.add_argument(
        "--output",
        default=None,
        help="Path to write the graph export JSON. Defaults to standard output.",
    )
    p_graph_export.set_defaults(func=cmd_graph_export)

    p_taxonomy = sub.add_parser("taxonomy", help="Validate and discover accepted topic taxonomy.")
    taxonomy_sub = p_taxonomy.add_subparsers(dest="taxonomy_command", required=True)

    p_taxonomy_record = taxonomy_sub.add_parser(
        "record", help="Record an accepted taxonomy JSON manifest."
    )
    _add_common_corpus_arg(p_taxonomy_record)
    p_taxonomy_record.add_argument(
        "--input",
        required=True,
        help="Accepted taxonomy JSON input.",
    )
    p_taxonomy_record.set_defaults(func=cmd_taxonomy_record)

    p_taxonomy_discover = taxonomy_sub.add_parser(
        "discover", help="Discover candidate child taxonomy nodes."
    )
    _add_common_corpus_arg(p_taxonomy_discover)
    p_taxonomy_discover.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier used to collect root topic members.",
    )
    p_taxonomy_discover.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_taxonomy_discover.add_argument(
        "--steering-feedback",
        default=None,
        help="Papyrus steering feedback JSON with reviewed suppressions.",
    )
    p_taxonomy_discover.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_taxonomy_discover.set_defaults(func=cmd_taxonomy_discover)

    p_ontology = sub.add_parser("ontology", help="Validate and materialize accepted ontology.")
    ontology_sub = p_ontology.add_subparsers(dest="ontology_command", required=True)

    p_ontology_record = ontology_sub.add_parser(
        "record", help="Record an accepted ontology JSON manifest."
    )
    _add_common_corpus_arg(p_ontology_record)
    p_ontology_record.add_argument(
        "--input",
        required=True,
        help="Accepted ontology JSON input.",
    )
    p_ontology_record.set_defaults(func=cmd_ontology_record)

    p_ontology_apply = ontology_sub.add_parser(
        "apply", help="Materialize accepted taxonomy and ontology into a graph snapshot."
    )
    _add_common_corpus_arg(p_ontology_apply)
    p_ontology_apply.add_argument(
        "--taxonomy",
        required=True,
        help="Taxonomy snapshot id or latest.",
    )
    p_ontology_apply.add_argument(
        "--relationships",
        required=True,
        help="Ontology relationship snapshot id or latest.",
    )
    p_ontology_apply.add_argument(
        "--graph-snapshot",
        required=True,
        help="Graph snapshot reference in extractor_id:snapshot_id form.",
    )
    p_ontology_apply.set_defaults(func=cmd_ontology_apply)

    p_ontology_query = ontology_sub.add_parser(
        "query", help="Query accepted ontology relationship assertions."
    )
    _add_common_corpus_arg(p_ontology_query)
    p_ontology_query.add_argument(
        "--relationships",
        required=True,
        help="Ontology relationship snapshot id or latest.",
    )
    p_ontology_query.add_argument("--source-ref", default=None, help="Source reference filter.")
    p_ontology_query.add_argument(
        "--relationship",
        default=None,
        help="Relationship type filter.",
    )
    p_ontology_query.add_argument(
        "--direction",
        choices=["outbound", "inbound", "both"],
        default="outbound",
        help="Relationship direction filter.",
    )
    p_ontology_query.set_defaults(func=cmd_ontology_query)

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

    p_steering = sub.add_parser("steering", help="Export Biblicus steering integration contracts.")
    steering_sub = p_steering.add_subparsers(dest="steering_command", required=True)

    p_steering_export = steering_sub.add_parser(
        "export", help="Emit a stable JSON bundle for external application import."
    )
    _add_common_corpus_arg(p_steering_export)
    p_steering_export.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier used to load the accepted topic set.",
    )
    p_steering_export.add_argument(
        "--topic-governance-snapshot",
        default=None,
        help="Topic governance snapshot identifier. Defaults to the latest pointer when omitted.",
    )
    p_steering_export.set_defaults(func=cmd_steering_export)

    p_steering_artifacts = steering_sub.add_parser(
        "artifacts", help="List stable Biblicus artifact references."
    )
    _add_common_corpus_arg(p_steering_artifacts)
    p_steering_artifacts.set_defaults(func=cmd_steering_artifacts)

    p_steering_graph_signals = steering_sub.add_parser(
        "graph-signals",
        help="Emit topic-informed graph steering signals.",
    )
    _add_common_corpus_arg(p_steering_graph_signals)
    p_steering_graph_signals.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier used to load accepted topics.",
    )
    p_steering_graph_signals.add_argument(
        "--graph-snapshot",
        required=True,
        help="Graph snapshot reference in extractor_id:snapshot_id form.",
    )
    p_steering_graph_signals.add_argument(
        "--steering-feedback",
        default=None,
        help="Papyrus steering feedback JSON with reviewed suppressions.",
    )
    p_steering_graph_signals.add_argument(
        "--format",
        choices=["json"],
        default="json",
        help="Output format.",
    )
    p_steering_graph_signals.set_defaults(func=cmd_steering_graph_signals)

    p_steering_proposals = steering_sub.add_parser(
        "proposals",
        help="Validate and record steering proposal bundles.",
    )
    steering_proposals_sub = p_steering_proposals.add_subparsers(
        dest="steering_proposals_command",
        required=True,
    )

    p_steering_proposals_validate = steering_proposals_sub.add_parser(
        "validate",
        help="Validate an externally authored steering proposal bundle.",
    )
    p_steering_proposals_validate.add_argument(
        "--input",
        required=True,
        help="Steering proposal bundle JSON input.",
    )
    p_steering_proposals_validate.set_defaults(func=cmd_steering_proposals_validate)

    p_steering_proposals_record = steering_proposals_sub.add_parser(
        "record",
        help="Record an externally authored steering proposal bundle.",
    )
    _add_common_corpus_arg(p_steering_proposals_record)
    p_steering_proposals_record.add_argument(
        "--input",
        required=True,
        help="Steering proposal bundle JSON input.",
    )
    p_steering_proposals_record.set_defaults(func=cmd_steering_proposals_record)

    p_steering_render = steering_sub.add_parser(
        "render-seed-manifest",
        help="Render an accepted steering topic set into a Biblicus seed manifest.",
    )
    p_steering_render.add_argument(
        "--input",
        required=True,
        help="Accepted steering topic-set JSON input.",
    )
    p_steering_render.add_argument(
        "--output",
        required=True,
        help="Destination Biblicus seed-manifest.json path.",
    )
    p_steering_render.set_defaults(func=cmd_steering_render_seed_manifest)

    p_research_intake = sub.add_parser(
        "research-intake", help="Assess and manage research-agent intake candidates."
    )
    research_intake_sub = p_research_intake.add_subparsers(
        dest="research_intake_command", required=True
    )

    p_research_intake_assess = research_intake_sub.add_parser(
        "assess", help="Assess a local candidate without ingesting it."
    )
    _add_common_corpus_arg(p_research_intake_assess)
    p_research_intake_assess.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_research_intake_assess.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to research intake configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_research_intake_assess.add_argument(
        "--metadata-file",
        required=True,
        help="YAML or JSON candidate metadata object.",
    )
    p_research_intake_assess.add_argument("source", help="Local candidate file path.")
    p_research_intake_assess.set_defaults(func=cmd_research_intake_assess)

    p_research_intake_ingest = research_intake_sub.add_parser(
        "ingest", help="Assess a local candidate and ingest it when accepted or pending."
    )
    _add_common_corpus_arg(p_research_intake_ingest)
    p_research_intake_ingest.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_research_intake_ingest.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to research intake configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_research_intake_ingest.add_argument(
        "--metadata-file",
        required=True,
        help="YAML or JSON candidate metadata object.",
    )
    p_research_intake_ingest.add_argument(
        "--source-uri",
        default=None,
        help="Explicit source uniform resource identifier for accepted or pending ingest.",
    )
    p_research_intake_ingest.add_argument(
        "--media-type",
        default=None,
        help="Explicit media type for accepted or pending ingest.",
    )
    p_research_intake_ingest.add_argument("--tags", default=None, help="Comma-separated tags.")
    p_research_intake_ingest.add_argument(
        "--tag", action="append", help="Repeatable tag to apply to accepted or pending ingest."
    )
    p_research_intake_ingest.add_argument("source", help="Local candidate file path.")
    p_research_intake_ingest.set_defaults(func=cmd_research_intake_ingest)

    p_research_intake_pending = research_intake_sub.add_parser(
        "pending", help="List research intake items awaiting review."
    )
    _add_common_corpus_arg(p_research_intake_pending)
    p_research_intake_pending.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_research_intake_pending.set_defaults(func=cmd_research_intake_pending)

    p_research_intake_decide = research_intake_sub.add_parser(
        "decide", help="Apply a human decision to an existing intake item."
    )
    _add_common_corpus_arg(p_research_intake_decide)
    p_research_intake_decide.add_argument(
        "--item-id",
        required=True,
        help="Pending item identifier.",
    )
    p_research_intake_decide.add_argument(
        "--decision",
        required=True,
        choices=["accept", "reject"],
        help="Human intake decision.",
    )
    p_research_intake_decide.add_argument(
        "--topic-uid",
        default=None,
        help="Reviewed topic identity for accepted items.",
    )
    p_research_intake_decide.add_argument(
        "--tags-add",
        action="append",
        default=None,
        help="Repeatable tag to add during the decision.",
    )
    p_research_intake_decide.add_argument(
        "--tags-remove",
        action="append",
        default=None,
        help="Repeatable tag to remove during the decision.",
    )
    p_research_intake_decide.add_argument(
        "--delete",
        action="store_true",
        help="Delete the item files when rejecting (reject-only).",
    )
    p_research_intake_decide.set_defaults(func=cmd_research_intake_decide)

    p_topic_classifier = sub.add_parser(
        "topic-classifier", help="Train and use semi-supervised topic classifiers."
    )
    topic_classifier_sub = p_topic_classifier.add_subparsers(
        dest="topic_classifier_command", required=True
    )

    p_topic_classifier_train = topic_classifier_sub.add_parser(
        "train", help="Train a topic classifier model version."
    )
    _add_common_corpus_arg(p_topic_classifier_train)
    p_topic_classifier_train.add_argument(
        "--manifest",
        required=True,
        help="Path to topic classifier seed-manifest.json.",
    )
    p_topic_classifier_train.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to topic classifier configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_topic_classifier_train.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_topic_classifier_train.add_argument(
        "--configuration-name",
        default="default",
        help="Human-readable configuration name.",
    )
    p_topic_classifier_train.add_argument(
        "--extraction-snapshot",
        default=None,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_topic_classifier_train.set_defaults(func=cmd_topic_classifier_train)

    p_topic_classifier_classify = topic_classifier_sub.add_parser(
        "classify", help="Classify an existing corpus item."
    )
    _add_common_corpus_arg(p_topic_classifier_classify)
    p_topic_classifier_classify.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_topic_classifier_classify.add_argument(
        "--item-id",
        required=True,
        help="Corpus item identifier to classify.",
    )
    p_topic_classifier_classify.add_argument(
        "--review-threshold",
        type=float,
        default=0.35,
        help="Minimum confidence score before review is recommended.",
    )
    p_topic_classifier_classify.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum ranked topic candidates to include.",
    )
    p_topic_classifier_classify.set_defaults(func=cmd_topic_classifier_classify)

    p_topic_classifier_project = topic_classifier_sub.add_parser(
        "project",
        help="Project a classifier from an authority corpus onto a target corpus.",
    )
    p_topic_classifier_project.add_argument(
        "--classifier-corpus",
        required=True,
        help="Corpus path or uniform resource identifier containing classifier artifacts.",
    )
    p_topic_classifier_project.add_argument(
        "--target-corpus",
        required=True,
        help="Corpus path or uniform resource identifier containing target items.",
    )
    p_topic_classifier_project.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_topic_classifier_project.add_argument(
        "--extraction-snapshot",
        required=True,
        help="Target corpus extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_topic_classifier_project.add_argument(
        "--all",
        action="store_true",
        dest="project_all",
        help="Project the classifier onto every target corpus item.",
    )
    p_topic_classifier_project.add_argument(
        "--item-id",
        action="append",
        default=[],
        help="Repeatable target item identifier to project.",
    )
    p_topic_classifier_project.add_argument(
        "--review-threshold",
        type=float,
        default=0.35,
        help="Minimum confidence score before review is recommended.",
    )
    p_topic_classifier_project.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum ranked topic candidates to include.",
    )
    p_topic_classifier_project.add_argument(
        "--record",
        action="store_true",
        help="Persist projection predictions as audit records in the target corpus.",
    )
    p_topic_classifier_project.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_topic_classifier_project.set_defaults(func=cmd_topic_classifier_project)

    p_topic_classifier_ingest = topic_classifier_sub.add_parser(
        "ingest-classify", help="Ingest one source and classify it immediately."
    )
    _add_common_corpus_arg(p_topic_classifier_ingest)
    p_topic_classifier_ingest.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_topic_classifier_ingest.add_argument(
        "--review-threshold",
        type=float,
        default=0.35,
        help="Minimum confidence score before review is recommended.",
    )
    p_topic_classifier_ingest.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum ranked topic candidates to include.",
    )
    p_topic_classifier_ingest.add_argument(
        "--record",
        action="store_true",
        help="Persist the prediction as an audit record.",
    )
    p_topic_classifier_ingest.add_argument("--tags", default=None, help="Comma-separated tags.")
    p_topic_classifier_ingest.add_argument(
        "--tag", action="append", help="Repeatable tag to apply to the ingested item."
    )
    p_topic_classifier_ingest.add_argument("source", help="Path or URL to ingest and classify.")
    p_topic_classifier_ingest.set_defaults(func=cmd_topic_classifier_ingest_classify)

    p_topic_classifier_review = topic_classifier_sub.add_parser(
        "review-batch",
        help="Review blind candidate items against classifier and discovery outputs.",
    )
    _add_common_corpus_arg(p_topic_classifier_review)
    p_topic_classifier_review.add_argument(
        "--classifier",
        required=True,
        help="Topic classifier identifier.",
    )
    p_topic_classifier_review.add_argument(
        "--extraction-snapshot",
        required=True,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_topic_classifier_review.add_argument(
        "--topic-modeling-snapshot",
        required=True,
        help="Exploratory topic modeling snapshot identifier.",
    )
    p_topic_classifier_review.add_argument(
        "--candidate-tag",
        default=None,
        help="Candidate tag required for included items.",
    )
    p_topic_classifier_review.add_argument(
        "--proposed-topic-uid",
        default=None,
        help="Candidate proposed topic identity required for included items.",
    )
    p_topic_classifier_review.add_argument(
        "--review-threshold",
        type=float,
        default=0.35,
        help="Minimum confidence score before review is recommended.",
    )
    p_topic_classifier_review.add_argument(
        "--record",
        action="store_true",
        help="Persist classifier predictions as audit records.",
    )
    p_topic_classifier_review.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_topic_classifier_review.set_defaults(func=cmd_topic_classifier_review_batch)

    p_topic_classifier_draft = topic_classifier_sub.add_parser(
        "draft-manifest", help="Draft a reviewed seed manifest without changing the baseline."
    )
    p_topic_classifier_draft.add_argument(
        "--base-manifest",
        required=True,
        help="Existing seed manifest to copy.",
    )
    p_topic_classifier_draft.add_argument(
        "--output",
        required=True,
        help="Destination path for the drafted seed manifest.",
    )
    p_topic_classifier_draft.add_argument(
        "--classifier-id",
        default=None,
        help="Optional classifier identifier override. Omit to preserve the base classifier identity.",
    )
    p_topic_classifier_draft.add_argument(
        "--display-name",
        default=None,
        help="Optional display name override. Omit to preserve the base display name.",
    )
    p_topic_classifier_draft.add_argument(
        "--description",
        default=None,
        help="Optional description override. Omit to preserve the base description.",
    )
    p_topic_classifier_draft.add_argument(
        "--topic-uid", required=True, help="Topic identity to add."
    )
    p_topic_classifier_draft.add_argument(
        "--topic-display-name",
        required=True,
        help="Human-readable topic label.",
    )
    p_topic_classifier_draft.add_argument(
        "--topic-description",
        required=True,
        help="Reviewed topic definition.",
    )
    p_topic_classifier_draft.add_argument(
        "--seed-item-id",
        action="append",
        required=True,
        help="Reviewed seed item identifier. Repeat for multiple seeds.",
    )
    p_topic_classifier_draft.add_argument(
        "--holdout-item-id",
        action="append",
        default=[],
        help="Reviewed holdout item identifier. Repeat for multiple holdouts.",
    )
    p_topic_classifier_draft.set_defaults(func=cmd_topic_classifier_draft_manifest)

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

    p_analyze_topic_granularity = analyze_sub.add_parser(
        "topic-granularity-sweep",
        help="Compare topic modeling granularity profiles and label the selected profile.",
    )
    _add_common_corpus_arg(p_analyze_topic_granularity)
    p_analyze_topic_granularity.add_argument(
        "--configuration",
        required=True,
        action="append",
        help="Path to topic modeling configuration YAML. Repeatable; later files override earlier ones.",
    )
    p_analyze_topic_granularity.add_argument(
        "--override",
        "--config",
        action="append",
        default=[],
        help="Override key=value pairs applied after composing configurations (supports dotted keys).",
    )
    p_analyze_topic_granularity.add_argument(
        "--configuration-name",
        default="granularity-sweep",
        help="Human-readable configuration name.",
    )
    p_analyze_topic_granularity.add_argument(
        "--extraction-snapshot",
        required=True,
        help="Extraction snapshot reference in the form extractor_id:snapshot_id.",
    )
    p_analyze_topic_granularity.add_argument(
        "--target-topic-range",
        default="10:20",
        help="Target non-outlier topic count range in min:max form.",
    )
    p_analyze_topic_granularity.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_analyze_topic_granularity.set_defaults(func=cmd_analyze_topic_granularity_sweep)

    p_analyze_topic_context = analyze_sub.add_parser(
        "topic-context", help="Generate Markdown or JSON topic context for research agents."
    )
    _add_common_corpus_arg(p_analyze_topic_context)
    p_analyze_topic_context.add_argument(
        "--topic-modeling-snapshot",
        required=True,
        help="Topic modeling snapshot identifier to summarize.",
    )
    p_analyze_topic_context.add_argument(
        "--max-topics",
        type=int,
        default=20,
        help="Maximum non-outlier topic buckets to include.",
    )
    p_analyze_topic_context.add_argument(
        "--examples-per-topic",
        type=int,
        default=3,
        help="Maximum representative examples per topic.",
    )
    p_analyze_topic_context.add_argument(
        "--summary-model",
        default=None,
        help="Optional OpenAI model for topic guidance and missing example summaries.",
    )
    p_analyze_topic_context.add_argument(
        "--include-outlier",
        action="store_true",
        help="Include BERTopic outlier topic -1 in the report.",
    )
    p_analyze_topic_context.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format.",
    )
    p_analyze_topic_context.set_defaults(func=cmd_analyze_topic_context)

    p_analyze_topic_trends = analyze_sub.add_parser(
        "topic-trends", help="Run publication-date topic trend analysis."
    )
    _add_common_corpus_arg(p_analyze_topic_trends)
    p_analyze_topic_trends.add_argument(
        "--topic-modeling-snapshot",
        required=True,
        help="Topic modeling snapshot identifier to analyze.",
    )
    p_analyze_topic_trends.add_argument(
        "--classifier",
        default=None,
        help="Optional topic classifier identifier for canonical topic coverage.",
    )
    p_analyze_topic_trends.add_argument(
        "--windows",
        default="30d,90d,1y,all",
        help="Comma-separated publication windows such as 30d,90d,1y,all.",
    )
    p_analyze_topic_trends.add_argument(
        "--as-of",
        default=None,
        help="Publication date anchor for trend windows. Defaults to latest dates.published_at.",
    )
    p_analyze_topic_trends.add_argument(
        "--rank-window",
        default="90d",
        help="Window used to rank topics. Must be included in --windows.",
    )
    p_analyze_topic_trends.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format.",
    )
    p_analyze_topic_trends.set_defaults(func=cmd_analyze_topic_trends)

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

    # -----------------------------------------------------------------
    # benchmark subcommand group
    # -----------------------------------------------------------------
    p_benchmark = sub.add_parser("benchmark", help="Run document understanding benchmarks.")
    benchmark_sub = p_benchmark.add_subparsers(dest="benchmark_command", required=True)

    p_benchmark_download = benchmark_sub.add_parser("download", help="Download benchmark datasets.")
    p_benchmark_download.add_argument(
        "--datasets",
        required=True,
        help="Comma-separated list of datasets to download (funsd, sroie, scanned-arxiv).",
    )
    p_benchmark_download.add_argument(
        "--corpus-dir",
        default="corpora",
        help="Base directory for benchmark corpora (default: corpora).",
    )
    p_benchmark_download.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of samples to download per dataset (default: dataset-specific).",
    )
    p_benchmark_download.add_argument(
        "--force", action="store_true", help="Overwrite existing corpus if present."
    )
    p_benchmark_download.set_defaults(func=cmd_benchmark_download)

    p_benchmark_run = benchmark_sub.add_parser("run", help="Run benchmark evaluation.")
    p_benchmark_run.add_argument(
        "--config",
        default="configs/benchmark/standard.yaml",
        help="Path to benchmark configuration file (default: configs/benchmark/standard.yaml).",
    )
    p_benchmark_run.add_argument(
        "--category",
        default=None,
        help="Run only a specific category (forms, academic, receipts).",
    )
    p_benchmark_run.add_argument(
        "--pipelines",
        default=None,
        help="Comma-separated list of pipeline config paths to benchmark.",
    )
    p_benchmark_run.add_argument(
        "--output",
        default=None,
        help="Output path for results JSON (default: results/benchmark_<name>.json).",
    )
    p_benchmark_run.set_defaults(func=cmd_benchmark_run)

    p_benchmark_report = benchmark_sub.add_parser(
        "report", help="Generate benchmark report from results."
    )
    p_benchmark_report.add_argument(
        "--input",
        required=True,
        help="Path to benchmark results JSON file(s). Supports glob patterns.",
    )
    p_benchmark_report.add_argument(
        "--output",
        default="docs/guides/benchmark-results.md",
        help="Output path for markdown report.",
    )
    p_benchmark_report.set_defaults(func=cmd_benchmark_report)

    p_benchmark_status = benchmark_sub.add_parser(
        "status", help="Show status of benchmark datasets."
    )
    p_benchmark_status.add_argument(
        "--corpus-dir",
        default="corpora",
        help="Base directory for benchmark corpora (default: corpora).",
    )
    p_benchmark_status.set_defaults(func=cmd_benchmark_status)

    # Dashboard commands
    p_dashboard = sub.add_parser("dashboard", help="Manage dashboard backend synchronization.")
    dashboard_sub = p_dashboard.add_subparsers(dest="dashboard_command", required=True)

    p_dashboard_sync = dashboard_sub.add_parser("sync", help="Sync corpus to dashboard backend.")
    _add_common_corpus_arg(p_dashboard_sync)
    p_dashboard_sync.add_argument(
        "--force",
        action="store_true",
        help="Force full sync even if catalog unchanged.",
    )
    p_dashboard_sync.set_defaults(func=cmd_dashboard_sync)

    p_dashboard_configure = dashboard_sub.add_parser(
        "configure", help="Configure Amplify backend credentials."
    )
    p_dashboard_configure.add_argument(
        "--endpoint",
        required=True,
        help="AppSync GraphQL endpoint URL.",
    )
    p_dashboard_configure.add_argument(
        "--api-key",
        required=True,
        help="AppSync API key.",
    )
    p_dashboard_configure.add_argument(
        "--bucket",
        required=True,
        help="S3 bucket name for corpus storage.",
    )
    p_dashboard_configure.add_argument(
        "--region",
        default="us-west-2",
        help="AWS region (default: us-west-2).",
    )
    p_dashboard_configure.set_defaults(func=cmd_dashboard_configure)

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
        RemoteSourceDependencyError,
        NotImplementedError,
        ValidationError,
    ) as exception:
        message = exception.args[0] if getattr(exception, "args", None) else str(exception)
        print(str(message), file=sys.stderr)
        return 2
