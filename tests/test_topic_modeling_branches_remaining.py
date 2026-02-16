import json
import types
from pathlib import Path

import pytest

from biblicus.analysis import topic_modeling as tm
from biblicus.analysis.models import (
    TopicModelingConfiguration,
    TopicModelingEntityRemovalConfig,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
)
from biblicus.analysis.topic_modeling import TopicModelingDocument


def test_entity_removal_provider_validation():
    config = TopicModelingEntityRemovalConfig.model_construct(
        enabled=True,
        provider="other",
        model="en_core_web_sm",
        entity_types=[],
        regex_patterns=[],
        regex_replace_with="",
        collapse_whitespace=False,
        replace_with=None,
    )
    with pytest.raises(ValueError):
        tm._apply_entity_removal(documents=[], config=config, cache_path=None)


def test_entity_removal_uses_cached_documents(tmp_path):
    cache = tmp_path / "cache.jsonl"
    cache.write_text(json.dumps({"document_id": "d1", "source_item_id": "s1", "text": "text"}) + "\n", encoding="utf-8")
    config = TopicModelingEntityRemovalConfig(enabled=True)
    report, processed = tm._apply_entity_removal(documents=[], config=config, cache_path=cache)
    assert report.status.value == "complete"
    assert processed and processed[0].text == "text"


def test_parse_itemized_response_handles_unescaped_json():
    payload = '[{\\"text\\":\\"a\\"}]'
    result = tm._parse_itemized_response(payload)
    assert result == []


def test_llm_extraction_logs_and_skips_empty(monkeypatch, capsys):
    docs = [TopicModelingDocument("d1", "s1", "alpha")]
    config = TopicModelingLlmExtractionConfig(
        enabled=True,
        client={"provider": "mock", "model": "m"},
        prompt_template="{text}",
        method=TopicModelingLlmExtractionMethod.SINGLE,
    )

    # return empty string to exercise empty path and logging cadence
    monkeypatch.setattr(tm, "generate_completion", lambda **kwargs: " ")
    with pytest.raises(ValueError):
        tm._apply_llm_extraction(documents=docs, config=config)
