# Layout-Aware OCR Example

This example demonstrates how to extract text from documents with complex layouts using Biblicus's layout-aware OCR pipeline.

## The Problem

Standard OCR tools process images line-by-line from top to bottom, which works well for simple documents but fails for complex layouts:

- **Multi-column documents**: Text is read across both columns instead of down each column
- **Mixed layouts**: Tables, sidebars, and text blocks are processed in the wrong order
- **Non-linear reading order**: Headers, footers, and captions get mixed into body text

### Example: Two-Column Document

Consider an academic paper with two columns:

```
+----------------------------------+
|         Title and Author         |
+----------------------------------+
| Column 1 text | Column 2 text    |
| continues     | continues         |
| down the left | down the right   |
+----------------------------------+
```

**Standard OCR reads**: Title → Column 1 line 1 → Column 2 line 1 → Column 1 line 2 → Column 2 line 2...

**Desired reading order**: Title → All of Column 1 → All of Column 2

## The Solution

Two-stage layout-aware OCR workflow:

> "For non-selectable files we use Heron to extract first the layout. Then Tesseract to extract the text. Because some of the files that do not have a linear layout are difficult to parse with the correct order."

Biblicus implements this workflow with a three-stage pipeline:

1. **Layout Detection** - Identify regions (headers, columns, tables) and their reading order
2. **Region-Based OCR** - Process each region separately
3. **Text Reconstruction** - Merge text in correct reading order

## Implementation

### Prerequisites

Install Tesseract OCR:

```bash
# Install Python dependencies
pip install "biblicus[tesseract]"

# Install Tesseract binary
# macOS:
brew install tesseract

# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# Windows:
# Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### Corpus Setup

Create a new corpus and ingest a document with complex layout:

```bash
# Initialize corpus
biblicus init /path/to/corpus

# Ingest multi-column document
biblicus --corpus /path/to/corpus ingest /path/to/document.pdf --tag multi-column
```

### Running the Pipeline

Build an extraction snapshot using the layout-aware OCR pipeline:

```bash
biblicus --corpus /path/to/corpus extract build \
  --stage "mock-layout-detector:layout_type=two-column" \
  --stage "ocr-tesseract:use_layout_metadata=true,lang=eng"
```

This command:
1. Runs `mock-layout-detector` to identify layout regions
2. Passes region metadata to `ocr-tesseract`
3. Tesseract OCRs each region in correct reading order

### Python API

For programmatic access:

```python
from pathlib import Path
from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot

# Initialize corpus
corpus_dir = Path("corpora/my-corpus")
corpus = Corpus.init(root=corpus_dir)

# Ingest document
result = corpus.ingest_source(
    Path("document.pdf"),
    tags=["multi-column", "academic-paper"]
)
item_id = result.item_id

# Run layout-aware OCR pipeline
snapshot = build_extraction_snapshot(
    corpus=corpus,
    extractor_id="pipeline",
    configuration_name="layout-aware-ocr",
    configuration={
        "stages": [
            {
                "extractor_id": "mock-layout-detector",
                "config": {"layout_type": "two-column"}
            },
            {
                "extractor_id": "ocr-tesseract",
                "config": {
                    "use_layout_metadata": True,
                    "lang": "eng",
                    "min_confidence": 0.5
                }
            }
        ]
    }
)

# Read extracted text
snapshot_dir = corpus.extraction_snapshot_dir(
    extractor_id="pipeline",
    snapshot_id=snapshot.snapshot_id
)
text_path = snapshot_dir / "text" / f"{item_id}.txt"
extracted_text = text_path.read_text()

print(extracted_text)
```

## Complete Demo Script

A full working example is available at `examples/layout_aware_ocr_demo.py`:

```bash
# Quick demo with generated test image (default)
python examples/layout_aware_ocr_demo.py

# Download and use real FUNSD scanned forms (requires internet)
python examples/layout_aware_ocr_demo.py --download-samples

# Use your own PDF
python examples/layout_aware_ocr_demo.py --pdf /path/to/document.pdf
```

This script:
1. Creates a demo corpus
2. Ingests documents (test image, FUNSD scanned forms, or custom file)
3. Runs **standard OCR** (no layout awareness)
4. Runs **layout-aware OCR pipeline**
5. Compares the results side-by-side

### Real Document Samples

The `--download-samples` option downloads the FUNSD dataset (Form Understanding in Noisy Scanned Documents):

- **199 annotated scanned forms** with OCR ground truth
- **31,485 words** with bounding boxes and text annotations
- **Real scanned documents** (not born-digital PDFs)
- **Perfect for testing** with quantifiable accuracy metrics

FUNSD provides ground truth annotations, enabling verification of OCR accuracy against known correct text

### Demo Output

```
======================================================================
LAYOUT-AWARE OCR DEMONSTRATION
======================================================================

This example demonstrates Os's suggested workflow:
  1. Layout detection → identifies regions and reading order
  2. Region-based OCR → processes each region with Tesseract
  3. Text reconstruction → merges in correct reading order

======================================================================

✓ Initialized corpus at: corpora/layout_ocr_demo

Downloading FUNSD scanned forms...
  ✓ Downloaded 3 forms
  ✓ Ground truth stored

✓ Ingested document: abc123...
  Type: FUNSD Scanned Form
  Media type: image/png
  Tags: funsd, scanned, form, testing, ground-truth

----------------------------------------------------------------------
COMPARISON 1: Standard OCR (No Layout Awareness)
----------------------------------------------------------------------
Running: ocr-tesseract (standard mode)...

Standard OCR Result:
Title Header
Left column line 1 Right column line 1
Left column line 2 Right column line 2
...

