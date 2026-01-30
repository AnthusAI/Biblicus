# Select Longest Text Extractor

**Extractor ID:** `select-longest-text`

**Category:** [Pipeline Utilities](index.md)

## Overview

The select-longest-text extractor chooses the extraction with the most text from previous pipeline steps. It implements a length-based selection policy for scenarios where multiple extractors may produce different outputs for the same item.

This extractor is useful when you want to maximize extracted content, assuming that longer outputs are more complete. It's ideal for comparing different extraction methods and choosing the one that extracts the most information.

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
class SelectLongestTextExtractorConfig(BaseModel):
    # This extractor requires no configuration
    pass
```

### Configuration Options

This extractor currently accepts no configuration options.

## Selection Rules

The extractor selects text using the following rules:

1. **Longest usable text**: Select the extraction with the greatest character count (after stripping whitespace)
2. **Tie breaking**: If multiple extractions have the same length, select the earliest (lowest step index)
3. **No usable text**: If all extractions are empty, select the earliest extraction
4. **No extractions**: If no previous extractions exist, return `None`

This provides deterministic selection that favors completeness.

## Usage

### Command Line

Select-longest-text is always used within a pipeline:

```bash
biblicus extract my-corpus --extractor pipeline \
  --config 'steps=[{"extractor_id":"ocr-rapidocr"},{"extractor_id":"docling-smol"},{"extractor_id":"select-longest-text"}]'
```

### Recipe File

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: ocr-rapidocr
    - extractor_id: docling-smol
    - extractor_id: select-longest-text  # Select longest result
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
            {"extractor_id": "ocr-rapidocr"},
            {"extractor_id": "docling-smol"},
            {"extractor_id": "select-longest-text"}
        ]
    }
)
```

## Examples

### Compare OCR Methods

Try multiple OCR approaches and keep the best:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: ocr-rapidocr
    - extractor_id: ocr-paddleocr-vl
    - extractor_id: select-longest-text  # Keep most complete
```

### Compare VLM Models

Test different VLM models and select the most thorough:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: docling-smol
    - extractor_id: docling-granite
    - extractor_id: select-longest-text
```

### Maximize Extraction

Try all available methods and keep the most complete:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("complex-docs")

results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pdf-text"},
            {"extractor_id": "markitdown"},
            {"extractor_id": "docling-smol"},
            {"extractor_id": "select-longest-text"}
        ]
    }
)
```

### Hybrid Extraction

Combine text extraction with OCR:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-longest-text
```

## Behavior Details

### Length Calculation

Text length is calculated after stripping whitespace. This prevents padding or formatting differences from affecting selection.

### Pipeline Position

Select-longest-text should be the **last step** in a pipeline. All extraction attempts should come before it.

### Parallel Extraction

All extractors in the pipeline run on the same item. This differs from select-text which stops at the first success.

### Source Tracking

The selected extraction retains its `producer_extractor_id` and `source_step_index`, allowing you to identify which extractor produced the final text.

### Performance Consideration

Since all extractors run (not just until first success), this approach is slower but more thorough than select-text.

## When to Use Select-Longest-Text

### Use select-longest-text when:
- You want the most complete extraction
- Multiple extractors may produce different results
- Completeness is more important than speed
- You're comparing extractor quality

### Use select-text when:
- Order matters (fast extractors first)
- You want to stop at first success
- Speed is more important than completeness

### Use select-override when:
- You want media type-based routing
- Last extractor should win for patterns

### Use select-smart-override when:
- You need intelligent routing
- Quality metrics (confidence, length) matter

## Best Practices

### Combine Similar Extractors

Group extractors that target the same content type:

```yaml
# OCR comparison
steps:
  - ocr-rapidocr
  - ocr-paddleocr-vl
  - select-longest-text

# VLM comparison
steps:
  - docling-smol
  - docling-granite
  - select-longest-text
```

### Consider Performance Trade-offs

Running all extractors is expensive:

```yaml
# Expensive but thorough
steps:
  - pdf-text           # Fast
  - markitdown         # Moderate
  - docling-smol       # Slow
  - docling-granite    # Slower
  - select-longest-text
```

Consider using select-text for performance:

```yaml
# Faster fallback chain
steps:
  - pdf-text
  - markitdown
  - docling-smol
  - select-text  # Stop at first success
```

### Always Place Last

Select-longest-text should always be the final step:

```yaml
steps:
  - extractor-1
  - extractor-2
  - extractor-3
  - select-longest-text  # Always last
```

### Monitor Extraction Statistics

Track which extractors produce the longest outputs:

```python
results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "ocr-rapidocr"},
            {"extractor_id": "docling-smol"},
            {"extractor_id": "select-longest-text"}
        ]
    }
)

# Check which extractor was selected most often
# (This requires inspecting extraction metadata)
```

## Use Cases

### Quality Comparison

Compare different extractors to find the best:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: markitdown
    - extractor_id: unstructured
    - extractor_id: docling-smol
    - extractor_id: select-longest-text
```

### Scanned PDF Processing

Try both text extraction and OCR:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text       # Works for digital PDFs
    - extractor_id: ocr-rapidocr   # Works for scanned PDFs
    - extractor_id: select-longest-text
```

### Maximize Content Extraction

Extract as much text as possible:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("documents")

# Try everything, keep the best
results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pass-through-text"},
            {"extractor_id": "pdf-text"},
            {"extractor_id": "markitdown"},
            {"extractor_id": "ocr-rapidocr"},
            {"extractor_id": "docling-smol"},
            {"extractor_id": "select-longest-text"}
        ]
    }
)
```

### Benchmark Extractors

Systematically compare extractor performance:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: markitdown
    - extractor_id: unstructured
    - extractor_id: docling-smol
    - extractor_id: select-longest-text
```

## Comparison with Other Selectors

| Feature | select-longest | select-text | select-override | select-smart-override |
|---------|----------------|-------------|-----------------|----------------------|
| Selection | Longest text | First usable | Last for pattern | Intelligent |
| All run | ✅ | ❌ | ✅ | ✅ |
| Order matters | Tie-break only | ✅ | Partial | Partial |
| Performance | Slow | Fast | Moderate | Moderate |
| Use case | Quality comparison | Fast fallback | Media routing | Smart routing |

## Performance Considerations

### All Extractors Run

Unlike select-text, **all extractors run** regardless of which produces the longest output. This means:

- Extraction takes as long as the slowest extractor
- API costs are incurred for all API-based extractors
- Computational resources are used for all local extractors

### When Performance Matters

If speed is critical, consider:
- Using select-text instead
- Reducing the number of extractors in the pipeline
- Using only fast extractors

### When Completeness Matters

If quality is critical, select-longest-text is ideal:
- All extraction methods are attempted
- The most thorough result is selected
- No potential text is missed

## Related Extractors

### Same Category

- [select-text](select-text.md) - First non-empty selection
- [select-override](select-override.md) - Simple override selection
- [select-smart-override](select-smart-override.md) - Intelligent routing
- [pipeline](pipeline.md) - Multi-step extraction

### Frequently Combined With

- [pdf-text](../text-document/pdf.md) - Fast PDF extraction
- [markitdown](../text-document/markitdown.md) - Office documents
- [ocr-rapidocr](../ocr/rapidocr.md) - Fast OCR
- [ocr-paddleocr-vl](../ocr/paddleocr-vl.md) - Advanced OCR
- [docling-smol](../vlm-document/docling-smol.md) - Fast VLM
- [docling-granite](../vlm-document/docling-granite.md) - High-accuracy VLM

## See Also

- [Pipeline Utilities Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [Pipeline Configuration](../../EXTRACTION.md#pipelines)
