from __future__ import annotations

from behave import then, when

import biblicus.text.slice as slice_module
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text.slice import TextSliceRequest, _validate_preserved_text, apply_text_slice
from biblicus.text.tool_loop import ToolLoopResult
from features.steps import openai_steps


def _build_slice_request(text: str) -> TextSliceRequest:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: insert <slice/> markers "
        "at the boundaries of the returned slices in the current text.\n\n"
        "Use the str_replace tool to insert <slice/> markers and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <slice/> inserted.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until slices are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    return TextSliceRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested slices.",
        system_prompt=system_prompt,
        max_rounds=2,
        max_edits_per_round=2,
    )


@when('I apply text slice to text "{text}"')
def step_apply_text_slice(context, text: str) -> None:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: insert <slice/> markers "
        "at the boundaries of the returned slices in the current text.\n\n"
        "Use the str_replace tool to insert <slice/> markers and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <slice/> inserted.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until slices are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextSliceRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested slices.",
        system_prompt=system_prompt,
        max_rounds=6,
        max_edits_per_round=10,
    )
    context.text_slice_result = apply_text_slice(request)


@when("I apply text slice to text:")
def step_apply_text_slice_multiline(context) -> None:
    text = str(getattr(context, "text", "") or "").strip("\n")
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: insert <slice/> markers "
        "at the boundaries of the returned slices in the current text.\n\n"
        "Use the str_replace tool to insert <slice/> markers and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <slice/> inserted.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until slices are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextSliceRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested slices.",
        system_prompt=system_prompt,
        max_rounds=10,
        max_edits_per_round=10,
    )
    context.text_slice_result = apply_text_slice(request)


@when('I apply text slice to text "{text}" with prompt template:')
def step_apply_text_slice_with_prompt(context, text: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: insert <slice/> markers "
        "at the boundaries of the returned slices in the current text.\n\n"
        "Use the str_replace tool to insert <slice/> markers and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <slice/> inserted.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until slices are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextSliceRequest(
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
    context.text_slice_result = apply_text_slice(request)


@when('I apply text slice to text "{text}" with prompt template and default system prompt:')
def step_apply_text_slice_with_prompt_default_system(context, text: str) -> None:
    prompt_template = str(getattr(context, "text", "") or "")
    request = TextSliceRequest(
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
    context.text_slice_result = apply_text_slice(request)


@when('I attempt to apply text slice to text "{text}"')
def step_attempt_apply_text_slice(context, text: str) -> None:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: insert <slice/> markers "
        "at the boundaries of the returned slices in the current text.\n\n"
        "Use the str_replace tool to insert <slice/> markers and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <slice/> inserted.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until slices are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextSliceRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested slices.",
        system_prompt=system_prompt,
        max_rounds=10,
        max_edits_per_round=10,
    )
    try:
        context.text_slice_result = apply_text_slice(request)
        context.text_slice_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_slice_error = str(exc)


@when(
    "I attempt to apply text slice to text \"{text}\" with max rounds {max_rounds:d} "
    "and max edits per round {max_edits:d}"
)
def step_attempt_text_slice_with_limits(
    context, text: str, max_rounds: int, max_edits: int
) -> None:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: insert <slice/> markers "
        "at the boundaries of the returned slices in the current text.\n\n"
        "Use the str_replace tool to insert <slice/> markers and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <slice/> inserted.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until slices are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextSliceRequest(
        text=text,
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested slices.",
        system_prompt=system_prompt,
        max_rounds=max_rounds,
        max_edits_per_round=max_edits,
    )
    try:
        context.text_slice_result = apply_text_slice(request)
        context.text_slice_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_slice_error = str(exc)


@when('I attempt to validate a text slice request with system prompt "{system_prompt}"')
def step_validate_text_slice_system_prompt(context, system_prompt: str) -> None:
    try:
        _ = TextSliceRequest(
            text="Hello",
            client=LlmClientConfig(
                provider=AiProvider.OPENAI,
                model="gpt-4o-mini",
                api_key="test-openai-key",
            ),
            prompt_template="Return the requested slices.",
            system_prompt=system_prompt,
            max_rounds=1,
            max_edits_per_round=1,
        )
        context.text_slice_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_slice_error = str(exc)


