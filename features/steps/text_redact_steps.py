from __future__ import annotations

import re
from typing import List, Optional

from behave import given, then, when

from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text.models import TextRedactRequest
from biblicus.text.redact import (
    _apply_redact_replace,
    _build_retry_message,
    _validate_preserved_text,
    _validate_redaction_markup,
    apply_text_redact,
)
from biblicus.text.tool_loop import ToolLoopResult


def _redact_system_prompt_template() -> str:
    return (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word 'return' in the user's request as: wrap the returned text with "
        "<span>...</span> in-place in the current text.\n"
        "{% if redaction_types %}"
        "Each span must include a redact attribute with one of: "
        "{{ redaction_types | join(', ') }}.\n"
        "{% else %}"
        "Do not add any span attributes.\n"
        "{% endif %}\n"
        "Use the str_replace tool to insert span tags and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <span ...> and </span> inserted.\n"
        "- Do not include <span or </span> inside old_str or new_str.\n"
        "- Do not insert nested spans.\n"
        "- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n"
        "- Do not delete, reorder, or paraphrase text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )


def _parse_redaction_types(raw: str) -> Optional[List[str]]:
    cleaned = [token.strip() for token in raw.split(",") if token.strip()]
    if not cleaned:
        return None
    return cleaned


def _build_redact_request(
    *,
    text: str,
    prompt_template: str,
    redaction_types: Optional[List[str]] = None,
    max_rounds: int = 6,
    max_edits_per_round: int = 10,
    api_key: Optional[str] = "test-openai-key",
    timeout_seconds: Optional[float] = None,
) -> TextRedactRequest:
    return TextRedactRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key=api_key,
            response_format="json_object",
            timeout_seconds=timeout_seconds,
        ),
        prompt_template=prompt_template,
        system_prompt=_redact_system_prompt_template(),
        redaction_types=redaction_types,
        max_rounds=max_rounds,
        max_edits_per_round=max_edits_per_round,
    )


@when('I apply text redact to text "{text}" without redaction types')
def step_apply_text_redact(context, text: str) -> None:
    request = _build_redact_request(text=text, prompt_template="Return the requested text.")
    context.text_redact_result = apply_text_redact(request)


@when('I apply text redact to text "{text}" with prompt template:')
def step_apply_text_redact_with_prompt(context, text: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    request = _build_redact_request(
        text=text,
        prompt_template=prompt_template,
        api_key=None,
        timeout_seconds=300.0,
    )
    context.text_redact_result = apply_text_redact(request)


@when('I apply text redact to text "{text}" with prompt template and default system prompt:')
def step_apply_text_redact_with_prompt_default_system(context, text: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    request = TextRedactRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key=None,
            response_format="json_object",
            timeout_seconds=300.0,
        ),
        prompt_template=prompt_template,
        max_rounds=10,
        max_edits_per_round=200,
    )
    context.text_redact_result = apply_text_redact(request)


@when('I apply text redact to text "{text}" with redaction types "{types}"')
def step_apply_text_redact_with_types(context, text: str, types: str) -> None:
    redaction_types = _parse_redaction_types(types)
    request = _build_redact_request(
        text=text,
        prompt_template="Return the requested text.",
        redaction_types=redaction_types,
    )
    context.text_redact_result = apply_text_redact(request)


@when('I apply text redact to text "{text}" with redaction types "{types}" and prompt template:')
def step_apply_text_redact_with_types_and_prompt(context, text: str, types: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    redaction_types = _parse_redaction_types(types)
    request = _build_redact_request(
        text=text,
        prompt_template=prompt_template,
        redaction_types=redaction_types,
        api_key=None,
        timeout_seconds=300.0,
    )
    context.text_redact_result = apply_text_redact(request)


@when('I attempt to apply text redact to text "{text}" without redaction types')
def step_attempt_text_redact(context, text: str) -> None:
    request = _build_redact_request(
        text=text,
        prompt_template="Return the requested text.",
        max_rounds=1,
        max_edits_per_round=5,
    )
    try:
        context.text_redact_result = apply_text_redact(request)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)


@when('I attempt to apply text redact to text "{text}" with redaction types "{types}"')
def step_attempt_text_redact_with_types(context, text: str, types: str) -> None:
    redaction_types = _parse_redaction_types(types)
    request = _build_redact_request(
        text=text,
        prompt_template="Return the requested text.",
        redaction_types=redaction_types,
        max_rounds=1,
        max_edits_per_round=5,
    )
    try:
        context.text_redact_result = apply_text_redact(request)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)


@then("the text redact has {count:d} spans")
def step_text_redact_span_count(context, count: int) -> None:
    result = context.text_redact_result
    assert len(result.spans) == count


