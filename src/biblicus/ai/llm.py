"""
Provider-backed chat completions.
"""

from __future__ import annotations

from typing import Optional

from .models import AiProvider, LlmClientConfig


def generate_completion(
    *,
    client: LlmClientConfig,
    system_prompt: Optional[str],
    user_prompt: str,
) -> str:
    """
    Generate a completion using the configured provider.

    :param client: LLM client configuration.
    :type client: biblicus.ai.models.LlmClientConfig
    :param system_prompt: Optional system prompt content.
    :type system_prompt: str or None
    :param user_prompt: User prompt content.
    :type user_prompt: str
    :return: Generated completion text.
    :rtype: str
    :raises ValueError: If required dependencies or credentials are missing.
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
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    client_instance = OpenAI(api_key=api_key, timeout=client.timeout_seconds)
    request = {
        "model": client.model,
        "messages": messages,
        "temperature": client.temperature,
        "max_tokens": client.max_tokens,
    }
    if client.response_format:
        request["response_format"] = {"type": client.response_format}
    response = client_instance.chat.completions.create(**request)
    content = response.choices[0].message.content
    return str(content or "")
