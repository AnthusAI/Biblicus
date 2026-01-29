# Corpus

A corpus is a normal folder on disk. It is the source of truth for your raw items.

The main goals are:

- You can ingest an item once and keep it as a file you can open and inspect.
- You can rebuild the catalog at any time.
- You can add derived artifacts later without changing the raw corpus.

## On disk layout

```
corpus/
  raw/
    <item files>
  .biblicus/
    config.json
    catalog.json
    runs/
      <run manifests and artifacts>
```

## Ingest items

The simplest ingestion flows use the command line interface.

Create a corpus:

```
python3 -m biblicus init corpora/example
```

Ingest a local file:

```
python3 -m biblicus ingest --corpus corpora/example path/to/file.pdf --tag paper
```

Ingest a web address:

```
python3 -m biblicus ingest --corpus corpora/example https://example.com --tag web
```

## Crawl a website prefix

To build a corpus from a website section, crawl a root uniform resource locator and restrict the crawl to an allowed prefix.

```
python3 -m biblicus crawl --corpus corpora/example \\
  --root-url https://example.com/docs/index.html \\
  --allowed-prefix https://example.com/docs/ \\
  --max-items 50 \\
  --tag crawled
```

The crawl command only follows links within the allowed prefix, and it respects `.biblicusignore` patterns against the path relative to the allowed prefix.

Ingest a text note:

```
python3 -m biblicus ingest --corpus corpora/example --note "Hello" --title "First note" --tag notes
```

List items:

```
python3 -m biblicus list --corpus corpora/example
```

Show an item:

```
python3 -m biblicus show --corpus corpora/example ITEM_ID
```

## Metadata

Metadata is intentionally simple and file based.

For Markdown items, metadata lives in a YAML front matter block.

For non Markdown items, metadata lives in a sidecar file with the suffix `.biblicus.yml`.

The raw file and its metadata file are meant to be opened, edited, and backed up with ordinary tools.

## Ignore rules

If you are importing a folder tree, ignore rules can prevent accidental ingestion of build artifacts, caches, or other irrelevant files.

Create a `.biblicusignore` file in the corpus root and add ignore patterns.

## Import a folder tree

To ingest an existing folder tree into a corpus while preserving relative paths, use the import command.

```
python3 -m biblicus import-tree --corpus corpora/example /path/to/folder/tree --tag imported
```

## Reindex

The catalog is rebuildable. If you edit files or sidecar metadata, refresh the catalog.

```
python3 -m biblicus reindex --corpus corpora/example
```

## Purge

Purging deletes all items and derived artifacts under the corpus. It requires you to type the corpus name as confirmation.

```
python3 -m biblicus purge --corpus corpora/example --confirm example
```
