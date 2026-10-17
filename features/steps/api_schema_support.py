"""
Minimal JSON Schema validation against the published Biblicus application programming interface schemas.

The validator covers the keywords that Pydantic emits so scenarios can prove that command-line
interface output conforms to the schema published in ``docs/api-schemas`` without an extra dependency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

PUBLISHED_SCHEMA_DIRECTORY = Path(__file__).resolve().parents[2] / "docs" / "api-schemas"

_TYPE_CHECKS = {
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "null": lambda value: value is None,
    "array": lambda value: isinstance(value, list),
    "object": lambda value: isinstance(value, dict),
}


def load_published_schema(command_name: str, kind: str) -> dict:
    """
    Load one published schema file.

    :param command_name: Command file stem, for example ``taxonomy-discover``.
    :type command_name: str
    :param kind: ``request`` or ``response``.
    :type kind: str
    :return: Parsed JSON Schema.
    :rtype: dict
    """
    path = PUBLISHED_SCHEMA_DIRECTORY / f"{command_name}.{kind}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def schema_violations(instance: Any, schema: dict, root: dict, location: str = "$") -> List[str]:
    """
    Collect every violation of a schema by an instance.

    :param instance: Parsed JSON value.
    :type instance: Any
    :param schema: Schema or sub-schema to apply.
    :type schema: dict
    :param root: Root schema used to resolve ``$ref``.
    :type root: dict
    :param location: Path of the instance inside the document, for messages.
    :type location: str
    :return: Violation descriptions; empty when valid.
    :rtype: list[str]
    """
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return schema_violations(instance, target, root, location)
    violations: List[str] = []
    if "anyOf" in schema or "oneOf" in schema:
        options = schema.get("anyOf") or schema.get("oneOf")
        if not any(not schema_violations(instance, option, root, location) for option in options):
            violations.append(f"{location}: matches none of the allowed alternatives")
    for option in schema.get("allOf", []):
        violations.extend(schema_violations(instance, option, root, location))
    if "const" in schema and instance != schema["const"]:
        violations.append(f"{location}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        violations.append(f"{location}: {instance!r} is not one of {schema['enum']!r}")
    if "type" in schema:
        allowed = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPE_CHECKS[name](instance) for name in allowed):
            violations.append(f"{location}: expected {allowed}, found {type(instance).__name__}")
            return violations
    if isinstance(instance, str) and len(instance) < schema.get("minLength", 0):
        violations.append(f"{location}: shorter than {schema['minLength']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            violations.append(f"{location}: below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            violations.append(f"{location}: above maximum {schema['maximum']}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            violations.append(f"{location}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for index, element in enumerate(instance):
                violations.extend(
                    schema_violations(element, schema["items"], root, f"{location}[{index}]")
                )
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in instance:
                violations.append(f"{location}: missing required property {name!r}")
        additional = schema.get("additionalProperties", True)
        for name, value in instance.items():
            if name in properties:
                violations.extend(
                    schema_violations(value, properties[name], root, f"{location}.{name}")
                )
            elif additional is False:
                violations.append(f"{location}: unexpected property {name!r}")
            elif isinstance(additional, dict):
                violations.extend(schema_violations(value, additional, root, f"{location}.{name}"))
    return violations


def assert_matches_published_schema(command_name: str, kind: str, instance: Any) -> None:
    """
    Assert that an instance conforms to a published schema.

    :param command_name: Command file stem, for example ``taxonomy-discover``.
    :type command_name: str
    :param kind: ``request`` or ``response``.
    :type kind: str
    :param instance: Parsed JSON value.
    :type instance: Any
    :raises AssertionError: If the instance violates the schema.
    """
    schema = load_published_schema(command_name, kind)
    violations = schema_violations(instance, schema, schema)
    assert not violations, f"{command_name} {kind} schema violations: {violations}"
