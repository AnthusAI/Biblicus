from __future__ import annotations

import re
from typing import Optional

from behave import given, then, when

from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text.link import (
    _apply_link_replace,
    _build_retry_message,
    _validate_link_markup,
    _validate_preserved_text,
    apply_text_link,
)
from biblicus.text.models import TextLinkRequest
from biblicus.text.tool_loop import ToolLoopResult


def _link_system_prompt_template() -> str:
    return (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word 'return' in the user's request as: wrap the returned text with "
        "<span ATTRIBUTE=\"VALUE\">...</span> in-place in the current text.\n"
        "Each span must include exactly one attribute: id for first mentions and ref for repeats.\n"
        "Id values must start with '{{ id_prefix }}'.\n\n"
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


def _build_link_request(
    *,
    text: str,
    prompt_template: str,
    id_prefix: Optional[str] = None,
    max_rounds: int = 6,
    max_edits_per_round: int = 10,
    api_key: Optional[str] = "test-openai-key",
    timeout_seconds: Optional[float] = None,
) -> TextLinkRequest:
    return TextLinkRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key=api_key,
            response_format="json_object",
            timeout_seconds=timeout_seconds,
        ),
        prompt_template=prompt_template,
        system_prompt=_link_system_prompt_template(),
        id_prefix=id_prefix or "link_",
        max_rounds=max_rounds,
        max_edits_per_round=max_edits_per_round,
    )


@when('I apply text link to text "{text}"')
def step_apply_text_link(context, text: str) -> None:
    request = _build_link_request(text=text, prompt_template="Return the requested text.")
    context.text_link_result = apply_text_link(request)


@when('I apply text link to text "{text}" with prompt template:')
def step_apply_text_link_with_prompt(context, text: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    request = _build_link_request(
        text=text,
        prompt_template=prompt_template,
        api_key=None,
        timeout_seconds=300.0,
    )
    context.text_link_result = apply_text_link(request)


@when('I attempt to apply text link to text "{text}"')
def step_attempt_text_link(context, text: str) -> None:
    request = _build_link_request(
        text=text,
        prompt_template="Return the requested text.",
        max_rounds=1,
        max_edits_per_round=5,
    )
    try:
        context.text_link_result = apply_text_link(request)
        context.text_link_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_link_error = str(exc)


@then('the text link has {count:d} spans')
def step_text_link_span_count(context, count: int) -> None:
    result = context.text_link_result
    assert len(result.spans) == count


@then('the text link has at least {count:d} spans')
def step_text_link_span_count_at_least(context, count: int) -> None:
    result = context.text_link_result
    assert len(result.spans) >= count


@then('the text link span {index:d} text equals "{expected}"')
def step_text_link_span_text(context, index: int, expected: str) -> None:
    result = context.text_link_result
    assert result.spans[index - 1].text == expected


@then('the text link span {index:d} has attribute "{name}" equals "{value}"')
def step_text_link_span_attribute(context, index: int, name: str, value: str) -> None:
    result = context.text_link_result
    assert result.spans[index - 1].attributes.get(name) == value


@then("the text link has an id span")
def step_text_link_has_id_span(context) -> None:
    result = context.text_link_result
    assert any("id" in span.attributes for span in result.spans)


@then("the text link has a ref span")
def step_text_link_has_ref_span(context) -> None:
    result = context.text_link_result
    assert any("ref" in span.attributes for span in result.spans)


@then("the text link does not split words")
def step_text_link_no_word_splits(context) -> None:
    result = context.text_link_result
    marked = result.marked_up_text
    assert re.search(r"\w<span\b", marked) is None
    assert re.search(r"\w</span>\w", marked) is None


@then('the text link error mentions "{text}"')
def step_text_link_error_mentions(context, text: str) -> None:
    error = context.text_link_error
    assert error is not None
    assert text in error


@given("the text link retry errors are:")
def step_set_text_link_retry_errors(context) -> None:
    raw = str(getattr(context, "text", "") or "")
    errors = [line.strip() for line in raw.splitlines() if line.strip()]
    context.text_link_retry_errors = errors


@when("I build a text link retry message for markup:")
def step_build_text_link_retry_message(context) -> None:
    errors = getattr(context, "text_link_retry_errors", []) or []
    current_text = str(getattr(context, "text", "") or "")
    context.text_link_retry_message = _build_retry_message(errors, current_text, "link_")


@then('the text link retry message includes "{text}"')
def step_text_link_retry_message_includes(context, text: str) -> None:
    message = context.text_link_retry_message
    assert text in message


@then("the text link retry message includes span context")
def step_text_link_retry_message_has_context(context) -> None:
    message = context.text_link_retry_message
    assert "Relevant spans" in message


@when("I apply text link with a non-done tool loop result")
def step_apply_text_link_with_incomplete_tool_loop(context) -> None:
    request = _build_link_request(text="Acme", prompt_template="Return the requested text.")
    replacement = "<span id=\"link_1\">Acme</span>"

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text=replacement, done=False, last_error=None)

    from biblicus.text import link as link_module

    original = link_module.run_tool_loop
    link_module.run_tool_loop = fake_tool_loop
    try:
        context.text_link_result = apply_text_link(request)
    finally:
        link_module.run_tool_loop = original


