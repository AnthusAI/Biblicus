from __future__ import annotations

from behave import then, when

from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text.extract import TextExtractRequest, _validate_preserved_text, apply_text_extract


@when('I apply text extract to text "{text}"')
def step_apply_text_extract(context, text: str) -> None:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: wrap the returned text with "
        "<span>...</span> in-place in the current text.\n\n"
        "Use the str_replace tool to insert <span>...</span> tags and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <span> and </span> inserted.\n"
        "- Do not include <span> or </span> inside old_str or new_str.\n"
        "- Do not insert nested spans.\n"
        "- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextExtractRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested text.",
        system_prompt=system_prompt,
        max_rounds=6,
        max_edits_per_round=10,
    )
    context.text_extract_result = apply_text_extract(request)


@when("I apply text extract to text:")
def step_apply_text_extract_multiline(context) -> None:
    text = str(getattr(context, "text", "") or "").strip("\n")
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: wrap the returned text with "
        "<span>...</span> in-place in the current text.\n\n"
        "Use the str_replace tool to insert <span>...</span> tags and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <span> and </span> inserted.\n"
        "- Do not include <span> or </span> inside old_str or new_str.\n"
        "- Do not insert nested spans.\n"
        "- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextExtractRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested text.",
        system_prompt=system_prompt,
        max_rounds=10,
        max_edits_per_round=10,
    )
    context.text_extract_result = apply_text_extract(request)


@when('I apply text extract to text "{text}" with prompt template:')
def step_apply_text_extract_with_prompt(context, text: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: wrap the returned text with "
        "<span>...</span> in-place in the current text.\n\n"
        "Use the str_replace tool to insert <span>...</span> tags and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <span> and </span> inserted.\n"
        "- Do not include <span> or </span> inside old_str or new_str.\n"
        "- Do not insert nested spans.\n"
        "- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextExtractRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key=None,
            response_format="json_object",
            timeout_seconds=300.0,
        ),
        prompt_template=prompt_template,
        system_prompt=system_prompt,
        max_rounds=10,
        max_edits_per_round=200,
    )
    context.text_extract_result = apply_text_extract(request)


@when('I attempt to apply text extract to text "{text}"')
def step_attempt_apply_text_extract(context, text: str) -> None:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: wrap the returned text with "
        "<span>...</span> in-place in the current text.\n\n"
        "Use the str_replace tool to insert <span>...</span> tags and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <span> and </span> inserted.\n"
        "- Do not include <span> or </span> inside old_str or new_str.\n"
        "- Do not insert nested spans.\n"
        "- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextExtractRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested text.",
        system_prompt=system_prompt,
        max_rounds=10,
        max_edits_per_round=10,
    )
    try:
        context.text_extract_result = apply_text_extract(request)
        context.text_extract_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_extract_error = str(exc)


@when('I attempt to apply text extract using provider "{provider}" on text "{text}"')
def step_attempt_apply_text_extract_with_provider(context, provider: str, text: str) -> None:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: wrap the returned text with "
        "<span>...</span> in-place in the current text.\n\n"
        "Use the str_replace tool to insert <span>...</span> tags and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <span> and </span> inserted.\n"
        "- Do not include <span> or </span> inside old_str or new_str.\n"
        "- Do not insert nested spans.\n"
        "- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextExtractRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider(provider),
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested text.",
        system_prompt=system_prompt,
        max_rounds=10,
        max_edits_per_round=10,
    )
    try:
        context.text_extract_result = apply_text_extract(request)
        context.text_extract_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_extract_error = str(exc)


