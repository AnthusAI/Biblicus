from __future__ import annotations

import importlib.util

import pytest

from biblicus.graph.extractors.ner_entities import NerEntitiesGraphExtractor
from biblicus.graph.reference_anchor import (
    build_reference_anchor_node,
    reference_title_blocked_forms,
    should_suppress_reference_title,
)
from biblicus.models import CatalogItem
from biblicus.corpus import Corpus


def _catalog_item(**overrides) -> CatalogItem:
    payload = {
        "id": "paper-1",
        "relpath": "raw/paper.pdf",
        "sha256": "abc",
        "bytes": 1,
        "media_type": "application/pdf",
        "title": "Donut: Document Understanding Transformer",
        "tags": [],
        "metadata": {},
        "created_at": "now",
        "source_uri": "file://paper.pdf",
    }
    payload.update(overrides)
    return CatalogItem(**payload)


def test_build_reference_anchor_node_uses_reference_type() -> None:
    item = _catalog_item()
    node = build_reference_anchor_node(item)
    assert node.node_id == "reference:paper-1"
    assert node.node_type == "reference"
    assert node.label == item.title
    assert node.properties["reference_id"] == "paper-1"
    assert node.properties["item_id"] == "paper-1"


def test_reference_title_blocked_forms_includes_title_and_stem() -> None:
    item = _catalog_item(title="AlphaGeometry2.pdf", relpath="raw/AlphaGeometry2.pdf")
    blocked = reference_title_blocked_forms(item)
    assert "alphageometry2.pdf" in blocked
    assert "alphageometry2" in blocked


def test_should_suppress_reference_title_matches_case_insensitive() -> None:
    blocked = {"donut: document understanding transformer"}
    assert should_suppress_reference_title("Donut: Document Understanding Transformer", blocked)


@pytest.mark.skipif(importlib.util.find_spec("spacy") is None, reason="spaCy not installed")
def test_ner_entities_emits_reference_anchor_not_item_node(tmp_path) -> None:
    extractor = NerEntitiesGraphExtractor()
    item = _catalog_item()
    corpus = Corpus(tmp_path)
    result = extractor.extract_graph(
        corpus=corpus,
        item=item,
        extracted_text="OpenAI published GPT-4 in San Francisco.",
        config={"model": "en_core_web_sm", "min_entity_length": 2, "include_item_node": True},
    )
    anchor_nodes = [node for node in result.nodes if node.node_type == "reference"]
    item_nodes = [node for node in result.nodes if node.node_type == "item"]
    assert len(anchor_nodes) == 1
    assert anchor_nodes[0].node_id == "reference:paper-1"
    assert item_nodes == []
    assert all(edge.src == "reference:paper-1" for edge in result.edges if edge.edge_type == "mentions")


@pytest.mark.skipif(importlib.util.find_spec("spacy") is None, reason="spaCy not installed")
def test_ner_entities_suppresses_reference_title_as_entity(tmp_path) -> None:
    extractor = NerEntitiesGraphExtractor()
    item = _catalog_item(title="ResNet", relpath="raw/resnet.pdf")
    corpus = Corpus(tmp_path)
    result = extractor.extract_graph(
        corpus=corpus,
        item=item,
        extracted_text="ResNet introduced residual connections for deep networks.",
        config={"model": "en_core_web_sm", "min_entity_length": 2, "include_item_node": True},
    )
    entity_labels = {node.label for node in result.nodes if node.node_type == "entity"}
    assert "ResNet" not in entity_labels
