from __future__ import annotations

import json
from typing import Dict, List

from behave import given, then, when

from biblicus.recipes import apply_dotted_overrides, parse_dotted_overrides, parse_override_value


@when("I parse override values:")
def step_parse_override_values(context) -> None:
    parsed: List[object] = []
    expected: List[object] = []
    for row in context.table:
        raw = str(row["raw"])
        expected_json = str(row["expected_json"])
        parsed.append(parse_override_value(raw))
        expected.append(json.loads(expected_json))
    context.parsed_override_values = parsed
    context.expected_override_values = expected


@then("the parsed override values match the expected JSON")
def step_parsed_override_values_match(context) -> None:
    parsed = getattr(context, "parsed_override_values", None)
    expected = getattr(context, "expected_override_values", None)
    assert parsed is not None and expected is not None
    assert parsed == expected


@given("a base config mapping exists:")
def step_base_config_mapping_exists(context) -> None:
    context.base_config_mapping = json.loads(str(getattr(context, "text", "") or "{}"))


@when("I apply dotted overrides:")
def step_apply_dotted_overrides(context) -> None:
    base = getattr(context, "base_config_mapping", None)
    assert isinstance(base, dict)
    overrides: Dict[str, object] = {}
    for row in context.table:
        key = str(row["key"]).strip()
        value = str(row["value"]).strip()
        overrides[key] = parse_override_value(value)
    context.updated_config_mapping = apply_dotted_overrides(base, overrides)


@then("the updated config JSON equals:")
def step_updated_config_json_equals(context) -> None:
    updated = getattr(context, "updated_config_mapping", None)
    assert isinstance(updated, dict)
    expected = json.loads(str(getattr(context, "text", "") or "{}"))
    assert updated == expected


@when("I attempt to parse dotted overrides:")
def step_attempt_parse_dotted_overrides(context) -> None:
    pairs: List[str] = [str(row["pair"]) for row in context.table]
    try:
        context.last_overrides = parse_dotted_overrides(pairs)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_overrides = None
        context.last_error = exc


@when("I attempt to apply dotted overrides:")
def step_attempt_apply_dotted_overrides(context) -> None:
    base = getattr(context, "base_config_mapping", None)
    assert isinstance(base, dict)
    overrides: Dict[str, object] = {}
    for row in context.table:
        key = str(row["key"])
        value = str(row["value"])
        overrides[key] = parse_override_value(value)
    try:
        context.updated_config_mapping = apply_dotted_overrides(base, overrides)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.updated_config_mapping = None
        context.last_error = exc


@then("a ValueError is raised")
def step_value_error_is_raised(context) -> None:
    exc = getattr(context, "last_error", None)
    assert exc is not None, "Expected an error but no error was raised"
    assert isinstance(exc, ValueError), f"Expected ValueError, got {type(exc).__name__}"


@then('the ValueError message includes "{snippet}"')
def step_value_error_message_includes(context, snippet: str) -> None:
    exc = getattr(context, "last_error", None)
    assert isinstance(exc, ValueError), "Expected ValueError"
    assert snippet in str(exc)