@then("the text redact has at least {count:d} spans")
def step_text_redact_span_count_at_least(context, count: int) -> None:
    result = context.text_redact_result
    assert len(result.spans) >= count


@then('the text redact span {index:d} text equals "{expected}"')
def step_text_redact_span_text(context, index: int, expected: str) -> None:
    result = context.text_redact_result
    assert result.spans[index - 1].text == expected


@then('the text redact span {index:d} has attribute "{name}" equals "{value}"')
def step_text_redact_span_attribute(context, index: int, name: str, value: str) -> None:
    result = context.text_redact_result
    assert result.spans[index - 1].attributes.get(name) == value


@then('the text redact has a span with attribute "{name}" equals "{value}"')
def step_text_redact_has_attribute_value(context, name: str, value: str) -> None:
    result = context.text_redact_result
    assert any(span.attributes.get(name) == value for span in result.spans)


@then("the text redact does not split words")
def step_text_redact_no_word_splits(context) -> None:
    result = context.text_redact_result
    marked = result.marked_up_text
    assert re.search(r"\w<span\b", marked) is None
    assert re.search(r"\w</span>\w", marked) is None


@then('the text redact error mentions "{text}"')
def step_text_redact_error_mentions(context, text: str) -> None:
    error = context.text_redact_error
    assert error is not None
    assert text in error


@given("the text redact retry errors are:")
def step_set_text_redact_retry_errors(context) -> None:
    raw = str(getattr(context, "text", "") or "")
    errors = [line.strip() for line in raw.splitlines() if line.strip()]
    context.text_redact_retry_errors = errors


@when("I build a text redact retry message for markup:")
def step_build_text_redact_retry_message(context) -> None:
    errors = getattr(context, "text_redact_retry_errors", []) or []
    current_text = str(getattr(context, "text", "") or "")
    context.text_redact_retry_message = _build_retry_message(errors, current_text, None)


@then('the text redact retry message includes "{text}"')
def step_text_redact_retry_message_includes(context, text: str) -> None:
    message = context.text_redact_retry_message
    assert text in message


@then("the text redact retry message includes span context")
def step_text_redact_retry_message_has_context(context) -> None:
    message = context.text_redact_retry_message
    assert "Relevant spans" in message


@when("I apply text redact with a non-done tool loop result")
def step_apply_text_redact_with_incomplete_tool_loop(context) -> None:
    request = _build_redact_request(text="Account", prompt_template="Return the requested text.")
    replacement = "<span>Account</span>"

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text=replacement, done=False, last_error=None, messages=[])

    from biblicus.text import redact as redact_module

    original = redact_module.run_tool_loop
    redact_module.run_tool_loop = fake_tool_loop
    try:
        context.text_redact_result = apply_text_redact(request)
    finally:
        redact_module.run_tool_loop = original


@when("I apply text redact with no edits and confirmation reaches max rounds without done")
def step_apply_text_redact_confirmation_max_rounds_without_done(context) -> None:
    request = _build_redact_request(
        text="Account",
        prompt_template="Return spans.",
        redaction_types=["pii"],
    )

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Account", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Account", done=False, last_error=None, messages=[])

    from biblicus.text import redact as redact_module

    original = redact_module.run_tool_loop
    original_confirm = redact_module.request_confirmation
    redact_module.run_tool_loop = fake_tool_loop
    redact_module.request_confirmation = fake_confirmation
    try:
        context.text_redact_result = apply_text_redact(request)
        context.text_redact_error = None
    finally:
        redact_module.run_tool_loop = original
        redact_module.request_confirmation = original_confirm


@when("I apply text redact with no edits and confirmation inserts spans")
def step_apply_text_redact_confirmation_inserts_spans(context) -> None:
    request = _build_redact_request(
        text="Account",
        prompt_template="Return spans.",
        redaction_types=["pii"],
    )
    marked_up = '<span redact="pii">Account</span>'

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Account", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text=marked_up, done=True, last_error=None, messages=[])

    from biblicus.text import redact as redact_module

    original = redact_module.run_tool_loop
    original_confirm = redact_module.request_confirmation
    redact_module.run_tool_loop = fake_tool_loop
    redact_module.request_confirmation = fake_confirmation
    try:
        context.text_redact_result = apply_text_redact(request)
        context.text_redact_error = None
    finally:
        redact_module.run_tool_loop = original
        redact_module.request_confirmation = original_confirm


