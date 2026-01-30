# RapidOCR Extractor

**Extractor ID:** `ocr-rapidocr`

**Category:** [OCR Extractors](index.md)

## Overview

The RapidOCR extractor performs optical character recognition on image files using the RapidOCR library with ONNX Runtime. It provides fast, accurate OCR without requiring external services or GPU acceleration.

RapidOCR is built on ONNX Runtime and uses optimized OCR models for efficient text detection and recognition. It's ideal for processing image corpora where embedded text needs to be extracted for search or analysis.

## Installation

RapidOCR is an optional dependency:

```bash
pip install "biblicus[ocr]"
```

This installs `rapidocr-onnxruntime` which includes all necessary models and the ONNX Runtime.

## Supported Media Types

- `image/png` - PNG images
- `image/jpeg` - JPEG/JPG images
- `image/gif` - GIF images
- `image/bmp` - BMP images
- `image/tiff` - TIFF images
- `image/webp` - WebP images

Only image media types are processed. Other media types are automatically skipped.

## Configuration

### Config Schema

```python
class RapidOcrExtractorConfig(BaseModel):
    min_confidence: float = 0.5  # Minimum confidence threshold (0.0-1.0)
    joiner: str = "\n"            # String to join recognized lines
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `min_confidence` | float | `0.5` | Minimum per-line confidence to include (0.0-1.0) |
| `joiner` | str | `"\n"` | String used to join recognized text lines |

## Usage

### Command Line

#### Basic Usage

```bash
# Extract text from images
biblicus extract my-corpus --extractor ocr-rapidocr
```

#### Custom Configuration

```bash
# Higher confidence threshold
biblicus extract my-corpus --extractor ocr-rapidocr \
  --config min_confidence=0.75

# Use space as joiner instead of newline
biblicus extract my-corpus --extractor ocr-rapidocr \
  --config joiner=" "
```

#### Recipe File

```yaml
extractor_id: ocr-rapidocr
config:
  min_confidence: 0.6
  joiner: "\n"
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
results = corpus.extract_text(extractor_id="ocr-rapidocr")

# Extract with custom config
results = corpus.extract_text(
    extractor_id="ocr-rapidocr",
    config={
        "min_confidence": 0.7,
        "joiner": " "
    }
)
```

### In Pipeline

#### OCR Fallback

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-text
```

#### Media Type Routing

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pass-through-text
  overrides:
    - media_type_pattern: "image/.*"
      extractor: ocr-rapidocr
```

## Examples

### Screenshot Collection

Extract text from screenshots:

```bash
biblicus extract screenshots --extractor ocr-rapidocr
```

### Scanned Documents

Process scanned document images:

```bash
biblicus extract scans --extractor ocr-rapidocr \
  --config min_confidence=0.7
```

### Document Photos

Extract text from photos of documents:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("document-photos")

results = corpus.extract_text(
    extractor_id="ocr-rapidocr",
    config={"min_confidence": 0.6}
)
```

### High-Confidence Extraction

Only include very confident results:

```bash
biblicus extract images --extractor ocr-rapidocr \
  --config min_confidence=0.9
```

## Confidence Scores

RapidOCR provides per-line confidence scores:

- **Confidence Range**: 0.0 to 1.0
- **Default Threshold**: 0.5 (50%)
- **Returned Confidence**: Average of accepted lines

The extractor:
1. Recognizes text lines with individual confidence scores
2. Filters lines below `min_confidence` threshold
3. Returns the average confidence of accepted lines

### Interpreting Confidence

- **0.9-1.0**: Excellent recognition
- **0.7-0.9**: Good recognition
- **0.5-0.7**: Acceptable recognition
- **0.0-0.5**: Poor recognition (filtered by default)

## Performance

- **Speed**: Fast (0.5-2 seconds per image)
- **Memory**: Moderate (models loaded once)
- **Accuracy**: Good for clear text, moderate for degraded images

RapidOCR is significantly faster than VLM approaches while maintaining good accuracy for standard OCR tasks.

## Error Handling

### Missing Dependency

If RapidOCR is not installed:

```
ExtractionRunFatalError: RapidOCR extractor requires an optional dependency.
Install it with pip install "biblicus[ocr]".
```

### Non-Image Items

Non-image items are silently skipped (returns `None`).

### No Text Recognized

Images without recognizable text produce empty extracted text and are counted in `extracted_empty_items`.

### Per-Item Errors

Processing errors for individual images are recorded but don't halt extraction.

## Use Cases

### Screenshot Archives

Extract text from UI screenshots:

```bash
biblicus extract screenshots --extractor ocr-rapidocr
```

### Scanned Document Collections

Process scanned paper documents:

```bash
biblicus extract scans --extractor ocr-rapidocr
```

### Photo Documentation

Extract text from photos of documents or signs:

```bash
biblicus extract photos --extractor ocr-rapidocr
```

### Mixed Media Pipeline

Combine with other extractors:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-text
```

## When to Use RapidOCR vs Alternatives

### Use RapidOCR when:
- Images contain primarily text
- You need fast, local OCR
- Text is reasonably clear
- No GPU is required

### Use PaddleOCR-VL when:
- Text is in CJK languages (Chinese, Japanese, Korean)
- You need better accuracy for complex layouts
- API-based processing is acceptable

### Use VLM extractors when:
- Images have complex layouts
- You need document understanding beyond text
- Tables, equations, or diagrams are present
- Highest accuracy is critical

### Use text extractors when:
- Documents have embedded text layers
- PDFs are born-digital (not scanned)
- You want instant extraction

## Best Practices

### Tune Confidence Threshold

Test different thresholds on sample images:

```bash
# Try different confidence levels
biblicus extract test-images --extractor ocr-rapidocr \
  --config min_confidence=0.7
```

### Monitor Confidence Scores

Check average confidence in results:

```python
results = corpus.extract_text(extractor_id="ocr-rapidocr")
# Confidence is available in extraction metadata
```

### Use for Clear Text

RapidOCR works best with:
- Clear, high-resolution images
- Good lighting/contrast
- Standard fonts
- Horizontal text orientation

### Consider Alternatives for:
- Very low quality images
- Complex multi-column layouts
- Mixed text/graphics
- Rotated or skewed text

## Image Quality Tips

For best OCR results:
- **Resolution**: 300+ DPI preferred
- **Contrast**: High contrast between text and background
- **Clarity**: Sharp focus, not blurry
- **Orientation**: Straight, not skewed
- **Lighting**: Even illumination

## Related Extractors

### Same Category

- [ocr-paddleocr-vl](paddleocr-vl.md) - PaddleOCR VL with better CJK support

### Alternatives

- [docling-smol](../vlm-document/docling-smol.md) - Fast VLM for complex documents
- [docling-granite](../vlm-document/docling-granite.md) - High-accuracy VLM
- [pdf-text](../text-document/pdf.md) - Fast text extraction from PDFs
- [markitdown](../text-document/markitdown.md) - Office document conversion

### Pipeline Utilities

- [select-text](../pipeline-utilities/select-text.md) - First non-empty selection
- [select-longest-text](../pipeline-utilities/select-longest.md) - Choose longest output
- [select-smart-override](../pipeline-utilities/select-smart-override.md) - Media type routing
- [pipeline](../pipeline-utilities/pipeline.md) - Multi-step extraction

## See Also

- [OCR Extractors Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [RapidOCR GitHub](https://github.com/RapidAI/RapidOCR)
