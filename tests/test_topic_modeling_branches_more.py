import pytest

from biblicus.analysis import topic_modeling
from biblicus.analysis.models import (
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
    TopicModelingLexicalProcessingConfig,
)
from biblicus.analysis.topic_modeling import TopicModelingDocument, _apply_lexical_processing


def test_topic_modeling_llm_extraction_handles_empty_response(monkeypatch):
    documents = [TopicModelingDocument(document_id="d1", source_item_id="i1", text="text")]
    config = TopicModelingLlmExtractionConfig.model_construct(
        enabled=True,
        method=TopicModelingLlmExtractionMethod.ITEMIZE,
        client={"provider": "mock", "model": "demo"},
        prompt_template="{text}",
        system_prompt=None,
        max_keywords=2,
        max_documents=1,
    )
    monkeypatch.setattr(topic_modeling, "generate_completion", lambda **kwargs: "[]")
    with pytest.raises(ValueError):
        topic_modeling._apply_llm_extraction(documents=documents, config=config)


def test_topic_modeling_lexical_processing_skips_when_disabled():
    docs = [TopicModelingDocument(document_id="d", source_item_id="", text="x")]
    cfg = TopicModelingLexicalProcessingConfig(enabled=False)
    report, processed = _apply_lexical_processing(documents=docs, config=cfg)
    assert report.status.name == "SKIPPED"
    assert processed == docs
