# Embedding index (in-memory)

This backend builds an embedding index in memory and queries it using exact cosine similarity.

It is intended for textbook demos and small corpora where you want a “real” embedding retrieval loop without running an
external vector database.

## Backend ID

`embedding-index-inmemory`

## What it builds

This backend builds a retrieval run that materializes:

- chunk records (text + boundaries + provenance)
- embedding vectors for each chunk

All of this lives in memory while the process is running. For safety, the backend enforces explicit caps so a build does
not accidentally consume unbounded memory.

## Chunking

Embeddings are computed over chunks. Chunking is configured per recipe by selecting a chunker and its configuration.

Chunking is part of the index contract: evidence references chunk boundaries so you can trace retrieval outputs back to
the original item text.

## Dependencies

- Requires an embedding provider configuration.

This backend does not require a database or server.

