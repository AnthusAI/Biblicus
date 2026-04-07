import sys
from types import SimpleNamespace

import pytest

from biblicus.analysis import topic_modeling
from biblicus.analysis.topic_modeling import (
    TopicModelingDocument,
    TopicModelingEntityRemovalConfig,
    TopicModelingLexicalProcessingConfig,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
    TopicModelingLlmFineTuningConfig,
)


def test_llm_extraction_empty_response(monkeypatch):
    docs = [TopicModelingDocument(document_id="1", source_item_id="s", text="t")]
    config = TopicModelingLlmExtractionConfig(
        enabled=True,
        client={"provider": "mock", "model": "m"},
        prompt_template="{text}",
        system_prompt="sys {text}",
        method=TopicModelingLlmExtractionMethod.SINGLE,
    )
    monkeypatch.setattr(topic_modeling, "generate_completion", lambda **kwargs: "")
    with pytest.raises(ValueError):
        topic_modeling._apply_llm_extraction(documents=docs, config=config)


def test_entity_removal_log_interval(monkeypatch, tmp_path):
    docs = [TopicModelingDocument(document_id=str(i), source_item_id="s", text=f"Text {i}") for i in range(55)]
    config = TopicModelingEntityRemovalConfig(
        enabled=True,
        provider="spacy",
        model="en",
        entity_types=[],
        replace_with="",
        regex_patterns=[],
        regex_replace_with="",
        collapse_whitespace=False,
    )
    sys.modules["spacy"] = SimpleNamespace(load=lambda model: (lambda text: SimpleNamespace(ents=[])))
    report, processed = topic_modeling._apply_entity_removal(documents=docs, config=config, cache_path=None)
    assert report.output_documents == 55
    assert len(processed) == 55


def test_lexical_processing_log_interval():
    docs = [TopicModelingDocument(document_id=str(i), source_item_id="s", text="Text!!") for i in range(80)]
    config = TopicModelingLexicalProcessingConfig(
        enabled=True,
        lowercase=True,
        strip_punctuation=True,
        collapse_whitespace=True,
    )
    report, processed = topic_modeling._apply_lexical_processing(documents=docs, config=config)
    assert report.output_documents == 80
    assert processed[0].text == "text"


def test_llm_fine_tuning_log_interval(monkeypatch):
    topics = [
        topic_modeling.TopicModelingTopic(
            topic_id=1,
            label="L",
            label_source=topic_modeling.TopicModelingLabelSource.LLM,
            keywords=[topic_modeling.TopicModelingKeyword(keyword="k", score=1.0)],
            document_ids=["d1"],
            document_count=1,
        )
        for _ in range(12)
    ]
    docs = [TopicModelingDocument(document_id="d1", source_item_id="s", text="hello")]
    config = TopicModelingLlmFineTuningConfig(
        enabled=True,
        client={"provider": "mock", "model": "m"},
        prompt_template="tmpl {keywords} {documents}",
        system_prompt="sys",
        max_keywords=1,
        max_documents=1,
    )

    monkeypatch.setattr(
        topic_modeling,
        "generate_completion",
        lambda **kwargs: '{"label":"L","evidence":"E"}',
    )

    report, labeled = topic_modeling._apply_llm_fine_tuning(
        topics=topics,
        documents=docs,
        config=config,
    )
    assert report.topics_labeled == len(topics)
    assert labeled
