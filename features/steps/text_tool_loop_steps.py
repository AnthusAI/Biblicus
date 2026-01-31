from __future__ import annotations

from behave import then, when

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
