from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import List

import pytest

from biblicus.graph import grobid_dedup
from biblicus.graph.extractors import ner_entities
from biblicus.graph.extractors.ner_entities import (
    NerEntitiesGraphConfig,
    NerEntitiesGraphExtractor,
)
from biblicus.graph.grobid_dedup import (
    grobid_blocked_surface_forms,
    grobid_structured_from_metadata,
    is_grobid_extraction_metadata,
    should_suppress_ner_entity,
)


class FakeSpacyEntity:
    """Test double: fake spacy entity."""

    def __init__(self, text: str, label: str, sentence_start: int) -> None:
        self.text = text
        self.label_ = label
        self.sent = SimpleNamespace(start=sentence_start)


class FakeSpacyEntityWithBrokenSentence:
    """Test double: fake spacy entity with broken sentence."""

    text = "Broken Sentence Org"
    label_ = "ORG"

    @property
    def sent(self):
        """Raise because sentence boundaries are unavailable."""
        raise RuntimeError("sentence boundaries unavailable")


class FakeSpacyDocument:
    """Test double: fake spacy document."""

    def __init__(self, entities) -> None:
        self.ents = entities


def install_fake_spacy_pipeline(monkeypatch, entities) -> None:
    """Install fake spacy pipeline."""
    monkeypatch.setattr(
        ner_entities,
        "_load_spacy_pipeline",
        lambda model_name: (lambda text: FakeSpacyDocument(entities)),
    )


def test_ner_validate_config_returns_parsed_configuration():
    """Verify ner validate config returns parsed configuration."""
    parsed = NerEntitiesGraphExtractor().validate_config({"model": "fake-model"})

    assert isinstance(parsed, NerEntitiesGraphConfig)
    assert parsed.include_relation_edges is False


def test_ner_extract_graph_builds_relation_edges_with_parsed_configuration(monkeypatch):
    """Verify ner extract graph builds relation edges with parsed configuration."""
    install_fake_spacy_pipeline(
        monkeypatch,
        [
            FakeSpacyEntity("Acme Corp", "ORG", 0),
            FakeSpacyEntity("Globex Inc", "ORG", 0),
            FakeSpacyEntity("Initech", "ORG", 0),
            FakeSpacyEntity("Acme Corp", "ORG", 10),
            FakeSpacyEntity("Globex Inc", "ORG", 10),
            FakeSpacyEntity("Paris", "GPE", 20),
            FakeSpacyEntity("Paris", "GPE", 20),
            FakeSpacyEntity("Ignored Label", "DATE", 0),
            FakeSpacyEntityWithBrokenSentence(),
        ],
    )
    parsed_configuration = NerEntitiesGraphConfig(
        model="fake-model",
        entity_labels=["ORG", "GPE"],
        include_item_node=False,
        include_relation_edges=True,
        min_relation_weight=2,
    )

    result = NerEntitiesGraphExtractor().extract_graph(
        corpus=SimpleNamespace(),
        item=SimpleNamespace(id="item-1", title=None, relpath="item.txt"),
        extracted_text="ignored",
        config=parsed_configuration,
    )

    labels = [node.label for node in result.nodes]
    assert "Ignored Label" not in labels
    assert "Broken Sentence Org" in labels
    relation_edges = [edge for edge in result.edges if edge.edge_type == "related_to"]
    assert [edge.edge_id for edge in relation_edges] == [
        "entity:acme_corp|related_to|entity:globex_inc"
    ]
    assert relation_edges[0].weight == 2.0
    assert relation_edges[0].properties == {"source": "sentence_cooccurrence"}


def test_ner_build_relation_edges_limits_entities_per_sentence():
    """Verify ner build relation edges limits entities per sentence."""
    edges = ner_entities._build_relation_edges(
        [("Alpha", "ORG", 0), ("Beta", "ORG", 0), ("Gamma", "ORG", 0)],
        max_entities_per_sentence=2,
        min_relation_weight=1,
    )

    assert [edge.edge_id for edge in edges] == ["entity:alpha|related_to|entity:beta"]


def test_ner_extract_entities_filters_labels_that_do_not_look_like_entities(monkeypatch):
    """Verify ner extract entities filters labels that do not look like entities."""
    install_fake_spacy_pipeline(
        monkeypatch,
        [
            FakeSpacyEntity("Line\nBreak", "ORG", 0),
            FakeSpacyEntity("Total,5", "ORG", 0),
            FakeSpacyEntity("J. Smith", "PERSON", 0),
            FakeSpacyEntity("12345", "CARDINAL", 0),
            FakeSpacyEntity("lowercase start", "ORG", 0),
            FakeSpacyEntity("Valid Entity", "ORG", 0),
        ],
    )

    entities = ner_entities._extract_entities(
        extracted_text="ignored",
        model_name="fake-model",
        min_length=3,
        max_length=120,
        entity_labels=None,
    )

    assert entities == [("Valid Entity", "ORG", 0)]


