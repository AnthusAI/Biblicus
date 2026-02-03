"""
Unit tests for text utility tool call sequencing.
"""

from __future__ import annotations

import json
import unittest

from biblicus.ai.llm import ChatCompletionResult
from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text import annotate as annotate_module
from biblicus.text import link as link_module
from biblicus.text import redact as redact_module
from biblicus.text import tool_loop as tool_loop_module
from biblicus.text.prompts import (
    DEFAULT_ANNOTATE_SYSTEM_PROMPT,
    DEFAULT_LINK_SYSTEM_PROMPT,
    DEFAULT_REDACT_SYSTEM_PROMPT,
)
from biblicus.text.tool_loop import run_tool_loop


class FakeAnnotateCompletion:
    """
    Fake annotate completion response with str_replace tool calls.
    """

    def __call__(self, **_kwargs: object) -> ChatCompletionResult:
        """
        Return a synthetic annotate completion result.
        """
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {
                            "old_str": "Long passage",
                            "new_str": '<span label="entity">Long passage',
                        }
                    ),
                },
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {
                            "old_str": "annotation.",
                            "new_str": "annotation.</span>",
                        }
                    ),
                },
            },
            {
                "id": "call_3",
                "type": "function",
                "function": {"name": "done", "arguments": "{}"},
            },
        ]
        return ChatCompletionResult(text="", tool_calls=tool_calls)


class FakeRedactCompletion:
    """
    Fake redact completion response with str_replace tool calls.
    """

    def __call__(self, **_kwargs: object) -> ChatCompletionResult:
        """
        Return a synthetic redact completion result.
        """
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {
                            "old_str": "Sensitive data",
                            "new_str": '<span redact="pii">Sensitive data',
                        }
                    ),
                },
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps({"old_str": "removed.", "new_str": "removed.</span>"}),
                },
            },
            {
                "id": "call_3",
                "type": "function",
                "function": {"name": "done", "arguments": "{}"},
            },
        ]
        return ChatCompletionResult(text="", tool_calls=tool_calls)


class FakeLinkCompletion:
    """
    Fake link completion response with str_replace tool calls.
    """

    def __call__(self, **_kwargs: object) -> ChatCompletionResult:
        """
        Return a synthetic link completion result.
        """
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {
                            "old_str": "Acme updated. ",
                            "new_str": '<span id="link_1">Acme updated. ',
                        }
                    ),
                },
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {"old_str": "Acme updated. ", "new_str": "Acme</span> updated. "}
                    ),
                },
            },
            {
                "id": "call_3",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {
                            "old_str": "Acme updated.",
                            "new_str": '<span ref="link_1">Acme updated.',
                        }
                    ),
                },
            },
            {
                "id": "call_4",
                "type": "function",
                "function": {
                    "name": "str_replace",
                    "arguments": json.dumps(
                        {"old_str": "Acme updated.", "new_str": "Acme</span> updated."}
                    ),
                },
            },
            {
                "id": "call_5",
                "type": "function",
                "function": {"name": "done", "arguments": "{}"},
            },
        ]
        return ChatCompletionResult(text="", tool_calls=tool_calls)


class TestTextUtilityToolCalls(unittest.TestCase):
    """
    Unit tests for text utility tool call sequencing.
    """

    def test_text_annotate_uses_two_str_replace_calls(self) -> None:
        """
        Ensure annotate uses two str_replace tool calls.
        """
        text = "Long passage needing annotation."
        allowed_attributes = ["label"]
        system_prompt = annotate_module._render_system_prompt(
            DEFAULT_ANNOTATE_SYSTEM_PROMPT,
            allowed_attributes=allowed_attributes,
        )
        fake_completion = FakeAnnotateCompletion()
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
                system_prompt=system_prompt,
                prompt_template="Return the requested text.",
                max_rounds=1,
                max_edits_per_round=5,
                apply_str_replace=annotate_module._apply_annotate_replace,
                validate_text=lambda current_text: annotate_module._validate_annotation_markup(
                    current_text, allowed_attributes
                ),
            )
        finally:
            tool_loop_module.chat_completion = original

        assistant_messages = [
            message for message in result.messages if message.get("role") == "assistant"
        ]
        tool_calls = assistant_messages[0].get("tool_calls") or []
        str_replace_calls = [
            call for call in tool_calls if call.get("function", {}).get("name") == "str_replace"
        ]
        self.assertEqual(len(str_replace_calls), 2)
        self.assertIn("<span", result.text)
        self.assertIn("</span>", result.text)

    def test_text_redact_uses_two_str_replace_calls(self) -> None:
        """
        Ensure redact uses two str_replace tool calls.
        """
        text = "Sensitive data should be removed."
        redaction_types = ["pii"]
        system_prompt = redact_module._render_system_prompt(
            DEFAULT_REDACT_SYSTEM_PROMPT,
            redaction_types=redaction_types,
        )
        fake_completion = FakeRedactCompletion()
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
                system_prompt=system_prompt,
                prompt_template="Return the requested text.",
                max_rounds=1,
                max_edits_per_round=5,
                apply_str_replace=redact_module._apply_redact_replace,
                validate_text=lambda current_text: redact_module._validate_redaction_markup(
                    current_text, redaction_types
                ),
            )
        finally:
            tool_loop_module.chat_completion = original

        assistant_messages = [
            message for message in result.messages if message.get("role") == "assistant"
        ]
        tool_calls = assistant_messages[0].get("tool_calls") or []
        str_replace_calls = [
            call for call in tool_calls if call.get("function", {}).get("name") == "str_replace"
        ]
        self.assertEqual(len(str_replace_calls), 2)
        self.assertIn("<span", result.text)
        self.assertIn("</span>", result.text)

    def test_text_link_uses_four_str_replace_calls(self) -> None:
        """
        Ensure link uses four str_replace tool calls.
        """
        text = "Acme updated. Acme updated."
        system_prompt = link_module._render_system_prompt(
            DEFAULT_LINK_SYSTEM_PROMPT, id_prefix="link_"
        )
        fake_completion = FakeLinkCompletion()
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
                system_prompt=system_prompt,
                prompt_template="Link repeated mentions.",
                max_rounds=1,
                max_edits_per_round=10,
                apply_str_replace=link_module._apply_link_replace,
                validate_text=lambda current_text: link_module._validate_link_markup(
                    current_text, "link_"
                ),
            )
        finally:
            tool_loop_module.chat_completion = original

        assistant_messages = [
            message for message in result.messages if message.get("role") == "assistant"
        ]
        tool_calls = assistant_messages[0].get("tool_calls") or []
        str_replace_calls = [
            call for call in tool_calls if call.get("function", {}).get("name") == "str_replace"
        ]
        self.assertEqual(len(str_replace_calls), 4)
        self.assertIn('id="link_1"', result.text)
        self.assertIn('ref="link_1"', result.text)


if __name__ == "__main__":
    unittest.main()
