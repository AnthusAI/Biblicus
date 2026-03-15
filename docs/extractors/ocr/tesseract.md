# Tesseract OCR Extractor

The Tesseract OCR extractor (`ocr-tesseract`) performs optical character recognition on image items using [Tesseract OCR](https://github.com/tesseract-ocr/tesseract).

## Features

- Extracts text from images using Tesseract OCR engine
- Supports confidence-based filtering of recognized text
- Configurable language support
- Layout-aware mode for reading region metadata from previous pipeline stages
- Per-word confidence scoring

## Installation

The Tesseract extractor requires both the Python wrapper and the Tesseract OCR binary:

```bash
# Install Python dependencies
pip install "biblicus[tesseract]"

# Install Tesseract OCR binary
# macOS:
brew install tesseract

# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# Windows:
# Download installer from https://github.com/UB-Mannheim/tesseract/wiki
```

## Configuration

### Parameters

- **`min_confidence`** (float, default: `0.0`): Minimum per-word confidence threshold (0.0-1.0). Words with confidence below this value are excluded from output.
- **`joiner`** (str, default: `"\n"`): String used to join recognized text segments.
- **`lang`** (str, default: `"eng"`): Tesseract language code (e.g., `"eng"`, `"fra"`, `"chi_sim"`).
- **`psm`** (int, default: `3`): Page Segmentation Mode (0-13). See [PSM Reference](#psm-reference) below.
- **`oem`** (int, default: `3`): OCR Engine Mode (0-3). See [OEM Reference](#oem-reference) below.
- **`use_layout_metadata`** (bool, default: `false`): Read region metadata from previous pipeline stage and OCR each region separately.

### Example Configuration

```yaml
extractor_id: ocr-tesseract
config:
  min_confidence: 0.6
  lang: eng
  psm: 3
  oem: 3
  use_layout_metadata: false
```

## Usage

### Basic OCR

Extract text from all images in a corpus:

```bash
biblicus --corpus /path/to/corpus extract build --stage ocr-tesseract
```

### With Confidence Filtering

Only include words with high confidence:

```bash
biblicus --corpus /path/to/corpus extract build --stage "ocr-tesseract:min_confidence=0.8"
```

### Layout-Aware OCR Pipeline

Use layout detection followed by region-based OCR:

```bash
biblicus --corpus /path/to/corpus extract build \
  --stage "mock-layout-detector:layout_type=two-column" \
  --stage "ocr-tesseract:use_layout_metadata=true"
```

### Python API

```python
from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot

corpus = Corpus.from_path("/path/to/corpus")

# Basic OCR
snapshot = build_extraction_snapshot(
    corpus=corpus,
    extractor_id="ocr-tesseract",
    configuration_name="basic-ocr",
    configuration={
        "min_confidence": 0.6,
        "lang": "eng",
    }
)

# Layout-aware OCR pipeline
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
                "config": {"use_layout_metadata": True}
            }
        ]
    }
)
```

## Layout-Aware Mode

When `use_layout_metadata` is enabled, the Tesseract extractor reads region metadata from the previous pipeline stage. This is useful for documents with complex layouts where the reading order matters.

### Requirements

1. Must be used within a pipeline extractor
2. Previous stage must output metadata with `regions` key
3. Each region must have: `bbox` (bounding box), `type`, and `order`

### Region Metadata Format

```json
{
  "layout_type": "two-column",
  "regions": [
    {
      "id": 1,
      "type": "header",
      "bbox": [50, 50, 700, 100],
      "order": 1
    },
    {
      "id": 2,
      "type": "text",
      "bbox": [50, 120, 350, 800],
      "order": 2
    },
    {
      "id": 3,
      "type": "text",
      "bbox": [380, 120, 350, 800],
      "order": 3
    }
  ]
}
```

### How It Works

1. Layout detector identifies regions and reading order
2. Tesseract crops each region based on bounding box
3. Each region is OCR'd separately
4. Text is merged in correct reading order (based on `order` field)
5. Regions are separated by double newlines (`\n\n`)

See the [Layout-Aware OCR Example](../../examples/layout-aware-ocr.md) for a complete walkthrough.

## PSM Reference

Page Segmentation Mode controls how Tesseract analyzes the page layout:

| PSM | Description |
|-----|-------------|
| 0 | Orientation and script detection (OSD) only |
| 1 | Automatic page segmentation with OSD |
| 2 | Automatic page segmentation, no OSD or OCR |
| 3 | Fully automatic page segmentation, no OSD (Default) |
| 4 | Assume a single column of text of variable sizes |
| 5 | Assume a single uniform block of vertically aligned text |
| 6 | Assume a single uniform block of text |
| 7 | Treat the image as a single text line |
| 8 | Treat the image as a single word |
| 9 | Treat the image as a single word in a circle |
| 10 | Treat the image as a single character |
| 11 | Sparse text. Find as much text as possible in no particular order |
| 12 | Sparse text with OSD |
| 13 | Raw line. Treat the image as a single text line, bypassing hacks |

## OEM Reference

OCR Engine Mode selects which Tesseract engine to use:

| OEM | Description |
|-----|-------------|
| 0 | Legacy engine only |
| 1 | Neural nets LSTM engine only |
| 2 | Legacy + LSTM engines |
| 3 | Default, based on what is available (Recommended) |

## Language Support

Tesseract supports over 100 languages. Common language codes:

- `eng` - English
- `fra` - French
- `deu` - German
- `spa` - Spanish
- `chi_sim` - Chinese Simplified
- `chi_tra` - Chinese Traditional
- `jpn` - Japanese
- `kor` - Korean
- `ara` - Arabic
- `rus` - Russian
- `por` - Portuguese
- `ita` - Italian

For the full list, see the [Tesseract language data repository](https://github.com/tesseract-ocr/tessdata).

To install additional language packs:

```bash
# macOS (via Homebrew)
brew install tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr-fra  # French
sudo apt-get install tesseract-ocr-deu  # German
# etc.
```

## Output

### Text Artifacts

Extracted text is written to: `{snapshot_dir}/text/{item_id}.txt`

### Metadata Artifacts

When using layout-aware mode, OCR metadata is written to: `{snapshot_dir}/metadata/{item_id}.json`

Example metadata:
```json
{
  "regions_processed": 3,
  "regions_with_text": 2
}
```

### Confidence

The extractor returns the average confidence of all accepted words (those above `min_confidence` threshold). Confidence is a float between 0.0 and 1.0.

## Related

- [Mock Layout Detector](../layout/mock-layout-detector.md) - Simulated layout detection for testing
- [Layout-Aware OCR Example](../../examples/layout-aware-ocr.md) - Complete workflow demonstration
- [Pipeline Extractor](../pipeline.md) - Combining multiple extractors
