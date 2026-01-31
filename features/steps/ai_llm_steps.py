from __future__ import annotations

from dataclasses import dataclass

from behave import when

from biblicus.ai.llm import generate_completion
from biblicus.ai.models import AiProvider, LlmClientConfig


@dataclass
class _Result:
    returncode: int
    stdout: str
    stderr: str


@when('I attempt to generate a completion with provider "{provider}"')
def step_attempt_generate_completion_with_provider(context, provider: str) -> None:
    try:
        client = LlmClientConfig(
            provider=AiProvider(provider),
            model="gpt-4o-mini",
            api_key="test-key",
        )
        _ = generate_completion(client=client, system_prompt=None, user_prompt="Hello")
        context.last_result = _Result(returncode=0, stdout="", stderr="")
    except Exception as exc:  # noqa: BLE001
        context.last_result = _Result(returncode=2, stdout="", stderr=str(exc))


@when('I generate a completion with response format "{response_format}"')
def step_generate_completion_with_response_format(context, response_format: str) -> None:
    client = LlmClientConfig(
        provider=AiProvider.OPENAI,
        model="gpt-4o-mini",
        api_key="test-key",
        response_format=response_format,
    )
    context.last_completion = generate_completion(
        client=client,
        system_prompt="System",
        user_prompt="User",
    )
