from __future__ import annotations

import pytest

from biblicus.catalog_compat import (
    load_corpus_catalog,
    sanitize_catalog_item_payload,
    sanitize_catalog_payload,
)


def test_sanitize_catalog_item_payload_rejects_non_mapping():
    """Verify sanitize catalog item payload rejects non mapping."""
    with pytest.raises(TypeError, match="Catalog item payload must be a mapping"):
        sanitize_catalog_item_payload(["not", "a", "mapping"])


def test_sanitize_catalog_item_payload_merges_nested_extension_dictionaries():
    """Verify sanitize catalog item payload merges nested extension dictionaries."""
    sanitized = sanitize_catalog_item_payload(
        {
            "id": "item-1",
            "papyrus": {"rating": 4},
            "summary": "Root summary",
            "metadata": {"papyrus": {"title": "Kept"}, "summary": {"replaced": True}},
        }
    )

    assert sanitized["id"] == "item-1"
    assert sanitized["metadata"]["papyrus"] == {"title": "Kept", "rating": 4}
    assert sanitized["metadata"]["summary"] == "Root summary"


def test_sanitize_catalog_item_payload_replaces_non_mapping_metadata():
    """Verify sanitize catalog item payload replaces non mapping metadata."""
    sanitized = sanitize_catalog_item_payload({"id": "item-1", "metadata": "corrupt"})

    assert sanitized == {"id": "item-1", "metadata": {}}


def test_sanitize_catalog_payload_rejects_non_mapping():
    """Verify sanitize catalog payload rejects non mapping."""
    with pytest.raises(TypeError, match="Catalog payload must be a mapping"):
        sanitize_catalog_payload("not-a-mapping")


def test_sanitize_catalog_payload_leaves_non_mapping_items_untouched():
    """Verify sanitize catalog payload leaves non mapping items untouched."""
    payload = {"schema_version": 2, "items": ["unexpected"]}

    assert sanitize_catalog_payload(payload) == payload


def test_sanitize_catalog_payload_drops_non_mapping_item_entries():
    """Verify sanitize catalog payload drops non mapping item entries."""
    sanitized = sanitize_catalog_payload(
        {"items": {"item-1": {"id": "item-1", "extra": 1}, "item-2": "corrupt"}}
    )

    assert sanitized["items"] == {"item-1": {"id": "item-1", "metadata": {"extra": 1}}}


def test_load_corpus_catalog_validates_sanitized_catalog():
    """Verify load corpus catalog validates sanitized catalog."""
    catalog = load_corpus_catalog(
        {
            "schema_version": 2,
            "generated_at": "2026-05-01T00:00:00Z",
            "corpus_uri": "file:///tmp/demo",
            "raw_dir": "raw",
            "items": {},
            "order": [],
        }
    )

    assert catalog.items == {}
