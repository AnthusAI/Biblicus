# Optical Character Recognition (OCR)

Traditional OCR extractors for text recognition from images and scanned documents.

## Overview

OCR extractors use computer vision to recognize text in images, scanned documents, and visual content. They are ideal for:

- Scanned PDFs without text layers
- Photographs of documents
- Screenshots with text
- Handwritten content (with appropriate models)

## Available Extractors

### [ocr-rapidocr](rapidocr.md)

RapidOCR provides fast ONNX-based text recognition with:
- Multi-language support
- Fast inference (CPU-optimized)
- No GPU required
- Lightweight deployment

**Installation**: `pip install biblicus[ocr]`

**Best for**: General-purpose OCR, scanned documents, mixed text/image content

### [ocr-paddleocr-vl](paddleocr-vl.md)

PaddleOCR vision-language model provides:
- Advanced document understanding
- Layout analysis
- Table detection
- Chinese/English/multilingual support

**Installation**: `pip install biblicus[paddleocr]`

**Best for**: Complex documents, tables, multi-column layouts, CJK text

## OCR vs VLM Document Understanding

### When to Use OCR

- Simple text recognition needs
- CPU-only environments
- Fast processing requirements
- Lightweight deployments

### When to Use VLM

For advanced document understanding with layout preservation, use [VLM extractors](../vlm-document/index.md):

- [docling-smol](../vlm-document/docling-smol.md) - Fast, 256M params
- [docling-granite](../vlm-document/docling-granite.md) - High accuracy, 258M params

VLM extractors provide:
- Semantic structure understanding
- Equation and code block recognition
- Superior table extraction
- Layout-aware markdown output

## Choosing an Extractor

| Use Case | Recommended Extractor | Notes |
|----------|----------------------|-------|
| English scanned docs | [ocr-rapidocr](rapidocr.md) | Fast, lightweight |
| Chinese/CJK documents | [ocr-paddleocr-vl](paddleocr-vl.md) | Excellent CJK support |
| Tables and complex layouts | [docling-granite](../vlm-document/docling-granite.md) | VLM approach |
| Simple screenshots | [ocr-rapidocr](rapidocr.md) | Quick results |
| Academic papers with equations | [docling-granite](../vlm-document/docling-granite.md) | Equation recognition |

## Common Patterns

### Fallback Chain

Try VLM first, fall back to OCR:

```yaml
extractor_id: select-text
config:
  extractors:
    - docling-smol
    - ocr-rapidocr
```

### Multi-Strategy Selection

Use longest output from multiple OCR approaches:

```yaml
extractor_id: select-longest-text
config:
  extractors:
    - ocr-rapidocr
    - ocr-paddleocr-vl
```

### Document Type Routing

Use smart overrides for different document types:

```yaml
extractor_id: select-smart-override
config:
  default_extractor: ocr-rapidocr
  overrides:
    - media_type_pattern: "image/.*"
      extractor: ocr-rapidocr
    - media_type_pattern: "application/pdf"
      extractor: docling-smol
```

## Performance Considerations

### RapidOCR

- **Speed**: Very fast (CPU-optimized ONNX)
- **Memory**: Low (~100MB models)
- **Accuracy**: Good for clean scans
- **Hardware**: CPU-only

### PaddleOCR VL

- **Speed**: Moderate (requires Paddle framework)
- **Memory**: Higher (~500MB models)
- **Accuracy**: Excellent for complex layouts
- **Hardware**: CPU or GPU

### VLM Alternatives

For best accuracy with complex documents, consider [VLM extractors](../vlm-document/index.md) which offer:
- Better layout understanding
- Semantic structure preservation
- Superior table and equation handling

## See Also

- [Extractors Overview](../index.md)
- [VLM Document Understanding](../vlm-document/index.md) - Advanced document processing
- [Text & Document Processing](../text-document/index.md) - For PDFs with text layers
- [Pipeline Utilities](../pipeline-utilities/index.md) - For combining strategies