def test_ner_entity_sentence_index_defaults_when_sentence_lookup_fails():
    """Verify ner entity sentence index defaults when sentence lookup fails."""
    assert ner_entities._entity_sentence_index(FakeSpacyEntityWithBrokenSentence()) == 0


def test_ner_load_spacy_pipeline_loads_once_and_caches(monkeypatch):
    """Verify ner load spacy pipeline loads once and caches."""
    load_requests: List[str] = []
    fake_spacy_module = ModuleType("spacy")

    def fake_load(model_name):
        """Record the requested model and return a fake pipeline."""
        load_requests.append(model_name)
        return f"pipeline:{model_name}"

    fake_spacy_module.load = fake_load
    monkeypatch.setitem(sys.modules, "spacy", fake_spacy_module)
    monkeypatch.setattr(ner_entities, "_SPACY_PIPELINE_CACHE", {})

    first = ner_entities._load_spacy_pipeline("fake-model")
    second = ner_entities._load_spacy_pipeline("fake-model")

    assert first == second == "pipeline:fake-model"
    assert load_requests == ["fake-model"]


def test_ner_load_spacy_pipeline_reports_missing_dependency(monkeypatch):
    """Verify ner load spacy pipeline reports missing dependency."""
    monkeypatch.setitem(sys.modules, "spacy", None)
    monkeypatch.setattr(ner_entities, "_SPACY_PIPELINE_CACHE", {})

    with pytest.raises(ValueError, match="requires spaCy"):
        ner_entities._load_spacy_pipeline("fake-model")


@pytest.mark.parametrize(
    "metadata, expected",
    [
        (None, False),
        ({"method": "llm-html"}, True),
        ({"structured": {"authors": [{"name": "A"}]}}, True),
        ({"structured": {"citations": []}}, False),
        ({"urlExtraction": {"structured": {"citations": [{"title": "T"}]}}}, True),
        ({"urlExtraction": {"structured": {"authors": []}}}, False),
        ({"urlExtraction": {"structured": "not-a-mapping"}}, False),
        ({"urlExtraction": "not-a-mapping"}, False),
    ],
)
def test_is_grobid_extraction_metadata_detects_structured_sources(metadata, expected):
    """Verify is grobid extraction metadata detects structured sources."""
    assert is_grobid_extraction_metadata(metadata) is expected


def test_grobid_structured_from_metadata_resolves_each_location():
    """Verify grobid structured from metadata resolves each location."""
    direct = {"authors": [{"name": "A"}]}
    nested = {"citations": [{"title": "T"}]}

    assert grobid_structured_from_metadata(None) == {}
    assert grobid_structured_from_metadata({"structured": direct}) is direct
    assert grobid_structured_from_metadata({"urlExtraction": {"structured": nested}}) is nested
    assert grobid_structured_from_metadata({"urlExtraction": {"structured": []}}) == {}
    assert grobid_structured_from_metadata({"method": "grobid"}) == {}


def test_grobid_blocked_surface_forms_collects_authors_dates_and_citations():
    """Verify grobid blocked surface forms collects authors dates and citations."""
    blocked = grobid_blocked_surface_forms(
        {
            "authors": [
                "not-a-mapping",
                {"name": "Ada Lovelace", "normalized_name": "lovelace, ada"},
                {"name": None},
            ],
            "publication_date": "2024-05-01",
            "publication_date_raw": "May 2024",
            "citations": [
                "not-a-mapping",
                {"title": "Analytical Engines", "raw": "!!!", "authors": ["Charles Babbage", None]},
                {"title": "Notes", "authors": "Single String Author"},
            ],
        }
    )

    assert {"ada lovelace", "lovelace ada", "ada", "lovelace"} <= blocked
    assert {"2024 05 01", "may 2024", "may"} <= blocked
    assert {"analytical engines", "charles babbage", "babbage", "notes"} <= blocked
    assert "single string author" not in blocked


def test_grobid_blocked_surface_forms_handles_missing_lists_and_short_tokens():
    """Verify grobid blocked surface forms handles missing lists and short tokens."""
    assert grobid_blocked_surface_forms({"authors": "nope", "citations": None}) == set()
    assert grobid_blocked_surface_forms({"authors": [{"name": "X"}]}) == {"x"}


