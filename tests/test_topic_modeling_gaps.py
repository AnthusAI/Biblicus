import json
import sys
import types
from pathlib import Path

import pytest

from biblicus.analysis import topic_modeling
from biblicus.analysis.models import (
    TopicModelingEntityRemovalConfig,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
)
from biblicus.analysis.topic_modeling import (
    TopicModelingDocument,
    _apply_entity_removal,
    _apply_llm_extraction,
    _parse_itemized_response,
)


class _DummyClient:
    pass


def test_topic_modeling_llm_single_empty_response(monkeypatch):
    config = TopicModelingLlmExtractionConfig(
        enabled=True,
        client={"provider": "mock", "model": "test-model"},
        prompt_template="{text}",
        method=TopicModelingLlmExtractionMethod.SINGLE,
    )
    documents = [TopicModelingDocument(document_id="d1", source_item_id="s1", text="alpha")]

    monkeypatch.setattr(topic_modeling, "generate_completion", lambda **_: "   ")

    with pytest.raises(ValueError):
        _apply_llm_extraction(documents=documents, config=config)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("[\"a\",\"b\"]", ["a", "b"]),
        ("[\\\"c\\\"]", ["c"]),
        ("not json", []),
    ],
)
def test_parse_itemized_response_variants(raw, expected):
    assert _parse_itemized_response(raw) == expected


def test_entity_removal_cache_path(tmp_path: Path):
    cache_path = tmp_path / "cache.jsonl"
    cache_path.write_text(json.dumps({"document_id": "d1", "source_item_id": "s1", "text": "t"}) + "\n")

    config = TopicModelingEntityRemovalConfig(enabled=True)
    report, docs = _apply_entity_removal(
        documents=[TopicModelingDocument("d1", "s1", "ignored")],
        config=config,
        cache_path=cache_path,
    )

    assert report.status.value == "complete"
    assert "Reused cached" in " ".join(report.warnings)
    assert [d.text for d in docs] == ["t"]


def test_entity_removal_with_regex_and_entities(monkeypatch):
    class FakeSpan:
        def __init__(self, start, end, label):
            self.start_char = start
            self.end_char = end
            self.label_ = label

    class FakeDoc:
        def __init__(self, text):
            self.text = text
            self.ents = [FakeSpan(0, 4, "PERSON")]

    def fake_load(model):  # noqa: ARG001
        return lambda text: FakeDoc(text)

    fake_spacy = types.SimpleNamespace(load=fake_load)
    monkeypatch.setitem(sys.modules, "spacy", fake_spacy)

    config = TopicModelingEntityRemovalConfig(
        enabled=True,
        replace_with="",
        regex_patterns=["", r"[0-9]"],
        regex_replace_with="",
    )
    report, processed = _apply_entity_removal(
        documents=[TopicModelingDocument("d1", "s1", "John 123 Doe")],
        config=config,
        cache_path=None,
    )

    assert report.status.value == "complete"
    assert processed[0].text == "Doe"
