from __future__ import annotations

import os
from dataclasses import dataclass

from behave import then, when
from pydantic import ValidationError

from biblicus.ai.models import AiProvider, EmbeddingsClientConfig, LlmClientConfig


@dataclass
class _Result:
    returncode: int
    stdout: str
    stderr: str


@when('I attempt to resolve an LLM API key for provider "{provider}"')
def step_attempt_resolve_llm_api_key(context, provider: str) -> None:
    try:
        config = LlmClientConfig(
            provider=AiProvider(provider), model="gpt-4o-mini", api_key="test-key"
        )
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
            api_key="test-key",
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