def test_should_suppress_ner_entity_rules():
    """Verify should suppress ner entity rules."""
    blocked_forms = {"ada lovelace", "Lovelace"}

    assert (
        should_suppress_ner_entity(label="!!!", entity_type="ORG", blocked_forms=blocked_forms)
        is False
    )
    assert (
        should_suppress_ner_entity(
            label="Ada Lovelace", entity_type="WORK_OF_ART", blocked_forms=blocked_forms
        )
        is True
    )
    assert (
        should_suppress_ner_entity(label="Lovelace", entity_type="ORG", blocked_forms=blocked_forms)
        is True
    )
    assert (
        should_suppress_ner_entity(label="Lovelace", entity_type="GPE", blocked_forms=blocked_forms)
        is False
    )
    assert (
        should_suppress_ner_entity(label="Babbage", entity_type="PERSON", blocked_forms={"", "x y"})
        is False
    )


def test_add_blocked_phrase_ignores_blank_values():
    """Verify add blocked phrase ignores blank values."""
    blocked: set[str] = set()

    grobid_dedup._add_blocked_phrase(blocked, "   ")

    assert blocked == set()


def test_ner_extract_graph_emits_item_node_mentions_and_grobid_suppression(monkeypatch):
    """Verify ner extract graph emits item node mentions and grobid suppression."""
    install_fake_spacy_pipeline(
        monkeypatch,
        [
            FakeSpacyEntity("Ada Lovelace", "PERSON", 0),
            FakeSpacyEntity("Royal Society", "ORG", 0),
            FakeSpacyEntity("Royal Society", "ORG", 5),
            FakeSpacyEntity("An Extremely Long Organisation Name", "ORG", 5),
        ],
    )

    result = NerEntitiesGraphExtractor().extract_graph(
        corpus=SimpleNamespace(),
        item=SimpleNamespace(id="item-1", title=None, relpath="notes/item.txt"),
        extracted_text="ignored",
        config={"model": "fake-model", "max_entity_length": 20},
        extraction_metadata={
            "method": "grobid",
            "structured": {"authors": [{"name": "Ada Lovelace"}]},
        },
    )

    assert [node.node_id for node in result.nodes] == ["item:item-1", "entity:royal_society"]
    assert result.nodes[0].label == "notes/item.txt"
    assert result.nodes[1].properties == {"canonical": "royal_society", "entity_type": "ORG"}
    assert [(edge.edge_id, edge.weight) for edge in result.edges] == [
        ("item:item-1|mentions|entity:royal_society", 2.0)
    ]


def test_ner_canonicalize_keeps_lowercased_label_when_only_symbols():
    """Verify ner canonicalize keeps lowercased label when only symbols."""
    assert ner_entities._canonicalize("+++") == "+++"


def test_should_suppress_ner_entity_keeps_unmatched_person_labels():
    """Verify should suppress ner entity keeps unmatched person labels."""
    assert (
        should_suppress_ner_entity(
            label="Lovelace", entity_type="PERSON", blocked_forms={"babbage", "byron"}
        )
        is False
    )


def test_graph_extractor_registry_rejects_unknown_identifier():
    """Verify graph extractor registry rejects unknown identifier."""
    from biblicus.graph.extractors import available_graph_extractors, get_graph_extractor

    assert "ner-entities" in available_graph_extractors()
    assert isinstance(get_graph_extractor("ner-entities"), NerEntitiesGraphExtractor)
    with pytest.raises(KeyError, match="Unknown graph extractor 'missing'"):
        get_graph_extractor("missing")


def test_graph_extractor_base_methods_raise_not_implemented():
    """Verify graph extractor base methods raise not implemented."""
    from biblicus.graph.base import GraphExtractor

    class DelegatingGraphExtractor(GraphExtractor):
        """Test double: delegating graph extractor."""

        extractor_id = "delegating"

        def validate_config(self, config):
            """Validate the configuration with the strict dummy model."""
            return super().validate_config(config)

        def extract_graph(self, **kwargs):
            """Return the next scripted extraction behavior for the item."""
            return super().extract_graph(**kwargs)

    extractor = DelegatingGraphExtractor()
    with pytest.raises(NotImplementedError):
        extractor.validate_config({})
    with pytest.raises(NotImplementedError):
        extractor.extract_graph(
            corpus=SimpleNamespace(),
            item=SimpleNamespace(),
            extracted_text="",
            config=SimpleNamespace(),
        )


def test_graph_snapshot_reference_parsing_and_serialization():
    """Verify graph snapshot reference parsing and serialization."""
    from biblicus.graph.models import GraphSnapshotReference, parse_graph_snapshot_reference

    reference = parse_graph_snapshot_reference(" ner-entities : snap ")
    assert reference == GraphSnapshotReference(extractor_id="ner-entities", snapshot_id="snap")
    assert reference.as_string() == "ner-entities:snap"
    with pytest.raises(ValueError, match="must be extractor_id:snapshot_id$"):
        parse_graph_snapshot_reference("missing-separator")
    with pytest.raises(ValueError, match="non-empty parts"):
        parse_graph_snapshot_reference("ner-entities: ")
