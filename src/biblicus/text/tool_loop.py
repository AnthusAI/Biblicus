"""
Shared tool loop for virtual file edit workflows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..ai.llm import chat_completion
from ..ai.models import LlmClientConfig


@dataclass
class ToolLoopResult:
    """
    Tool loop result payload.

    :param text: Final text after tool edits.
    :type text: str
    :param done: Whether the model called done.
    :type done: bool
    :param last_error: Last error message, if any.
    :type last_error: str or None
    :param messages: Conversation history including tool calls/results.
    :type messages: list[dict[str, Any]]
    """

    text: str
    done: bool
    last_error: Optional[str]
    messages: List[Dict[str, Any]]


def run_tool_loop(
    *,
    text: str,
    client: LlmClientConfig,
    system_prompt: str,
    prompt_template: str,
    max_rounds: int,
    max_edits_per_round: int,
    apply_str_replace: Callable[[str, str, str], str],
    validate_text: Optional[Callable[[str], Sequence[str]]] = None,
    build_retry_message: Optional[Callable[[Sequence[str], str], str]] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
) -> ToolLoopResult:
    """
    Run a tool-driven virtual file edit loop.

    :param text: Input text to edit.
    :type text: str
    :param client: LLM client configuration.
    :type client: biblicus.ai.models.LlmClientConfig
    :param system_prompt: System prompt containing the text placeholder.
    :type system_prompt: str
    :param prompt_template: User prompt describing what to return.
    :type prompt_template: str
    :param max_rounds: Maximum number of rounds.
    :type max_rounds: int
    :param max_edits_per_round: Maximum edits per round.
    :type max_edits_per_round: int
    :param apply_str_replace: Replacement function for str_replace edits.
    :type apply_str_replace: Callable[[str, str, str], str]
    :param validate_text: Optional validation callback returning error messages.
    :type validate_text: Callable[[str], Sequence[str]] or None
    :param build_retry_message: Optional retry message builder.
    :type build_retry_message: Callable[[Sequence[str], str], str] or None
    :param messages: Optional conversation history to continue (system prompt should already be included).
    :type messages: list[dict[str, Any]] or None
    :return: Tool loop result.
    :rtype: ToolLoopResult
    :raises ValueError: If the provider backend is unavailable.

    Validation errors trigger a retry by appending a user feedback message to the
    conversation history (including all prior tool calls and tool results).
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "str_replace",
                "description": "Replace an exact substring with a new string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "old_str": {"type": "string"},
                        "new_str": {"type": "string"},
                    },
                    "required": ["old_str", "new_str"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "view",
                "description": "Return the current text.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "done",
                "description": "Finish editing.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
    ]

    if messages is None:
        rendered_prompt = _render_template(
            prompt_template,
            text=text,
            text_length=len(text),
            error="",
        )
        rendered_system = _render_template(
            system_prompt,
            text=text,
            text_length=len(text),
            error="",
        )
        messages = [
            {"role": "system", "content": rendered_system},
            {"role": "user", "content": rendered_prompt},
        ]
    else:
        messages = list(messages)

    done = False
    last_error: Optional[str] = None
    current_text = text

    for _ in range(max_rounds):
        had_tool_error = False
        response = chat_completion(
            client=client,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        tool_calls = response.tool_calls
        if not tool_calls:
            content = response.text or ""
            last_error = "Tool loop requires tool calls (str_replace/view/done)"
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": _build_no_tool_calls_message(
                        assistant_message=content,
                        current_text=current_text,
                    ),
                }
            )
            continue
        messages.append(
            {
                "role": "assistant",
                "content": response.text or "",
                "tool_calls": list(tool_calls),
            }
        )
        edit_count = 0
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = str(function.get("name") or "")
            args = json.loads(str(function.get("arguments") or "{}"))
            if name == "str_replace":
                edit_count += 1
                if edit_count > max_edits_per_round:
                    last_error = "Tool loop exceeded max edits per round"
                    tool_result = f"Error: {last_error}"
                else:
                    old_str = str(args.get("old_str", ""))
                    new_str = str(args.get("new_str", ""))
                    if not old_str or not new_str:
                        last_error = "Tool loop requires non-empty old_str and new_str"
                        tool_result = f"Error: {last_error}"
                    else:
                        try:
                            current_text = apply_str_replace(current_text, old_str, new_str)
                            tool_result = (
                                "Applied str_replace.\nCurrent text:\n---\n" f"{current_text}\n---"
                            )
                            last_error = None
                        except ValueError as exc:
                            last_error = str(exc)
                            tool_result = f"Error: {last_error}"
                            had_tool_error = True
            elif name == "view":
                tool_result = f"Current text:\n---\n{current_text}\n---"
            elif name == "done":
                done = True
                tool_result = "Done"
            else:
                raise ValueError(f"Tool loop received unknown tool: {name}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "content": tool_result,
                }
            )
        if had_tool_error and last_error is not None:
            done = False
            messages.append(
                {
                    "role": "user",
                    "content": _build_tool_error_message(
                        error_message=last_error,
                        current_text=current_text,
                    ),
                }
            )
            continue
        if validate_text is not None:
            validation_errors = list(validate_text(current_text))
            if validation_errors:
                last_error = "; ".join(validation_errors)
                done = False
                retry_message = _build_retry_message(
                    validation_errors=validation_errors,
                    current_text=current_text,
                    build_retry_message=build_retry_message,
                )
                messages.append({"role": "user", "content": retry_message})
                continue
        if done:
            break

    return ToolLoopResult(
        text=current_text,
        done=done,
        last_error=last_error,
        messages=messages,
    )


