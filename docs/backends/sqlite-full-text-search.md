# SQLite Full-Text Search Backend

**Backend ID:** `sqlite-full-text-search`

**Category:** [Retrieval Backends](index.md)

## Overview

The SQLite full-text search backend provides production-ready retrieval using SQLite's FTS5 extension with BM25 ranking algorithm. It builds a persistent index with configurable chunking and delivers fast queries even for large corpora.

This backend is ideal for production applications, offering sub-second query times after a one-time indexing step. It supports text chunking with overlap for better context matching and uses BM25 scoring for relevance ranking.

## Installation

The backend is included with Biblicus by default:

```bash
pip install biblicus
```

### Requirements

- **Python**: 3.9+
- **SQLite**: With FTS5 support (included in most Python builds)

### Verify FTS5 Support

```python
import sqlite3
conn = sqlite3.connect(':memory:')
try:
    conn.execute("CREATE VIRTUAL TABLE test USING fts5(content)")
    print("FTS5 is available")
except sqlite3.OperationalError:
    print("FTS5 is NOT available")
```

If FTS5 is not available, you may need to rebuild Python with a newer SQLite version.

## When to Use

### Good Use Cases

- **Production applications**: Fast, consistent query performance
- **Medium to large corpora** (1,000+ items): Essential for acceptable query times
- **Repeated queries**: Persistent index avoids re-scanning
- **Better ranking**: BM25 algorithm provides quality relevance scores
- **Local deployment**: No external services required

### Not Recommended For

- **Very small corpora** (< 100 items): Build overhead not worth it, use [scan](scan.md)
- **Rapidly changing content**: Index must be rebuilt after content changes
- **Semantic search**: Use vector databases for embedding-based search

## Configuration

### Config Schema

```python
class SqliteFullTextSearchRecipeConfig(BaseModel):
    chunk_size: int = 800                  # Maximum characters per chunk
    chunk_overlap: int = 200               # Overlap between chunks
    snippet_characters: int = 400          # Maximum snippet length
    extraction_run: Optional[str] = None   # Extraction run reference
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `chunk_size` | int | `800` | Maximum characters per chunk (must be >= 1) |
| `chunk_overlap` | int | `200` | Overlap characters between chunks (must be < chunk_size) |
| `snippet_characters` | int | `400` | Maximum characters in evidence snippets |
| `extraction_run` | str | `None` | Optional extraction run reference (extractor_id:run_id) |

### Chunking Strategy

Text is split into overlapping chunks:

```
Text: "ABCDEFGHIJ"
chunk_size: 6
chunk_overlap: 2

Chunks:
  [ABCDEF]
      [EFGHIJ]
```

**Why chunking?**
- Improves match granularity for large documents
- Provides better context in snippets
- Enables ranking at sub-document level

**Tuning tips:**
- Larger chunks: Better context, fewer chunks, slower queries
- Smaller chunks: More precise matching, more chunks, faster queries
- Overlap: Prevents matches being split across chunk boundaries

## Usage

### Command Line

#### Basic Usage

```bash
# Build FTS index (creates SQLite database)
biblicus build my-corpus --backend sqlite-full-text-search

# Query the index
biblicus query my-corpus --query "search terms"
```

#### Custom Configuration

```bash
# Larger chunks with more overlap
biblicus build my-corpus --backend sqlite-full-text-search \
  --config chunk_size=1200 \
  --config chunk_overlap=300 \
  --config snippet_characters=600

# With extraction run
biblicus build my-corpus --backend sqlite-full-text-search \
  --config extraction_run=pdf-text:abc123
```

#### Recipe File

```yaml
backend_id: sqlite-full-text-search
recipe_name: "Production FTS index"
config:
  chunk_size: 800
  chunk_overlap: 200
  snippet_characters: 400
  extraction_run: null
```

```bash
biblicus build my-corpus --recipe recipe.yml
```

### Python API

```python
from biblicus import Corpus
from biblicus.backends import get_backend
from biblicus.models import QueryBudget

