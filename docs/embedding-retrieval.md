# Embedding Retrieval

Embedding retrieval turns a large collection of text into a reusable index that can be queried efficiently.

Biblicus supports embedding retrieval through backends that:

1) chunk extracted text,
2) compute embeddings for each chunk,
3) build an index under the corpus as snapshot artifacts, and
4) return evidence with chunk provenance on query.

## Why embedding retrieval?

Biblicus already supports deterministic lexical retrieval and hybrid retrieval wiring. Embedding retrieval adds backends that build a reusable index so retrieval is fast, repeatable, and evaluatable.

Chunking is treated as part of the indexing contract (not an afterthought): embeddings are computed over chunks, and retrieval returns evidence with item-level provenance plus chunk boundaries.

### What problem does this solve?

- Provide a real embedding retrieval backend with an explicit build/query lifecycle.
- Make chunking a first-class, fully configurable pipeline stage for embedding retrieval.
- Establish a stable surface for swapping embedding providers without rewriting backends.

## Concepts

- **Chunking**: the unit of embedding and retrieval. See `docs/chunking.md`.
- **Embedding provider**: a pluggable implementation that turns text into vectors.
- **Embedding index backend**: a retrieval backend that materializes vectors and supports similarity search.

## A local, textbook embedding index

Biblicus provides two embedding index backends that avoid external services while still being “real” retrievers:

1.  **`embedding-index-inmemory`**: For small demos with safety caps.
2.  **`embedding-index-file`**: A file-backed, memory-mapped exact index (NumPy-backed).

Both backends use exact cosine similarity. This is intentionally “textbook” behavior that is easy to validate and compare. Approximate nearest neighbor (ANN) indexes are explicitly out of scope for the initial slice to prioritize correctness and simplicity.

## Build and query

Embedding retrieval is a run-based workflow:

1) ingest items
2) extract text (or select an existing extraction snapshot)
3) build an embedding retrieval snapshot (which materializes artifacts under the corpus)
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
