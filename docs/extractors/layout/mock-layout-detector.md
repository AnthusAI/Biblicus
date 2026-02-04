# Mock Layout Detector

The `mock-layout-detector` extractor emits deterministic layout metadata for images.
It is intended for tests and documentation examples that demonstrate layout-aware OCR
pipelines.

This extractor does **not** perform real layout detection. It simply returns
predefined regions based on the `layout_type` configuration.

## Usage

```bash
biblicus extract build \
  --corpus my-corpus \
  --step "mock-layout-detector:layout_type=two-column" \
  --step "ocr-tesseract:use_layout_metadata=true"
```

## Configuration

- `layout_type`: One of `single-column`, `two-column`, or `complex`.

## Output Metadata

Example metadata for `two-column`:

```json
{
  "layout_detector": "mock-layout-detector",
  "layout_type": "two-column",
  "regions": [
    {"id": 1, "type": "header", "bbox": [50, 50, 700, 100], "order": 1},
    {"id": 2, "type": "text", "bbox": [50, 120, 350, 800], "order": 2},
    {"id": 3, "type": "text", "bbox": [380, 120, 350, 800], "order": 3}
  ],
  "num_regions": 3
}
```