def _build_retry_message(
    *,
    validation_errors: Sequence[str],
    current_text: str,
    build_retry_message: Optional[Callable[[Sequence[str], str], str]],
) -> str:
    if build_retry_message is not None:
        return build_retry_message(validation_errors, current_text)
    error_lines = "\n".join(f"- {error}" for error in validation_errors)
    return (
        "Your last edit did not validate.\n"
        "Issues:\n"
        f"{error_lines}\n\n"
        "Please fix the markup using str_replace and keep the source text unchanged.\n"
        "Current text:\n"
        f"---\n{current_text}\n---"
    )


def _build_tool_error_message(*, error_message: str, current_text: str) -> str:
    if "not unique" in error_message:
        guidance = (
            "Use a longer unique old_str by including surrounding words or punctuation "
            "so it matches exactly once."
        )
    elif "not found" in error_message:
        guidance = (
            "Copy the exact old_str from the current text (including punctuation/case) "
            "or call view to inspect the latest text."
        )
    else:
        guidance = "Fix the tool call and try again."
    return (
        "Your last tool call failed.\n"
        f"Error: {error_message}\n"
        f"{guidance}\n"
        "Current text:\n"
        f"---\n{current_text}\n---"
    )


def _build_no_tool_calls_message(*, assistant_message: str, current_text: str) -> str:
    guidance = (
        "Use the tools to edit the text. "
        "Call str_replace to insert markup, view to inspect, and done when finished."
    )
    message = "Your last response did not include any tool calls."
    if assistant_message.strip():
        message = f"{message}\nAssistant message: {assistant_message}"
    return f"{message}\n" f"{guidance}\n" "Current text:\n" f"---\n{current_text}\n---"


def request_confirmation(
    *,
    result: ToolLoopResult,
    text: str,
    client: LlmClientConfig,
    system_prompt: str,
    prompt_template: str,
    max_rounds: int,
    max_edits_per_round: int,
    apply_str_replace: Callable[[str, str, str], str],
    confirmation_message: str,
    validate_text: Optional[Callable[[str], Sequence[str]]] = None,
    build_retry_message: Optional[Callable[[Sequence[str], str], str]] = None,
) -> ToolLoopResult:
    """
    Continue a tool loop with a confirmation message appended to the conversation history.

    This preserves the model's prior tool calls and the current text state while giving it
    a chance to confirm an empty/ambiguous result.
    """
    messages = list(result.messages)
    messages.append({"role": "user", "content": confirmation_message})
    return run_tool_loop(
        text=text,
        client=client,
        system_prompt=system_prompt,
        prompt_template=prompt_template,
        max_rounds=max_rounds,
        max_edits_per_round=max_edits_per_round,
        apply_str_replace=apply_str_replace,
        validate_text=validate_text,
        build_retry_message=build_retry_message,
        messages=messages,
    )


def _render_template(template: str, *, text: str, text_length: int, error: str) -> str:
    rendered = template.replace("{text_length}", str(text_length)).replace("{error}", error)
    return rendered.replace("{text}", text)
