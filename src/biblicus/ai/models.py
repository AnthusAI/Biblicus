"""
Pydantic models for provider-backed AI clients.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field, field_validator

from ..analysis.schema import AnalysisSchemaModel
from ..user_config import resolve_openai_api_key


class AiProvider(str, Enum):
    """
    Supported AI providers.
    """

    OPENAI = "openai"
    BEDROCK = "bedrock"
    LITELLM = "litellm"


class LlmClientConfig(AnalysisSchemaModel):
    """
    Configuration for a chat completion invocation.

    :ivar provider: Provider identifier.
    :vartype provider: AiProvider
    :ivar model: Model identifier.
    :vartype model: str
    :ivar api_key: Optional API key override.
    :vartype api_key: str or None
    :ivar temperature: Optional generation temperature.
    :vartype temperature: float or None
    :ivar max_tokens: Optional maximum output tokens.
    :vartype max_tokens: int or None
    :ivar response_format: Optional response format identifier.
    :vartype response_format: str or None
    :ivar max_retries: Optional maximum retry count for transient failures.
    :vartype max_retries: int
    :ivar timeout_seconds: Optional request timeout in seconds.
    :vartype timeout_seconds: float or None
    """

    provider: AiProvider
    model: str = Field(min_length=1)
    api_key: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    response_format: Optional[str] = None
    max_retries: int = Field(default=0, ge=0)
    timeout_seconds: Optional[float] = Field(default=None, gt=0.0)

    @field_validator("provider", mode="before")
    @classmethod
    def _parse_provider(cls, value: object) -> AiProvider:
        if isinstance(value, AiProvider):
            return value
        if isinstance(value, str):
            return AiProvider(value)
        raise ValueError("llm client provider must be a string or AiProvider")

    def resolve_api_key(self) -> str:
        """
        Resolve an API key for the configured provider.

        :return: API key string.
        :rtype: str
        :raises ValueError: If the provider requires a key and none is configured.
        """
        if self.provider != AiProvider.OPENAI:
            raise ValueError(f"Unsupported provider: {self.provider}")
        api_key = self.api_key or resolve_openai_api_key()
        if api_key is None:
            raise ValueError(
                "OpenAI provider requires an OpenAI API key. "
                "Set OPENAI_API_KEY or configure it in ~/.biblicus/config.yml or ./.biblicus/config.yml under "
                "openai.api_key."
            )
        return api_key


class EmbeddingsClientConfig(AnalysisSchemaModel):
    """
    Configuration for an embeddings invocation.

    :ivar provider: Provider identifier.
    :vartype provider: AiProvider
    :ivar model: Model identifier.
    :vartype model: str
    :ivar api_key: Optional API key override.
    :vartype api_key: str or None
    :ivar batch_size: Maximum number of texts per request.
    :vartype batch_size: int
    :ivar parallelism: Maximum number of concurrent requests.
    :vartype parallelism: int
    :ivar max_retries: Optional maximum retry count for transient failures.
    :vartype max_retries: int
    """

    provider: AiProvider
    model: str = Field(min_length=1)
    api_key: Optional[str] = None
    batch_size: int = Field(default=64, ge=1)
    parallelism: int = Field(default=4, ge=1)
    max_retries: int = Field(default=0, ge=0)

    @field_validator("provider", mode="before")
    @classmethod
    def _parse_provider(cls, value: object) -> AiProvider:
        if isinstance(value, AiProvider):
            return value
        if isinstance(value, str):
            return AiProvider(value)
        raise ValueError("embeddings provider must be a string or AiProvider")

    def resolve_api_key(self) -> str:
        """
        Resolve an API key for the configured provider.

        :return: API key string.
        :rtype: str
        :raises ValueError: If the provider requires a key and none is configured.
        """
        if self.provider != AiProvider.OPENAI:
            raise ValueError(f"Unsupported provider: {self.provider}")
        api_key = self.api_key or resolve_openai_api_key()
        if api_key is None:
            raise ValueError(
                "OpenAI provider requires an OpenAI API key. "
                "Set OPENAI_API_KEY or configure it in ~/.biblicus/config.yml or ./.biblicus/config.yml under "
                "openai.api_key."
            )
        return api_key
