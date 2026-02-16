import pytest

from biblicus.analysis.topic_modeling import (
    TopicModelingDocument,
    _apply_llm_extraction,
    _parse_itemized_response,
)
from biblicus.analysis.models import TopicModelingLlmExtractionConfig, TopicModelingLlmExtractionMethod


def test_llm_itemized_empty_results_raise(monkeypatch):
    docs = [TopicModelingDocument("d1", "s1", "alpha") for _ in range(60)]
    config = TopicModelingLlmExtractionConfig(
        enabled=True,
        client={"provider": "mock", "model": "m"},
        prompt_template="{text}",
        method=TopicModelingLlmExtractionMethod.ITEMIZE,
    )
    monkeypatch.setattr(
        "biblicus.analysis.topic_modeling.generate_completion",
        lambda **_: "[]",
    )
    with pytest.raises(ValueError):
        _apply_llm_extraction(documents=docs, config=config)


def test_parse_itemized_response_nested_string_list():
    nested = '"[\\"a\\"]"'
    assert _parse_itemized_response(nested) == ["a"]
