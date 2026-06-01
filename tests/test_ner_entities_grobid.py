"""Tests for NER graph extraction with GROBID deduplication."""

from __future__ import annotations

from types import SimpleNamespace

from biblicus.graph.extractors import ner_entities


class _FakeEnt:
    def __init__(self, text: str, label: str) -> None:
        self.text = text
        self.label_ = label
        self.sent = SimpleNamespace(start=0)


class _FakeDoc:
    def __init__(self, ents) -> None:
        self.ents = ents


def test_extract_entities_suppresses_grobid_authors(monkeypatch):
    def fake_nlp(_text):
        return _FakeDoc(
            [
                _FakeEnt("Alice Wang", "PER"),
                _FakeEnt("Stanford University", "ORG"),
                _FakeEnt("Wang", "ORG"),
            ]
        )

    monkeypatch.setattr(
        "biblicus.graph.extractors.ner_entities._load_spacy_pipeline",
        lambda _name: fake_nlp,
    )

    blocked = {"alice wang", "wang"}
    entities = ner_entities._extract_entities(
        extracted_text="ignored",
        model_name="fake",
        min_length=2,
        max_length=120,
        entity_labels=["PER", "ORG"],
        grobid_blocked_forms=blocked,
    )
    labels = {text for text, _label, _idx in entities}
    assert "Alice Wang" not in labels
    assert "Wang" not in labels
    assert "Stanford University" in labels


def test_extract_graph_passes_grobid_blocked_forms_when_metadata_present(monkeypatch):
    captured: dict = {}

    def fake_extract(**kwargs):
        captured.update(kwargs)
        return [("Stanford University", "ORG", 0)]

    monkeypatch.setattr(ner_entities, "_extract_entities", fake_extract)
    extractor = ner_entities.NerEntitiesGraphExtractor()
    extractor.extract_graph(
        corpus=SimpleNamespace(),
        item=SimpleNamespace(id="i1", title="t", relpath="r"),
        extracted_text="Alice Wang works at Stanford University.",
        config={
            "model": "en",
            "min_entity_length": 2,
            "include_item_node": False,
            "include_relation_edges": False,
        },
        extraction_metadata={
            "method": "grobid",
            "structured": {"authors": [{"name": "Alice Wang"}], "citations": []},
        },
    )
    blocked = captured.get("grobid_blocked_forms")
    assert blocked is not None
    assert "alice wang" in blocked
    assert "wang" in blocked


def test_extract_graph_omits_grobid_blocked_forms_without_grobid_metadata(monkeypatch):
    captured: dict = {}

    def fake_extract(**kwargs):
        captured.update(kwargs)
        return [("OpenAI", "ORG", 0)]

    monkeypatch.setattr(ner_entities, "_extract_entities", fake_extract)
    extractor = ner_entities.NerEntitiesGraphExtractor()
    extractor.extract_graph(
        corpus=SimpleNamespace(),
        item=SimpleNamespace(id="i1", title="t", relpath="r"),
        extracted_text="OpenAI builds models.",
        config={
            "model": "en",
            "min_entity_length": 2,
            "include_item_node": False,
            "include_relation_edges": False,
        },
        extraction_metadata=None,
    )
    assert captured.get("grobid_blocked_forms") is None
