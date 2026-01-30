# Select Smart Override Extractor

**Extractor ID:** `select-smart-override`

**Category:** [Pipeline Utilities](index.md)

## Overview

The select-smart-override extractor implements intelligent media type-based routing with quality-aware selection. It compares extraction results using confidence scores and text length to make smart decisions about which output to use.

This is the most sophisticated selector in Biblicus, combining media type routing with quality assessment. It's ideal for production pipelines where you want to override specific types with higher-quality extractors while falling back intelligently when those extractors fail or produce poor results.

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
class SelectSmartOverrideConfig(BaseModel):
    media_type_patterns: List[str] = ["*/*"]
    min_confidence_threshold: float = 0.7
    min_text_length: int = 10
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `media_type_patterns` | list[str] | `["*/*"]` | Glob patterns for media types to consider |
| `min_confidence_threshold` | float | `0.7` | Minimum confidence to consider extraction good (0.0-1.0) |
| `min_text_length` | int | `10` | Minimum text length for meaningful content |

## Selection Rules

For items matching configured patterns, the extractor applies smart selection:

1. **Last is meaningful**: If the last extraction has meaningful content, use it
2. **Previous is better**: If last is empty/low-quality but a previous extraction is good, use the previous one
3. **Use last anyway**: Otherwise, use the last extraction (even if empty)

For non-matching items:
- Always use the **last** extraction

### Meaningful Content

Content is considered meaningful when:
- Text length (stripped) >= `min_text_length` **AND**
- Confidence >= `min_confidence_threshold` OR confidence is not available

This allows confident, substantial results to override less complete attempts.

## Usage

### Command Line

Select-smart-override is always used within a pipeline:

```bash
biblicus extract my-corpus --extractor pipeline \
  --config 'steps=[{"extractor_id":"pdf-text"},{"extractor_id":"ocr-rapidocr"},{"extractor_id":"select-smart-override","config":{"media_type_patterns":["application/pdf"]}}]'
```

### Recipe File

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["application/pdf"]
        min_confidence_threshold: 0.7
        min_text_length: 10
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
                "extractor_id": "select-smart-override",
                "config": {
                    "media_type_patterns": ["application/pdf"],
                    "min_confidence_threshold": 0.75,
                    "min_text_length": 20
                }
            }
        ]
    }
)
```

## Examples

### Smart PDF Processing

Use OCR only when text extraction fails:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text      # Fast, works for digital PDFs
    - extractor_id: ocr-rapidocr  # Slower, for scanned PDFs
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["application/pdf"]
        min_confidence_threshold: 0.6
        min_text_length: 10
```

If pdf-text produces good content, use it. If empty/failed, use ocr-rapidocr.

### Image with VLM Fallback

Try fast OCR first, fall back to VLM for poor results:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: ocr-rapidocr   # Fast
    - extractor_id: docling-smol   # Accurate but slower
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["image/*"]
        min_confidence_threshold: 0.7
        min_text_length: 20
```

If RapidOCR succeeds with high confidence, use it. Otherwise, use VLM.

### High-Confidence Override

Only use expensive extractor when cheap one fails:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("documents")

results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "markitdown"},       # Fast
            {"extractor_id": "docling-granite"},  # Expensive
            {
                "extractor_id": "select-smart-override",
                "config": {
                    "media_type_patterns": ["application/pdf", "image/*"],
                    "min_confidence_threshold": 0.8,  # High bar
                    "min_text_length": 50
                }
            }
        ]
    }
)
```

### Mixed Corpus with Smart Routing

Different strategies for different media types:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: docling-smol
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["application/pdf", "image/*"]
        min_confidence_threshold: 0.7
        min_text_length: 15
```

## Behavior Details

### Pattern Matching

Uses Python's `fnmatch` for glob pattern matching:

```python
# Specific
"application/pdf" matches PDFs only

# Wildcard
"image/*" matches all images

# Multiple types
["application/pdf", "image/*"] matches PDFs and images
```

### Confidence Handling

- **With confidence**: Must meet `min_confidence_threshold`
- **No confidence**: Passes confidence check (assume good)
- **Mixed**: Earlier extraction with confidence can override later without

### Text Length

Text length is measured **after stripping whitespace**:

```python
"   Hello   " → length 5 (not 11)
```

### Pipeline Position

Select-smart-override should be the **last step** in a pipeline. All extraction attempts should come before it.

### Comparison with Last

The smart override compares the **last extraction** against **all previous** extractions:

1. Check if last is meaningful
2. If not, find the most recent meaningful previous extraction
3. Use that one if it has good confidence
4. Otherwise, use last anyway

## When to Use Select-Smart-Override

### Use select-smart-override when:
- You want intelligent quality-based selection
- Confidence scores are available
- Some extractors may fail or produce poor output
- Cost/speed optimization matters

### Use select-override when:
- Simple last-wins logic is sufficient
- No quality assessment needed
- All extractors are equally reliable

### Use select-text when:
- First success is preferred
- No quality comparison needed
- Speed is critical

### Use select-longest-text when:
- Length is the only quality metric
- No confidence scores available

## Best Practices

### Order Extractors by Cost/Speed

Put cheaper/faster extractors first:

```yaml
steps:
  - extractor_id: pdf-text         # Free, fast
  - extractor_id: ocr-rapidocr     # Free, moderate
  - extractor_id: docling-granite  # Expensive, slow
  - extractor_id: select-smart-override
