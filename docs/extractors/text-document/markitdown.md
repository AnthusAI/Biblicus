# MarkItDown Extractor

**Extractor ID:** `markitdown`

**Category:** [Text/Document Extractors](index.md)

## Overview

The MarkItDown extractor uses Microsoft's MarkItDown library to convert various document formats into Markdown-formatted text. It provides broad format coverage for Office documents, PDFs, images, and other file types.

MarkItDown is designed to produce clean, readable Markdown output from diverse sources. It automatically skips text items to preserve the role of the pass-through extractor for canonical text handling.

## Installation

MarkItDown is an optional dependency that requires Python 3.10 or higher:

```bash
pip install "biblicus[markitdown]"
```

### Python Version Requirement

- **Minimum**: Python 3.10
- **Recommended**: Python 3.11 or higher

If you're using Python 3.9 or earlier, use alternative extractors like `unstructured`.

## Supported Media Types

MarkItDown supports a wide range of formats:

### Office Documents
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - DOCX
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` - XLSX
- `application/vnd.openxmlformats-officedocument.presentationml.presentation` - PPTX
- `application/msword` - DOC (legacy)
- `application/vnd.ms-excel` - XLS (legacy)
- `application/vnd.ms-powerpoint` - PPT (legacy)

### Documents
- `application/pdf` - PDF files
- `text/html` - HTML documents
- `application/xhtml+xml` - XHTML documents

### Images
- `image/png`, `image/jpeg`, `image/gif`
- `image/bmp`, `image/tiff`, `image/webp`

### Audio/Video
- Various audio and video formats (converts metadata)

### Archives
- `application/zip` - ZIP archives (lists contents)

The extractor automatically skips text items (`text/plain`, `text/markdown`) to avoid interfering with the pass-through extractor.

## Configuration

### Config Schema

```python
class MarkItDownExtractorConfig(BaseModel):
    enable_plugins: bool = False  # Enable MarkItDown plugin system
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enable_plugins` | bool | `false` | Enable MarkItDown's plugin system for extended format support |

## Usage

### Command Line

#### Basic Usage

```bash
# Convert Office documents to Markdown
biblicus extract my-corpus --extractor markitdown
```

#### Custom Configuration

```bash
# Enable plugins for extended format support
biblicus extract my-corpus --extractor markitdown \
  --config enable_plugins=true
```

#### Recipe File

```yaml
extractor_id: markitdown
config:
  enable_plugins: false
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
results = corpus.extract_text(extractor_id="markitdown")

# Extract with plugins enabled
results = corpus.extract_text(
    extractor_id="markitdown",
    config={"enable_plugins": True}
)
```

### In Pipeline

#### Office Document Pipeline

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: pass-through-text  # Handle text files
    - extractor_id: markitdown          # Convert Office docs
    - extractor_id: select-text
```

#### Media Type Routing

```yaml
extractor_id: select-smart-override
config:
  default_extractor: pass-through-text
  overrides:
    - media_type_pattern: "application/vnd.openxmlformats.*"
      extractor: markitdown
    - media_type_pattern: "application/pdf"
      extractor: pdf-text
```

## Examples

### Office Document Collection

Convert DOCX, XLSX, PPTX files to Markdown:

```bash
biblicus extract office-docs --extractor markitdown
```

### Mixed Format Corpus

Handle text, Office, and PDF documents:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("mixed-docs")

results = corpus.extract_text(
    extractor_id="pipeline",
    config={
        "steps": [
            {"extractor_id": "pass-through-text"},
            {"extractor_id": "markitdown"},
            {"extractor_id": "select-text"}
        ]
    }
)
```

### PowerPoint Presentations

Extract text from presentation decks:

```bash
biblicus extract presentations --extractor markitdown
```

### Excel Spreadsheets

Convert spreadsheet data to Markdown tables:

```bash
biblicus extract spreadsheets --extractor markitdown
```

## Output Format

MarkItDown produces Markdown-formatted text that preserves document structure:

### Document Elements
- **Headings**: Converted to Markdown headers (`#`, `##`, etc.)
- **Lists**: Preserved as Markdown lists
- **Tables**: Converted to Markdown tables
- **Links**: Preserved as Markdown links
- **Bold/Italic**: Converted to Markdown emphasis

