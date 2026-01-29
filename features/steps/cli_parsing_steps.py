from __future__ import annotations

from typing import List

from behave import then, when

from biblicus.cli import _parse_config_pairs, _parse_step_spec


def _table_pairs(rows) -> List[str]:
    pairs: List[str] = []
    for row in rows:
        if "pair" in row.headings:
            pairs.append(row["pair"])
        else:
            pairs.append(row[0])
    return pairs


@when("I parse config pairs:")
def step_parse_config_pairs(context) -> None:
    pairs = _table_pairs(context.table)
    context.parsed_config = _parse_config_pairs(pairs)


@then('the parsed config value "{key}" is float {expected:g}')
def step_config_value_float(context, key: str, expected: float) -> None:
    value = context.parsed_config.get(key)
    assert isinstance(value, float)
    assert value == expected


@then('the parsed config value "{key}" is string "{expected}"')
def step_config_value_string(context, key: str, expected: str) -> None:
    value = context.parsed_config.get(key)
    assert isinstance(value, str)
    assert value == expected


@when("I attempt to parse config pairs:")
def step_attempt_parse_config_pairs(context) -> None:
    pairs = _table_pairs(context.table)
    try:
        _parse_config_pairs(pairs)
        context.config_parse_error = None
    except ValueError as exc:
        context.config_parse_error = exc


@then("a config parsing error is raised")
def step_config_parse_error(context) -> None:
    assert context.config_parse_error is not None


@then('the config parsing error mentions "{message}"')
def step_config_parse_error_message(context, message: str) -> None:
    assert message in str(context.config_parse_error)


@when("I attempt to parse an empty step spec")
def step_attempt_parse_empty_step_spec(context) -> None:
    try:
        _parse_step_spec("")
        context.step_spec_parse_error = None
    except ValueError as exc:
        context.step_spec_parse_error = exc


@then("a step spec parsing error is raised")
def step_step_spec_parse_error(context) -> None:
    assert context.step_spec_parse_error is not None


@then('the step spec parsing error mentions "{message}"')
def step_step_spec_parse_error_message(context, message: str) -> None:
    assert message in str(context.step_spec_parse_error)