# Load corpus
corpus = Corpus.from_directory("my-corpus")

# Get backend
backend = get_backend("sqlite-full-text-search")

# Build index
run = backend.build_run(
    corpus,
    recipe_name="Production index",
    config={
        "chunk_size": 800,
        "chunk_overlap": 200
    }
)

print(f"Built index: {run.run_id}")
print(f"Stats: {run.stats}")

# Query
result = backend.query(
    corpus,
    run=run,
    query_text="machine learning",
    budget=QueryBudget(max_total_items=10)
)

# Access evidence
for evidence in result.evidence:
    print(f"\n{evidence.item_id} (score: {evidence.score:.2f})")
    print(f"  {evidence.text[:100]}...")
```

### With Extraction Runs

```python
# Extract text from PDFs
extraction_run = corpus.extract_text(
    extractor_id="pdf-text"
)

# Build FTS with extraction
run = backend.build_run(
    corpus,
    recipe_name="FTS with PDF extraction",
    config={
        "extraction_run": f"pdf-text:{extraction_run.run_id}",
        "chunk_size": 1000
    }
)
```

## How It Works

### Index Building

1. **Load corpus catalog**: Read all item metadata
2. **Create SQLite database**: Initialize FTS5 virtual table
3. **Process items**: For each text item:
   - Load text content (raw or extracted)
   - Split into overlapping chunks
   - Insert chunks into FTS5 table with metadata
4. **Commit**: Write database to disk
5. **Record stats**: Count items, chunks, bytes

### Query Processing

1. **Parse query**: SQLite FTS5 query syntax
2. **Execute FTS5 search**: Use BM25 ranking
3. **Fetch candidates**: Retrieve top N chunks (5x budget)
4. **Extract snippets**: Truncate chunks to snippet length
5. **Sort by score**: Rank evidence by BM25 score
6. **Apply budget**: Select top items according to budget

### BM25 Ranking

SQLite FTS5 uses the BM25 algorithm:

- **Term frequency (TF)**: How often query terms appear in chunk
- **Inverse document frequency (IDF)**: Rarity of terms in corpus
- **Document length normalization**: Adjusts for chunk size

BM25 provides better ranking than simple term frequency by considering term rarity and document length.

## Performance

### Build Time

- **O(n)**: Linear in corpus size
- ~5-10 seconds for 1,000 items
- ~50-100 seconds for 10,000 items
- Depends on item size and chunk settings

### Query Time

- **O(log n)**: Logarithmic with index
- <100ms for most queries on 10,000-item corpus
- Faster than scan by 100-1000x for large corpora

### Memory Usage

- **Moderate**: SQLite index held in memory during queries
- ~1-5 MB per 1,000 text items
- Configurable SQLite cache size

### Disk Usage

- **~1-5 MB per 1,000 items**: Depends on text density and chunking
- Stored in `.biblicus/runs/<run_id>.sqlite`

## Examples

### Production Deployment

```bash
# Build index once
biblicus init prod-corpus
biblicus ingest prod-corpus documents/
biblicus extract prod-corpus --extractor pdf-text
biblicus build prod-corpus --backend sqlite-full-text-search \
  --config extraction_run=pdf-text:latest

# Fast repeated queries
biblicus query prod-corpus --query "customer retention"
biblicus query prod-corpus --query "revenue model"
biblicus query prod-corpus --query "market analysis"
```

### Tuned for Large Documents

```python
# Larger chunks for academic papers
backend = get_backend("sqlite-full-text-search")

run = backend.build_run(
    corpus,
    recipe_name="Academic papers index",
    config={
        "chunk_size": 1500,      # Larger chunks
        "chunk_overlap": 400,    # More overlap
        "snippet_characters": 800  # Larger snippets
    }
)
```

### Multi-Format Corpus

```bash
# Extract from multiple sources
biblicus extract corpus --extractor select-text \
  --config extractors='["pdf-text","markitdown","ocr-rapidocr"]'

