# PDF Text Extractor

**Extractor ID:** `pdf-text`

**Category:** [Text/Document Extractors](index.md)

## Overview

The PDF text extractor uses PyPDF to extract embedded text from PDF documents. It works best with digital PDFs that contain selectable text layers, providing fast extraction without OCR overhead.

This extractor is ideal for text-based PDFs like reports, papers, and ebooks. For scanned PDFs or images within PDFs, consider using an OCR extractor or VLM-based approach instead.

## Installation

The PyPDF library is included as a core dependency:

```bash
pip install biblicus
```

No additional dependencies required.

## Supported Media Types

- `application/pdf` - PDF documents

Only PDF items are processed. Other media types are automatically skipped.

## Configuration

### Config Schema

```python
class PortableDocumentFormatTextExtractorConfig(BaseModel):
    max_pages: Optional[int] = None  # Maximum pages to extract
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_pages` | int or null | `null` | Maximum number of pages to process (unlimited if null) |

## Usage

### Command Line

#### Basic Usage

```bash
# Extract text from PDF documents
biblicus extract my-corpus --extractor pdf-text
```

#### Custom Configuration

```bash
# Extract only first 10 pages of each PDF
biblicus extract my-corpus --extractor pdf-text \
  --config max_pages=10
```

#### Recipe File

```yaml
extractor_id: pdf-text
config:
  max_pages: 50
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
results = corpus.extract_text(extractor_id="pdf-text")

# Extract with page limit
results = corpus.extract_text(
    extractor_id="pdf-text",
    config={"max_pages": 20}
)
```

### In Pipeline

#### PDF-First Fallback Chain

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text       # Try fast text extraction
    - extractor_id: docling-smol   # Fallback to VLM for scanned PDFs
    - extractor_id: select-text
```

#### Media Type Routing

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pass-through-text
  overrides:
    - media_type_pattern: "application/pdf"
      extractor: pdf-text
```

## Examples

### Extract Academic Papers

Process a collection of research papers:

```bash
biblicus extract papers-corpus --extractor pdf-text
```

### Extract First Pages Only

Useful for abstracts or summaries:

```bash
biblicus extract papers-corpus --extractor pdf-text \
  --config max_pages=2
```

### Large Document Corpus

Limit pages for performance on large documents:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("ebooks")

# Extract first 100 pages of each book
results = corpus.extract_text(
    extractor_id="pdf-text",
    config={"max_pages": 100}
)
```

### Hybrid PDF Pipeline

Combine fast text extraction with OCR fallback:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
      config:
        max_pages: null
    - extractor_id: ocr-rapidocr
    - extractor_id: select-longest-text  # Choose best result
```

## Behavior Details

### Text Extraction Method

PyPDF extracts embedded text from PDF structure. It does not:
- Perform OCR on images
- Preserve complex formatting
- Extract text from images within PDFs
- Maintain table structures

### Page Processing

Pages are processed sequentially. Text from each page is joined with newlines.

### Empty Pages

Pages without extractable text produce empty strings. If all pages are empty, the entire document produces empty extracted text.

### Encoding

PyPDF handles PDF text encoding internally. Output is always UTF-8.

## Performance

- **Speed**: Fast (5-50 pages/second depending on PDF complexity)
- **Memory**: Moderate (entire PDF loaded into memory)
- **Accuracy**: 100% for digital PDFs, 0% for scanned PDFs

This extractor is significantly faster than OCR or VLM approaches but only works with text-based PDFs.

## Error Handling

### Non-PDF Items

Non-PDF items are silently skipped (returns `None`).

### Corrupt PDFs

Corrupt or malformed PDFs cause per-item errors recorded in `errored_items` but don't halt extraction.

### Password-Protected PDFs

Encrypted PDFs without password support cause per-item failures.

### Scanned PDFs

Scanned PDFs (images without text layer) produce empty extracted text and are counted in `extracted_empty_items`.

## Use Cases

### Digital Documents

Ideal for born-digital PDFs:

```bash
biblicus extract reports-corpus --extractor pdf-text
```

### Research Papers

Extract academic publications:

```bash
biblicus extract arxiv-corpus --extractor pdf-text
```

### Ebooks

Process digital book collections:

```bash
biblicus extract ebooks --extractor pdf-text
```

### Mixed PDF Corpus

Handle both digital and scanned PDFs with fallback:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: docling-smol   # Handles scanned PDFs
    - extractor_id: select-longest-text
```

## When to Use PDF Text vs Alternatives

### Use pdf-text when:
- PDFs contain embedded text (digital/born-digital)
- Speed is important
- You need simple, reliable extraction
- PDFs are not scanned/image-based

### Use VLM extractors when:
- PDFs are scanned or image-based
- You need layout understanding
- PDFs contain complex tables or equations
- Documents have multi-column layouts

### Use OCR extractors when:
- PDFs are scanned but layout is simple
- You need faster processing than VLM
- Documents are primarily text without complex structure

## Best Practices

### Test with Sample PDFs

Always test on representative samples:

```bash
# Extract a few PDFs to check quality
biblicus extract test-corpus --extractor pdf-text
```

### Check for Empty Results

Monitor `extracted_empty_items` in statistics to identify scanned PDFs.

### Use Fallback for Mixed Corpora

Combine with OCR/VLM for heterogeneous PDF collections:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pdf-text
    - extractor_id: ocr-rapidocr
    - extractor_id: select-text
```

### Consider Page Limits

For large documents, use `max_pages` to control processing time and memory:

```yaml
extractor_id: pdf-text
config:
  max_pages: 500  # Reasonable limit for most use cases
```

## Related Extractors

### Same Category

- [pass-through-text](pass-through.md) - Direct text file reading
- [metadata-text](metadata.md) - Metadata-based text
- [markitdown](markitdown.md) - Office document conversion
- [unstructured](unstructured.md) - Universal document parser

### Alternatives for Scanned PDFs

- [ocr-rapidocr](../ocr/rapidocr.md) - Fast OCR for scanned PDFs
- [ocr-paddleocr-vl](../ocr/paddleocr-vl.md) - VL-enhanced OCR
- [docling-smol](../vlm-document/docling-smol.md) - VLM for complex PDFs
- [docling-granite](../vlm-document/docling-granite.md) - High-accuracy VLM

### Pipeline Utilities

- [select-text](../pipeline-utilities/select-text.md) - First non-empty selection
- [select-longest-text](../pipeline-utilities/select-longest.md) - Choose longest output
- [select-smart-override](../pipeline-utilities/select-smart-override.md) - Intelligent routing
- [pipeline](../pipeline-utilities/pipeline.md) - Multi-step extraction

## See Also

- [Text/Document Extractors Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [PyPDF Documentation](https://pypdf.readthedocs.io/)
