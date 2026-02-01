from __future__ import annotations

import re
from typing import List, Optional

from behave import given, then, when

from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text.annotate import (
    _apply_annotate_replace,
    _build_retry_message,
    _validate_preserved_text,
    apply_text_annotate,
)
from biblicus.text.markup import _parse_span_attributes, build_span_context_section
from biblicus.text.models import TextAnnotateRequest
from biblicus.text.tool_loop import ToolLoopResult


def _annotate_system_prompt_template() -> str:
    return (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word 'return' in the user's request as: wrap the returned text with "
        '<span ATTRIBUTE="VALUE">...</span> in-place in the current text.\n'
        "Each span must include exactly one attribute. Allowed attributes: "
        "{{ allowed_attributes | join(', ') }}.\n\n"
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
        "- Do not delete, reorder, paraphrase, or label text outside the span attributes.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )


def _parse_allowed_attributes(raw: str) -> Optional[List[str]]:
    cleaned = [token.strip() for token in raw.split(",") if token.strip()]
    if not cleaned:
        return None
    return cleaned


def _build_annotate_request(
    *,
    text: str,
    prompt_template: str,
    allowed_attributes: Optional[List[str]] = None,
    max_rounds: int = 6,
    max_edits_per_round: int = 10,
    api_key: Optional[str] = "test-openai-key",
    timeout_seconds: Optional[float] = None,
) -> TextAnnotateRequest:
    return TextAnnotateRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key=api_key,
            response_format="json_object",
            timeout_seconds=timeout_seconds,
        ),
        prompt_template=prompt_template,
        system_prompt=_annotate_system_prompt_template(),
        allowed_attributes=allowed_attributes,
        max_rounds=max_rounds,
        max_edits_per_round=max_edits_per_round,
    )


@when('I apply text annotate to text "{text}"')
def step_apply_text_annotate(context, text: str) -> None:
    request = _build_annotate_request(text=text, prompt_template="Return the requested text.")
    context.text_annotate_result = apply_text_annotate(request)


