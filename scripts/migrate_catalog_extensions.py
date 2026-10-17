"""
Migrate a corpus catalog so extension data lives under item ``metadata``.

Earlier Biblicus releases folded unknown top-level catalog item fields into
``metadata`` while reading. Catalog loading is now strict, so catalogs that still
carry such fields must be migrated once with this script. Extension data belongs
under ``metadata`` (for example ``metadata.papyrus``); Biblicus stores it and never
interprets it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from biblicus.corpus import Corpus
from biblicus.models import CatalogItem

CATALOG_ITEM_ROOT_FIELDS = frozenset(CatalogItem.model_fields.keys())


def migrate_catalog_item_payload(item: Mapping[str, Any]) -> dict[str, Any]:
    """
    Move unknown top-level keys of one catalog item under its ``metadata``.

    Dictionary values are merged into an existing dictionary under the same
    ``metadata`` key, with the top-level value winning on conflicts.

    :param item: Raw catalog item mapping.
    :type item: Mapping[str, Any]
    :return: Item mapping containing only canonical root fields.
    :rtype: dict[str, Any]
    """
    migrated: dict[str, Any] = {}
    existing_metadata = item.get("metadata")
    metadata = dict(existing_metadata) if isinstance(existing_metadata, dict) else {}
    for key, value in item.items():
        if key == "metadata":
            continue
        if key in CATALOG_ITEM_ROOT_FIELDS:
            migrated[key] = value
            continue
        if isinstance(metadata.get(key), dict) and isinstance(value, dict):
            metadata[key] = {**metadata[key], **value}
        else:
            metadata[key] = value
    migrated["metadata"] = metadata
    return migrated


def migrate_catalog_payload(catalog_data: Mapping[str, Any]) -> dict[str, Any]:
    """
    Migrate every item of a raw catalog document.

    :param catalog_data: Raw catalog mapping.
    :type catalog_data: Mapping[str, Any]
    :return: Catalog mapping with canonical item fields.
    :rtype: dict[str, Any]
    """
    migrated = dict(catalog_data)
    migrated["items"] = {
        item_identifier: migrate_catalog_item_payload(item)
        for item_identifier, item in catalog_data.get("items", {}).items()
    }
    return migrated


def migrate_catalog_file(corpus_path: Path, *, dry_run: bool) -> int:
    """
    Migrate the catalog of one corpus, writing atomically unless ``dry_run`` is set.

    :param corpus_path: Corpus root path.
    :type corpus_path: Path
    :param dry_run: When true, report changes and write nothing.
    :type dry_run: bool
    :return: Number of items whose top-level fields were moved.
    :rtype: int
    """
    catalog_path = Corpus.open(corpus_path).catalog_path
    catalog_data = json.loads(catalog_path.read_text(encoding="utf-8"))
    migrated = migrate_catalog_payload(catalog_data)
    changed_item_count = sum(
        1
        for item_identifier, item in catalog_data.get("items", {}).items()
        if migrated["items"][item_identifier] != item
    )
    if changed_item_count and not dry_run:
        temporary_path = catalog_path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(migrated, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(catalog_path)
    return changed_item_count


def main(argument_list: Optional[Sequence[str]] = None) -> int:
    """
    Run the migration command-line interface.

    :param argument_list: Optional argument list; defaults to ``sys.argv``.
    :type argument_list: Sequence[str] or None
    :return: Process exit code.
    :rtype: int
    """
    parser = argparse.ArgumentParser(
        description="Move unknown top-level catalog item fields under item metadata."
    )
    parser.add_argument("corpus", type=Path, help="Corpus root path.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing."
    )
    arguments = parser.parse_args(argument_list)
    changed_item_count = migrate_catalog_file(arguments.corpus, dry_run=arguments.dry_run)
    verb = "Would migrate" if arguments.dry_run else "Migrated"
    print(f"{verb} {changed_item_count} item(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
