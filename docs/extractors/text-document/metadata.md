# Metadata Text Extractor

**Extractor ID:** `metadata-text`

**Category:** [Text/Document Extractors](index.md)

## Overview

The metadata text extractor generates searchable text representations from catalog item metadata. Instead of processing file content, it creates small, stable text artifacts from titles and tags stored in the corpus catalog.

This extractor is designed for retrieval over non-text items like images, audio, or binary files where the metadata provides the primary semantic signal. It's also useful for comparing retrieval backends while keeping extraction deterministic and stable.

## Installation

No additional dependencies required. This extractor is part of the core Biblicus installation.

```bash
pip install biblicus
```

## Supported Media Types

All media types are supported. The extractor processes any catalog item that has metadata (title or tags).

## Configuration

### Config Schema

```python
class MetadataTextExtractorConfig(BaseModel):
    include_title: bool = True   # Include item title
    include_tags: bool = True    # Include tags line
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `include_title` | bool | `true` | Include the item title as the first line |
| `include_tags` | bool | `true` | Include a `tags: ...` line if tags exist |

## Usage

### Command Line

#### Basic Usage

```bash
# Extract metadata as text
biblicus extract my-corpus --extractor metadata-text
```

#### Custom Configuration

```bash
# Only include titles, skip tags
biblicus extract my-corpus --extractor metadata-text \
  --config include_tags=false
```

#### Recipe File

```yaml
extractor_id: metadata-text
config:
  include_title: true
  include_tags: true
```

```bash
biblicus extract my-corpus --recipe recipe.yml
```

### Python API

```python
from biblicus import Corpus

# Load corpus
corpus = Corpus.from_directory("my-corpus")

# Extract with defaults
results = corpus.extract_text(extractor_id="metadata-text")

# Extract with custom config
results = corpus.extract_text(
    extractor_id="metadata-text",
    config={
        "include_title": True,
        "include_tags": False
    }
)
```

### In Pipeline

#### Metadata Fallback

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: metadata-text  # Fallback for non-text items
    - extractor_id: select-text
```

#### Image Metadata Retrieval

```yaml
extractor_id: select-smart-override
config:
  default_extractor: metadata-text
  overrides:
    - media_type_pattern: "image/.*"
      extractor: metadata-text
```

## Examples

### Basic Metadata Extraction

Given a catalog item with metadata:

```yaml
id: photo-001
media_type: image/jpeg
title: "Sunset over mountains"
tags: ["nature", "landscape", "golden-hour"]
```

Extracted text:
```
Sunset over mountains
tags: nature, landscape, golden-hour
```

### Title-Only Extraction

Extract just titles for minimal overhead:

```bash
biblicus extract photos-corpus --extractor metadata-text \
  --config include_tags=false
```

Output:
```
Sunset over mountains
```

### Image Corpus Retrieval

Create searchable text for an image collection:

```python
from biblicus import Corpus

# Corpus of photos with descriptive metadata
corpus = Corpus.from_directory("photos")

# Extract metadata as text for retrieval
results = corpus.extract_text(extractor_id="metadata-text")
```

### Mixed Media Pipeline

Use metadata for items that can't be processed:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: ocr-rapidocr
    - extractor_id: metadata-text    # Catch-all for remaining items
    - extractor_id: select-text
```

## Output Format

The output is plain text formatted as:

1. **Title line** (if `include_title` is true and title exists): The item title as-is
2. **Tags line** (if `include_tags` is true and tags exist): `tags: tag1, tag2, tag3`

Both elements are optional. If neither title nor tags exist, the extractor returns `None`.

## Behavior Details

### Empty Metadata

Items without title or tags (or with both disabled) return `None`, causing the extractor to skip them.

### Whitespace Handling

- Titles are stripped of leading/trailing whitespace
- Empty titles (only whitespace) are treated as missing
- Tags are individually stripped and empty tags are filtered out

### Tag Formatting

Tags are joined with commas and spaces: `tags: tag1, tag2, tag3`

### Deterministic Output

Output is completely deterministic based on catalog metadata. No file I/O is performed, making this extractor extremely stable for benchmarking retrieval systems.

## Performance

- **Speed**: Near-instant (no file I/O)
- **Memory**: Minimal (metadata only)
- **Consistency**: 100% deterministic

This is one of the fastest extractors as it only accesses in-memory catalog metadata.

## Error Handling

### Missing Metadata

Items without applicable metadata are silently skipped (returns `None`).

### Invalid Metadata Types

Non-string titles or tags are filtered out. The extractor is defensive against malformed catalog data.

## Use Cases

### Image Retrieval

Build text indices for image collections:

```bash
biblicus extract photos --extractor metadata-text
```

### Audio Library Search

Create searchable text for music or podcast libraries:

```bash
biblicus extract music-library --extractor metadata-text
```

### Retrieval Benchmarking

Compare retrieval backends with stable extraction:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("benchmark-corpus")

# Stable extraction for fair comparison
results = corpus.extract_text(extractor_id="metadata-text")
```

### Non-Text Fallback

Provide searchable text for items that can't be processed:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: docling-smol
    - extractor_id: metadata-text  # Fallback
    - extractor_id: select-text
```

## Best Practices

### When to Use Metadata Extractor

**Use metadata-text when:**
- Items have rich, descriptive metadata
- You need deterministic extraction for benchmarking
- File content is unavailable or unreliable
- You want minimal processing overhead

**Don't use metadata-text when:**
- File content provides the primary signal
- Metadata is missing or poor quality
- You need full document understanding

### Metadata Quality

The effectiveness of this extractor depends entirely on metadata quality:

- **Good**: Descriptive titles, relevant tags
- **Poor**: Generic titles ("IMG_001"), no tags

### Catalog Preparation

Ensure your catalog has good metadata:

```yaml
# Good metadata
id: research-paper-001
title: "Neural Networks for Document Understanding"
tags: ["ml", "nlp", "research", "deep-learning"]

# Poor metadata
id: doc001
title: "Document 1"
tags: []
```

## Related Extractors

### Same Category

- [pass-through-text](pass-through.md) - Direct text file reading
- [pdf-text](pdf.md) - PDF text extraction
- [markitdown](markitdown.md) - Office document conversion
- [unstructured](unstructured.md) - Universal document parser

### Alternatives

- [ocr-rapidocr](../ocr/rapidocr.md) - Image text extraction
- [stt-openai](../speech-to-text/openai.md) - Audio transcription
- [docling-smol](../vlm-document/docling-smol.md) - VLM document understanding

### Pipeline Utilities

- [select-text](../pipeline-utilities/select-text.md) - First non-empty selection
- [select-longest-text](../pipeline-utilities/select-longest.md) - Longest output selection
- [pipeline](../pipeline-utilities/pipeline.md) - Multi-step extraction

## See Also

- [Text/Document Extractors Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [Catalog Specification](../../EXTRACTION.md#catalog-format)
