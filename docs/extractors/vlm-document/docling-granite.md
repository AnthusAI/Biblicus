# Granite Docling-258M Extractor

**Extractor ID:** `docling-granite`

**Category:** [Vision-Language Models (VLM)](index.md)

## Overview

The Granite Docling-258M extractor uses IBM Research's Granite Docling vision-language model for state-of-the-art document understanding. It achieves superior accuracy on technical content including tables, code blocks, and mathematical equations.

Granite Docling-258M is a 258-million parameter VLM optimized for high-accuracy document processing. It outperforms SmolDocling on complex document structures with F1 scores of 0.988 for code, 0.992 for tables, and 0.975 for equations.

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
class DoclingGraniteExtractorConfig(BaseModel):
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
# Extract using Granite Docling with defaults (markdown, MLX)
biblicus extract my-corpus --extractor docling-granite
```

#### Custom Configuration

```bash
# Use Transformers backend with HTML output
biblicus extract my-corpus --extractor docling-granite \
  --config output_format=html \
  --config backend=transformers
```

#### Recipe File

```yaml
extractor_id: docling-granite
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
results = corpus.extract_text(extractor_id="docling-granite")

# Extract with custom config
results = corpus.extract_text(
    extractor_id="docling-granite",
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
    - docling-granite  # Highest accuracy
    - docling-smol     # Faster fallback
    - ocr-rapidocr     # Traditional OCR
```

#### High-Accuracy Override

```yaml
extractor_id: select-smart-override
config:
  default_extractor: docling-smol
  overrides:
    - media_type_pattern: "application/pdf"
      extractor: docling-granite  # Use Granite for PDFs
```

## Examples

### Academic Papers with Equations

Extract research papers with mathematical equations:

```bash
biblicus extract papers-corpus --extractor docling-granite \
  --config output_format=markdown
```

### Technical Documentation

Process documentation with code blocks:

```bash
biblicus extract docs-corpus --extractor docling-granite \
  --config output_format=html
```

### Complex Tables

Extract spreadsheets and documents with complex tables:

```bash
biblicus extract tables-corpus --extractor docling-granite \
  --config backend=mlx
```

### High-Accuracy Pipeline

Prioritize accuracy over speed:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("important-docs")

# Use Granite for maximum accuracy
results = corpus.extract_text(
    extractor_id="docling-granite",
    config={
        "output_format": "markdown",
        "backend": "mlx"
    }
)
```

## Performance

### Benchmarks

- **Speed**: ~7 seconds/page (MLX on Apple Silicon, estimated)
- **Tables F1**: 0.992 ⭐
- **Code F1**: 0.988 ⭐
- **Equations F1**: 0.975 ⭐

### Comparison with SmolDocling

| Metric | Granite-258M | SmolDocling-256M |
|--------|--------------|------------------|
| Tables F1 | **0.992** | 0.985 |
| Code F1 | **0.988** | 0.980 |
| Equations F1 | **0.975** | 0.970 |
| Speed | ~7 sec/page | 6.15 sec/page |

### When to Use Granite vs SmolDocling

**Use Granite Docling-258M when:**
- Accuracy is critical
- Processing technical documents (code, equations)
- Complex table extraction is needed
- Document quality is worth the extra processing time

**Use [SmolDocling-256M](docling-smol.md) when:**
- Speed is more important than accuracy
- Processing large corpus volumes
- Documents are relatively simple
- Resource constraints exist

## Error Handling

### Missing Dependency

If the Docling library is not installed:

```
ExtractionRunFatalError: DoclingGranite extractor requires an optional dependency.
Install it with pip install "biblicus[docling]".
```

### Missing MLX Support

If MLX backend is configured but not available:

```
ExtractionRunFatalError: DoclingGranite extractor with MLX backend requires MLX support.
Install it with pip install "biblicus[docling-mlx]".
```

### Empty Output

Documents that cannot be processed produce empty extracted text and are counted in `extracted_empty_items` statistics.

### Per-Item Errors

Processing errors for individual items are recorded in the extraction run but don't halt the entire extraction. Check `errored_items` in extraction statistics.

## Use Cases

### Research Papers

Granite excels at academic papers with:
- LaTeX-style equations
- Complex bibliography formatting
- Multi-column layouts
- Figures and captions

### Source Code Documentation

Ideal for technical documentation with:
- Syntax-highlighted code blocks
- API reference tables
- Inline code snippets
- Function signatures

### Financial Reports

Handles business documents with:
- Complex financial tables
- Merged cells and hierarchies
- Mixed text and numeric data
- Charts and graphs

### Legal Documents

Processes legal content with:
- Multi-level numbering
- Nested clauses
- Citation formatting
- Footnotes and references

## Related Extractors

### Same Category

- [docling-smol](docling-smol.md) - SmolDocling-256M for faster processing

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
