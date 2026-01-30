# Retrieval Backends

Biblicus provides pluggable retrieval backends that implement different search and ranking strategies. Each backend defines how evidence is retrieved from your corpus.

## Available Backends

### [scan](scan.md)

Naive full-scan backend that searches all text items at query time without pre-built indexes.

- **Backend ID**: `scan`
- **Installation**: Included by default
- **Best for**: Small corpora, development, baseline comparisons
- **Index**: None (scans at query time)
- **Speed**: Slow for large corpora

### [sqlite-full-text-search](sqlite-full-text-search.md)

Production-ready full-text search using SQLite FTS5 with BM25 ranking.

- **Backend ID**: `sqlite-full-text-search`
- **Installation**: Included by default (requires SQLite with FTS5 support)
- **Best for**: Medium to large corpora, production use
- **Index**: SQLite database with FTS5 virtual tables
- **Speed**: Fast with persistent index

## Quick Start

### Installation

Both backends are included with the base Biblicus installation:

```bash
pip install biblicus
```

### Basic Usage

#### Command Line

```bash
# Initialize corpus
biblicus init my-corpus

# Ingest documents
biblicus ingest my-corpus document.pdf

# Extract text
biblicus extract my-corpus --extractor pdf-text

# Build retrieval run with a backend
biblicus build my-corpus --backend sqlite-full-text-search

# Query the run
biblicus query my-corpus --query "search terms"
```

#### Python API

```python
from biblicus import Corpus
from biblicus.backends import get_backend

# Load corpus
corpus = Corpus.from_directory("my-corpus")

# Get backend
backend = get_backend("sqlite-full-text-search")

# Build run
run = backend.build_run(
    corpus,
    recipe_name="My search index",
    config={}
)

# Query
result = backend.query(
    corpus,
    run=run,
    query_text="search terms",
    budget={"max_total_items": 10}
)
```

## Choosing a Backend

| Use Case | Recommended Backend | Notes |
|----------|---------------------|-------|
| Development & testing | [scan](scan.md) | No index to build, immediate results |
| Small corpora (<1000 items) | [scan](scan.md) | Fast enough without indexing overhead |
| Production applications | [sqlite-full-text-search](sqlite-full-text-search.md) | Fast queries with BM25 ranking |
| Large corpora (>10,000 items) | [sqlite-full-text-search](sqlite-full-text-search.md) | Essential for performance |
| Baseline comparisons | [scan](scan.md) | Simple reference implementation |

## Performance Comparison

### Scan Backend

- **Build time**: None (no index)
- **Query time**: O(n) - linear scan of all items
- **Memory**: Low (no index storage)
- **Disk**: None (no artifacts)

**Example**: 1000-item corpus, 5-10 second query time

### SQLite Full-Text Search Backend

- **Build time**: O(n) - one-time indexing
- **Query time**: O(log n) - indexed search
- **Memory**: Moderate (SQLite index)
- **Disk**: ~1-5 MB per 1000 text items

**Example**: 10,000-item corpus, <100ms query time after indexing

## Common Patterns

### Development Workflow

Use scan backend during development for immediate feedback:

```bash
biblicus build my-corpus --backend scan
biblicus query my-corpus --query "test"
```

### Production Deployment

Build a persistent index with sqlite-full-text-search:

```bash
biblicus build my-corpus --backend sqlite-full-text-search \
  --config chunk_size=800 \
  --config chunk_overlap=200
```

### Baseline Comparison

Compare backends using the same corpus:

```bash
# Build with both backends
biblicus build my-corpus --backend scan --recipe scan-baseline
biblicus build my-corpus --backend sqlite-full-text-search --recipe fts-index

# Query both
biblicus query my-corpus --run scan:RUN_ID --query "test"
biblicus query my-corpus --run sqlite-full-text-search:RUN_ID --query "test"
```

### Using Extracted Text

Both backends support extraction runs for non-text content:

```bash
# Extract text from PDFs
biblicus extract my-corpus --extractor pdf-text

# Build backend with extraction run
biblicus build my-corpus --backend sqlite-full-text-search \
  --config extraction_run=pdf-text:EXTRACTION_RUN_ID
```

## Backend Configuration

### Common Configuration Options

Both backends support these configuration options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `snippet_characters` | int | 400 | Maximum characters in evidence snippets |
| `extraction_run` | str | None | Extraction run reference (extractor_id:run_id) |

### Backend-Specific Options

#### Scan Backend

No additional configuration options.

#### SQLite Full-Text Search Backend

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `chunk_size` | int | 800 | Maximum characters per chunk |
| `chunk_overlap` | int | 200 | Overlap characters between chunks |

## Architecture

### Backend Interface

All backends implement the `RetrievalBackend` interface:

```python
class RetrievalBackend:
    backend_id: str

    def build_run(self, corpus, *, recipe_name, config) -> RetrievalRun:
        """Build a retrieval run (may create artifacts)."""

    def query(self, corpus, *, run, query_text, budget) -> RetrievalResult:
        """Query the run and return evidence."""
```

### Evidence Model

All backends return structured `Evidence` objects:

```python
class Evidence:
    item_id: str                  # Corpus item identifier
    source_uri: Optional[str]     # Original source URI
    media_type: str               # MIME type
    score: float                  # Relevance score
    rank: int                     # Result rank
    text: str                     # Evidence snippet
    span_start: Optional[int]     # Span start offset
    span_end: Optional[int]       # Span end offset
    stage: str                    # Processing stage
    recipe_id: str                # Recipe identifier
    run_id: str                   # Run identifier
    hash: str                     # Content hash
```

## Implementing Custom Backends

To implement a custom backend:

1. Subclass `RetrievalBackend`
2. Implement `build_run()` and `query()` methods
3. Register in `biblicus.backends.available_backends`
4. Add BDD specifications with 100% coverage

See [BACKENDS.md](../BACKENDS.md) for implementation details.

## See Also

- [scan backend](scan.md) - Naive full-scan backend
- [sqlite-full-text-search backend](sqlite-full-text-search.md) - SQLite FTS5 backend
- [BACKENDS.md](../BACKENDS.md) - Backend implementation guide
- [EXTRACTION.md](../EXTRACTION.md) - Text extraction pipeline
- [Extractor Reference](../extractors/index.md) - Text extraction plugins