@when("I attempt text redact where confirmation fails with a last error")
def step_attempt_text_redact_confirmation_last_error(context) -> None:
    request = _build_redact_request(
        text="Account",
        prompt_template="Return spans.",
        redaction_types=["pii"],
    )

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Account", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(
            text="Account",
            done=False,
            last_error="confirmation error",
            messages=[],
        )

    from biblicus.text import redact as redact_module

    original = redact_module.run_tool_loop
    original_confirm = redact_module.request_confirmation
    redact_module.run_tool_loop = fake_tool_loop
    redact_module.request_confirmation = fake_confirmation
    try:
        apply_text_redact(request)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)
    finally:
        redact_module.run_tool_loop = original
        redact_module.request_confirmation = original_confirm


@then("the text redact warnings include max rounds")
def step_text_redact_warnings_include_max_rounds(context) -> None:
    warnings = context.text_redact_result.warnings
    assert any("max rounds" in warning for warning in warnings)


@when("I attempt text redact with a tool loop error and done")
def step_attempt_text_redact_tool_loop_error_done(context) -> None:
    request = _build_redact_request(text="Account", prompt_template="Return the requested text.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Account", done=True, last_error="tool loop error", messages=[])

    from biblicus.text import redact as redact_module

    original = redact_module.run_tool_loop
    redact_module.run_tool_loop = fake_tool_loop
    try:
        apply_text_redact(request)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)
    finally:
        redact_module.run_tool_loop = original


@when("I attempt text redact with no spans and done")
def step_attempt_text_redact_no_spans(context) -> None:
    request = _build_redact_request(text="Account", prompt_template="Return the requested text.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Account", done=True, last_error=None, messages=[])

    from biblicus.text import redact as redact_module

    original = redact_module.run_tool_loop
    original_confirm = redact_module.request_confirmation
    redact_module.run_tool_loop = fake_tool_loop
    redact_module.request_confirmation = lambda **_kwargs: ToolLoopResult(
        text="Account", done=True, last_error=None, messages=[]
    )
    try:
        context.text_redact_result = apply_text_redact(request)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)
    finally:
        redact_module.run_tool_loop = original
        redact_module.request_confirmation = original_confirm


@then('the text redact warnings include "{text}"')
def step_text_redact_warnings_include(context, text: str) -> None:
    warnings = context.text_redact_result.warnings
    assert any(text in warning for warning in warnings)


@when("I attempt text redact with invalid spans after the tool loop")
def step_attempt_text_redact_invalid_spans_after_loop(context) -> None:
    request = _build_redact_request(
        text="Account",
        prompt_template="Return the requested text.",
        redaction_types=["pii"],
    )
    marked_up = '<span redact="bad">Account</span>'

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text=marked_up, done=True, last_error=None, messages=[])

    from biblicus.text import redact as redact_module

    original = redact_module.run_tool_loop
    redact_module.run_tool_loop = fake_tool_loop
    try:
        apply_text_redact(request)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)
    finally:
        redact_module.run_tool_loop = original


@when("I attempt text redact with invalid spans in confirmation")
def step_attempt_text_redact_invalid_spans_in_confirmation(context) -> None:
    request = _build_redact_request(
        text="Account",
        prompt_template="Return spans.",
        redaction_types=["pii"],
    )

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Account", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(
            text='<span redact="bad">Account</span>',
            done=True,
            last_error=None,
            messages=[],
        )

    from biblicus.text import redact as redact_module

    original = redact_module.run_tool_loop
    original_confirm = redact_module.request_confirmation
    redact_module.run_tool_loop = fake_tool_loop
    redact_module.request_confirmation = fake_confirmation
    try:
        apply_text_redact(request)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)
    finally:
        redact_module.run_tool_loop = original
        redact_module.request_confirmation = original_confirm


@when('I attempt redact replace with old_str "{old_str}" and new_str "{new_str}"')
def step_attempt_redact_replace(context, old_str: str, new_str: str) -> None:
    try:
        _apply_redact_replace("Account Account", old_str, new_str)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)


@when('I attempt redact replace in text "{text}" with old_str "{old_str}" and new_str "{new_str}"')
def step_attempt_redact_replace_in_text(context, text: str, old_str: str, new_str: str) -> None:
    try:
        _apply_redact_replace(text, old_str, new_str)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)


@when("I attempt to validate redact markup:")
def step_attempt_validate_redact_markup(context) -> None:
    markup = str(getattr(context, "text", "") or "")
    errors = _validate_redaction_markup(markup, None)
    if errors:
        context.text_redact_error = "; ".join(errors)
    else:
        context.text_redact_error = None


@when(
    'I attempt to validate redact preservation with original "{original}" and marked up "{marked_up}"'
)
def step_attempt_validate_redact_preservation(context, original: str, marked_up: str) -> None:
    try:
        _validate_preserved_text(original=original, marked_up=marked_up)
        context.text_redact_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_redact_error = str(exc)
