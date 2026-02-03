from __future__ import annotations

import json

from behave import then, when

from biblicus.ai.llm import ChatCompletionResult
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import tool_loop


@when("I build a tool loop retry message with a custom builder")
def step_build_tool_loop_retry_message(context) -> None:
    def builder(errors: list[str], current_text: str) -> str:
        return f"Custom: {len(errors)} errors in {current_text}"

    context.tool_loop_retry_message = tool_loop._build_retry_message(
        validation_errors=["one"],
        current_text="Text",
        build_retry_message=builder,
    )


@then('the tool loop retry message equals "{expected}"')
def step_tool_loop_retry_message_equals(context, expected: str) -> None:
    assert context.tool_loop_retry_message == expected


@when("I build a tool loop retry message with default builder")
def step_build_tool_loop_retry_message_default(context) -> None:
    context.tool_loop_retry_message = tool_loop._build_retry_message(
        validation_errors=["Missing span"],
        current_text="Sample",
        build_retry_message=None,
    )


@then('the tool loop retry message includes "{text}"')
def step_tool_loop_retry_message_includes(context, text: str) -> None:
    assert text in context.tool_loop_retry_message


@when("I run a tool loop with a no-op str_replace")
def step_run_tool_loop_no_op(context) -> None:
    class FakeCompletion:
        def __call__(self, **_kwargs: object) -> ChatCompletionResult:
            tool_calls = [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "str_replace",
                        "arguments": json.dumps({"old_str": "Hello", "new_str": "Hello"}),
                    },
                },
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {"name": "done", "arguments": "{}"},
                },
            ]
            return ChatCompletionResult(text="", tool_calls=tool_calls)

    original = tool_loop.chat_completion
    tool_loop.chat_completion = FakeCompletion()
    try:
        context.tool_loop_result = tool_loop.run_tool_loop(
            text="Hello world",
            client=LlmClientConfig(
                provider=AiProvider.OPENAI,
                model="gpt-4o-mini",
                api_key="test-openai-key",
                response_format="json_object",
            ),
            system_prompt="You are a virtual file editor.\nCurrent text:\n---\n{text}\n---",
            prompt_template="Return the requested text.",
            max_rounds=1,
            max_edits_per_round=5,
            apply_str_replace=lambda current, old, new: current.replace(old, new, 1),
        )
    finally:
        tool_loop.chat_completion = original


@then('the tool loop error mentions "{text}"')
def step_tool_loop_error_mentions(context, text: str) -> None:
    assert text in (context.tool_loop_result.last_error or "")


@then('the tool loop error message includes "{text}"')
def step_tool_loop_error_message_includes(context, text: str) -> None:
    messages = context.tool_loop_result.messages
    assert messages
    assert text in messages[-1]["content"]


@when('I build a tool loop error message for "{error_message}" with old_str "{old_str}"')
def step_build_tool_loop_error_message(context, error_message: str, old_str: str) -> None:
    context.tool_loop_error_message = tool_loop._build_tool_error_message(
        error_message=error_message,
        current_text="hi hi",
        old_str=old_str,
    )


@then('the built tool loop error message includes "{text}"')
def step_tool_loop_error_message_contains(context, text: str) -> None:
    assert text in context.tool_loop_error_message


@when('I strip markup from "{text}"')
def step_strip_markup(context, text: str) -> None:
    context.stripped_text = tool_loop._strip_markup(text)


@then('the stripped text equals "{expected}"')
def step_stripped_text_equals(context, expected: str) -> None:
    assert context.stripped_text == expected


@when('I apply a unique str_replace to "{text}" replacing "{old_str}" with "{new_str}"')
def step_apply_unique_str_replace(context, text: str, old_str: str, new_str: str) -> None:
    try:
        context.unique_replace_result = tool_loop.apply_unique_str_replace(text, old_str, new_str)
        context.unique_replace_error = None
    except Exception as exc:  # noqa: BLE001
        context.unique_replace_result = None
        context.unique_replace_error = str(exc)


@then('the unique str_replace error mentions "{text}"')
def step_unique_str_replace_error_mentions(context, text: str) -> None:
    assert text in (context.unique_replace_error or "")


@then('the unique str_replace result equals "{expected}"')
def step_unique_str_replace_result_equals(context, expected: str) -> None:
    assert context.unique_replace_result == expected
