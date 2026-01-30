# Scan Backend

**Backend ID:** `scan`

**Category:** [Retrieval Backends](index.md)

## Overview

The scan backend is a naive full-scan retrieval implementation that searches all text items at query time without building a persistent index. It provides a simple baseline for retrieval evaluation and is suitable for small corpora or development workflows.

The scan backend tokenizes queries into terms, scores items by term frequency, and returns ranked evidence with snippet extraction. It requires no build time but scales linearly with corpus size.

## Installation

The scan backend is included by default with Biblicus:

```bash
pip install biblicus
```

No additional dependencies or setup required.

## When to Use

### Good Use Cases

- **Small corpora** (< 1000 items): Fast enough without indexing overhead
- **Development & testing**: Immediate results without build step
- **Baseline comparisons**: Simple reference for evaluating other backends
- **Ad-hoc exploration**: Quick searches without commitment to index

### Not Recommended For

- **Large corpora** (> 10,000 items): Query time becomes prohibitive
- **Production applications**: No persistent index, slow repeated queries
- **High-frequency queries**: Every query re-scans entire corpus

## Configuration

### Config Schema

```python
class ScanRecipeConfig(BaseModel):
    snippet_characters: int = 400       # Maximum characters in snippets
    extraction_run: Optional[str] = None  # Extraction run reference
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `snippet_characters` | int | `400` | Maximum characters to include in evidence snippets |
| `extraction_run` | str | `None` | Optional extraction run reference (extractor_id:run_id) |

## Usage

### Command Line

#### Basic Usage

```bash
# Build scan run (no artifacts created)
biblicus build my-corpus --backend scan

# Query the run
biblicus query my-corpus --query "search terms"
```

#### Custom Configuration

```bash
# Larger snippets
biblicus build my-corpus --backend scan \
  --config snippet_characters=800

# With extraction run
biblicus build my-corpus --backend scan \
  --config extraction_run=pdf-text:abc123
```

#### Recipe File

```yaml
backend_id: scan
recipe_name: "Development scan"
config:
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

# Get scan backend
backend = get_backend("scan")

# Build run (no index created)
run = backend.build_run(
    corpus,
    recipe_name="Quick scan",
    config={}
)

# Query
result = backend.query(
    corpus,
    run=run,
    query_text="search terms",
    budget=QueryBudget(max_total_items=10)
)

# Access evidence
for evidence in result.evidence:
    print(f"{evidence.item_id}: {evidence.score}")
    print(f"  {evidence.text[:100]}...")
```

### With Extraction Runs

```python
# Extract text first
extraction_run = corpus.extract_text(
    extractor_id="pdf-text"
)

# Build scan with extraction
run = backend.build_run(
    corpus,
    recipe_name="Scan with extraction",
    config={
        "extraction_run": f"pdf-text:{extraction_run.run_id}"
    }
)
```

## How It Works

### Query Processing

1. **Tokenization**: Query text is lowercased and split into tokens
2. **Scanning**: All corpus items are loaded and scanned sequentially
3. **Scoring**: Items are scored by term frequency (count of query tokens in text)
4. **Ranking**: Scored items are sorted by score (descending), then by item ID
5. **Snippet Extraction**: First match location is found, snippet extracted around it
6. **Budget Application**: Top-ranked items are selected according to query budget

### Scoring Algorithm

```python
def score_item(item_text, query_tokens):
    """Score = sum of token frequencies in item text."""
    lower_text = item_text.lower()
    return sum(lower_text.count(token) for token in query_tokens)
```

### Snippet Extraction

- Finds first occurrence of any query token
- Centers snippet around match location
- Falls back to start of text if no match (shouldn't happen with non-zero scores)
- Truncates to `snippet_characters` length

## Performance

### Build Time

- **None**: No index is created, build is instant
- Only validates configuration and counts text items

### Query Time

- **O(n)**: Linear scan of all corpus items
- ~1-2 seconds for 1000 items
- ~10-20 seconds for 10,000 items
- Depends on item size and disk I/O

### Memory Usage

- **Low**: No persistent index stored
- Only active item being processed is in memory

### Disk Usage

- **None**: No artifacts created (only run manifest)

## Examples

### Quick Development Search

```bash
# Initialize and populate corpus
biblicus init demo-corpus
echo "Machine learning applications" > ml.txt
echo "Deep learning neural networks" > dl.txt
biblicus ingest demo-corpus ml.txt dl.txt

# Immediate search (no index build)
biblicus build demo-corpus --backend scan
biblicus query demo-corpus --query "learning"
```

### Baseline Comparison

```python
from biblicus import Corpus
from biblicus.backends import get_backend

corpus = Corpus.from_directory("test-corpus")

# Build with both backends
scan_backend = get_backend("scan")
fts_backend = get_backend("sqlite-full-text-search")

scan_run = scan_backend.build_run(corpus, recipe_name="Scan baseline", config={})
fts_run = fts_backend.build_run(corpus, recipe_name="FTS index", config={})

# Compare results
query = "neural networks"
budget = {"max_total_items": 10}

scan_result = scan_backend.query(corpus, run=scan_run, query_text=query, budget=budget)
fts_result = fts_backend.query(corpus, run=fts_run, query_text=query, budget=budget)

print(f"Scan returned {len(scan_result.evidence)} items")
print(f"FTS returned {len(fts_result.evidence)} items")
```

### Ad-hoc Exploration

```bash
# No commitment to index structure
biblicus build corpus --backend scan
biblicus query corpus --query "term1"
biblicus query corpus --query "term2"
biblicus query corpus --query "term3"

# Switch to FTS when ready
biblicus build corpus --backend sqlite-full-text-search
```

## Limitations

### Scalability

- Linear query time makes it unsuitable for large corpora
- No optimization for repeated queries
- Every query re-reads items from disk

### Ranking Quality

- Simple term frequency scoring (no TF-IDF, BM25, or semantic ranking)
- No phrase matching or proximity scoring
- Single-token matching only

### Query Features

- No support for boolean operators (AND, OR, NOT)
- No wildcard or fuzzy matching
- No field-specific queries

## When to Upgrade

Consider switching to [sqlite-full-text-search](sqlite-full-text-search.md) when:

- Corpus exceeds 1000 items
- Query time becomes noticeable (>2 seconds)
- You need repeated queries on the same corpus
- You want better ranking (BM25 algorithm)
- Production deployment requires consistent performance

## Error Handling

### Missing Extraction Run

If configured extraction run doesn't exist:

```
FileNotFoundError: Missing extraction run: pdf-text:abc123
```

**Fix**: Verify extraction run ID or run extraction first.

### Non-Text Items

Non-text items without extraction run are skipped automatically. No error raised.

## Statistics

Build run statistics:

```json
{
  "items": 1000,
  "text_items": 850
}
```

Query result statistics:

```json
{
  "candidates": 42,
  "returned": 10
}
```

## Related Backends

- [sqlite-full-text-search](sqlite-full-text-search.md) - Fast indexed search with BM25 ranking

## See Also

- [Backends Overview](index.md) - All available backends
- [BACKENDS.md](../BACKENDS.md) - Backend implementation guide
- [EXTRACTION.md](../EXTRACTION.md) - Text extraction pipeline
- [Extractor Reference](../extractors/index.md) - Text extraction plugins
