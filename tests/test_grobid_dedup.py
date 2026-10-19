"""Tests for GROBID-aware spaCy NER deduplication."""

from __future__ import annotations

from biblicus.graph.grobid_dedup import (
    grobid_blocked_surface_forms,
    is_grobid_extraction_metadata,
    should_suppress_ner_entity,
)


def test_is_grobid_extraction_metadata_method_flag():
    assert is_grobid_extraction_metadata({"method": "grobid"}) is True
    assert is_grobid_extraction_metadata({"method": "llm-html"}) is True
    assert is_grobid_extraction_metadata({"method": "pypdf"}) is False
    assert is_grobid_extraction_metadata({"method": "pypdf-fallback"}) is False


def test_is_grobid_extraction_metadata_structured_authors():
    assert is_grobid_extraction_metadata(
        {"structured": {"authors": [{"name": "Jane Doe"}]}}
    ) is True


def test_grobid_blocked_surface_forms_includes_author_and_citation_tokens():
    structured = {
        "authors": [{"name": "Alice Wang", "normalized_name": "wang alice"}],
        "citations": [
            {
                "title": "Deep Learning for NLP",
                "raw": "Deep Learning for NLP (2020)",
                "authors": ["Bob Smith"],
            }
        ],
    }
    blocked = grobid_blocked_surface_forms(structured)
    assert "alice wang" in blocked
    assert "wang" in blocked
    assert "deep learning for nlp" in blocked
    assert "bob smith" in blocked


def test_should_suppress_ner_entity_exact_author_match():
    blocked = grobid_blocked_surface_forms(
        {"authors": [{"name": "Yann LeCun"}], "citations": []}
    )
    assert should_suppress_ner_entity(
        label="Yann LeCun", entity_type="PER", blocked_forms=blocked
    )
    assert not should_suppress_ner_entity(
        label="Geoffrey Hinton", entity_type="PER", blocked_forms=blocked
    )


def test_should_suppress_ner_entity_mislabeled_org_surname():
    blocked = grobid_blocked_surface_forms(
        {"authors": [{"name": "Zhang Wei"}], "citations": []}
    )
    assert should_suppress_ner_entity(
        label="Zhang", entity_type="ORG", blocked_forms=blocked
    )


def test_should_suppress_ner_entity_citation_title():
    blocked = grobid_blocked_surface_forms(
        {
            "authors": [],
            "citations": [{"title": "Attention Is All You Need", "raw": "", "authors": []}],
        }
    )
    assert should_suppress_ner_entity(
        label="Attention Is All You Need",
        entity_type="WORK_OF_ART",
        blocked_forms=blocked,
    )
