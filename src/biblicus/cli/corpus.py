"""
Corpus, ingestion, source, collection, and pipeline commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..api import validate_request
from ..collections import load_collection_config, pull_collection
from ..corpus import Corpus
from ..corpus_audit import build_corpus_audit, corpus_audit_markdown
from ..errors import IngestCollisionError
from ..migration import migrate_layout
from ..models import (
    CorpusConfig,
    RemoteCorpusSourceConfig,
)
from ..pipelines import run_pipeline_recipe
from ..uris import corpus_ref_to_path
from .common import (
    _add_common_corpus_arg,
    _corpus_path_from_arguments,
    _load_ingest_metadata_file,
    _parse_tags,
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
    from ..api import ReindexRequest, reindex

    request = validate_request(
        ReindexRequest, "reindex", corpus_path=_corpus_path_from_arguments(arguments)
    )
    print(reindex(request).model_dump_json(indent=2))
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


def cmd_migrate_publication_dates(arguments: argparse.Namespace) -> int:
    """
    Migrate legacy publication date metadata into the canonical dates block.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..topic_trends import migrate_publication_dates

    corpus = (
        Corpus.open(arguments.corpus)
        if getattr(arguments, "corpus", None)
        else Corpus.find(Path.cwd())
    )
    output = migrate_publication_dates(corpus=corpus)
    print(output.model_dump_json(indent=2))
    return 0


def register_corpus_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the corpus commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_init = subparsers.add_parser("init", help="Initialize a new corpus at PATH.")
    p_init.add_argument("path", help="Corpus path or file:// uniform resource identifier.")
    p_init.add_argument(
        "--force", action="store_true", help="Overwrite existing config if present."
    )
    p_init.set_defaults(func=cmd_init)

    p_migrate = subparsers.add_parser(
        "migrate-layout", help="Migrate a legacy corpus layout to the current layout."
    )
    p_migrate.add_argument("path", help="Corpus path or file:// uniform resource identifier.")
    p_migrate.add_argument(
        "--force", action="store_true", help="Overwrite existing paths if present."
    )
    p_migrate.set_defaults(func=cmd_migrate_layout)

    p_migrate_dates = subparsers.add_parser(
        "migrate-publication-dates",
        help="Move legacy publication metadata into dates.published_at and dates.updated_at.",
    )
    _add_common_corpus_arg(p_migrate_dates)
    p_migrate_dates.set_defaults(func=cmd_migrate_publication_dates)

    p_ingest = subparsers.add_parser("ingest", help="Ingest file(s) and/or text into the corpus.")
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

    p_list = subparsers.add_parser("list", help="List recently ingested items.")
    _add_common_corpus_arg(p_list)
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_list)

    p_show = subparsers.add_parser("show", help="Show metadata for an item identifier.")
    _add_common_corpus_arg(p_show)
    p_show.add_argument("id", help="Item identifier (universally unique identifier).")
    p_show.set_defaults(func=cmd_show)

    p_reindex = subparsers.add_parser(
        "reindex", help="Rebuild/refresh the corpus catalog from the on-disk corpus."
    )
    _add_common_corpus_arg(p_reindex)
    p_reindex.set_defaults(func=cmd_reindex)

    p_corpus = subparsers.add_parser("corpus", help="Inspect and audit corpora.")
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

    p_import_tree = subparsers.add_parser(
        "import-tree", help="Import a folder tree into the corpus."
    )
    _add_common_corpus_arg(p_import_tree)
    p_import_tree.add_argument("path", help="Folder tree root to import.")
    p_import_tree.add_argument(
        "--tags", default=None, help="Comma-separated tags to apply to imported items."
    )
    p_import_tree.add_argument(
        "--tag", action="append", help="Repeatable tag to apply to imported items."
    )
    p_import_tree.set_defaults(func=cmd_import_tree)

    p_source = subparsers.add_parser("source", help="Manage remote corpus sources.")
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

    p_collection = subparsers.add_parser("collection", help="Manage remote collections.")
    collection_sub = p_collection.add_subparsers(dest="collection_command", required=True)
    p_collection_show = collection_sub.add_parser("show", help="Show the collection config.")
    p_collection_show.add_argument("--collection", required=True, help="Collection root path.")
    p_collection_show.set_defaults(func=cmd_collection_show)
    p_collection_pull = collection_sub.add_parser("pull", help="Mirror a remote collection.")
    p_collection_pull.add_argument("--collection", required=True, help="Collection root path.")
    p_collection_pull.set_defaults(func=cmd_collection_pull)

    p_pipeline = subparsers.add_parser("pipeline", help="Run pipeline recipes.")
    pipeline_sub = p_pipeline.add_subparsers(dest="pipeline_command", required=True)
    p_pipeline_run = pipeline_sub.add_parser("run", help="Run a pipeline recipe.")
    p_pipeline_run.add_argument("--recipe", required=True, help="Pipeline recipe path.")
    p_pipeline_run.set_defaults(func=cmd_pipeline_run)

    p_purge = subparsers.add_parser(
        "purge", help="Delete all items and derived files (requires confirmation)."
    )
    _add_common_corpus_arg(p_purge)
    p_purge.add_argument(
        "--confirm",
        default=None,
        help="Type the corpus name (directory basename) to confirm purging.",
    )
    p_purge.set_defaults(func=cmd_purge)