@then("the text link warnings include max rounds")
def step_text_link_warnings_include_max_rounds(context) -> None:
    warnings = context.text_link_result.warnings
    assert any("max rounds" in warning for warning in warnings)


@when("I attempt text link with a tool loop error and done")
def step_attempt_text_link_tool_loop_error_done(context) -> None:
    request = _build_link_request(text="Acme", prompt_template="Return the requested text.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Acme", done=True, last_error="tool loop error")

    from biblicus.text import link as link_module

    original = link_module.run_tool_loop
    link_module.run_tool_loop = fake_tool_loop
    try:
        apply_text_link(request)
        context.text_link_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_link_error = str(exc)
    finally:
        link_module.run_tool_loop = original


@when("I attempt text link with no spans and done")
def step_attempt_text_link_no_spans(context) -> None:
    request = _build_link_request(text="Acme", prompt_template="Return the requested text.")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Acme", done=True, last_error=None)

    from biblicus.text import link as link_module

    original = link_module.run_tool_loop
    link_module.run_tool_loop = fake_tool_loop
    try:
        apply_text_link(request)
        context.text_link_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_link_error = str(exc)
    finally:
        link_module.run_tool_loop = original


@when("I attempt text link with invalid spans after the tool loop")
def step_attempt_text_link_invalid_spans_after_loop(context) -> None:
    request = _build_link_request(text="Acme", prompt_template="Return the requested text.")
    marked_up = "<span label=\"x\">Acme</span>"

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text=marked_up, done=True, last_error=None)

    from biblicus.text import link as link_module

    original = link_module.run_tool_loop
    link_module.run_tool_loop = fake_tool_loop
    try:
        apply_text_link(request)
        context.text_link_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_link_error = str(exc)
    finally:
        link_module.run_tool_loop = original


@when('I attempt link replace with old_str "{old_str}" and new_str "{new_str}"')
def step_attempt_link_replace(context, old_str: str, new_str: str) -> None:
    try:
        _apply_link_replace("Acme Acme", old_str, new_str)
        context.text_link_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_link_error = str(exc)

@when(
    'I attempt link replace in text "{text}" with old_str "{old_str}" and new_str "{new_str}"'
)
def step_attempt_link_replace_in_text(
    context, text: str, old_str: str, new_str: str
) -> None:
    try:
        _apply_link_replace(text, old_str, new_str)
        context.text_link_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_link_error = str(exc)


@when("I attempt to validate link markup:")
def step_attempt_validate_link_markup(context) -> None:
    markup = str(getattr(context, "text", "") or "")
    errors = _validate_link_markup(markup, "link_")
    if errors:
        context.text_link_error = "; ".join(errors)
    else:
        context.text_link_error = None


@when(
    'I attempt to validate link preservation with original "{original}" and marked up "{marked_up}"'
)
def step_attempt_validate_link_preservation(context, original: str, marked_up: str) -> None:
    try:
        _validate_preserved_text(original=original, marked_up=marked_up)
        context.text_link_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_link_error = str(exc)
