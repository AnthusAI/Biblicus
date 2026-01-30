from __future__ import annotations

from typing import Dict

from behave import then, when
from pydantic import ValidationError

from biblicus.analysis import get_analysis_backend
from biblicus.analysis.base import CorpusAnalysisBackend
from biblicus.analysis.llm import LlmClientConfig, LlmProvider
from biblicus.analysis.models import (
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
    TopicModelingLlmFineTuningConfig,
    TopicModelingKeyword,
    TopicModelingLabelSource,
    TopicModelingTopic,
    TopicModelingVectorizerConfig,
)
from biblicus.analysis.topic_modeling import (
    _TopicDocument,
    _apply_llm_fine_tuning,
    _parse_itemized_response,
)
from biblicus.models import ExtractionRunReference
from features.steps.openai_steps import (
    _FakeOpenAiChatBehavior,
    _ensure_fake_openai_chat_behaviors,
    _install_fake_openai_module,
)


class _DummyAnalysisBackend(CorpusAnalysisBackend):
    analysis_id = "dummy"

    def run_analysis(
        self,
        corpus,
        *,
        recipe_name: str,
        config: Dict[str, object],
        extraction_run: ExtractionRunReference,
    ):
        return super().run_analysis(
            corpus,
            recipe_name=recipe_name,
            config=config,
            extraction_run=extraction_run,
        )


@when('I attempt to resolve analysis backend "{analysis_id}"')
def step_attempt_resolve_analysis_backend(context, analysis_id: str) -> None:
    try:
        get_analysis_backend(analysis_id)
        context.analysis_error = None
    except KeyError as exc:
        context.analysis_error = exc


@then('the analysis backend error mentions "{text}"')
def step_analysis_backend_error_mentions(context, text: str) -> None:
    error = getattr(context, "analysis_error", None)
    assert error is not None
    assert text in str(error)


@when("I invoke the analysis backend base class")
def step_invoke_analysis_backend_base(context) -> None:
    backend = _DummyAnalysisBackend()
    try:
        backend.run_analysis(
            None,
            recipe_name="test",
            config={},
            extraction_run=ExtractionRunReference(extractor_id="pipeline", run_id="run"),
        )
        context.analysis_error = None
    except NotImplementedError as exc:
        context.analysis_error = exc


@then("a not implemented error is raised")
def step_analysis_not_implemented_error(context) -> None:
    error = getattr(context, "analysis_error", None)
    assert isinstance(error, NotImplementedError)


@when("I validate an LLM client config with enum provider")
def step_validate_llm_client_config_enum(context) -> None:
    context.llm_client_config = LlmClientConfig(
        provider=LlmProvider.OPENAI,
        model="gpt-4o-mini",
    )


@then('the LLM client config provider equals "{provider}"')
def step_llm_client_config_provider_equals(context, provider: str) -> None:
    config = getattr(context, "llm_client_config", None)
    assert config is not None
    assert config.provider.value == provider


@when("I attempt to validate an LLM client config with invalid provider type")
def step_invalid_llm_client_config_provider(context) -> None:
    try:
        LlmClientConfig.model_validate({"provider": 123, "model": "gpt-4o-mini"})
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I validate an LLM extraction config with enum method")
def step_validate_llm_extraction_config_enum(context) -> None:
    context.llm_extraction_config = TopicModelingLlmExtractionConfig(
        enabled=False,
        method=TopicModelingLlmExtractionMethod.SINGLE,
    )


@then('the LLM extraction config method equals "{method}"')
def step_llm_extraction_config_method_equals(context, method: str) -> None:
    config = getattr(context, "llm_extraction_config", None)
    assert config is not None
    assert config.method.value == method


@when("I attempt to validate an LLM extraction config with invalid method type")
def step_invalid_llm_extraction_config_method(context) -> None:
    try:
        TopicModelingLlmExtractionConfig.model_validate({"enabled": False, "method": 123})
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@then('the validation error mentions "{text}"')
def step_validation_error_mentions(context, text: str) -> None:
    error = getattr(context, "validation_error", None)
    assert error is not None
    assert text in str(error)


@when("I run LLM fine-tuning with missing document references")
def step_run_llm_fine_tuning_missing_documents(context) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_chat_behaviors(context)
    behaviors.append(_FakeOpenAiChatBehavior(response="Label"))
    client = LlmClientConfig(provider=LlmProvider.OPENAI, model="gpt-4o-mini", api_key="test-key")
    config = TopicModelingLlmFineTuningConfig(
        enabled=True,
        client=client,
        prompt_template="Keywords: {keywords}\nDocuments:\n{documents}",
    )
    topics = [
        TopicModelingTopic(
            topic_id=0,
            label="alpha",
            label_source=TopicModelingLabelSource.BERTOPIC,
            keywords=[TopicModelingKeyword(keyword="alpha", score=1.0)],
            document_count=1,
            document_examples=[],
            document_ids=["missing"],
        )
    ]
    documents = [
        _TopicDocument(document_id="present", source_item_id="present", text="Text")
    ]
    report, labeled_topics = _apply_llm_fine_tuning(
        topics=topics,
        documents=documents,
        config=config,
    )
    context.fine_tuning_report = report
    context.fine_tuning_topics = labeled_topics


@then("the fine-tuning topics labeled equals {count:d}")
def step_fine_tuning_topics_labeled(context, count: int) -> None:
    report = getattr(context, "fine_tuning_report", None)
    assert report is not None
    assert report.topics_labeled == count


@when("I parse an itemized response JSON string")
def step_parse_itemized_response_json_string(context) -> None:
    response_text = "\"[\\\"Alpha\\\", \\\"Beta\\\"]\""
    context.itemized_response = _parse_itemized_response(response_text)


@then("the itemized response contains {count:d} items")
def step_itemized_response_contains_count(context, count: int) -> None:
    items = getattr(context, "itemized_response", None)
    assert items is not None
    assert len(items) == count


@when("I validate a vectorizer config with stop words list")
def step_validate_vectorizer_stop_words_list(context) -> None:
    context.last_model = TopicModelingVectorizerConfig(stop_words=["the", "and"])


@when("I validate a vectorizer config with stop words english")
def step_validate_vectorizer_stop_words_english(context) -> None:
    context.last_model = TopicModelingVectorizerConfig(stop_words="english")


@when("I attempt to validate a vectorizer config with invalid stop words")
def step_validate_vectorizer_stop_words_invalid(context) -> None:
    try:
        TopicModelingVectorizerConfig(stop_words=[1, "the"])
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc
    except Exception as exc:  # noqa: BLE001
        context.validation_error = exc


@when("I validate a vectorizer config with no stop words")
def step_validate_vectorizer_no_stop_words(context) -> None:
    context.last_model = TopicModelingVectorizerConfig.model_validate({"stop_words": None})


@when('I attempt to validate a vectorizer config with stop words "{value}"')
def step_validate_vectorizer_stop_words_string(context, value: str) -> None:
    try:
        TopicModelingVectorizerConfig(stop_words=value)
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@then('the vectorizer stop words includes "{token}"')
def step_vectorizer_stop_words_includes(context, token: str) -> None:
    model = context.last_model
    assert model.stop_words is not None
    assert token in model.stop_words


@then('the vectorizer stop words equals "{value}"')
def step_vectorizer_stop_words_equals(context, value: str) -> None:
    model = context.last_model
    assert model.stop_words == value


@then("the vectorizer stop words are absent")
def step_vectorizer_stop_words_absent(context) -> None:
    model = context.last_model
    assert model.stop_words is None
