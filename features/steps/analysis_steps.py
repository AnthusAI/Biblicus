from __future__ import annotations

from typing import Dict

from behave import then, when
from pydantic import ValidationError

from biblicus.analysis import get_analysis_backend
from biblicus.analysis.base import CorpusAnalysisBackend
from biblicus.analysis.llm import LlmClientConfig, LlmProvider
from biblicus.analysis.models import (
    ProfilingRecipeConfig,
    TopicModelingKeyword,
    TopicModelingLabelSource,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
    TopicModelingLlmFineTuningConfig,
    TopicModelingTopic,
    TopicModelingVectorizerConfig,
)
from biblicus.analysis.profiling import _ordered_catalog_items, _percentile_value
from biblicus.analysis.topic_modeling import (
    _apply_llm_fine_tuning,
    _parse_itemized_response,
    _TopicDocument,
)
from biblicus.models import CatalogItem, ExtractionRunReference
from features.steps.openai_steps import (
    _ensure_fake_openai_chat_behaviors,
    _FakeOpenAiChatBehavior,
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
    documents = [_TopicDocument(document_id="present", source_item_id="present", text="Text")]
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
    response_text = '"[\\"Alpha\\", \\"Beta\\"]"'
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


@when("I attempt to validate a profiling config with sample size {value:d}")
def step_validate_profiling_sample_size(context, value: int) -> None:
    try:
        ProfilingRecipeConfig(sample_size=value)
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when('I attempt to validate a profiling config with percentiles "{values}"')
def step_validate_profiling_percentiles(context, values: str) -> None:
    try:
        percentiles = [int(value.strip()) for value in values.split(",") if value.strip()]
        ProfilingRecipeConfig(percentiles=percentiles)
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when('I attempt to validate a profiling config with tag filters "{values}"')
def step_validate_profiling_tag_filters(context, values: str) -> None:
    try:
        tags = [value.strip() for value in values.split(",")]
        ProfilingRecipeConfig(tag_filters=tags)
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a profiling config with schema version {value:d}")
def step_validate_profiling_schema_version(context, value: int) -> None:
    try:
        ProfilingRecipeConfig(schema_version=value)
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I attempt to validate a profiling config with empty percentiles")
def step_validate_profiling_empty_percentiles(context) -> None:
    try:
        ProfilingRecipeConfig(percentiles=[])
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when('I attempt to validate a profiling config with tag filters string "{value}"')
def step_validate_profiling_tag_filters_string(context, value: str) -> None:
    try:
        ProfilingRecipeConfig(tag_filters=value)
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@when("I validate a profiling config with tag filters None")
def step_validate_profiling_tag_filters_none(context) -> None:
    context.last_model = ProfilingRecipeConfig(tag_filters=None)


@when('I validate a profiling config with tag filters list "{values}"')
def step_validate_profiling_tag_filters_list(context, values: str) -> None:
    tags = [value.strip() for value in values.split(",")]
    context.last_model = ProfilingRecipeConfig(tag_filters=tags)


@then("the profiling tag filters are absent")
def step_profiling_tag_filters_absent(context) -> None:
    model = context.last_model
    assert model.tag_filters is None


@then('the profiling tag filters include "{value}"')
def step_profiling_tag_filters_include(context, value: str) -> None:
    model = context.last_model
    assert model.tag_filters is not None
    assert value in model.tag_filters


@when("I order catalog items with missing entries")
def step_order_catalog_items_with_missing_entries(context) -> None:
    items = {
        "a": CatalogItem(
            id="a",
            relpath="raw/a.txt",
            sha256="a",
            bytes=1,
            media_type="text/plain",
            title=None,
            tags=[],
            metadata={},
            created_at="2020-01-01T00:00:00Z",
            source_uri=None,
        ),
        "b": CatalogItem(
            id="b",
            relpath="raw/b.txt",
            sha256="b",
            bytes=2,
            media_type="text/plain",
            title=None,
            tags=[],
            metadata={},
            created_at="2020-01-01T00:00:00Z",
            source_uri=None,
        ),
        "c": CatalogItem(
            id="c",
            relpath="raw/c.txt",
            sha256="c",
            bytes=3,
            media_type="text/plain",
            title=None,
            tags=[],
            metadata={},
            created_at="2020-01-01T00:00:00Z",
            source_uri=None,
        ),
    }
    ordered = _ordered_catalog_items(items, ["a", "missing", "c"])
    context.ordered_catalog_ids = [item.id for item in ordered]


@then('the ordered catalog item identifiers equal "{values}"')
def step_ordered_catalog_item_identifiers_equal(context, values: str) -> None:
    expected = [value.strip() for value in values.split(",") if value.strip()]
    assert context.ordered_catalog_ids == expected


@when("I compute a profiling percentile on empty values")
def step_compute_profiling_percentile_empty(context) -> None:
    context.percentile_value = _percentile_value([], 50)


@then("the profiling percentile value equals {value:d}")
def step_profiling_percentile_value_equals(context, value: int) -> None:
    assert context.percentile_value == value