### Example Output

Input (DOCX):
```
Title: Project Report
Subtitle: Q4 2024

Key Findings:
- Revenue increased 25%
- User growth exceeded targets
```

Output (Markdown):
```markdown
# Project Report

## Q4 2024

Key Findings:
- Revenue increased 25%
- User growth exceeded targets
```

## Performance

- **Speed**: Moderate (1-10 seconds per document)
- **Memory**: Moderate (depends on document size)
- **Format Coverage**: Excellent (Office, PDF, images, archives)

Faster than VLM approaches but slower than simple text extraction.

## Error Handling

### Missing Dependency

If MarkItDown is not installed:

```
ExtractionRunFatalError: MarkItDown extractor requires an optional dependency.
Install it with pip install "biblicus[markitdown]".
```

### Python Version Mismatch

If Python version is below 3.10:

```
ExtractionRunFatalError: MarkItDown requires Python 3.10 or higher.
Upgrade your interpreter or use a compatible extractor.
```

### Text Items

Text items are silently skipped (returns `None`) to preserve pass-through extractor behavior.

### Unsupported Formats

Files that MarkItDown cannot process produce empty extracted text and are counted in `extracted_empty_items`.

### Per-Item Errors

Processing errors for individual items are recorded but don't halt extraction.

## Use Cases

### Office Document Archives

Convert corporate document collections:

```bash
biblicus extract corporate-docs --extractor markitdown
```

### Documentation Processing

Handle mixed documentation formats:

```bash
biblicus extract documentation --extractor markitdown
```

### Report Extraction

Extract text from formatted reports:

```bash
biblicus extract quarterly-reports --extractor markitdown
```

### Knowledge Base Migration

Convert legacy documents to Markdown:

```python
from biblicus import Corpus

corpus = Corpus.from_directory("legacy-kb")
results = corpus.extract_text(extractor_id="markitdown")
```

## When to Use MarkItDown vs Alternatives

### Use MarkItDown when:
- Processing Office documents (DOCX, XLSX, PPTX)
- You want Markdown-formatted output
- Python 3.10+ is available
- Simple, reliable conversion is needed

### Use Unstructured when:
- Python 3.9 or earlier is required
- More format coverage is needed
- You need advanced document parsing

### Use VLM extractors when:
- Documents have complex layouts
- Visual understanding is important
- Accuracy is more critical than speed

### Use PDF-specific extractors when:
- Processing only PDFs
- Speed is critical
- PDFs are text-based (not scanned)

## Best Practices

### Test Conversion Quality

Always test on representative samples:

```bash
biblicus extract test-corpus --extractor markitdown
```

### Monitor Empty Results

Check extraction statistics for unsupported formats:

```python
print(f"Empty items: {results.stats.extracted_empty_items}")
```

### Use in Pipelines

Combine with other extractors for robustness:

```yaml
extractor_id: pipeline
config:
  steps:
    - extractor_id: markitdown
    - extractor_id: unstructured  # Fallback
    - extractor_id: select-longest-text
```

### Check Python Version

Verify Python 3.10+ before deployment:

```bash
python --version
```

## Related Extractors

### Same Category

- [pass-through-text](pass-through.md) - Direct text file reading
- [metadata-text](metadata.md) - Metadata-based text
- [pdf-text](pdf.md) - Fast PDF text extraction
- [unstructured](unstructured.md) - Universal document parser

### Alternatives

- [unstructured](unstructured.md) - More format coverage, Python 3.9 support
- [docling-smol](../vlm-document/docling-smol.md) - VLM for complex documents
- [docling-granite](../vlm-document/docling-granite.md) - High-accuracy VLM

### Pipeline Utilities

- [select-text](../pipeline-utilities/select-text.md) - First non-empty selection
- [select-longest-text](../pipeline-utilities/select-longest.md) - Choose longest output
- [select-smart-override](../pipeline-utilities/select-smart-override.md) - Media type routing
- [pipeline](../pipeline-utilities/pipeline.md) - Multi-step extraction

## See Also

- [Text/Document Extractors Overview](index.md)
- [Extractors Index](../index.md)
- [EXTRACTION.md](../../EXTRACTION.md) - Extraction pipeline concepts
- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
