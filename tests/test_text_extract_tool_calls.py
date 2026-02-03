"""
Unit tests for text extract tool call behavior.
"""

from __future__ import annotations

import json
import unittest

from biblicus.ai.llm import ChatCompletionResult
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import tool_loop as tool_loop_module
from biblicus.text.extract import _apply_extract_replace, _validate_extract_markup
from biblicus.text.prompts import DEFAULT_EXTRACT_SYSTEM_PROMPT
from biblicus.text.tool_loop import run_tool_loop


class FakeChatCompletion:
    """
    Fake chat completion that emits two str_replace calls and done.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> ChatCompletionResult:
        """
        Return a synthetic chat completion with str_replace tool calls.
        """
        self.calls.append(dict(kwargs))
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {"old_str": "This", "new_str": "<span>This"},
                    ),
                },
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {"old_str": "wrapped.", "new_str": "wrapped.</span>"},
                    ),
                },
            },
            {
                "id": "call_3",
                "type": "function",
                "function": {
                    "name": "done",
                    "arguments": "{}",
                },
            },
        ]
        return ChatCompletionResult(text="", tool_calls=tool_calls)


class TestTextExtractToolCalls(unittest.TestCase):
    """
    Tests for str_replace call sequencing.
    """

    def test_long_span_uses_two_str_replace_calls(self) -> None:
        """
        Ensure long spans require two str_replace tool calls.
        """
        text = "This is a long passage that should be wrapped."
        fake_completion = FakeChatCompletion()
        original = tool_loop_module.chat_completion
        tool_loop_module.chat_completion = fake_completion
        try:
            result = run_tool_loop(
                text=text,
                client=LlmClientConfig(
                    provider=AiProvider.OPENAI,
                    model="gpt-4o-mini",
                    api_key="test-openai-key",
                    response_format="json_object",
                ),
                system_prompt=DEFAULT_EXTRACT_SYSTEM_PROMPT,
                prompt_template="Return the requested text.",
                max_rounds=1,
                max_edits_per_round=5,
                apply_str_replace=_apply_extract_replace,
                validate_text=_validate_extract_markup,
            )
        finally:
            tool_loop_module.chat_completion = original

        assistant_messages = [
            message for message in result.messages if message.get("role") == "assistant"
        ]
        self.assertTrue(assistant_messages)
        tool_calls = assistant_messages[0].get("tool_calls") or []
        str_replace_calls = [
            call for call in tool_calls if call.get("function", {}).get("name") == "str_replace"
        ]
        self.assertEqual(len(str_replace_calls), 2)
        self.assertIn("<span>", result.text)
        self.assertIn("</span>", result.text)


if __name__ == "__main__":
    unittest.main()
