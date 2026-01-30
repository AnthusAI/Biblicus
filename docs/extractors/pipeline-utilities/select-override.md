# Select Override Extractor

**Extractor ID:** `select-override`

**Category:** [Pipeline Utilities](index.md)

## Overview

The select-override extractor implements simple media type-based routing by always using the last extraction for matching items. It provides basic override logic where specific media types get special handling while others follow default behavior.

This extractor is useful when you want to override extraction results for specific media types, such as always using OCR output for images or VLM output for PDFs, regardless of what other extractors produced.

## Installation

No additional dependencies required. This extractor is part of the core Biblicus installation.

```bash
pip install biblicus
```

## Supported Media Types

All media types are supported. Selection behavior depends on configured media type patterns.

## Configuration

### Config Schema

```python
class SelectOverrideConfig(BaseModel):
    media_type_patterns: List[str] = ["*/*"]
    fallback_to_first: bool = False
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `media_type_patterns` | list[str] | `["*/*"]` | Glob patterns for media types to override |
| `fallback_to_first` | bool | `false` | If true, use first extraction for non-matching types |

### Pattern Matching

Patterns use standard glob syntax:
- `*/*` - Matches all media types
- `image/*` - Matches all image types
- `application/pdf` - Matches only PDF
- `audio/*` - Matches all audio types

## Selection Rules

The extractor selects text using the following rules:

1. **Pattern match**: If item media type matches any pattern, use **last** extraction
2. **No match + fallback_to_first=true**: Use **first** extraction
3. **No match + fallback_to_first=false**: Use **last** extraction
4. **No extractions**: Return `None`

## Usage

### Command Line

Select-override is always used within a pipeline:

```bash
biblicus extract my-corpus --extractor pipeline \
  --config 'steps=[{"extractor_id":"pdf-text"},{"extractor_id":"ocr-rapidocr"},{"extractor_id":"select-override","config":{"media_type_patterns":["image/*"]}}]'
```

### Recipe File

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-override
      config:
        media_type_patterns: ["image/*"]
        fallback_to_first: true
```

```bash
biblicus extract my-corpus --recipe recipe.yml
```

### Python API

```python
from biblicus import Corpus

corpus = Corpus.from_directory("my-corpus")

results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pdf-text"},
            {"extractor_id": "ocr-rapidocr"},
            {
                "extractor_id": "select-override",
                "config": {
                    "media_type_patterns": ["image/*"],
                    "fallback_to_first": True
                }
            }
        ]
    }
)
```

## Examples

### Override Images Only

Use OCR for images, text extraction for everything else:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-override
      config:
        media_type_patterns: ["image/*"]
        fallback_to_first: true
```

For images: Uses ocr-rapidocr (last)
For PDFs: Uses pdf-text (first, due to fallback_to_first=true)

### Override PDFs

Use VLM for PDFs, basic extraction for everything else:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: docling-smol
    - extractor_id: select-override
      config:
        media_type_patterns: ["application/pdf"]
        fallback_to_first: true
```

For PDFs: Uses docling-smol (last matching)
For text files: Uses pass-through-text (first, due to fallback)

### Override Multiple Types

Override specific types with different extractors:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("mixed-corpus")

results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pass-through-text"},
            {"extractor_id": "pdf-text"},
            {"extractor_id": "markitdown"},
            {"extractor_id": "ocr-rapidocr"},
            {
                "extractor_id": "select-override",
                "config": {
                    "media_type_patterns": ["image/*", "application/pdf"],
                    "fallback_to_first": True
                }
            }
        ]
    }
)
```

### Always Use Last

Default behavior (no fallback):

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: docling-smol
    - extractor_id: select-override  # Uses last for all types
```

## Behavior Details

### Pattern Matching

Uses Python's `fnmatch` for glob pattern matching:

```python
# Exact match
"application/pdf" matches "application/pdf" only

# Wildcard
"image/*" matches "image/png", "image/jpeg", etc.

# Universal
"*/*" matches all media types
```

### Last Wins

For matching types, the **last** extraction is always used, regardless of whether earlier extractions exist or are non-empty.

### Fallback Behavior

When `fallback_to_first=true` and media type doesn't match:
- Use **first** extraction instead of last
- Useful for preferring fast extractors for non-override types

When `fallback_to_first=false` (default):
- Use **last** extraction for everything
- Simpler logic, fewer cases

### Pipeline Position

Select-override should be the **last step** in a pipeline. All extraction attempts should come before it.

## When to Use Select-Override

### Use select-override when:
- You want simple media type-based routing
- Last extractor should always win for specific types
- You need basic override logic
- Simplicity is important

### Use select-smart-override when:
- You need confidence-based selection
- Intelligent fallback is desired
- Quality metrics matter

### Use select-text when:
- Order matters (fast first)
- First success is preferred
- No media type routing needed

### Use select-longest-text when:
- Longest output is preferred
- No routing needed

## Best Practices

### Place Override Extractors Last

Put the extractor you want to use for overrides at the end:

```yaml
steps:
  - extractor_id: pdf-text        # Default for PDFs
  - extractor_id: docling-smol    # Override for PDFs
  - extractor_id: select-override
    config:
      media_type_patterns: ["application/pdf"]
