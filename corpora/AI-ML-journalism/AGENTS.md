# AI-ML-Journalism Corpus Agent Notes

This corpus stores journalism, court records, public records, and primary-source documents about artificial intelligence and machine learning in public life. Use it for material that helps explain how AI and machine learning systems are built, governed, funded, contested, reported, or audited.

## Add One New Item

Prefer source-specific URL ingestion when the source platform has a Biblicus resolver. DocumentCloud URLs should be ingested from the viewer URL when available:

```bash
biblicus ingest \
  --corpus corpora/AI-ML-journalism \
  --import-rationale "Explain why this item matters to AI and machine learning journalism." \
  https://www.documentcloud.org/documents/example-document/
```

Every manually imported item must include `--import-rationale`. The rationale should explain why the item is relevant to the knowledge base, not just summarize the document.

## Verify The Item

After ingesting, reindex and inspect the item:

```bash
biblicus reindex --corpus corpora/AI-ML-journalism
biblicus show --corpus corpora/AI-ML-journalism <item-id>
```

For DocumentCloud items, verify that metadata includes `source_resolution.identity_key`, `source_resolution.raw_asset_uri`, `source_resolution.derived_assets.full_text_uri`, and `curation.import_rationale`.

## Extract Text

Use the source-provided text recipe for platforms that advertise derived text assets:

```bash
biblicus extract build \
  --corpus corpora/AI-ML-journalism \
  --configuration-name ai-ml-journalism-source-text \
  --configuration configurations/extraction/ai-ml-journalism-source-text.yml
```