@when('I attempt to validate a text slice request with prompt template "{prompt_template}"')
def step_validate_text_slice_prompt_template(context, prompt_template: str) -> None:
    try:
        _ = TextSliceRequest(
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
        context.text_slice_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_slice_error = str(exc)


@when('I attempt to validate slice preserved text "{original}" with marked-up text "{marked_up}"')
def step_validate_text_slice_preserved_text(context, original: str, marked_up: str) -> None:
    try:
        _validate_preserved_text(original=original, marked_up=marked_up)
        context.text_slice_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_slice_error = str(exc)


@when("I attempt to apply text slice with forced empty slices")
def step_attempt_text_slice_forced_empty(context) -> None:
    system_prompt = (
        "You are a virtual file editor. Use the available tools to edit the text.\n"
        "Interpret the word “return” in the user’s request as: insert <slice/> markers "
        "at the boundaries of the returned slices in the current text.\n\n"
        "Use the str_replace tool to insert <slice/> markers and the done tool when finished.\n"
        "When finished, call done. Do NOT return JSON in the assistant message.\n\n"
        "Rules:\n"
        "- Use str_replace only.\n"
        "- old_str must match exactly once in the current text.\n"
        "- old_str and new_str must be non-empty strings.\n"
        "- new_str must be identical to old_str with only <slice/> inserted.\n"
        "- If a tool call fails, read the error and keep editing. Do not call done until slices are inserted.\n"
        "- Do not delete, reorder, paraphrase, or label text.\n\n"
        "Current text:\n---\n{text}\n---\n"
    )
    request = TextSliceRequest(
        text="Hello",
        client=LlmClientConfig(
            provider=AiProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="test-openai-key",
            response_format="json_object",
        ),
        prompt_template="Return the requested slices.",
        system_prompt=system_prompt,
        max_rounds=1,
        max_edits_per_round=1,
    )
    openai_steps._install_fake_openai_module(context)
    behaviors = openai_steps._ensure_fake_openai_chat_behaviors(context)
    behaviors.append(
        openai_steps._FakeOpenAiChatBehavior(
            response='{"operations":[{"command":"str_replace","old_str":"Hello","new_str":"Hello<slice/>"}],"done":true}',
            match_text="Current text",
        )
    )
    original_extract = slice_module._extract_slices
    try:
        def _empty_slices(*, marked_up_text: str) -> list:
            _ = marked_up_text
            return []

        slice_module._extract_slices = _empty_slices
        context.text_slice_result = apply_text_slice(request)
        context.text_slice_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_slice_error = str(exc)
    finally:
        slice_module._extract_slices = original_extract


@then('the text slice has {count:d} slices')
def step_text_slice_count(context, count: int) -> None:
    result = context.text_slice_result
    assert len(result.slices) == count


@then('the text slice has at least {count:d} slices')
def step_text_slice_at_least_count(context, count: int) -> None:
    result = context.text_slice_result
    assert len(result.slices) >= count


@then('the text slice slice {index:d} text equals "{expected}"')
def step_text_slice_text_at_index(context, index: int, expected: str) -> None:
    result = context.text_slice_result
    assert result.slices[index - 1].text == expected


@then('the text slice error mentions "{text}"')
def step_text_slice_error_mentions(context, text: str) -> None:
    error = context.text_slice_error
    assert error is not None
    assert text in error


@then('the text slice warnings include "{text}"')
def step_text_slice_warnings_include(context, text: str) -> None:
    warnings = context.text_slice_result.warnings
    assert any(text in warning for warning in warnings)


@when("I attempt to apply text slice where confirmation fails with a last error")
def step_attempt_text_slice_confirmation_last_error(context) -> None:
    request = _build_slice_request("Hello")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=False, last_error="confirmation error", messages=[])

    original = slice_module.run_tool_loop
    original_confirm = slice_module.request_confirmation
    slice_module.run_tool_loop = fake_tool_loop
    slice_module.request_confirmation = fake_confirmation
    try:
        apply_text_slice(request)
        context.text_slice_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_slice_error = str(exc)
    finally:
        slice_module.run_tool_loop = original
        slice_module.request_confirmation = original_confirm


@when("I attempt to apply text slice where confirmation inserts a marker but no slices are returned")
def step_attempt_text_slice_confirmation_produces_no_slices(context) -> None:
    request = _build_slice_request("Hello")

    def fake_tool_loop(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello", done=True, last_error=None, messages=[])

    def fake_confirmation(**_kwargs: object) -> ToolLoopResult:
        return ToolLoopResult(text="Hello<slice/>", done=True, last_error=None, messages=[])

    def fake_extract_slices(*, marked_up_text: str) -> list:
        _ = marked_up_text
        return []

    original = slice_module.run_tool_loop
    original_confirm = slice_module.request_confirmation
    original_extract = slice_module._extract_slices
    slice_module.run_tool_loop = fake_tool_loop
    slice_module.request_confirmation = fake_confirmation
    slice_module._extract_slices = fake_extract_slices
    try:
        apply_text_slice(request)
        context.text_slice_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_slice_error = str(exc)
    finally:
        slice_module.run_tool_loop = original
        slice_module.request_confirmation = original_confirm
        slice_module._extract_slices = original_extract
