"""
Unit tests for tool loop safeguards and feedback.
"""

from __future__ import annotations

import json
import unittest

from biblicus.ai.llm import ChatCompletionResult
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import tool_loop as tool_loop_module
from biblicus.text.tool_loop import apply_unique_str_replace, run_tool_loop


class FakeNoOpCompletion:
    """
    Fake completion that attempts a no-op replacement.
    """

    def __call__(self, **_kwargs: object) -> ChatCompletionResult:
        """
        Return a synthetic no-op completion result.
        """
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps({"old_str": "Hello", "new_str": "Hello"}),
                },
            },
            {"id": "call_2", "type": "function", "function": {"name": "done", "arguments": "{}"}},
        ]
        return ChatCompletionResult(text="", tool_calls=tool_calls)


class FakeMultiMatchCompletion:
    """
    Fake completion that uses a short old_str with multiple matches.
    """

    def __call__(self, **_kwargs: object) -> ChatCompletionResult:
        """
        Return a synthetic completion with ambiguous matches.
        """
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps({"old_str": "hi", "new_str": "<span>hi</span>"}),
                },
            },
            {"id": "call_2", "type": "function", "function": {"name": "done", "arguments": "{}"}},
        ]
        return ChatCompletionResult(text="", tool_calls=tool_calls)


class FakeRemovalCompletion:
    """
    Fake completion that attempts to remove content.
    """

    def __call__(self, **_kwargs: object) -> ChatCompletionResult:
        """
        Return a synthetic completion that removes content.
        """
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps({"old_str": "Hello world", "new_str": "Hello"}),
                },
            },
            {"id": "call_2", "type": "function", "function": {"name": "done", "arguments": "{}"}},
        ]
        return ChatCompletionResult(text="", tool_calls=tool_calls)


class FakeShortNotFoundCompletion:
    """
    Fake completion that uses a short old_str with no matches.
    """

    def __call__(self, **_kwargs: object) -> ChatCompletionResult:
        """
        Return a synthetic completion that yields no matches.
        """
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps({"old_str": "a", "new_str": "<span>a</span>"}),
                },
            },
            {"id": "call_2", "type": "function", "function": {"name": "done", "arguments": "{}"}},
        ]
        return ChatCompletionResult(text="", tool_calls=tool_calls)


class TestToolLoopSafeguards(unittest.TestCase):
    """
    Unit tests for tool loop safeguards.
    """

    def _run(self, *, text: str, fake_completion: object) -> tool_loop_module.ToolLoopResult:
        """
        Run the tool loop with a fake completion implementation.
        """
        original = tool_loop_module.chat_completion
        tool_loop_module.chat_completion = fake_completion
        try:
            return run_tool_loop(
                text=text,
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
                apply_str_replace=apply_unique_str_replace,
            )
        finally:
            tool_loop_module.chat_completion = original

    def test_no_op_replacement_is_rejected(self) -> None:
        """
        Ensure no-op replacements are rejected.
        """
        result = self._run(text="Hello", fake_completion=FakeNoOpCompletion())
        self.assertIn("requires str_replace to make a change", result.last_error or "")
        self.assertFalse(result.done)
        self.assertIn("Your last tool call failed", result.messages[-1]["content"])

    def test_multiple_matches_are_rejected_with_guidance(self) -> None:
        """
        Ensure ambiguous replacements are rejected with guidance.
        """
        result = self._run(text="hi hi", fake_completion=FakeMultiMatchCompletion())
        self.assertIn("found 2 matches", result.last_error or "")
        self.assertIn("longer unique old_str", result.messages[-1]["content"])

    def test_removal_is_rejected(self) -> None:
        """
        Ensure replacements that remove content are rejected.
        """
        result = self._run(text="Hello world", fake_completion=FakeRemovalCompletion())
        self.assertIn("may only insert markup tags", result.last_error or "")

    def test_short_old_str_hints_view(self) -> None:
        """
        Ensure short unmatched strings produce a helpful hint.
        """
        result = self._run(text="bbb", fake_completion=FakeShortNotFoundCompletion())
        self.assertIn("found 0 matches", result.last_error or "")
        self.assertIn("call view", result.messages[-1]["content"])


if __name__ == "__main__":
    unittest.main()