# Build unified index
biblicus build corpus --backend sqlite-full-text-search \
  --config extraction_run=select-text:latest
```

### Query with Context

```python
result = backend.query(
    corpus,
    run=run,
    query_text="machine learning applications",
    budget=QueryBudget(
        max_total_items=5,
        max_items_per_source=2
    )
)

# Evidence includes span information
for evidence in result.evidence:
    if evidence.span_start is not None:
        print(f"Match at offset {evidence.span_start}-{evidence.span_end}")
    print(f"  {evidence.text}")
```

## Advanced Configuration

### SQLite Query Syntax

FTS5 supports advanced query operators:

```bash
# Phrase search
biblicus query corpus --query '"machine learning"'

# Boolean AND
biblicus query corpus --query 'machine AND learning'

# Boolean OR
biblicus query corpus --query 'machine OR artificial'

# Boolean NOT
biblicus query corpus --query 'learning NOT supervised'

# Prefix matching
biblicus query corpus --query 'comput*'

# Column-specific (if indexed)
biblicus query corpus --query 'content:machine'
```

### Rebuilding Indexes

Index must be rebuilt when:
- Corpus content changes
- New items ingested
- Extraction runs updated

```bash
# Delete old run
biblicus extract delete corpus --run sqlite-full-text-search:old_id --confirm sqlite-full-text-search:old_id

# Build new run
biblicus build corpus --backend sqlite-full-text-search
```

## Limitations

### Query Features

- No semantic/embedding-based search
- No wildcard in middle of words (only prefix: `word*`)
- No fuzzy matching (typo tolerance)
- No field weighting (all text treated equally)

### Scalability

- Single-machine only (no distributed search)
- Index size grows with corpus size
- Rebuild required for content updates

### Ranking

- BM25 is keyword-based (not semantic)
- No learning-to-rank or custom scoring
- Fixed ranking algorithm

## When to Upgrade

Consider external search engines when:

- Corpus exceeds 100,000 items
- Need distributed/clustered search
- Require semantic/vector search
- Need real-time index updates
- Want advanced ranking (learning-to-rank)

External options: Elasticsearch, OpenSearch, Meilisearch, Typesense

## Error Handling

### FTS5 Not Available

```
RuntimeError: SQLite full-text search version five is required but not available
```

**Fix**: Rebuild Python with newer SQLite or use pre-built binaries with FTS5.

### Missing Extraction Run

```
FileNotFoundError: Missing extraction run: pdf-text:abc123
```

**Fix**: Verify extraction run exists or run extraction first.

### Invalid Configuration

```
ValueError: chunk_overlap must be smaller than chunk_size
```

**Fix**: Ensure `chunk_overlap < chunk_size`.

## Statistics

Build run statistics:

```json
{
  "items": 1000,
  "text_items": 850,
  "chunks": 3200,
  "bytes": 4567890
}
```

Query result statistics:

```json
{
  "candidates": 42,
  "returned": 10
}
```

## Index Artifacts

The backend creates a SQLite database stored at:

```
corpus/
  .biblicus/
    runs/
      <run_id>.sqlite  # FTS5 index database
```

Database schema:

```sql
CREATE VIRTUAL TABLE chunks_full_text_search USING fts5(
    content,           -- Chunk text (indexed)
    item_id UNINDEXED, -- Corpus item ID
    source_uri UNINDEXED,
    media_type UNINDEXED,
    relpath UNINDEXED,
    title UNINDEXED,
    start_offset UNINDEXED,
    end_offset UNINDEXED
);
```

## Related Backends

- [scan](scan.md) - Naive full-scan backend for baselines

## See Also

- [Backends Overview](index.md) - All available backends
- [BACKENDS.md](../BACKENDS.md) - Backend implementation guide
- [EXTRACTION.md](../EXTRACTION.md) - Text extraction pipeline
- [Extractor Reference](../extractors/index.md) - Text extraction plugins
- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html) - Official SQLite FTS5 docs
