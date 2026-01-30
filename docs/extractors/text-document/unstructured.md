# Unstructured Extractor

**Extractor ID:** `unstructured`

**Category:** [Text/Document Extractors](index.md)

## Overview

The Unstructured extractor uses the Unstructured.io library to parse a wide variety of document formats. It's designed as a universal, last-resort extractor with broad format coverage when specialized extractors aren't suitable.

Unstructured provides robust handling of diverse document types including Office documents, PDFs, HTML, emails, and many others. Like MarkItDown, it automatically skips text items to preserve canonical text handling.

## Installation

Unstructured is an optional dependency:

```bash
pip install "biblicus[unstructured]"
```

### System Requirements

Unstructured may require additional system libraries depending on document types:

```bash
# Ubuntu/Debian
sudo apt-get install libmagic-dev poppler-utils tesseract-ocr

# macOS
brew install libmagic poppler tesseract
```

## Supported Media Types

Unstructured supports an extensive range of formats:

### Office Documents
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - DOCX
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` - XLSX
- `application/vnd.openxmlformats-officedocument.presentationml.presentation` - PPTX
- `application/msword` - DOC
- `application/vnd.ms-excel` - XLS
- `application/vnd.ms-powerpoint` - PPT

### Documents
- `application/pdf` - PDF files
- `text/html` - HTML documents
- `application/xml` - XML documents
- `text/csv` - CSV files

### Email
- `message/rfc822` - EML files
- `application/vnd.ms-outlook` - MSG files

### Images
- `image/png`, `image/jpeg`, `image/tiff`
- Other image formats (with OCR support)

### Rich Text
- `application/rtf` - RTF documents
- `text/rtf` - Rich text format

### And Many More

Unstructured's auto-partitioning attempts to handle virtually any document format.

The extractor automatically skips text items (`text/plain`, `text/markdown`) to avoid interfering with the pass-through extractor.

## Configuration

### Config Schema

```python
class UnstructuredExtractorConfig(BaseModel):
    # Version zero provides no configuration options
    pass
```

### Configuration Options

This extractor currently accepts no configuration. Future versions may expose Unstructured library options.

## Usage

### Command Line

#### Basic Usage

```bash
# Extract from diverse document formats
biblicus extract my-corpus --extractor unstructured
```

#### Recipe File

```yaml
extractor_id: unstructured
config: {}
```

```bash
biblicus extract my-corpus --recipe recipe.yml
```

### Python API

```python
from biblicus import Corpus

# Load corpus
corpus = Corpus.from_directory("my-corpus")

# Extract with Unstructured
results = corpus.extract_text(extractor_id="unstructured")
```

### In Pipeline

#### Universal Fallback

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: pdf-text
    - extractor_id: unstructured  # Catch-all for remaining formats
    - extractor_id: select-text
```

#### Last Resort Extraction

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: markitdown
    - extractor_id: unstructured
    - extractor_id: select-longest-text
```

## Examples

### Mixed Format Archive

Process a heterogeneous document collection:

```bash
biblicus extract archive --extractor unstructured
```

### Email Corpus

Extract text from email archives:

```bash
biblicus extract emails --extractor unstructured
```

### Legacy Document Migration

Handle old file formats:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("legacy-files")
results = corpus.extract_text(extractor_id="unstructured")
```

### Comprehensive Pipeline

Maximum format coverage with multiple extractors:

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

## Output Format

Unstructured produces plain text by extracting element text:

### Element Processing

1. Documents are partitioned into elements (paragraphs, tables, etc.)
2. Text is extracted from each element
3. Elements are joined with newlines
4. Empty elements are filtered out

### Example Output

Input (DOCX with mixed content):
```
Heading 1

This is a paragraph with some text.

• Bullet point 1
• Bullet point 2

Table content...
```

Output (Plain Text):
```
Heading 1
This is a paragraph with some text.
Bullet point 1
Bullet point 2
Table content...
```

## Performance