```

### Tune Thresholds

Adjust thresholds based on your needs:

```yaml
# Conservative - prefer high quality
config:
  min_confidence_threshold: 0.8
  min_text_length: 50

# Aggressive - prefer fast extractors
config:
  min_confidence_threshold: 0.5
  min_text_length: 10
```

### Use with Confidence-Producing Extractors

Smart override works best with extractors that produce confidence scores:
- OCR extractors (RapidOCR, PaddleOCR-VL)
- VLM extractors (potentially)

### Monitor Selection Behavior

Track which extractors are being selected:

```python
# The selected extraction retains producer_extractor_id
# Use this to analyze selection patterns
```

### Always Place Last

Select-smart-override should always be the final step:

```yaml
steps:
  - extractor-1
  - extractor-2
  - extractor-3
  - select-smart-override  # Always last
```

## Use Cases

### Cost Optimization

Try free methods before expensive APIs:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text           # Free
    - extractor_id: stt-openai         # Paid
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["application/pdf", "audio/*"]
        min_confidence_threshold: 0.6
```

### Quality Fallback

Use fast extractors when they work, expensive when they don't:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: ocr-rapidocr    # Fast
    - extractor_id: docling-granite # Accurate
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["image/*"]
        min_confidence_threshold: 0.75
        min_text_length: 20
```

### Scanned Document Detection

Auto-detect scanned PDFs and apply OCR:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text         # Fails on scanned PDFs
    - extractor_id: ocr-rapidocr     # Works on scanned PDFs
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["application/pdf"]
        min_text_length: 50  # PDF text extraction should get substantial content
```

### Production Pipeline

Robust multi-format processing:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("production-corpus")

results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pass-through-text"},
            {"extractor_id": "pdf-text"},
            {"extractor_id": "markitdown"},
            {"extractor_id": "ocr-rapidocr"},
            {"extractor_id": "docling-smol"},
            {
                "extractor_id": "select-smart-override",
                "config": {
                    "media_type_patterns": ["*/*"],
                    "min_confidence_threshold": 0.7,
                    "min_text_length": 15
                }
            }
        ]
    }
)
```

## Tuning Guidelines

### Confidence Threshold

- **0.5-0.6**: Permissive (accept most results)
- **0.7**: Balanced (default)
- **0.8-0.9**: Strict (only high-confidence)

### Text Length

- **5-10**: Short snippets acceptable
- **10-20**: Moderate content required
- **50+**: Substantial content required

### Combined Tuning

```yaml
# For screenshots/images (often short text)
config:
  min_confidence_threshold: 0.7
  min_text_length: 5

# For documents (expect longer text)
config:
  min_confidence_threshold: 0.7
  min_text_length: 50
```

## Comparison with Other Selectors

| Feature | select-smart-override | select-override | select-text | select-longest |
|---------|----------------------|----------------|-------------|----------------|
| Selection | Intelligent | Last for pattern | First usable | Longest |
| Media type aware | ✅ | ✅ | ❌ | ❌ |
| Confidence aware | ✅ | ❌ | ❌ | ❌ |
| Length aware | ✅ | ❌ | ❌ | ✅ |
| Complexity | High | Low | Low | Low |
| Best for | Production | Simple override | Fast fallback | Quality comparison |

## Related Extractors

### Same Category

- [select-text](select-text.md) - First non-empty selection
- [select-longest-text](select-longest.md) - Longest output selection
- [select-override](select-override.md) - Simple override selection
- [pipeline](pipeline.md) - Multi-step extraction

### Frequently Combined With

- [pdf-text](../text-document/pdf.md) - Fast PDF extraction
- [ocr-rapidocr](../ocr/rapidocr.md) - Fast OCR with confidence
- [ocr-paddleocr-vl](../ocr/paddleocr-vl.md) - Advanced OCR with confidence
- [docling-smol](../vlm-document/docling-smol.md) - VLM extraction
- [docling-granite](../vlm-document/docling-granite.md) - High-accuracy VLM

## See Also

- [Pipeline Utilities Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [Pipeline Configuration](../../EXTRACTION.md#pipelines)
