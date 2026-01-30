"""
Lightweight LLM client configuration for analysis pipelines.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator

from ..user_config import resolve_openai_api_key
from .schema import AnalysisSchemaModel


class LlmProvider(str, Enum):
    """
    Supported LLM providers.
    """

    OPENAI = "openai"


class LlmClientConfig(AnalysisSchemaModel):
    """
    Configuration for an LLM client invocation.

    :ivar provider: LLM provider identifier.
    :vartype provider: LlmProvider
    :ivar model: Model identifier for the provider.
    :vartype model: str
    :ivar api_key: Optional API key override.
    :vartype api_key: str or None
    :ivar temperature: Optional generation temperature.
    :vartype temperature: float or None
    :ivar max_tokens: Optional maximum output tokens.
    :vartype max_tokens: int or None
    :ivar max_retries: Optional maximum retry count for transient failures.
    :vartype max_retries: int
    """

    provider: LlmProvider
    model: str = Field(min_length=1)
    api_key: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    max_retries: int = Field(default=0, ge=0)

    @field_validator("provider", mode="before")
    @classmethod
    def _parse_provider(cls, value: object) -> LlmProvider:
        if isinstance(value, LlmProvider):
            return value
        if isinstance(value, str):
            return LlmProvider(value)
        raise ValueError("llm client provider must be a string or LlmProvider")


def generate_completion(
    *,
    client: LlmClientConfig,
    system_prompt: Optional[str],
    user_prompt: str,
) -> str:
    """
    Generate a completion using the configured LLM provider.

    :param client: LLM client configuration.
    :type client: LlmClientConfig
    :param system_prompt: Optional system prompt content.
    :type system_prompt: str or None
    :param user_prompt: User prompt content.
    :type user_prompt: str
    :return: Generated completion text.
    :rtype: str
    :raises ValueError: If required dependencies or credentials are missing.
    """
    try:
        from openai import OpenAI
    except ImportError as import_error:
        raise ValueError(
            "OpenAI LLM provider requires an optional dependency. "
            'Install it with pip install "biblicus[openai]".'
        ) from import_error
    api_key = client.api_key or resolve_openai_api_key()
    if api_key is None:
        raise ValueError(
            "OpenAI LLM provider requires an OpenAI API key. "
            "Set OPENAI_API_KEY or configure it in ~/.biblicus/config.yml or ./.biblicus/config.yml under "
            "openai.api_key."
        )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    client_instance = OpenAI(api_key=api_key)
    response = client_instance.chat.completions.create(
        model=client.model,
        messages=messages,
        temperature=client.temperature,
        max_tokens=client.max_tokens,
    )
    content = response.choices[0].message.content
    return str(content or "")
