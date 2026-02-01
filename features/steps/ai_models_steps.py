from __future__ import annotations

import os
from dataclasses import dataclass

from behave import then, when
from pydantic import ValidationError

from biblicus.ai.models import AiProvider, EmbeddingsClientConfig, LlmClientConfig


def _parse_literal(value: str) -> object:
    try:
        return int(value)
    except ValueError:
        return value


@dataclass
class _Result:
    returncode: int
    stdout: str
    stderr: str


@when('I attempt to resolve an LLM API key for provider "{provider}"')
def step_attempt_resolve_llm_api_key(context, provider: str) -> None:
    try:
        config = LlmClientConfig(provider=AiProvider(provider), model="gpt-4o-mini")
        _ = config.resolve_api_key()
        context.last_result = _Result(returncode=0, stdout="", stderr="")
    except Exception as exc:  # noqa: BLE001
        context.last_result = _Result(returncode=2, stdout="", stderr=str(exc))


@when('I attempt to resolve an embeddings API key for provider "{provider}"')
def step_attempt_resolve_embeddings_api_key(context, provider: str) -> None:
    try:
        config = EmbeddingsClientConfig(
            provider=AiProvider(provider),
            model="text-embedding-3-small",
        )
        _ = config.resolve_api_key()
        context.last_result = _Result(returncode=0, stdout="", stderr="")
    except Exception as exc:  # noqa: BLE001
        context.last_result = _Result(returncode=2, stdout="", stderr=str(exc))


@when("I attempt to validate an embeddings client config with invalid provider type")
def step_attempt_validate_embeddings_client_invalid_provider_type(context) -> None:
    try:
        EmbeddingsClientConfig.model_validate({"provider": 123, "model": "text-embedding-3-small"})
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to resolve an embeddings API key without an explicit api key")
def step_attempt_resolve_embeddings_api_key_missing(context) -> None:
    prior_home = os.environ.get("HOME")
    prior_key = os.environ.get("OPENAI_API_KEY")
    prior_cwd = os.getcwd()
    try:
        os.environ["HOME"] = str(getattr(context, "workdir"))
        os.environ.pop("OPENAI_API_KEY", None)
        os.chdir(str(getattr(context, "workdir")))
        config = EmbeddingsClientConfig(provider=AiProvider.OPENAI, model="text-embedding-3-small")
        _ = config.resolve_api_key()
        context.last_result = _Result(returncode=0, stdout="", stderr="")
    except Exception as exc:  # noqa: BLE001
        context.last_result = _Result(returncode=2, stdout="", stderr=str(exc))
    finally:
        os.chdir(prior_cwd)
        if prior_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = prior_home
        if prior_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = prior_key


@when("I access the Biblicus ai module exports")
def step_access_ai_module_exports(context) -> None:
    import biblicus.ai as ai_module

    context.ai_module = ai_module


@then('the ai module exposes "{name}"')
def step_ai_module_exposes(context, name: str) -> None:
    ai_module = context.ai_module
    exported = getattr(ai_module, name)
    assert exported is not None


@then('the ai module rejects unknown export "{name}"')
def step_ai_module_rejects_unknown(context, name: str) -> None:
    ai_module = context.ai_module
    try:
        _ = getattr(ai_module, name)
    except AttributeError:
        context.ai_module_error = None
        return
    raise AssertionError("Expected AttributeError for unknown export")


@when(
    'I resolve an LLM model identifier for provider "{provider}" and model "{model}"'
)
def step_resolve_llm_model_identifier(context, provider: str, model: str) -> None:
    config = LlmClientConfig(provider=AiProvider(provider), model=model)
    context.last_llm_model_identifier = config.litellm_model()


@then('the LLM model identifier equals "{expected}"')
def step_llm_model_identifier_equals(context, expected: str) -> None:
    resolved = getattr(context, "last_llm_model_identifier", None)
    assert resolved == expected


@when("I build LLM client kwargs with extra params")
def step_build_llm_kwargs_with_extra_params(context) -> None:
    config = LlmClientConfig(
        provider=AiProvider.OPENAI,
        model="gpt-4o-mini",
        api_key="test-key",
        extra_params={"openai_reasoning_effort": "high"},
    )
    context.last_llm_kwargs = config.build_litellm_kwargs()


@then('the LLM kwargs include "{key}" with value "{value}"')
def step_llm_kwargs_include_value(context, key: str, value: str) -> None:
    kwargs = getattr(context, "last_llm_kwargs", None)
    assert kwargs is not None
    assert kwargs.get(key) == _parse_literal(value)


@when('I resolve an embeddings API key with explicit key "{api_key}"')
def step_resolve_embeddings_api_key_explicit(context, api_key: str) -> None:
    config = EmbeddingsClientConfig(
        provider=AiProvider.OPENAI,
        model="text-embedding-3-small",
        api_key=api_key,
    )
    context.resolved_api_key = config.resolve_api_key()


@when('I resolve an embeddings API key from environment "{api_key}"')
def step_resolve_embeddings_api_key_from_environment(context, api_key: str) -> None:
    prior_key = os.environ.get("OPENAI_API_KEY")
    try:
        os.environ["OPENAI_API_KEY"] = api_key
        config = EmbeddingsClientConfig(
            provider=AiProvider.OPENAI,
            model="text-embedding-3-small",
        )
        context.resolved_api_key = config.resolve_api_key()
    finally:
        if prior_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = prior_key


@when("I build embeddings client kwargs with extra params")
def step_build_embeddings_kwargs_with_extra_params(context) -> None:
    config = EmbeddingsClientConfig(
        provider=AiProvider.OPENAI,
        model="text-embedding-3-small",
        api_key="test-key",
        extra_params={"dimensions": 3},
    )
    context.last_embeddings_kwargs = config.build_litellm_kwargs()


@then('the embeddings kwargs include "{key}" with value "{value}"')
def step_embeddings_kwargs_include_value(context, key: str, value: str) -> None:
    kwargs = getattr(context, "last_embeddings_kwargs", None)
    assert kwargs is not None
    assert kwargs.get(key) == _parse_literal(value)
