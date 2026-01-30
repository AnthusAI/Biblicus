# Pass-Through Text Extractor

**Extractor ID:** `pass-through-text`

**Category:** [Text/Document Extractors](index.md)

## Overview

The pass-through text extractor is the simplest extractor in Biblicus. It reads text files directly from the corpus and returns their content without any processing. For Markdown files, it parses and strips front matter, returning only the body content.

This extractor is fundamental to Biblicus workflows as the canonical way to handle text items. It preserves the exact content of text files while providing special handling for Markdown front matter.

## Installation

No additional dependencies required. This extractor is part of the core Biblicus installation.

```bash
pip install biblicus
```

## Supported Media Types

- `text/plain` - Plain text files
- `text/markdown` - Markdown files (with front matter parsing)
- `text/*` - Any text media type

Non-text items are automatically skipped.

## Configuration

### Config Schema

```python
class PassThroughTextExtractorConfig(BaseModel):
    # This extractor requires no configuration
    pass
```

### Configuration Options

This extractor is intentionally minimal and accepts no configuration options.

## Usage

### Command Line

#### Basic Usage

```bash
# Extract text files from corpus
biblicus extract my-corpus --extractor pass-through-text
```

#### Recipe File

```yaml
extractor_id: pass-through-text
config: {}
```

```bash
biblicus extract my-corpus --recipe recipe.yml
```

### Python API

```python
from biblicus import Corpus

# Load corpus
corpus = Corpus.from_directory("my-corpus")

# Extract text files
results = corpus.extract_text(extractor_id="pass-through-text")
```

### In Pipeline

#### Text-First Fallback Chain

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: select-text
```

#### Mixed Media Type Routing

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pass-through-text
  overrides:
    - media_type_pattern: "application/pdf"
      extractor: pdf-text
    - media_type_pattern: "image/.*"
      extractor: ocr-rapidocr
```

## Examples

### Extract Text Corpus

Process a corpus containing only text files:

```bash
biblicus extract notes-corpus --extractor pass-through-text
```

### Extract Markdown with Front Matter

The extractor automatically handles front matter:

```markdown
---
title: My Document
tags: [note, draft]
---

This is the body content that is extracted.
```

Output text:
```
This is the body content that is extracted.
```

### Mixed Format Pipeline

Use as first step in a multi-format pipeline:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("mixed-corpus")

# Text files pass through, other formats processed by other extractors
results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pass-through-text"},
            {"extractor_id": "markitdown"},
            {"extractor_id": "select-text"}
        ]
    }
)
```

## Behavior Details

### Front Matter Handling

For `text/markdown` items, the extractor:
1. Parses YAML front matter enclosed in `---` delimiters
2. Strips the front matter section
3. Returns only the body content

Front matter metadata is preserved in the catalog but not included in extracted text.

### Character Encoding

All text files are decoded as UTF-8. Files with other encodings may produce errors or incorrect output.

### Empty Files

Empty text files produce empty extracted text (zero-length string). These are counted in `extracted_empty_items` statistics.

## Performance

- **Speed**: Near-instant (file read only)
- **Memory**: Minimal (one file at a time)
- **Accuracy**: 100% (no processing)

This is the fastest extractor in Biblicus as it performs only file I/O and optional front matter parsing.

## Error Handling

### Non-Text Items

Non-text items are silently skipped (returns `None`). This allows the extractor to work safely in pipelines with mixed media types.

### Encoding Errors

UTF-8 decoding errors cause per-item failures recorded in `errored_items` but do not halt the entire extraction run.

### Missing Files

Missing corpus files result in standard file I/O errors and are recorded as per-item failures.

## Use Cases

### Documentation Corpora

Ideal for documentation consisting of Markdown or plain text:

```bash
biblicus extract docs-corpus --extractor pass-through-text
```

### Note Collections

Process personal notes or knowledge bases:

```bash
biblicus extract notes-corpus --extractor pass-through-text
```

### Source Code Comments

Extract text documentation from code repositories:

```bash
biblicus extract code-docs-corpus --extractor pass-through-text
```

### Mixed Pipelines

Use as the fast path for text in heterogeneous corpora:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: unstructured  # Handles everything else
    - extractor_id: select-text
```

## Related Extractors

### Same Category

- [metadata-text](metadata.md) - Metadata-based text representation
- [pdf-text](pdf.md) - PDF text extraction
- [markitdown](markitdown.md) - Office document conversion
- [unstructured](unstructured.md) - Universal document parser

### Pipeline Utilities

- [select-text](../pipeline-utilities/select-text.md) - First non-empty selection
- [select-longest-text](../pipeline-utilities/select-longest.md) - Longest output selection
- [pipeline](../pipeline-utilities/pipeline.md) - Multi-step extraction

## See Also

- [Text/Document Extractors Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [Front Matter Documentation](../../EXTRACTION.md#front-matter-handling)
