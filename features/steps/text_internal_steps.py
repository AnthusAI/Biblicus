from __future__ import annotations

import json
from typing import Any, Optional

from behave import then, when

from biblicus.text.extract import _extract_validation_error_from_messages
from biblicus.text.tool_loop import _build_no_tool_calls_message


@when(
    'I build a no-tool-calls message with assistant text "{assistant_text}" and current text "{current_text}"'
)
def step_build_no_tool_calls_message(context, assistant_text: str, current_text: str) -> None:
    context.no_tool_calls_message = _build_no_tool_calls_message(
        assistant_message=assistant_text, current_text=current_text
    )


@when('I build a no-tool-calls message with empty assistant text and current text "{current_text}"')
def step_build_no_tool_calls_message_empty_assistant(context, current_text: str) -> None:
    context.no_tool_calls_message = _build_no_tool_calls_message(
        assistant_message="", current_text=current_text
    )


@then('the no-tool-calls message includes "{expected}"')
def step_no_tool_calls_message_includes(context, expected: str) -> None:
    message = getattr(context, "no_tool_calls_message", None)
    assert isinstance(message, str)
    assert expected in message


@then('the no-tool-calls message does not include "{unexpected}"')
def step_no_tool_calls_message_does_not_include(context, unexpected: str) -> None:
    message = getattr(context, "no_tool_calls_message", None)
    assert isinstance(message, str)
    assert unexpected not in message


@when("I attempt to extract a validation error from messages:")
def step_extract_validation_error_from_messages(context) -> None:
    raw = str(getattr(context, "text", "") or "")
    parsed = json.loads(raw)
    assert isinstance(parsed, list)
    messages: list[dict[str, Any]] = []
    for entry in parsed:
        assert isinstance(entry, dict)
        messages.append(entry)
    context.extracted_validation_error = _extract_validation_error_from_messages(messages)


@then('the extracted validation error equals "{expected}"')
def step_extracted_validation_error_equals(context, expected: str) -> None:
    extracted = getattr(context, "extracted_validation_error", None)
    assert isinstance(extracted, str)
    assert extracted == expected


@then("no extracted validation error is returned")
def step_no_extracted_validation_error(context) -> None:
    extracted: Optional[str] = getattr(context, "extracted_validation_error", None)
    assert extracted is None
