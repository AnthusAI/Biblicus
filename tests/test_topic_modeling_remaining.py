import sys
import types

import pytest

from biblicus.analysis.topic_modeling import (
    TopicModelingDocument,
    _apply_entity_removal,
    _apply_llm_extraction,
)
from biblicus.analysis.models import (
    TopicModelingEntityRemovalConfig,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
)


def test_entity_removal_provider_not_spacy_validates():
    config = TopicModelingEntityRemovalConfig(enabled=True, provider="spacy")
    # ensure no exception when provider is correct
    assert config.provider == "spacy"


def test_entity_removal_logs_progress_large(monkeypatch, capsys):
    docs = [TopicModelingDocument(str(i), "s", "text") for i in range(1200)]

    class FakeDoc:
        def __init__(self, text):
            self.text = text
            self.ents = []

    def fake_load(model):  # noqa: ARG001
        return lambda text: FakeDoc(text)

    fake_spacy = types.SimpleNamespace(load=fake_load)
    monkeypatch.setitem(sys.modules, "spacy", fake_spacy)

    config = TopicModelingEntityRemovalConfig(enabled=True)
    report, processed = _apply_entity_removal(documents=docs, config=config, cache_path=None)
    assert report.status.value == "complete"
    assert len(processed) == 1200
    captured = capsys.readouterr()
    assert "topic-modeling" in captured.err


def test_llm_itemized_empty_raises(monkeypatch):
    docs = [TopicModelingDocument("d1", "s1", "alpha"), TopicModelingDocument("d2", "s2", "beta")]
    config = TopicModelingLlmExtractionConfig(
        enabled=True,
        client={"provider": "mock", "model": "m"},
        prompt_template="{text}",
        method=TopicModelingLlmExtractionMethod.ITEMIZE,
    )
    monkeypatch.setattr(
        "biblicus.analysis.topic_modeling.generate_completion",
        lambda **_: "\n\n",
    )
    with pytest.raises(ValueError):
        _apply_llm_extraction(documents=docs, config=config)
