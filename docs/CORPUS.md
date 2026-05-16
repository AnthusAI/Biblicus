# Corpus

A corpus is a normal folder on disk. It is the source of truth for your raw items.

The main goals are:

- You can ingest an item once and keep it as a file you can open and inspect.
- You can rebuild the catalog at any time.
- You can add derived artifacts later without changing the raw corpus.

## On disk layout

```
corpus/
  metadata/
    config.json
    catalog.json
  extracted/
    <extractor>/<snapshot_id>/...
    <extractor>/latest.json
  graph/
    <extractor>/<snapshot_id>/...
    <extractor>/latest.json
  retrieval/
    <backend_id>/<snapshot_id>/...
    <backend_id>/latest.json
  analysis/
    <analysis_id>/<snapshot_id>/...
    <analysis_id>/latest.json
  <raw files and folders>
  <sidecars next to raw files> *.biblicus.yml
```

## Core concepts

- **Item**: raw bytes plus metadata and provenance.
- **Catalog**: the inventory of items and their metadata.
- **Snapshot**: a reproducible snapshot of derived artifacts (extraction, retrieval, analysis).

The corpus is designed so the raw items remain the source of truth and everything else can be rebuilt.

## Ingest items

The simplest ingestion flows use the command line interface.

Create a corpus:

```
python -m biblicus init corpora/example
```

Ingest a local file:

```
python -m biblicus ingest --corpus corpora/example path/to/file.pdf --tag paper
```

Local file ingestion requires the file to live under the corpus root. If it is outside, move it into the corpus and run `reindex`.

Ingest a web address:

```
python -m biblicus ingest --corpus corpora/example https://example.com --tag web
```

## Remote corpus sources

A corpus can mirror a remote storage source as its authoritative input. When configured, the corpus is refreshed by pulling from the remote source, and local ingest is disabled.

If a remote root contains **many subfolders** that should each become a corpus, use **collections** instead of configuring a single corpus. See `docs/collections.md`.
If you want one file to run extraction, retrieval, and analysis for a corpus or collection, see `docs/pipeline-recipes.md`.

Example corpus config (`metadata/config.json`):

```json
{
  "schema_version": 2,
  "created_at": "2026-02-19T12:00:00Z",
  "corpus_uri": "file:///path/to/corpus",
  "raw_dir": ".",
  "source": {
    "kind": "s3",
    "profile": "s3-archive",
    "name": "client-archive",
    "bucket": "client-archive",
    "prefix": "exports/"
  }
}
```

Pull and mirror the remote source:

```
python -m biblicus source pull --corpus corpora/example
```

Remote items are stored under:

```
imports/remote/<source_name>/<remote_key>
```

## Crawl a website prefix

To build a corpus from a website section, crawl a root uniform resource locator and restrict the crawl to an allowed prefix.

```
python -m biblicus crawl --corpus corpora/example \\
  --root-url https://example.com/docs/index.html \\
  --allowed-prefix https://example.com/docs/ \\
  --max-items 50 \\
  --tag crawled
```

The crawl command only follows links within the allowed prefix, and it respects `.biblicusignore` patterns against the path relative to the allowed prefix.

Ingest a text note:

```
python -m biblicus ingest --corpus corpora/example --note "Hello" --title "First note" --tag notes
```

List items:

```
python -m biblicus list --corpus corpora/example
```

Show an item:

```
python -m biblicus show --corpus corpora/example ITEM_ID
```

## Metadata

Metadata is intentionally simple and file based.

For Markdown items, metadata lives in a YAML front matter block.

For non Markdown items, metadata lives in a sidecar file with the suffix `.biblicus.yml`.

The raw file and its metadata file are meant to be opened, edited, and backed up with ordinary tools.

### Metadata example (Markdown)

```
---
title: Example note
tags: [demo, notes]
---
This is the body of the note.
```

### Metadata example (sidecar)

```
title: Example PDF
tags:
  - paper
  - reports
```

## Standard single-item ingest

Use `biblicus ingest` when another tool has already retrieved the item and prepared curated metadata.

```
python -m biblicus ingest --corpus corpora/example paper.pdf \
  --metadata-file paper.metadata.yml \
  --source-uri https://example.test/paper \
  --published-at 2026-05-15 \
  --tag paper
```

The metadata file must be a YAML or JSON object.

```
title: Example PDF
abstract: A short summary.
authors:
  - Ada Lovelace
dates:
  published_at: "2026-05-15"
date_provenance:
  published_at: "source-metadata"
```

Biblicus stores the raw item, writes the `.biblicus.yml` sidecar, records the `biblicus.id` and `biblicus.source` provenance block, and updates the catalog. Retrieval, download, and metadata enrichment happen before this command.
Trend analysis should use `dates.published_at`, not ingest `created_at`, retrieval time, or legacy top-level publication metadata.

Verify the stored item with:

```
python -m biblicus show --corpus corpora/example ITEM_ID
```

## Ignore rules

If you are importing a folder tree, ignore rules can prevent accidental ingestion of build artifacts, caches, or other irrelevant files.

Create a `.biblicusignore` file in the corpus root and add ignore patterns.

## Import a folder tree

To ingest an existing folder tree into a corpus while preserving relative paths, place the folder tree under the corpus root and use the import command.

```
python -m biblicus import-tree --corpus corpora/example /path/to/folder/tree --tag imported
```

## Reindex

The catalog is rebuildable. If you edit files or sidecar metadata, refresh the catalog.

```
python -m biblicus reindex --corpus corpora/example
```

## Reproducibility checklist

- Keep raw files and sidecars in source control or backed up as immutable inputs.
- Record the catalog timestamp when comparing snapshot outputs.
- Prefer `import-tree` for reproducible ingest of existing folder structures.

## Common pitfalls

- Editing raw files without running `reindex` (catalog becomes stale).
- Renaming raw files directly without updating sidecars.
- Comparing runs built from different catalog states.

## Purge

Purging deletes all items and derived artifacts under the corpus. It requires you to type the corpus name as confirmation.

```
python -m biblicus purge --corpus corpora/example --confirm example
```
