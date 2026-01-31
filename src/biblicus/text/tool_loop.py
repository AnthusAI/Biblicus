"""
Shared tool loop for virtual file edit workflows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..ai.models import AiProvider, LlmClientConfig


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
    """

    text: str
    done: bool
    last_error: Optional[str]


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
    :return: Tool loop result.
    :rtype: ToolLoopResult
    :raises ValueError: If the provider is unsupported or the OpenAI client is unavailable.
    """
    if client.provider != AiProvider.OPENAI:
        raise ValueError(f"Unsupported provider: {client.provider}")
    try:
        from openai import OpenAI
    except ImportError as import_error:
        raise ValueError(
            "OpenAI provider requires an optional dependency. "
            'Install it with pip install "biblicus[openai]".'
        ) from import_error

    api_key = client.resolve_api_key()
    client_instance = OpenAI(api_key=api_key, timeout=client.timeout_seconds)
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
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": rendered_system},
        {"role": "user", "content": rendered_prompt},
    ]

    done = False
    last_error: Optional[str] = None
    current_text = text

    for _ in range(max_rounds):
        response = client_instance.chat.completions.create(
            model=client.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=client.temperature,
            max_tokens=client.max_tokens,
        )
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            content = getattr(message, "content", None) or ""
            raise ValueError(
                "Tool loop expected tool calls but received a message. "
                f"Content: {content}"
            )
        messages.append(
            {
                "role": "assistant",
                "content": getattr(message, "content", None) or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in tool_calls
                ],
            }
        )
        edit_count = 0
        for tool_call in tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
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
                                "Applied str_replace.\nCurrent text:\n---\n"
                                f"{current_text}\n---"
                            )
                            last_error = None
                        except ValueError as exc:
                            last_error = str(exc)
                            tool_result = f"Error: {last_error}"
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
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                }
            )
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

    return ToolLoopResult(text=current_text, done=done, last_error=last_error)


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


def _render_template(template: str, *, text: str, text_length: int, error: str) -> str:
    rendered = template.replace("{text_length}", str(text_length)).replace("{error}", error)
    return rendered.replace("{text}", text)
