# Select Text Extractor

**Extractor ID:** `select-text`

**Category:** [Pipeline Utilities](index.md)

## Overview

The select-text extractor chooses the first usable extracted text from previous pipeline steps. It implements a simple, deterministic selection policy for fallback chains where multiple extractors may produce results for the same item.

This extractor is fundamental to pipeline composition, enabling graceful fallback patterns where you try fast extractors first and fall back to more powerful (but slower) alternatives.

## Installation

No additional dependencies required. This extractor is part of the core Biblicus installation.

```bash
pip install biblicus
```

## Supported Media Types

All media types are supported. This extractor operates on previous extraction results, not the raw item.

## Configuration

### Config Schema

```python
class SelectTextExtractorConfig(BaseModel):
    # This extractor requires no configuration
    pass
```

### Configuration Options

This extractor is intentionally minimal and accepts no configuration options.

## Selection Rules

The extractor selects text using the following rules:

1. **Usable text**: Select the first extraction with non-empty text (after stripping whitespace)
2. **Any text**: If no usable text exists, select the first extraction even if empty
3. **No extractions**: If no previous extractions exist, return `None`

This ensures deterministic behavior: given the same pipeline order and inputs, the same extraction is always selected.

## Usage

### Command Line

Select-text is always used within a pipeline:

```bash
biblicus extract my-corpus --extractor pipeline \
  --config 'steps=[{"extractor_id":"pdf-text"},{"extractor_id":"ocr-rapidocr"},{"extractor_id":"select-text"}]'
```

### Recipe File

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-text  # Select first usable result
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
            {"extractor_id": "select-text"}
        ]
    }
)
```

## Examples

### Fast-to-Slow Fallback

Try fast extraction first, fall back to slower methods:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text  # Fastest
    - extractor_id: pdf-text           # Fast
    - extractor_id: ocr-rapidocr       # Moderate
    - extractor_id: docling-smol       # Slower
    - extractor_id: select-text        # Select first result
```

### Text-First Strategy

Prefer text extraction over OCR:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: select-text  # Prefer text over OCR
```

### Multi-Format Corpus

Handle diverse document types:

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
            {"extractor_id": "unstructured"},
            {"extractor_id": "select-text"}
        ]
    }
)
```

### OCR Fallback Chain

Try multiple OCR approaches:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: ocr-rapidocr
    - extractor_id: ocr-paddleocr-vl
    - extractor_id: docling-smol
    - extractor_id: select-text
```

## Behavior Details

### Pipeline Position

Select-text should be the **last step** in a pipeline. All extraction attempts should come before it.

### Empty Results

If all previous extractors produce empty text, select-text returns the first empty result (not `None`). This distinguishes "processed but empty" from "not processed."

### Source Tracking

The selected extraction retains its `producer_extractor_id` and `source_step_index`, allowing you to identify which extractor produced the final text.

### Determinism

Given the same pipeline configuration and inputs, select-text always produces the same result. This makes it suitable for reproducible research and testing.

## When to Use Select-Text

### Use select-text when:
- You want the first successful extraction
- Order matters (try cheap extractors first)
- You need deterministic, predictable selection
- Simplicity is preferred

### Use select-longest-text when:
- Multiple extractors may succeed
- You want the most complete output
- Order doesn't matter

### Use select-override when:
- You want to override specific media types
- Last extractor should win for certain items

### Use select-smart-override when:
- You need intelligent routing by media type
- Quality metrics (confidence, length) matter

## Best Practices

### Order Extractors by Speed

Put faster extractors first:

```yaml
steps:
  - pass-through-text  # Instant
  - pdf-text           # Fast
  - markitdown         # Moderate
  - docling-smol       # Slow
  - select-text
```

### Order Extractors by Accuracy

Or prioritize accuracy:

```yaml
steps:
  - docling-granite    # Best accuracy
  - docling-smol       # Good accuracy
  - ocr-rapidocr       # Basic OCR
  - select-text
```

### Always Place Last

Select-text should always be the final step:

```yaml
steps:
  - extractor-1
  - extractor-2
  - extractor-3
  - select-text  # Always last
```

### Combine with Media Type Routing

Use select-text within smart routing:

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pipeline
  default_config:
    steps:
      - extractor_id: pass-through-text
      - extractor_id: select-text
  overrides:
    - media_type_pattern: "application/pdf"
      extractor: pipeline
      config:
        steps:
          - extractor_id: pdf-text
          - extractor_id: docling-smol
          - extractor_id: select-text
```

## Use Cases

### Heterogeneous Corpus

Process corpora with mixed document types:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: markitdown
    - extractor_id: ocr-rapidocr
    - extractor_id: select-text
```

### Cost Optimization

Try free/cheap methods before expensive APIs:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text  # Free
    - extractor_id: pdf-text           # Free
    - extractor_id: stt-openai         # Paid API
    - extractor_id: select-text
```

### Graceful Degradation

Provide fallbacks for when preferred extractors fail:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: docling-granite  # Preferred
    - extractor_id: docling-smol     # Fallback 1
    - extractor_id: ocr-rapidocr     # Fallback 2
    - extractor_id: metadata-text    # Last resort
    - extractor_id: select-text
```

## Comparison with Other Selectors

| Feature | select-text | select-longest | select-override | select-smart-override |
|---------|-------------|----------------|-----------------|----------------------|
| Selection | First usable | Longest text | Last for pattern | Intelligent |
| Order matters | ✅ | ❌ | Partial | Partial |
| Media type aware | ❌ | ❌ | ✅ | ✅ |
| Confidence aware | ❌ | ❌ | ❌ | ✅ |
| Complexity | Simple | Simple | Moderate | Complex |

## Related Extractors

### Same Category

- [select-longest-text](select-longest.md) - Select longest output
- [select-override](select-override.md) - Simple override selection
- [select-smart-override](select-smart-override.md) - Intelligent routing
- [pipeline](pipeline.md) - Multi-step extraction

### Frequently Combined With

- [pass-through-text](../text-document/pass-through.md) - Text file reading
- [pdf-text](../text-document/pdf.md) - PDF extraction
- [markitdown](../text-document/markitdown.md) - Office documents
- [ocr-rapidocr](../ocr/rapidocr.md) - Fast OCR
- [docling-smol](../vlm-document/docling-smol.md) - Fast VLM

## See Also

- [Pipeline Utilities Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [Pipeline Configuration](../../EXTRACTION.md#pipelines)