```

### Use Fallback for Efficiency

Enable fallback to prefer fast extractors for non-override types:

```yaml
config:
  media_type_patterns: ["image/*"]
  fallback_to_first: true  # Use fast extractors for non-images
```

### Be Specific with Patterns

Use specific patterns to avoid unintended matches:

```yaml
# Good - specific
media_type_patterns: ["image/png", "image/jpeg"]

# Careful - broad
media_type_patterns: ["image/*"]

# Very broad
media_type_patterns: ["*/*"]
```

### Always Place Last

Select-override should always be the final step:

```yaml
steps:
  - extractor-1
  - extractor-2
  - extractor-3
  - select-override  # Always last
```

## Use Cases

### Image-Specific Processing

Use advanced OCR for images, basic extraction for documents:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: ocr-paddleocr-vl  # For images
    - extractor_id: select-override
      config:
        media_type_patterns: ["image/*"]
        fallback_to_first: true
```

### PDF Override

Use VLM for PDFs, simpler extractors for other types:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: markitdown
    - extractor_id: docling-smol      # For PDFs
    - extractor_id: select-override
      config:
        media_type_patterns: ["application/pdf"]
        fallback_to_first: true
```

### Multi-Type Override

Override multiple specific types:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("corpus")

results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pass-through-text"},
            {"extractor_id": "pdf-text"},
            {"extractor_id": "ocr-rapidocr"},
            {
                "extractor_id": "select-override",
                "config": {
                    "media_type_patterns": ["image/*", "application/pdf"],
                    "fallback_to_first": True
                }
            }
        ]
    }
)
```

## Comparison with Other Selectors

| Feature | select-override | select-text | select-longest | select-smart-override |
|---------|----------------|-------------|----------------|----------------------|
| Selection | Last for pattern | First usable | Longest | Intelligent |
| Media type aware | ✅ | ❌ | ❌ | ✅ |
| Confidence aware | ❌ | ❌ | ❌ | ✅ |
| Quality aware | ❌ | ❌ | ✅ | ✅ |
| Complexity | Simple | Simple | Simple | Complex |
| Override control | Last only | None | None | Configurable |

## Related Extractors

### Same Category

- [select-text](select-text.md) - First non-empty selection
- [select-longest-text](select-longest.md) - Longest output selection
- [select-smart-override](select-smart-override.md) - Intelligent routing
- [pipeline](pipeline.md) - Multi-step extraction

### Frequently Combined With

- [pass-through-text](../text-document/pass-through.md) - Text files
- [pdf-text](../text-document/pdf.md) - PDF extraction
- [markitdown](../text-document/markitdown.md) - Office documents
- [ocr-rapidocr](../ocr/rapidocr.md) - Fast OCR
- [docling-smol](../vlm-document/docling-smol.md) - VLM extraction

## See Also

- [Pipeline Utilities Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [Pipeline Configuration](../../EXTRACTION.md#pipelines)
