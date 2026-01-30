# Vision-Language Models (VLM) for Document Understanding

Advanced VLM-based document understanding with layout analysis, semantic structure preservation, and intelligent content extraction.

## Overview

Vision-Language Model extractors use multimodal AI to understand documents holistically, combining visual layout analysis with semantic text extraction. They excel at:

- Complex document layouts (multi-column, mixed content)
- Mathematical equations and chemical formulas
- Code blocks and syntax preservation
- Tables with complex structure
- Diagrams and figure captions
- Academic papers and technical documentation

## Available Extractors

### [docling-smol](docling-smol.md)

SmolDocling-256M provides fast, efficient document understanding:

- **Model**: SmolDocling-256M (256M parameters)
- **Speed**: 6.15 seconds/page (MLX on Apple Silicon)
- **Formats**: PDF, DOCX, XLSX, PPTX, HTML, images
- **Backends**: MLX (Apple Silicon) or Transformers (cross-platform)
- **Output**: Markdown, HTML, or plain text

**Installation**:
- Transformers: `pip install biblicus[docling]`
- MLX (Apple Silicon): `pip install biblicus[docling-mlx]`

**Best for**: General document processing, fast inference, balanced accuracy

### [docling-granite](docling-granite.md)

Granite Docling-258M provides state-of-the-art accuracy:

- **Model**: Granite Docling-258M (258M parameters)
- **Accuracy**: Superior F1 scores (0.988 code, 0.992 tables, 0.975 equations)
- **Formats**: PDF, DOCX, XLSX, PPTX, HTML, images
- **Backends**: MLX (Apple Silicon) or Transformers (cross-platform)
- **Output**: Markdown, HTML, or plain text

**Installation**:
- Transformers: `pip install biblicus[docling]`
- MLX (Apple Silicon): `pip install biblicus[docling-mlx]`

**Best for**: High-accuracy extraction, tables, equations, code blocks

## VLM vs Traditional OCR

### Use VLM When:

- **Complex layouts**: Multi-column papers, mixed content
- **Structured data**: Tables with merged cells, complex hierarchy
- **Technical content**: Equations, code blocks, chemical formulas
- **Semantic understanding**: Need layout-aware markdown output
- **Quality priority**: Accuracy more important than speed

### Use Traditional OCR When:

- **Simple text recognition**: Plain scanned documents
- **CPU-only constraints**: No GPU/MLX acceleration available
- **Speed priority**: Need fastest possible processing
- **Lightweight deployment**: Minimal dependencies required

See [OCR Extractors](../ocr/index.md) for traditional OCR options.

## Choosing a VLM Extractor

| Use Case | Recommended | Notes |
|----------|-------------|-------|
| General documents | [docling-smol](docling-smol.md) | Fast, balanced accuracy |
| Academic papers | [docling-granite](docling-granite.md) | Better equation/code recognition |
| Business documents | [docling-smol](docling-smol.md) | Good table extraction |
| Technical documentation | [docling-granite](docling-granite.md) | Superior code block handling |
| Large corpus processing | [docling-smol](docling-smol.md) | Faster inference |
| Maximum accuracy | [docling-granite](docling-granite.md) | Best overall metrics |

## Performance Comparison

### SmolDocling-256M

- **Parameters**: 256M
- **Speed**: 6.15 sec/page (MLX)
- **Tables F1**: 0.985
- **Code F1**: 0.980
- **Equations F1**: 0.970

### Granite Docling-258M

- **Parameters**: 258M
- **Speed**: ~7 sec/page (MLX, estimated)
- **Tables F1**: 0.992
- **Code F1**: 0.988
- **Equations F1**: 0.975

## Backend Options

### MLX Backend (Apple Silicon)

- **Platform**: macOS with Apple Silicon (M1/M2/M3/M4)
- **Performance**: 2-3x faster than Transformers
- **Memory**: Efficient unified memory usage
- **Installation**: `pip install biblicus[docling-mlx]`

### Transformers Backend (Cross-Platform)

- **Platform**: Any platform (CPU, CUDA, ROCm)
- **Performance**: Slower but widely compatible
- **Memory**: Standard PyTorch memory requirements
- **Installation**: `pip install biblicus[docling]`

## Output Formats

All VLM extractors support multiple output formats:

### Markdown (Default)

Preserves document structure with headings, lists, tables, code blocks:

```yaml
extractor_id: docling-smol
config:
  output_format: markdown  # default
```

### HTML

Produces semantic HTML with proper tagging:

```yaml
extractor_id: docling-smol
config:
  output_format: html
```

### Plain Text

Simple text output without formatting:

```yaml
extractor_id: docling-smol
config:
  output_format: text
```

## Common Patterns

### Fallback to OCR

Try VLM first, fall back to traditional OCR:

```yaml
extractor_id: select-text
config:
  extractors:
    - docling-granite
    - ocr-rapidocr
```

### Speed vs Accuracy Trade-off

Use SmolDocling for speed, Granite for accuracy:

```yaml
extractor_id: select-smart-override
config:
  default_extractor: docling-smol
  overrides:
    - media_type_pattern: "application/pdf"
      extractor: docling-granite  # Higher accuracy for important PDFs
```

### Backend Selection

Choose backend based on platform:

```yaml
# MLX for Apple Silicon (fast)
extractor_id: docling-smol
config:
  backend: mlx

# Transformers for other platforms (compatible)
extractor_id: docling-smol
config:
  backend: transformers
```

## Installation Guide

### Apple Silicon (Recommended)

```bash
# Install with MLX backend for best performance
pip install biblicus[docling-mlx]
```

### Other Platforms

```bash
# Install with Transformers backend
pip install biblicus[docling]
```

### Both Extractors

```bash
# Install all Docling dependencies
pip install biblicus[docling-mlx]  # Includes base docling extras
```

## Supported Document Types

- **PDF**: Scanned and digital PDFs
- **DOCX**: Microsoft Word documents
- **XLSX**: Excel spreadsheets
- **PPTX**: PowerPoint presentations
- **HTML**: Web pages
- **Images**: PNG, JPEG, SVG, and other image formats

## See Also

- [Extractors Overview](../index.md)
- [docling-smol](docling-smol.md) - SmolDocling-256M extractor details
- [docling-granite](docling-granite.md) - Granite Docling-258M extractor details
- [OCR Extractors](../ocr/index.md) - Traditional OCR alternatives
- [Pipeline Utilities](../pipeline-utilities/index.md) - Combining extraction strategies
