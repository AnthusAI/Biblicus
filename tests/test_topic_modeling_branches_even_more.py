from types import SimpleNamespace

from biblicus.analysis import topic_modeling
from biblicus.analysis.topic_modeling import (
    TopicModelingDocument,
    TopicModelingEntityRemovalConfig,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
    TopicModelingLexicalProcessingConfig,
)


def test_llm_extraction_logs_large_batches(monkeypatch):
    documents = [TopicModelingDocument(document_id=str(i), source_item_id="s", text="text") for i in range(51)]
    config = TopicModelingLlmExtractionConfig(
        enabled=True,
        client={"provider": "mock", "model": "x"},
        prompt_template="{text}",
        system_prompt="sys {text}",
        method=TopicModelingLlmExtractionMethod.SINGLE,
    )
    monkeypatch.setattr(topic_modeling, "generate_completion", lambda **kwargs: "result")
    report, extracted = topic_modeling._apply_llm_extraction(documents=documents, config=config)
    assert report.output_documents == 51
    assert len(extracted) == 51


def test_entity_removal_uses_cache_and_regex(monkeypatch, tmp_path):
    docs = [TopicModelingDocument(document_id="1", source_item_id="s", text="Hello WORLD 123")]
    cache_path = tmp_path / "cache.jsonl"
    # prepopulate cache with different text to ensure reuse path taken
    cache_path.write_text('{"document_id":"1","source_item_id":"s","text":"cached"}\n', encoding="utf-8")
    config = TopicModelingEntityRemovalConfig(
        enabled=True,
        provider="spacy",
        model="en",
        entity_types=["PERSON"],
        replace_with="",
        regex_patterns=[r"\\d+"],
        regex_replace_with="",
        collapse_whitespace=True,
    )
    topic_modeling.spacy = SimpleNamespace(load=lambda model: (lambda text: SimpleNamespace(ents=[])))
    report, processed = topic_modeling._apply_entity_removal(
        documents=docs,
        config=config,
        cache_path=cache_path,
    )
    assert report.warnings  # cached path warning
    assert processed[0].text == "cached"


def test_lexical_processing_large_log_interval():
    docs = [TopicModelingDocument(document_id=str(i), source_item_id="s", text="TeXT!!!") for i in range(60)]
    config = TopicModelingLexicalProcessingConfig(
        enabled=True,
        lowercase=True,
        strip_punctuation=True,
        collapse_whitespace=True,
    )
    report, processed = topic_modeling._apply_lexical_processing(documents=docs, config=config)
    assert report.output_documents == 60
    assert all(doc.text == "text" for doc in processed)