- **Speed**: Moderate to slow (2-30 seconds per document)
- **Memory**: Moderate to high (depends on document complexity)
- **Format Coverage**: Excellent (broadest coverage)

Slower than specialized extractors but handles virtually any format.

## Error Handling

### Missing Dependency

If Unstructured is not installed:

```
ExtractionRunFatalError: Unstructured extractor requires an optional dependency.
Install it with pip install "biblicus[unstructured]".
```

### Missing System Libraries

If required system libraries are missing, you may see errors related to specific document types. Install required dependencies per the installation section.

### Text Items

Text items are silently skipped (returns `None`) to preserve pass-through extractor behavior.

### Unsupported Formats

Files that Unstructured cannot process produce empty extracted text and are counted in `extracted_empty_items`.

### Per-Item Errors

Processing errors for individual items are recorded but don't halt extraction.

## Use Cases

### Universal Document Processing

Handle any document type:

```bash
biblicus extract everything --extractor unstructured
```

### Email Archives

Extract text from email collections:

```bash
biblicus extract email-archive --extractor unstructured
```

### Legacy Format Migration

Process old or uncommon file formats:

```bash
biblicus extract old-docs --extractor unstructured
```

### Fallback Extractor

Use as last resort in pipelines:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text
    - extractor_id: markitdown
    - extractor_id: unstructured
    - extractor_id: select-text
```

## When to Use Unstructured vs Alternatives

### Use Unstructured when:
- Format coverage is most important
- You need to handle diverse, unknown formats
- Specialized extractors don't support your formats
- You want a universal fallback

### Use MarkItDown when:
- Processing primarily Office documents
- Python 3.10+ is available
- You want Markdown-formatted output
- Speed is more important

### Use specialized extractors when:
- You know your document formats
- Speed is critical
- You need format-specific features

### Use VLM extractors when:
- Documents have complex visual layouts
- You need deep document understanding
- Accuracy is more important than speed

## Best Practices

### Test Format Support

Always test on representative samples:

```bash
biblicus extract test-corpus --extractor unstructured
```

### Install System Dependencies

Ensure required system libraries are installed for full format support.

### Use as Fallback

Position Unstructured as a catch-all in pipelines:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: specialized-extractor
    - extractor_id: unstructured  # Fallback
    - extractor_id: select-text
```

### Monitor Performance

Track extraction time for large corpora:

```python
import time

start = time.time()
results = corpus.extract_text(extractor_id="unstructured")
elapsed = time.time() - start
print(f"Extraction took {elapsed:.2f} seconds")
```

### Handle Empty Results

Check statistics for unsupported formats:

```python
print(f"Empty items: {results.stats.extracted_empty_items}")
print(f"Errored items: {results.stats.errored_items}")
```

## Comparison with Other Extractors

| Feature | Unstructured | MarkItDown | PDF-Text | VLM |
|---------|-------------|------------|----------|-----|
| Format Coverage | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ |
| Speed | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| Accuracy | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Setup Complexity | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

## Related Extractors

### Same Category

- [pass-through-text](pass-through.md) - Direct text file reading
- [metadata-text](metadata.md) - Metadata-based text
- [pdf-text](pdf.md) - Fast PDF text extraction
- [markitdown](markitdown.md) - Office document conversion

### Alternatives

- [markitdown](markitdown.md) - Better for Office documents
- [docling-smol](../vlm-document/docling-smol.md) - VLM for visual understanding
- [docling-granite](../vlm-document/docling-granite.md) - High-accuracy VLM
- [ocr-rapidocr](../ocr/rapidocr.md) - Fast OCR for images

### Pipeline Utilities

- [select-text](../pipeline-utilities/select-text.md) - First non-empty selection
- [select-longest-text](../pipeline-utilities/select-longest.md) - Choose longest output
- [select-smart-override](../pipeline-utilities/select-smart-override.md) - Media type routing
- [pipeline](../pipeline-utilities/pipeline.md) - Multi-step extraction

## See Also

- [Text/Document Extractors Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [Unstructured.io Documentation](https://unstructured-io.github.io/unstructured/)
