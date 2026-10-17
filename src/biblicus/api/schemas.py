"""
Generation and drift checking for the published JSON Schemas of the typed application programming interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from . import build_api_schemas

PUBLISHED_SCHEMA_DIRECTORY_NAME = "api-schemas"


def schema_file_name(schema_key: str) -> str:
    """
    Map a schema key such as ``taxonomy-discover.request`` to its published file name.

    :param schema_key: Key from :func:`biblicus.api.build_api_schemas`.
    :type schema_key: str
    :return: File name ending in ``.schema.json``.
    :rtype: str
    """
    return f"{schema_key}.schema.json"


def render_schema_text(schema: Dict[str, Any]) -> str:
    """
    Render one schema as stable, human-diffable JSON text.

    :param schema: JSON Schema object.
    :type schema: dict[str, Any]
    :return: Indented JSON with sorted keys and a trailing newline.
    :rtype: str
    """
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def write_api_schemas(directory: Path) -> List[str]:
    """
    Write every request and response schema into a directory.

    :param directory: Destination directory, created when missing.
    :type directory: pathlib.Path
    :return: Names of the files written, sorted.
    :rtype: list[str]
    """
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for schema_key, schema in build_api_schemas().items():
        file_name = schema_file_name(schema_key)
        (directory / file_name).write_text(render_schema_text(schema), encoding="utf-8")
        written.append(file_name)
    return sorted(written)


def find_stale_api_schemas(directory: Path) -> List[str]:
    """
    Compare the published schemas in a directory with the models and list every difference.

    :param directory: Directory holding the published schema files.
    :type directory: pathlib.Path
    :return: Descriptions of missing, changed and unexpected files; empty when current.
    :rtype: list[str]
    """
    expected = {
        schema_file_name(schema_key): render_schema_text(schema)
        for schema_key, schema in build_api_schemas().items()
    }
    problems = []
    for file_name, expected_text in sorted(expected.items()):
        path = directory / file_name
        if not path.is_file():
            problems.append(f"missing: {file_name}")
        elif path.read_text(encoding="utf-8") != expected_text:
            problems.append(f"changed: {file_name}")
    present = (
        {path.name for path in directory.glob("*.schema.json")} if directory.is_dir() else set()
    )
    for file_name in sorted(present - set(expected)):
        problems.append(f"unexpected: {file_name}")
    return problems
