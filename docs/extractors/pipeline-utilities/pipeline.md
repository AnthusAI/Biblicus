# Pipeline Extractor

**Extractor ID:** `pipeline`

**Category:** [Pipeline Utilities](index.md)

## Overview

The pipeline extractor is a configuration shim that enables multi-step extraction workflows. It allows you to compose multiple extractors into a sequential pipeline where each step can build upon or choose from the results of previous steps.

Pipelines are the fundamental composition mechanism in Biblicus, enabling sophisticated extraction strategies like fallback chains, parallel extraction with selection, and media type-specific routing.

## Installation

No additional dependencies required. This extractor is part of the core Biblicus installation.

```bash
pip install biblicus
```

## Supported Media Types

All media types are supported. The pipeline delegates to configured extractors, each handling their own media types.

## Configuration

### Config Schema

```python
class PipelineStepSpec(BaseModel):
    extractor_id: str
    config: Dict[str, Any] = {}

class PipelineExtractorConfig(BaseModel):
    steps: List[PipelineStepSpec]
```

### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `steps` | list | ✅ | Ordered list of extractor steps |
| `steps[].extractor_id` | str | ✅ | Extractor identifier for this step |
| `steps[].config` | dict | ❌ | Configuration for this extractor |

### Constraints

- Must have at least one step
- Cannot include `pipeline` as a step (no nested pipelines)
- Steps are executed in order

## Usage

### Command Line

#### Simple Pipeline

```bash
biblicus extract my-corpus --extractor pipeline \
  --config 'steps=[{"extractor_id":"pdf-text"},{"extractor_id":"select-text"}]'
```

#### Recipe File

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-text
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
            {"extractor_id": "pass-through-text"},
            {"extractor_id": "pdf-text"},
            {"extractor_id": "ocr-rapidocr"},
            {"extractor_id": "select-text"}
        ]
    }
)
```

### With Per-Step Configuration

```python
results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {
                "extractor_id": "pdf-text",
                "config": {"max_pages": 100}
            },
            {
                "extractor_id": "ocr-rapidocr",
                "config": {"min_confidence": 0.7}
            },
            {"extractor_id": "select-longest-text"}
        ]
    }
)
```

## Pipeline Patterns

### Fallback Chain

Try extractors in order, use first success:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text  # Try text first
    - extractor_id: pdf-text           # Then PDF
    - extractor_id: markitdown         # Then Office docs
    - extractor_id: ocr-rapidocr       # Then OCR
    - extractor_id: select-text        # Use first success
```

### Parallel Extraction + Selection

Run all extractors, choose best:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: ocr-rapidocr
    - extractor_id: ocr-paddleocr-vl
    - extractor_id: docling-smol
    - extractor_id: select-longest-text  # Choose longest
```

### Media Type Routing

Route different types to different extractors:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: stt-openai
    - extractor_id: select-text
```

Text files → pass-through-text
PDFs → pdf-text
Images → ocr-rapidocr
Audio → stt-openai

### Smart Override

Intelligent quality-based routing:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text           # Fast
    - extractor_id: docling-smol       # Accurate
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["application/pdf"]
        min_confidence_threshold: 0.7
```

## Examples

### Simple Text Extraction

Handle text and PDFs:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: select-text
```

### Comprehensive Document Processing

Maximum format coverage:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: markitdown
    - extractor_id: unstructured
    - extractor_id: select-longest-text
```

### OCR with Fallback

Try fast OCR, fall back to VLM:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: ocr-rapidocr
    - extractor_id: docling-smol
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["image/*"]
        min_confidence_threshold: 0.75
```

### Multilingual Pipeline

Handle multiple languages:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("multilingual")

results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pass-through-text"},
            {
                "extractor_id": "ocr-paddleocr-vl",
                "config": {"lang": "ch"}  # Chinese
            },
            {
                "extractor_id": "stt-openai",
                "config": {"language": "zh"}  # Chinese audio
            },
            {"extractor_id": "select-text"}
        ]
    }
)
```

### Cost-Optimized Pipeline

Try free methods before paid APIs:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text    # Free
    - extractor_id: pdf-text             # Free
    - extractor_id: markitdown           # Free
    - extractor_id: ocr-rapidocr         # Free
    - extractor_id: stt-deepgram         # Paid
    - extractor_id: select-text
```

## Behavior Details

### Sequential Execution

Steps execute in order. Each step can access results from all previous steps.

### Per-Item Processing

The pipeline runs completely for each item before moving to the next. It does not process all items through step 1, then all through step 2.

### Previous Extractions

Selector extractors (select-text, etc.) receive all previous step outputs for the current item.

### Short-Circuiting

