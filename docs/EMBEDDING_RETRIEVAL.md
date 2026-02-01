# Embedding Retrieval

Embedding retrieval turns a large collection of text into a reusable index that can be queried efficiently.

Biblicus supports embedding retrieval through backends that:

1) chunk extracted text,
2) compute embeddings for each chunk,
3) build an index under the corpus as run artifacts, and
4) return evidence with chunk provenance on query.

## Concepts

- **Chunking**: the unit of embedding and retrieval. See `docs/CHUNKING.md`.
- **Embedding provider**: a pluggable implementation that turns text into vectors.
- **Embedding index backend**: a retrieval backend that materializes vectors and supports similarity search.

## A local, textbook embedding index

Biblicus provides two embedding index backends that avoid external services:

- `embedding-index-inmemory` for small demos with safety caps
- `embedding-index-file` for a file-backed, memory-mapped exact index

Both use exact cosine similarity. This is intentionally easy to validate and compare.

## Build and query

Embedding retrieval is a run-based workflow:

1) ingest items
2) extract text (or select an existing extraction run)
3) build an embedding retrieval run (which materializes artifacts under the corpus)
4) query the run and inspect evidence

Example build:

```
python -m biblicus build --corpus corpora/example --backend embedding-index-file
```

Example query:

```
python -m biblicus query --corpus corpora/example --run embedding-index-file:RUN_ID --query "meaningful phrase"
```

## Evidence and provenance

Evidence returned by embedding retrieval includes:

- the parent `item_id` and `source_uri`
- a retrieval `score` and `rank`
- chunk provenance (boundaries and identifiers)

This allows downstream tooling (including context pack formatting) to remain evidence-first and reproducible.