@when('I apply text annotate to text "{text}" with prompt template:')
def step_apply_text_annotate_with_prompt(context, text: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    request = _build_annotate_request(
        text=text,
        prompt_template=prompt_template,
        api_key=None,
        timeout_seconds=300.0,
    )
    context.text_annotate_result = apply_text_annotate(request)


@when('I apply text annotate to text "{text}" with prompt template and default system prompt:')
def step_apply_text_annotate_with_prompt_default_system(context, text: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    request = TextAnnotateRequest(
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
    context.text_annotate_result = apply_text_annotate(request)


@when(
    'I apply text annotate to text "{text}" with allowed attributes "{allowed}" '
    "and prompt template:"
)
def step_apply_text_annotate_with_allowed_attributes(context, text: str, allowed: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    allowed_attributes = _parse_allowed_attributes(allowed)
    extra_env = getattr(context, "extra_env", {}) or {}
    api_key = None if extra_env.get("OPENAI_API_KEY") else "test-openai-key"
    timeout_seconds = 300.0 if api_key is None else None
    request = _build_annotate_request(
        text=text,
        prompt_template=prompt_template,
        allowed_attributes=allowed_attributes,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    context.text_annotate_result = apply_text_annotate(request)


@when('I attempt to apply text annotate to text "{text}"')
def step_attempt_text_annotate(context, text: str) -> None:
    request = _build_annotate_request(
        text=text,
        prompt_template="Return the requested text.",
        max_rounds=1,
        max_edits_per_round=5,
    )
    try:
        context.text_annotate_result = apply_text_annotate(request)
        context.text_annotate_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_annotate_error = str(exc)


@then("the text annotate has {count:d} spans")
def step_text_annotate_span_count(context, count: int) -> None:
    result = context.text_annotate_result
    assert len(result.spans) == count


@then("the text annotate has at least {count:d} spans")
def step_text_annotate_minimum_spans(context, count: int) -> None:
    result = context.text_annotate_result
    assert len(result.spans) >= count


@then('the text annotate span {index:d} text equals "{expected}"')
def step_text_annotate_span_text(context, index: int, expected: str) -> None:
    result = context.text_annotate_result
    assert result.spans[index - 1].text == expected


@then('the text annotate span {index:d} attribute "{name}" equals "{value}"')
def step_text_annotate_span_attribute(context, index: int, name: str, value: str) -> None:
    result = context.text_annotate_result
    assert result.spans[index - 1].attributes.get(name) == value


@then('the text annotate uses only allowed attributes "{allowed}"')
def step_text_annotate_allowed_attributes(context, allowed: str) -> None:
    allowed_set = set(_parse_allowed_attributes(allowed) or [])
    result = context.text_annotate_result
    for span in result.spans:
        assert len(span.attributes) == 1
        name = next(iter(span.attributes.keys()))
        assert name in allowed_set


@then("the text annotate does not split words")
def step_text_annotate_no_word_splits(context) -> None:
    result = context.text_annotate_result
    marked = result.marked_up_text
    assert re.search(r"\w<span\b", marked) is None
    assert re.search(r"\w</span>\w", marked) is None


@then('the text annotate error mentions "{text}"')
def step_text_annotate_error_mentions(context, text: str) -> None:
    error = context.text_annotate_error
    assert error is not None
    assert text in error


@when("I attempt to parse a span tag:")
def step_attempt_parse_span_tag(context) -> None:
    tag_text = str(getattr(context, "text", "") or "").strip()
    try:
        _parse_span_attributes(tag_text)
        context.span_parse_error = None
    except Exception as exc:  # noqa: BLE001
        context.span_parse_error = str(exc)


@then('the span parse error mentions "{text}"')
def step_span_parse_error_mentions(context, text: str) -> None:
    error = context.span_parse_error
    assert error is not None
    assert text in error


@given("the text annotate retry errors are:")
def step_set_text_annotate_retry_errors(context) -> None:
    raw = str(getattr(context, "text", "") or "")
    errors = [line.strip() for line in raw.splitlines() if line.strip()]
    context.text_annotate_retry_errors = errors


@when("I build a text annotate retry message for markup:")
def step_build_text_annotate_retry_message(context) -> None:
    errors = getattr(context, "text_annotate_retry_errors", []) or []
    current_text = str(getattr(context, "text", "") or "")
    context.text_annotate_retry_message = _build_retry_message(errors, current_text, ["label"])


@then('the text annotate retry message includes "{text}"')
def step_text_annotate_retry_message_includes(context, text: str) -> None:
    message = context.text_annotate_retry_message
    assert text in message


@then("the text annotate retry message includes span context")
def step_text_annotate_retry_message_has_context(context) -> None:
    message = context.text_annotate_retry_message
    assert "Relevant spans" in message


@when("I apply text annotate with a non-done tool loop result")
def step_apply_text_annotate_with_incomplete_tool_loop(context) -> None:
    request = _build_annotate_request(text="Hello", prompt_template="Return the requested text.")
    replacement = '<span label="greeting">Hello</span>'

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text=replacement, done=False, last_error=None, messages=[])

    from biblicus.text import annotate as annotate_module

    original = annotate_module.run_tool_loop
    annotate_module.run_tool_loop = fake_tool_loop
    try:
        context.text_annotate_result = apply_text_annotate(request)
    finally:
        annotate_module.run_tool_loop = original


@when("I apply text annotate with no edits and confirmation reaches max rounds without done")
def step_apply_text_annotate_confirmation_max_rounds_without_done(context) -> None:
    request = _build_annotate_request(text="Hello", prompt_template="Return spans.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=False, last_error=None, messages=[])

    from biblicus.text import annotate as annotate_module

    original = annotate_module.run_tool_loop
    original_confirm = annotate_module.request_confirmation
    annotate_module.run_tool_loop = fake_tool_loop
    annotate_module.request_confirmation = fake_confirmation
    try:
        context.text_annotate_result = apply_text_annotate(request)
        context.text_annotate_error = None
    finally:
        annotate_module.run_tool_loop = original
        annotate_module.request_confirmation = original_confirm


@when("I apply text annotate with no edits and confirmation inserts spans")
def step_apply_text_annotate_confirmation_inserts_spans(context) -> None:
    request = _build_annotate_request(text="Hello", prompt_template="Return spans.")
    marked_up = '<span label="greeting">Hello</span>'

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text=marked_up, done=True, last_error=None, messages=[])

    from biblicus.text import annotate as annotate_module

    original = annotate_module.run_tool_loop
    original_confirm = annotate_module.request_confirmation
    annotate_module.run_tool_loop = fake_tool_loop
    annotate_module.request_confirmation = fake_confirmation
    try:
        context.text_annotate_result = apply_text_annotate(request)
        context.text_annotate_error = None
    finally:
        annotate_module.run_tool_loop = original
        annotate_module.request_confirmation = original_confirm


@then("the text annotate warnings include max rounds")
def step_text_annotate_warnings_include_max_rounds(context) -> None:
    warnings = context.text_annotate_result.warnings
    assert any("max rounds" in warning for warning in warnings)


@when("I attempt text annotate with a tool loop error and done")
def step_attempt_text_annotate_tool_loop_error_done(context) -> None:
    request = _build_annotate_request(text="Hello", prompt_template="Return the requested text.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=True, last_error="tool loop error", messages=[])

    from biblicus.text import annotate as annotate_module

    original = annotate_module.run_tool_loop
    annotate_module.run_tool_loop = fake_tool_loop
    try:
        apply_text_annotate(request)
        context.text_annotate_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_annotate_error = str(exc)
    finally:
        annotate_module.run_tool_loop = original


@when("I attempt text annotate with no spans and done")
def step_attempt_text_annotate_no_spans(context) -> None:
    request = _build_annotate_request(text="Hello", prompt_template="Return the requested text.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=True, last_error=None, messages=[])

    from biblicus.text import annotate as annotate_module

    original = annotate_module.run_tool_loop
    original_confirm = annotate_module.request_confirmation
    annotate_module.run_tool_loop = fake_tool_loop
    annotate_module.request_confirmation = lambda **_kwargs: ToolLoopResult(
        text="Hello", done=True, last_error=None, messages=[]
    )
    try:
        context.text_annotate_result = apply_text_annotate(request)
        context.text_annotate_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_annotate_error = str(exc)
    finally:
        annotate_module.run_tool_loop = original
        annotate_module.request_confirmation = original_confirm


@when("I attempt text annotate where confirmation fails with a last error")
def step_attempt_text_annotate_confirmation_last_error(context) -> None:
    request = _build_annotate_request(text="Hello", prompt_template="Return spans.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(
            text="Hello",
            done=False,
            last_error="confirmation error",
            messages=[],
        )

    from biblicus.text import annotate as annotate_module

    original = annotate_module.run_tool_loop
    original_confirm = annotate_module.request_confirmation
    annotate_module.run_tool_loop = fake_tool_loop
    annotate_module.request_confirmation = fake_confirmation
    try:
        apply_text_annotate(request)
        context.text_annotate_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_annotate_error = str(exc)
    finally:
        annotate_module.run_tool_loop = original
        annotate_module.request_confirmation = original_confirm


@then('the text annotate warnings include "{text}"')
def step_text_annotate_warnings_include(context, text: str) -> None:
    warnings = context.text_annotate_result.warnings
    assert any(text in warning for warning in warnings)


@when("I attempt text annotate with invalid spans after the tool loop")
def step_attempt_text_annotate_invalid_spans_after_loop(context) -> None:
    request = _build_annotate_request(text="Hello", prompt_template="Return the requested text.")
    marked_up = '<span wrong="x">Hello</span>'

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text=marked_up, done=True, last_error=None, messages=[])

    from biblicus.text import annotate as annotate_module

    original = annotate_module.run_tool_loop
    annotate_module.run_tool_loop = fake_tool_loop
    try:
        apply_text_annotate(request)
        context.text_annotate_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_annotate_error = str(exc)
    finally:
        annotate_module.run_tool_loop = original


@when("I attempt text annotate with invalid spans in confirmation")
def step_attempt_text_annotate_invalid_spans_in_confirmation(context) -> None:
    request = _build_annotate_request(text="Hello", prompt_template="Return spans.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(
            text='<span wrong="x">Hello</span>',
            done=True,
            last_error=None,
            messages=[],
        )

    from biblicus.text import annotate as annotate_module

    original = annotate_module.run_tool_loop
    original_confirm = annotate_module.request_confirmation
    annotate_module.run_tool_loop = fake_tool_loop
    annotate_module.request_confirmation = fake_confirmation
    try:
        apply_text_annotate(request)
        context.text_annotate_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_annotate_error = str(exc)
    finally:
        annotate_module.run_tool_loop = original
        annotate_module.request_confirmation = original_confirm


@when('I attempt annotate replace with old_str "{old_str}" and new_str "{new_str}"')
def step_attempt_annotate_replace(context, old_str: str, new_str: str) -> None:
    try:
        _apply_annotate_replace("Hello Hello", old_str, new_str)
        context.text_annotate_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_annotate_error = str(exc)


@when(
    'I attempt to validate annotate preservation with original "{original}" and marked up "{marked_up}"'
)
def step_attempt_validate_annotate_preservation(context, original: str, marked_up: str) -> None:
    try:
        _validate_preserved_text(original=original, marked_up=marked_up)
        context.text_annotate_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_annotate_error = str(exc)


@when("I build a span context section for markup:")
def step_build_span_context_section(context) -> None:
    errors = getattr(context, "text_annotate_retry_errors", []) or []
    marked_up = str(getattr(context, "text", "") or "")
    context.span_context_section = build_span_context_section(marked_up, errors)


@then("the span context section is empty")
def step_span_context_section_empty(context) -> None:
    assert context.span_context_section == ""
