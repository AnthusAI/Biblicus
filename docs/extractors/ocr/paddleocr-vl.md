# PaddleOCR-VL Extractor

**Extractor ID:** `ocr-paddleocr-vl`

**Category:** [OCR Extractors](index.md)

## Overview

The PaddleOCR-VL extractor uses PaddleOCR's vision-language model for optical character recognition. It provides enhanced accuracy for complex layouts and multilingual text, especially Chinese, Japanese, and Korean (CJK) languages.

PaddleOCR-VL combines traditional OCR with vision-language understanding to achieve better results on challenging images. It supports both local inference and API-based processing via HuggingFace Inference API.

## Installation

### Local Inference

For local processing, install the PaddleOCR library:

```bash
pip install "biblicus[paddleocr]"
```

### API-Based Inference

For API-based processing via HuggingFace:

```bash
pip install biblicus
```

No additional dependencies required, but you'll need a HuggingFace API key.

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
class PaddleOcrVlExtractorConfig(BaseModel):
    backend: InferenceBackendConfig = InferenceBackendConfig()
    min_confidence: float = 0.5
    joiner: str = "\n"
    use_angle_cls: bool = True
    lang: str = "en"
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `backend.mode` | str | `local` | Inference mode: `local` or `api` |
| `backend.api_provider` | str | `huggingface` | API provider (when mode is `api`) |
| `backend.api_key` | str or null | `null` | API key (or use env var) |
| `backend.model_id` | str or null | `null` | Model ID for API inference |
| `min_confidence` | float | `0.5` | Minimum confidence threshold (0.0-1.0) |
| `joiner` | str | `"\n"` | String to join recognized lines |
| `use_angle_cls` | bool | `true` | Use angle classification for rotated text |
| `lang` | str | `"en"` | Language code (`en`, `ch`, `japan`, `korean`, etc.) |

## Usage

### Command Line

#### Basic Usage (Local)

```bash
# Extract with local inference
biblicus extract my-corpus --extractor ocr-paddleocr-vl
```

#### API-Based Inference

```bash
# Extract using HuggingFace API
export HUGGINGFACE_API_KEY="your-key-here"

biblicus extract my-corpus --extractor ocr-paddleocr-vl \
  --config 'backend={"mode":"api","api_provider":"huggingface"}'
```

#### Language Configuration

```bash
# Process Chinese text
biblicus extract my-corpus --extractor ocr-paddleocr-vl \
  --config lang=ch

# Process Japanese text
biblicus extract my-corpus --extractor ocr-paddleocr-vl \
  --config lang=japan
```

#### Recipe File

```yaml
extractor_id: ocr-paddleocr-vl
config:
  backend:
    mode: local
  min_confidence: 0.6
  use_angle_cls: true
  lang: en
```

```bash
biblicus extract my-corpus --recipe recipe.yml
```

### Python API

```python
from biblicus import Corpus

# Load corpus
corpus = Corpus.from_directory("my-corpus")

# Extract with defaults (local inference)
results = corpus.extract_text(extractor_id="ocr-paddleocr-vl")

# Extract with API backend
results = corpus.extract_text(
    extractor_id="ocr-paddleocr-vl",
    config={
        "backend": {
            "mode": "api",
            "api_provider": "huggingface"
        },
        "min_confidence": 0.7
    }
)

# Extract Chinese text
results = corpus.extract_text(
    extractor_id="ocr-paddleocr-vl",
    config={"lang": "ch"}
)
```

### In Pipeline

#### OCR with Fallback

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: ocr-paddleocr-vl
    - extractor_id: select-text
```

#### Multi-Language Processing

```yaml
extractor_id: select-smart-override
config:
  default_extractor: ocr-rapidocr
  overrides:
    - media_type_pattern: "image/.*"
      extractor: ocr-paddleocr-vl
      config:
        lang: ch
```

## Examples

### Chinese Document Processing

Extract Chinese text with high accuracy:

```bash
biblicus extract chinese-docs --extractor ocr-paddleocr-vl \
  --config lang=ch
```

### Rotated Text Handling

Use angle classification for rotated images:

```bash
biblicus extract rotated-images --extractor ocr-paddleocr-vl \
  --config use_angle_cls=true
```

### API-Based Processing

Use HuggingFace API for serverless OCR:

```python
from biblicus import Corpus
import os

os.environ["HUGGINGFACE_API_KEY"] = "your-key"

corpus = Corpus.from_directory("images")

results = corpus.extract_text(
    extractor_id="ocr-paddleocr-vl",
    config={
        "backend": {
            "mode": "api",
            "api_provider": "huggingface"
        }
    }
)
```

### High-Confidence Extraction

Only include very confident results:

```bash
biblicus extract images --extractor ocr-paddleocr-vl \
  --config min_confidence=0.8