Some patterns enable short-circuiting:
- select-text stops at first success
- Extractors can return None to skip

### Error Handling

Errors in individual steps are recorded but don't halt the pipeline. The pipeline continues with remaining steps.

### No Nested Pipelines

Pipelines cannot contain other pipeline extractors. This prevents infinite recursion and keeps configuration manageable.

## Performance Considerations

### Extraction Order

Order matters for performance:

```yaml
# Fast to slow (efficient)
steps:
  - pass-through-text  # Instant
  - pdf-text           # Fast
  - ocr-rapidocr       # Moderate
  - docling-smol       # Slow
  - select-text        # Stop at first success

# Slow to fast (inefficient)
steps:
  - docling-smol       # Runs for everything!
  - pass-through-text
  - select-text
```

### Selector Choice

- **select-text**: Stops at first success (efficient)
- **select-longest-text**: Runs all extractors (thorough but slow)
- **select-smart-override**: Runs all but intelligently chooses

### API Costs

Pipeline order affects API costs:

```yaml
# Cost-optimized
steps:
  - pass-through-text  # Free
  - pdf-text           # Free
  - stt-openai         # Paid - only runs if free methods fail
  - select-text

# Expensive
steps:
  - stt-openai         # Paid - runs for everything!
  - pass-through-text
  - select-longest-text
```

## Best Practices

### Always Include a Selector

End pipelines with a selection step:

```yaml
steps:
  - extractor-1
  - extractor-2
  - select-text  # Always include
```

### Order by Speed or Priority

```yaml
# By speed (recommended)
steps:
  - fast-extractor
  - moderate-extractor
  - slow-extractor
  - select-text

# By accuracy
steps:
  - best-extractor
  - good-extractor
  - fallback-extractor
  - select-text
```

### Configure Steps Appropriately

Provide per-step configuration when needed:

```yaml
steps:
  - extractor_id: pdf-text
    config:
      max_pages: 100
  - extractor_id: ocr-rapidocr
    config:
      min_confidence: 0.7
  - extractor_id: select-longest-text
```

### Use Recipe Files

For complex pipelines, always use recipe files:

```yaml
# recipe.yml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
      config:
        max_pages: 200
    - extractor_id: markitdown
      config:
        enable_plugins: false
    - extractor_id: ocr-rapidocr
      config:
        min_confidence: 0.6
    - extractor_id: select-smart-override
      config:
        media_type_patterns: ["application/pdf", "image/*"]
        min_confidence_threshold: 0.7
        min_text_length: 20
```

### Test on Samples

Always test pipelines on representative samples:

```bash
# Test on small corpus first
biblicus extract test-corpus --recipe pipeline.yml
```

## Common Pipeline Recipes

### Universal Pipeline

Handle any document type:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: markitdown
    - extractor_id: ocr-rapidocr
    - extractor_id: stt-openai
    - extractor_id: select-text
```

### Quality-First Pipeline

Prioritize accuracy:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: docling-granite
    - extractor_id: docling-smol
    - extractor_id: ocr-rapidocr
    - extractor_id: select-text
```

### Speed-First Pipeline

Prioritize performance:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: metadata-text
    - extractor_id: select-text
```

### Research Pipeline

Maximum extraction quality:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: markitdown
    - extractor_id: ocr-paddleocr-vl
    - extractor_id: docling-granite
    - extractor_id: select-longest-text
```

## Limitations

### No Nested Pipelines

This is invalid:

```yaml
# ❌ Invalid - nested pipelines not allowed
extractor_id: pipeline
config:
  steps:
    - extractor_id: pipeline  # Not allowed!
      config:
        steps: [...]
```

### Linear Flow Only

Pipelines execute linearly. No branching or conditional logic (use selectors instead).

### No Step Communication

Steps cannot directly communicate. They only share via the extraction results list.

## Related Extractors

### Selection Utilities

- [select-text](select-text.md) - First non-empty selection
- [select-longest-text](select-longest.md) - Longest output selection
- [select-override](select-override.md) - Simple override selection
- [select-smart-override](select-smart-override.md) - Intelligent routing

### Frequently Combined Extractors

- [pass-through-text](../text-document/pass-through.md) - Text files
- [pdf-text](../text-document/pdf.md) - PDF extraction
- [markitdown](../text-document/markitdown.md) - Office documents
- [ocr-rapidocr](../ocr/rapidocr.md) - Fast OCR
- [stt-openai](../speech-to-text/openai.md) - Audio transcription
- [docling-smol](../vlm-document/docling-smol.md) - VLM extraction

## See Also

- [Pipeline Utilities Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [Recipe File Format](../../EXTRACTION.md#recipe-files)
