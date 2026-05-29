from biblicus.catalog_compat import load_corpus_catalog, sanitize_catalog_item_payload


def test_sanitize_catalog_item_payload_folds_foreign_root_fields() -> None:
    sanitized = sanitize_catalog_item_payload(
        {
            "id": "item-1",
            "relpath": "raw/paper.pdf",
            "sha256": "abc",
            "bytes": 10,
            "media_type": "application/pdf",
            "created_at": "2026-05-01T00:00:00Z",
            "title": "Paper title",
            "identifiers": {"doi": "10.1234/example"},
            "papyrus": {"quality_rating": {"rating": 4}},
            "summary": "Short summary",
            "metadata": {"authors": ["Ada Lovelace"]},
        }
    )
    assert sanitized["title"] == "Paper title"
    assert "identifiers" not in sanitized
    assert "papyrus" not in sanitized
    assert "summary" not in sanitized
    assert sanitized["metadata"]["authors"] == ["Ada Lovelace"]
    assert sanitized["metadata"]["identifiers"] == {"doi": "10.1234/example"}
    assert sanitized["metadata"]["papyrus"] == {"quality_rating": {"rating": 4}}
    assert sanitized["metadata"]["summary"] == "Short summary"


def test_load_corpus_catalog_accepts_extension_polluted_items() -> None:
    catalog = load_corpus_catalog(
        {
            "schema_version": 2,
            "generated_at": "2026-05-01T00:00:00Z",
            "corpus_uri": "file:///tmp/demo",
            "raw_dir": "raw",
            "items": {
                "item-1": {
                    "id": "item-1",
                    "relpath": "raw/paper.pdf",
                    "sha256": "abc",
                    "bytes": 10,
                    "media_type": "application/pdf",
                    "created_at": "2026-05-01T00:00:00Z",
                    "papyrus": {"title_subtitle": {"summary": "Editorial summary"}},
                }
            },
            "order": ["item-1"],
        }
    )
    item = catalog.items["item-1"]
    assert item.metadata["papyrus"]["title_subtitle"]["summary"] == "Editorial summary"
