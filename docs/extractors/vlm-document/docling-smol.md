# SmolDocling-256M Extractor

**Extractor ID:** `docling-smol`

**Category:** [Vision-Language Models (VLM)](index.md)

## Overview

The SmolDocling-256M extractor uses IBM Research's SmolDocling vision-language model for fast, accurate document understanding. It combines visual layout analysis with semantic text extraction to handle complex documents.

SmolDocling-256M is a 256-million parameter VLM optimized for document processing. It achieves 6.15 seconds per page on Apple Silicon with MLX, making it one of the fastest VLM extractors while maintaining excellent accuracy.

## Installation

### Transformers Backend (Cross-Platform)

```bash
pip install "biblicus[docling]"
```

### MLX Backend (Apple Silicon - Recommended)

```bash
pip install "biblicus[docling-mlx]"
```

The MLX backend provides 2-3x faster inference on Apple Silicon (M1/M2/M3/M4) with lower memory usage.

## Supported Media Types

- `application/pdf` - PDF documents (digital and scanned)
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - DOCX
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` - XLSX
- `application/vnd.openxmlformats-officedocument.presentationml.presentation` - PPTX
- `text/html` - HTML files
- `application/xhtml+xml` - XHTML files
- `image/png` - PNG images
- `image/jpeg` - JPEG images
- `image/gif` - GIF images
- `image/webp` - WebP images
- `image/tiff` - TIFF images
- `image/bmp` - BMP images

The extractor automatically skips text items (`text/plain`, `text/markdown`) and audio items.

## Configuration

### Config Schema

```python
class DoclingSmolExtractorConfig(BaseModel):
    output_format: str = "markdown"  # markdown, text, or html
    backend: str = "mlx"              # mlx or transformers
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `output_format` | str | `markdown` | Output format: `markdown`, `text`, or `html` |
| `backend` | str | `mlx` | Inference backend: `mlx` (Apple Silicon) or `transformers` (cross-platform) |

### Output Formats

- **markdown** (default): Preserves document structure with headings, lists, tables, code blocks
- **html**: Produces semantic HTML with proper tagging
- **text**: Simple plain text without formatting

## Usage

### Command Line

#### Basic Usage

```bash
# Extract using SmolDocling with defaults (markdown, MLX)
biblicus extract my-corpus --extractor docling-smol
```

#### Custom Configuration

```bash
# Use Transformers backend with HTML output
biblicus extract my-corpus --extractor docling-smol \
  --config output_format=html \
  --config backend=transformers
```

#### Recipe File

```yaml
extractor_id: docling-smol
config:
  output_format: markdown
  backend: mlx
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
results = corpus.extract_text(extractor_id="docling-smol")

# Extract with custom config
results = corpus.extract_text(
    extractor_id="docling-smol",
    config={
        "output_format": "html",
        "backend": "transformers"
    }
)
```

### In Pipeline

#### Fallback Chain

```yaml
extractor_id: select-text
config:
  extractors:
    - pdf-text         # Try text extraction first
    - docling-smol     # Fall back to VLM
```

#### Media Type Routing

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pdf-text
  overrides:
    - media_type_pattern: "image/.*"
      extractor: docling-smol
```

## Examples

### Academic Papers

Extract academic papers with equations and code blocks:

```bash
biblicus extract papers-corpus --extractor docling-smol \
  --config output_format=markdown
```

### Office Documents

Process DOCX, XLSX, PPTX files:

```bash
biblicus extract office-corpus --extractor docling-smol \
  --config output_format=html
```

### Scanned Documents

OCR scanned PDFs and images:

```bash
biblicus extract scans-corpus --extractor docling-smol \
  --config backend=mlx
```

### Multi-Format Corpus

Handle mixed document types with automatic routing:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("mixed-corpus")

# Route based on media type
results = corpus.extract_text(
    extractor_id="select-smart-override",
    config={
        "default_extractor": "pass-through-text",
        "overrides": [
            {"media_type_pattern": "application/pdf", "extractor": "docling-smol"},
            {"media_type_pattern": "image/.*", "extractor": "docling-smol"},
            {"media_type_pattern": "application/vnd\\.openxmlformats.*", "extractor": "docling-smol"},
        ]
    }
)
```

## Performance

### Benchmarks

- **Speed**: 6.15 seconds/page (MLX on Apple Silicon M2)
- **Tables F1**: 0.985
- **Code F1**: 0.980
- **Equations F1**: 0.970

### Backend Comparison

| Backend | Platform | Speed | Memory |
|---------|----------|-------|--------|
| MLX | Apple Silicon | 6.15 sec/page | Efficient |
| Transformers | Any (CPU/CUDA) | 15-20 sec/page | Higher |

### When to Use SmolDocling vs Granite

- **SmolDocling-256M**: Faster inference, balanced accuracy, good for large corpus processing
- **[Granite Docling-258M](docling-granite.md)**: Better accuracy (F1: 0.988 code, 0.992 tables), slower

## Error Handling

### Missing Dependency

If the Docling library is not installed:

```
ExtractionRunFatalError: DoclingSmol extractor requires an optional dependency.
Install it with pip install "biblicus[docling]".
```

### Missing MLX Support

If MLX backend is configured but not available:

```
ExtractionRunFatalError: DoclingSmol extractor with MLX backend requires MLX support.
Install it with pip install "biblicus[docling-mlx]".
```

### Empty Output

Documents that cannot be processed produce empty extracted text and are counted in `extracted_empty_items` statistics.

### Per-Item Errors

Processing errors for individual items are recorded in the extraction run but don't halt the entire extraction. Check `errored_items` in extraction statistics.

## Related Extractors

### Same Category

- [docling-granite](docling-granite.md) - Granite Docling-258M for higher accuracy

### Alternatives

- [ocr-rapidocr](../ocr/rapidocr.md) - Traditional OCR (faster, less accurate)
- [ocr-paddleocr-vl](../ocr/paddleocr-vl.md) - PaddleOCR VL (good for CJK)
- [markitdown](../text-document/markitdown.md) - MarkItDown for Office docs (no VLM)

### Pipeline Utilities

- [select-text](../pipeline-utilities/select-text.md) - Fallback chain
- [select-longest-text](../pipeline-utilities/select-longest.md) - Select best output
- [select-smart-override](../pipeline-utilities/select-smart-override.md) - Media type routing

## See Also

- [VLM Document Understanding Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