```

## Inference Backends

### Local Inference

**Pros:**
- Full control over processing
- No API costs
- Works offline
- Supports all configuration options

**Cons:**
- Requires installing PaddleOCR
- Uses local compute resources
- Slower initial model loading

### API Inference (HuggingFace)

**Pros:**
- No local dependencies
- Serverless/scalable
- No model download required

**Cons:**
- Requires API key
- API rate limits apply
- Network dependency
- Limited configuration options

## Language Support

PaddleOCR-VL supports many languages:

- `en` - English
- `ch` - Chinese (Simplified)
- `chinese_cht` - Chinese (Traditional)
- `japan` - Japanese
- `korean` - Korean
- `latin` - Latin script languages
- `arabic` - Arabic
- `cyrillic` - Cyrillic script languages
- `devanagari` - Devanagari script languages

And many more. See PaddleOCR documentation for the full list.

## Performance

### Local Inference
- **Speed**: Moderate (2-5 seconds per image)
- **Memory**: High (model loaded in memory)
- **Accuracy**: Excellent for CJK, good for Latin

### API Inference
- **Speed**: Variable (depends on API latency)
- **Memory**: Minimal (no local model)
- **Accuracy**: Good (model-dependent)

## Error Handling

### Missing Dependency (Local Mode)

If PaddleOCR is not installed:

```
ExtractionRunFatalError: PaddleOCR-VL extractor (local mode) requires paddleocr.
Install it with pip install "biblicus[paddleocr]".
```

### Missing API Key (API Mode)

If API key is not configured:

```
ExtractionRunFatalError: PaddleOCR-VL extractor (API mode) requires an API key for HUGGINGFACE.
Set HUGGINGFACE_API_KEY environment variable or configure huggingface in user config.
```

### Non-Image Items

Non-image items are silently skipped (returns `None`).

### No Text Recognized

Images without recognizable text produce empty extracted text and are counted in `extracted_empty_items`.

## Use Cases

### Chinese Document Processing

Ideal for Chinese text extraction:

```bash
biblicus extract chinese-docs --extractor ocr-paddleocr-vl \
  --config lang=ch
```

### Japanese Manga/Comics

Extract Japanese text from comics:

```bash
biblicus extract manga --extractor ocr-paddleocr-vl \
  --config lang=japan
```

### Multi-Language Corpora

Process documents in multiple languages:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("multilingual")

results = corpus.extract_text(
    extractor_id="ocr-paddleocr-vl",
    config={"lang": "ch"}  # or detect automatically
)
```

### Rotated Document Photos

Handle photos taken at angles:

```bash
biblicus extract photos --extractor ocr-paddleocr-vl \
  --config use_angle_cls=true
```

## When to Use PaddleOCR-VL vs Alternatives

### Use PaddleOCR-VL when:
- Processing CJK languages (Chinese, Japanese, Korean)
- Text may be rotated or skewed
- You need better accuracy than basic OCR
- Complex layouts require VL understanding

### Use RapidOCR when:
- Processing primarily English text
- Speed is more important than accuracy
- Simple layouts with clear text
- Local inference only

### Use VLM extractors when:
- Documents have complex visual layouts
- You need table/equation understanding
- Highest accuracy is critical
- Multi-modal understanding is needed

## Configuration via User Config

Configure API keys in `~/.biblicus/config.yml`:

```yaml
huggingface:
  api_key: YOUR_KEY_HERE
```

Or use environment variables:

```bash
export HUGGINGFACE_API_KEY="your-key"
```

## Best Practices

### Choose Appropriate Language

Set the `lang` parameter to match your content:

```yaml
config:
  lang: ch  # For Chinese content
```

### Tune Confidence Threshold

Test different thresholds on samples:

```bash
biblicus extract test-images --extractor ocr-paddleocr-vl \
  --config min_confidence=0.7
```

### Use Local for Batch Processing

For large corpora, local inference is more cost-effective:

```yaml
config:
  backend:
    mode: local
```

### Use API for Quick Tests

For small jobs or testing, API mode is convenient:

```yaml
config:
  backend:
    mode: api
    api_provider: huggingface
```

## Related Extractors

### Same Category

- [ocr-rapidocr](rapidocr.md) - Fast traditional OCR

### Alternatives

- [docling-smol](../vlm-document/docling-smol.md) - Fast VLM for documents
- [docling-granite](../vlm-document/docling-granite.md) - High-accuracy VLM
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
- [Inference Backend Configuration](../../USER_CONFIGURATION.md)
- [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR)
