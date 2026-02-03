# Chunking

Embedding retrieval depends on chunking.

Most corpora contain documents that are too long to retrieve effectively as single “whole-document” units. Biblicus
therefore treats chunking as part of the retrieval indexing contract: embeddings are computed over chunks, and retrieval
returns evidence with chunk boundaries so you can trace results back to the original item text.

## Chunkers are pluggable

Chunking is a pluggable interface selected by identifier in a retrieval configuration:

- `chunker_id`
- `chunker_config` (Pydantic validated; `extra="forbid"`)

There are no hidden fallbacks. If you select a chunker without providing required configuration, Biblicus fails with a
user-facing error that explains what is missing.

## Chunk identifiers and provenance

Chunks must be addressable and reproducible:

- Each chunk has a stable `chunk_id`.
- Each chunk references a parent `item_id`.
- Each chunk records boundaries (for example `start_char` and `end_char`) and optional metadata.

Evidence produced by embedding retrieval references chunk provenance so downstream tooling can reconstruct context packs
without guessing.

## Built-in chunking strategies

Biblicus provides multiple built-in chunking strategies so you can compare tradeoffs explicitly:

### Fixed character window

Split text into windows of a fixed character length with optional overlap.

Typical parameters:

- `window_characters`
- `overlap_characters`

### Paragraph chunking

Split text into paragraphs (blank-line delimited), with optional joining/splitting rules to avoid chunks that are too
small or too large.

Typical parameters:

- `max_characters`
- `join_short_paragraphs`

### Fixed token window

Split text into windows of a fixed token length with optional overlap.

Token-based chunking depends on a tokenizer interface (see next section) so Biblicus can support multiple tokenization
strategies without locking into a single library.

## Tokenization is pluggable too

Token-based chunkers depend on a second pluggable interface selected by identifier:

- `tokenizer_id`
- `tokenizer_config`

This keeps the surface configurable while avoiding implicit dependencies. If a token-based chunker is selected without
a tokenizer implementation configured, Biblicus fails fast with explicit guidance.