@when(
    "I attempt to apply text extract to text \"{text}\" with max rounds {max_rounds:d} "
    "and max edits per round {max_edits:d}"
)
def step_attempt_text_extract_with_limits(
    context, text: str, max_rounds: int, max_edits: int
) -> None:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: wrap the returned text with "
        "<span>...</span> in-place in the current text.\n\n"
        "Use the str_replace tool to insert <span>...</span> tags and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <span> and </span> inserted.\n"
        "- Do not include <span> or </span> inside old_str or new_str.\n"
        "- Do not insert nested spans.\n"
        "- If a tool call fails due to non-unique old_str, retry with a longer unique old_str.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until spans are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextExtractRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested text.",
        system_prompt=system_prompt,
        max_rounds=max_rounds,
        max_edits_per_round=max_edits,
    )
    try:
        context.text_extract_result = apply_text_extract(request)
        context.text_extract_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_extract_error = str(exc)


@when('I attempt to validate a text extract request with system prompt "{system_prompt}"')
def step_validate_text_extract_system_prompt(context, system_prompt: str) -> None:
    try:
        _ = TextExtractRequest(
            text="Hello",
            client=LlmClientConfig(
                provider=AiProvider.OPENAI,
                model="gpt-4o-mini",
                api_key="test-openai-key",
            ),
            prompt_template="Return the requested text.",
            system_prompt=system_prompt,
            max_rounds=1,
            max_edits_per_round=1,
        )
        context.text_extract_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_extract_error = str(exc)


@when('I attempt to validate a text extract request with prompt template "{prompt_template}"')
def step_validate_text_extract_prompt_template(context, prompt_template: str) -> None:
    try:
        _ = TextExtractRequest(
            text="Hello",
            client=LlmClientConfig(
                provider=AiProvider.OPENAI,
                model="gpt-4o-mini",
                api_key="test-openai-key",
            ),
            prompt_template=prompt_template,
            system_prompt="System {text}",
            max_rounds=1,
            max_edits_per_round=1,
        )
        context.text_extract_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_extract_error = str(exc)


@when(
    'I attempt to validate preserved text "{original}" with marked-up text "{marked_up}"'
)
def step_validate_text_extract_preserved_text(context, original: str, marked_up: str) -> None:
    try:
        _validate_preserved_text(original=original, marked_up=marked_up)
        context.text_extract_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_extract_error = str(exc)


@then('the text extract has {count:d} span')
def step_text_extract_span_count(context, count: int) -> None:
    result = context.text_extract_result
    assert len(result.spans) == count


@then('the text extract has at least {count:d} spans')
def step_text_extract_at_least_count(context, count: int) -> None:
    result = context.text_extract_result
    assert len(result.spans) >= count


@then('the first span text equals "{expected}"')
def step_text_extract_first_span_text(context, expected: str) -> None:
    result = context.text_extract_result
    assert result.spans[0].text == expected


@then('the text extract span {index:d} text equals "{expected}"')
def step_text_extract_span_text_at_index(context, index: int, expected: str) -> None:
    result = context.text_extract_result
    assert result.spans[index - 1].text == expected


@then('the text extract marked-up text equals "{expected}"')
def step_text_extract_marked_up_text_equals(context, expected: str) -> None:
    result = context.text_extract_result
    assert result.marked_up_text == expected


@then("the text extract has at least one span")
def step_text_extract_at_least_one_span(context) -> None:
    result = context.text_extract_result
    assert len(result.spans) >= 1


@then('the text extract has a span containing "{text}"')
def step_text_extract_has_span_containing(context, text: str) -> None:
    result = context.text_extract_result
    assert any(text in span.text for span in result.spans)


@then("the text extract does not split words")
def step_text_extract_no_word_splits(context) -> None:
    import re

    result = context.text_extract_result
    marked = result.marked_up_text
    assert re.search(r"\\w<span>\\w", marked) is None
    assert re.search(r"\\w</span>\\w", marked) is None


@then('the text extract warnings include "{text}"')
def step_text_extract_warnings_include(context, text: str) -> None:
    result = context.text_extract_result
    warnings = result.warnings
    assert any(text in warning for warning in warnings)


@then('the text extract error mentions "{text}"')
def step_text_extract_error_mentions(context, text: str) -> None:
    error = context.text_extract_error
    assert error is not None
    assert text in error