❌ PROBLEM: Text may be in wrong order (reads across both columns)

----------------------------------------------------------------------
COMPARISON 2: Layout-Aware OCR Pipeline
----------------------------------------------------------------------
Running: mock-layout-detector → ocr-tesseract (layout-aware mode)...

✓ Layout Detection Results:
  Layout Type: two-column
  Regions Detected: 3
    - Region 1: header (order: 1, bbox: [50, 50, 700, 100])
    - Region 2: text (order: 2, bbox: [50, 120, 350, 800])
    - Region 3: text (order: 3, bbox: [380, 120, 350, 800])

✓ Layout-Aware OCR Result:
Title Header

Left column line 1
Left column line 2
...

Right column line 1
Right column line 2
...

✅ SUCCESS: Text in correct reading order (left column → right column)

✓ OCR Processing Stats:
  Regions processed: 3
  Regions with text: 3

======================================================================
SUMMARY
======================================================================

The layout-aware OCR pipeline solves the reading order problem by:
  1. Detecting layout regions before OCR
  2. Processing each region separately
  3. Merging text in the correct reading order

This enables accurate text extraction from:
  • Multi-column documents
  • Documents with complex layouts
  • Scanned documents with non-linear reading order
```

## How It Works

### Stage 1: Layout Detection

The `mock-layout-detector` identifies document regions:

```json
{
  "layout_type": "two-column",
  "regions": [
    {"id": 1, "type": "header", "bbox": [50, 50, 700, 100], "order": 1},
    {"id": 2, "type": "text", "bbox": [50, 120, 350, 800], "order": 2},
    {"id": 3, "type": "text", "bbox": [380, 120, 350, 800], "order": 3}
  ]
}
```

This metadata is saved to: `{snapshot_dir}/stages/01-mock-layout-detector/metadata/{item_id}.json`

### Stage 2: Region-Based OCR

The `ocr-tesseract` extractor (with `use_layout_metadata: true`):

1. Reads the layout metadata from Stage 1
2. Sorts regions by `order` field
3. For each region:
   - Crops the image using the `bbox` (bounding box)
   - Runs Tesseract OCR on just that region
   - Collects the extracted text
4. Joins all region texts with double newlines (`\n\n`)

### Stage 3: Text Reconstruction

The final text artifact preserves reading order:

```
Header Text

Left Column
...

Right Column
...
```

Saved to: `{snapshot_dir}/text/{item_id}.txt`

## Customization

### Different Layout Types

The mock layout detector supports multiple layout types:

```bash
# Single column
--stage "mock-layout-detector:layout_type=single-column"

# Two columns
--stage "mock-layout-detector:layout_type=two-column"

# Complex (multiple columns + tables)
--stage "mock-layout-detector:layout_type=complex"
```

### OCR Configuration

Adjust Tesseract OCR parameters:

```bash
--stage "ocr-tesseract:use_layout_metadata=true,lang=fra,min_confidence=0.8,psm=6"
```

Parameters:
- `lang`: Language code (e.g., `eng`, `fra`, `deu`, `spa`)
- `min_confidence`: Minimum word confidence (0.0-1.0)
- `psm`: Page Segmentation Mode (0-13)
- `oem`: OCR Engine Mode (0-3)

See [Tesseract Extractor Documentation](../extractors/ocr/tesseract.md) for details.

## Production Use

### Replace Mock Layout Detector

The `mock-layout-detector` uses hardcoded region data. For production:

1. **Use PaddleOCR** (already in Biblicus):
   ```bash
   biblicus --corpus /path/to/corpus extract build \
     --stage "paddleocr-vl" \
     --stage "ocr-tesseract:use_layout_metadata=true"
   ```

2. **Integrate Layout Parser**:
   - Install: `pip install layoutparser`
   - Create custom extractor that outputs compatible metadata
   - See [Creating Custom Extractors](../guides/custom-extractors.md)

3. **Use Docling** (includes layout analysis):
   ```bash
   biblicus --corpus /path/to/corpus extract build \
     --stage "docling-smol"
   ```

### Real-World Layouts

For actual documents:
- Academic papers: Use `"layout_type=two-column"`
- Books: Use `"layout_type=single-column"`
- Technical docs with tables: Use `"layout_type=complex"`
- Mixed documents: Implement custom layout detection

## Troubleshooting

### Tesseract Not Found

```
Error: Tesseract OCR binary not found
```

**Solution**: Install Tesseract binary (see [Prerequisites](#prerequisites))

### Low Confidence Text

If OCR results are poor:

1. **Lower confidence threshold**:
   ```bash
   --stage "ocr-tesseract:min_confidence=0.0"
   ```

2. **Try different PSM**:
   ```bash
   --stage "ocr-tesseract:psm=6"  # Single uniform block
   ```

3. **Check image quality**: Tesseract works best on 300+ DPI images

### Wrong Language

If text contains non-English characters:

```bash
# French
--stage "ocr-tesseract:lang=fra"

# Chinese Simplified
--stage "ocr-tesseract:lang=chi_sim"

# Multiple languages
--stage "ocr-tesseract:lang=eng+fra"
```

## Related GitHub Issues

This example implements the features discussed in:

- **Issue #4**: Tesseract OCR Integration
- **Issue #5**: Layout Detection Research ("Heron")
- **PR #7**: Metadata Field for Extraction Pipeline

## Further Reading

- [Tesseract OCR Extractor](../extractors/ocr/tesseract.md)
- [Mock Layout Detector](../extractors/layout/mock-layout-detector.md)
- [Pipeline Extractor](../extractors/pipeline.md)
- [Metadata Passing in Pipelines](../guides/pipeline-metadata.md)
