# Embedding index (file-backed)

This backend builds an embedding index under a corpus and queries it using exact cosine similarity.

It is intended for larger corpora where you want a local, pip-installable workflow that does not depend on an external
vector database.

## Backend ID

`embedding-index-file`

## What it builds

This backend builds a retrieval snapshot that materializes snapshot artifacts under the corpus, for example:

- an embedding matrix stored as a NumPy array on disk
- an id mapping from chunk identifiers to embedding row offsets
- chunk records (text + boundaries + provenance)

Queries memory-map the embedding matrix and scan in batches so memory usage stays bounded, even when the index is larger
than available RAM.

## Chunking

Embeddings are computed over chunks. Chunking is configured per configuration by selecting a chunker and its configuration.

Chunking is part of the index contract: evidence references chunk boundaries so you can trace retrieval outputs back to
the original item text.

## Dependencies

- Requires `numpy`.
- Requires an embedding provider configuration.

