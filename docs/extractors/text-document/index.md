# Text & Document Processing

Basic text extraction from structured documents and plain text formats.

## Overview

Text and document extractors handle files with explicit text content or structured document formats. These extractors are ideal for:

- PDF documents with text layers
- Office documents (DOCX, XLSX, PPTX)
- Markdown and HTML files
- Plain text files
- Web content

## Available Extractors

### [pass-through-text](pass-through.md)

Returns existing extracted text without re-extraction. Useful for:
- Skipping extraction when text already exists
- Testing and debugging pipelines
- Preserving manually curated text

**Installation**: Included by default

### [metadata-text](metadata.md)

Extracts text from item metadata (title, tags, keywords). Useful for:
- Creating searchable metadata
- Generating synthetic corpus entries
- Testing without file content

**Installation**: Included by default

### [pdf-text](pdf.md)

Extracts text from PDF documents using pypdf. Ideal for:
- PDFs with selectable text layers
- Fast extraction without OCR overhead
- Simple document processing

**Installation**: Included by default

### [markitdown](markitdown.md)

Microsoft MarkItDown for Office documents and web content. Supports:
- DOCX, XLSX, PPTX
- HTML, MHTML
- Images (via OCR)
- Audio (via transcription)
- ZIP archives

**Installation**: `pip install biblicus[markitdown]` (Python 3.10+ only)

### [unstructured](unstructured.md)

Unstructured.io for complex document parsing. Supports:
- DOCX, XLSX, PPTX
- Email formats (EML, MSG)
- Markdown, HTML, XML
- Advanced chunking and partitioning

**Installation**: `pip install biblicus[unstructured]`

## Choosing an Extractor

| Format | Recommended Extractor | Alternative |
|--------|----------------------|-------------|
| PDF (text layer) | [pdf-text](pdf.md) | [markitdown](markitdown.md) |
| PDF (scanned) | See [OCR](../ocr/index.md) or [VLM](../vlm-document/index.md) | |
| DOCX, XLSX, PPTX | [markitdown](markitdown.md) | [unstructured](unstructured.md) |
| Markdown, HTML | [markitdown](markitdown.md) | [unstructured](unstructured.md) |
| Plain text | [pass-through-text](pass-through.md) | [metadata-text](metadata.md) |

## Common Patterns

### Fallback Chain

Use [select-text](../pipeline-utilities/select-text.md) to try multiple extractors:

```yaml
extractor_id: select-text
config:
  extractors:
    - pdf-text
    - markitdown
    - unstructured
```

### Metadata + Content

Use [pipeline](../pipeline-utilities/pipeline.md) to combine metadata and content:

```yaml
extractor_id: pipeline
config:
  extractors:
    - metadata-text
    - pdf-text
```

## See Also

- [Extractors Overview](../index.md)
- [OCR Extractors](../ocr/index.md) - For scanned documents
- [VLM Extractors](../vlm-document/index.md) - For complex layouts
- [Pipeline Utilities](../pipeline-utilities/index.md) - For combining strategies
