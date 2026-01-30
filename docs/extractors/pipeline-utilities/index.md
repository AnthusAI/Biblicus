# Pipeline Utilities

Meta-extractors for combining, selecting, and orchestrating extraction strategies.

## Overview

Pipeline utility extractors don't extract text themselves. Instead, they coordinate other extractors to:

- Try multiple extractors and select the best result
- Override extraction for specific items
- Chain extractors sequentially
- Implement fallback strategies
- Route items to different extractors

## Available Extractors

### Selection Extractors

#### [select-text](select-text.md)

Selects the first successful extractor from a list.

**Use case**: Fallback chain (try extractor A, fall back to B, then C)

```yaml
extractor_id: select-text
config:
  extractors:
    - pdf-text
    - ocr-rapidocr
    - markitdown
```

#### [select-longest-text](select-longest.md)

Runs all extractors and selects the longest output.

**Use case**: Maximize extracted content when multiple strategies work

```yaml
extractor_id: select-longest-text
config:
  extractors:
    - pdf-text
    - markitdown
    - unstructured
```

### Override Extractors

#### [select-override](select-override.md)

Overrides extraction for specific items by ID.

**Use case**: Manual overrides for problematic documents

```yaml
extractor_id: select-override
config:
  default_extractor: pdf-text
  overrides:
    - item_id: abc123
      extractor: ocr-rapidocr
```

#### [select-smart-override](select-smart-override.md)

Routes items to different extractors based on media type patterns.

**Use case**: Automatic routing by document type

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pdf-text
  overrides:
    - media_type_pattern: "image/.*"
      extractor: ocr-rapidocr
    - media_type_pattern: "audio/.*"
      extractor: stt-deepgram
```

### Composition Extractor

#### [pipeline](pipeline.md)

Chains multiple extractors sequentially, concatenating results.

**Use case**: Combine metadata with content, or process in stages

```yaml
extractor_id: pipeline
config:
  extractors:
    - metadata-text
    - pdf-text
```

## Common Patterns

### PDF Fallback Strategy

Try text extraction first, fall back to OCR:

```yaml
extractor_id: select-text
config:
  extractors:
    - pdf-text          # Fast for PDFs with text
    - docling-smol       # VLM for complex layouts
    - ocr-rapidocr       # Traditional OCR fallback
```

### Media Type Routing

Route different media types to specialized extractors:

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pass-through-text
  overrides:
    - media_type_pattern: "application/pdf"
      extractor: pdf-text
    - media_type_pattern: "image/.*"
      extractor: ocr-rapidocr
    - media_type_pattern: "audio/.*"
      extractor: stt-deepgram
    - media_type_pattern: "application/vnd\\.openxmlformats-officedocument\\..*"
      extractor: markitdown
```

### Maximum Coverage

Extract as much as possible by selecting longest output:

```yaml
extractor_id: select-longest-text
config:
  extractors:
    - pdf-text
    - markitdown
    - unstructured
    - ocr-rapidocr
```

### Metadata + Content

Combine metadata with extracted content:

```yaml
extractor_id: pipeline
config:
  extractors:
    - metadata-text    # Extract title, tags
    - pdf-text         # Extract document content
```

### Selective Override

Use default strategy with exceptions:

```yaml
extractor_id: select-override
config:
  default_extractor: pdf-text
  overrides:
    - item_id: problematic-doc-123
      extractor: ocr-rapidocr
    - item_id: complex-layout-456
      extractor: docling-granite
```

## Decision Tree

### Which Utility Extractor to Use?

1. **Need fallback behavior?** → Use [select-text](select-text.md)
   - Tries extractors in order, stops at first success

2. **Want to maximize output?** → Use [select-longest-text](select-longest.md)
   - Runs all extractors, picks longest result

3. **Need per-document overrides?** → Use [select-override](select-override.md)
   - Override specific items by ID

4. **Want automatic routing?** → Use [select-smart-override](select-smart-override.md)
   - Route by media type pattern

5. **Need sequential processing?** → Use [pipeline](pipeline.md)
   - Chain extractors, concatenate results

## Performance Considerations

### select-text (Short-Circuit)

- Runs extractors sequentially
- Stops at first success
- **Fast**: Only runs what's needed
- **Cost-effective**: Minimal API calls

### select-longest-text (Parallel)

- Runs all extractors
- Compares all outputs
- **Slower**: Runs everything
- **Higher cost**: All API calls executed

### select-override (Conditional)

- Routes to appropriate extractor
- **Fast**: Single extractor per item
- **Efficient**: No redundant processing

### select-smart-override (Pattern-Based)

- Routes by media type
- **Fast**: Single extractor per item
- **Flexible**: Pattern-based routing

### pipeline (Sequential)

- Runs extractors in order
- Concatenates all results
- **Predictable**: Always runs all steps
- **Comprehensive**: Captures all outputs

## See Also

- [Extractors Overview](../index.md)
- [Text & Document Processing](../text-document/index.md)
- [OCR Extractors](../ocr/index.md)
- [VLM Extractors](../vlm-document/index.md)
- [Speech-to-Text](../speech-to-text/index.md)
