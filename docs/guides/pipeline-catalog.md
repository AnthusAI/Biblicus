# Pipeline Catalog

Complete reference of all extraction pipelines available for benchmarking in Biblicus.

## Overview

Biblicus includes 8+ pre-configured extraction pipelines with different speed/accuracy trade-offs. Each pipeline is defined in a YAML configuration file under `configs/`.

## Pipeline Comparison Table

| Pipeline | F1 Score | Recall | Speed | Use Case |
|----------|----------|--------|-------|----------|
| [PaddleOCR](#2-paddleocr) | **0.787** | 0.782 | Medium | Best overall accuracy |
| [Docling-Smol](#3-docling-smol) | 0.728 | 0.675 | Slow | Tables & formulas |
| [Unstructured](#5-unstructured) | 0.649 | 0.626 | Medium | General documents |
| [Baseline Tesseract](#1-baseline-tesseract) | 0.607 | 0.599 | Fast | Simple baseline |
| [Layout-Aware Tesseract (PaddleOCR)](#6-layout-aware-tesseract-paddleocr) | 0.601 | 0.732 | Medium | High recall needs |
| [Heron + Tesseract](#7-heron--tesseract) | 0.519 | **0.810** | Slow | Maximum extraction |
| [RapidOCR](#4-rapidocr) | 0.507 | 0.467 | **Fast** | Lightweight/embedded |

## Basic OCR Pipelines

### 1. Baseline Tesseract

Simple Tesseract OCR without layout detection.

**Configuration:** `configs/baseline-ocr.yaml`

```yaml
extractor_id: ocr-tesseract
config:
  min_confidence: 0.0
  lang: eng
```

**Performance (FUNSD Forms):**
- F1 Score: 0.607
- Recall: 0.599
- Precision: 0.615

**Strengths:**
- Fast processing
- Minimal dependencies
- Good baseline for comparison

**Weaknesses:**
- No layout understanding
- Struggles with complex formatting
- Lower accuracy on forms

**Best for:** Simple documents, baseline comparisons, speed-critical applications

---

### 2. PaddleOCR

PaddleOCR with VL model - **best overall performer**.

**Configuration:** `configs/ocr-paddleocr.yaml`

```yaml
extractor_id: ocr-paddleocr-vl
config:
  lang: en
```

**Performance (FUNSD Forms):**
- F1 Score: **0.787** ⭐ **BEST F1**
- Recall: 0.782
- Precision: 0.792
- Word Error Rate: 0.533

**Strengths:**
- Highest F1 score across benchmarks
- Built-in layout detection
- Good balance of precision and recall
- Handles complex layouts

**Weaknesses:**
- Requires PaddleOCR dependencies
- Slower than Tesseract
- Higher memory usage

**Best for:** Production systems, complex documents, when accuracy matters most

**Installation:**
```bash
pip install "biblicus[paddleocr]"
```

---

### 3. Docling-Smol

Docling with SmolDocling-256M vision-language model for document understanding.

**Configuration:** `configs/docling-smol.yaml`

```yaml
extractor_id: docling-smol
config:
  output_format: markdown
```

**Performance (FUNSD Forms):**
- F1 Score: 0.728
- Recall: 0.675
- Precision: 0.788

**Strengths:**
- Advanced VLM-based extraction
- Excellent for tables and formulas
- Structured output (markdown)
- Good semantic understanding

**Weaknesses:**
- Slower processing
- Higher resource requirements
- May be overkill for simple forms

**Best for:** Academic papers, technical documents, tables and formulas

**Installation:**
```bash
pip install "biblicus[docling]"
```

---

### 4. RapidOCR

Fast, lightweight OCR library for resource-constrained environments.

**Configuration:** `configs/ocr-rapidocr.yaml`

```yaml
extractor_id: ocr-rapidocr
config:
  use_det: true
  use_cls: true
  use_rec: true
```

**Performance (FUNSD Forms):**
- F1 Score: 0.507
- Recall: 0.467
- Precision: 0.556

**Strengths:**
- Very fast processing
- Minimal dependencies
- Low memory footprint
- Good for embedded systems

**Weaknesses:**
- Lower accuracy than PaddleOCR/Tesseract
- Limited language support
- Simpler text detection

**Best for:** Real-time applications, edge devices, resource constraints

**Installation:**
```bash
pip install "biblicus[ocr]"
```

---

### 5. Unstructured

Unstructured.io document parser with multi-format support.

**Configuration:** `configs/unstructured.yaml`

```yaml
extractor_id: unstructured
config: {}
```

**Performance (FUNSD Forms):**
- F1 Score: 0.649
- Recall: 0.626
- Precision: 0.673

**Strengths:**
- Handles many document formats
- Good general-purpose parser
- Structured element extraction
- PDF, Word, HTML, etc.

**Weaknesses:**
- Heavy dependency footprint
- Slower than specialized OCR
- May be overkill for images only

**Best for:** Mixed document types, production pipelines handling various formats

**Installation:**
```bash
pip install "biblicus[unstructured]"
```

---

### 8. MarkItDown

Microsoft's MarkItDown converter for document-to-markdown conversion.

**Configuration:** `configs/markitdown.yaml`

```yaml
extractor_id: markitdown
config: {}
```

**Strengths:**
- Excellent markdown output
- Handles Office documents
- Preserves structure

**Weaknesses:**
- Requires Python 3.10+
- Not optimized for OCR

**Best for:** Converting Office documents, markdown workflows

**Installation:**
```bash
pip install "biblicus[markitdown]"
```

---

## Layout-Aware Pipelines

Layout-aware pipelines use a two-stage approach:
1. **Layout detection** to identify document regions and reading order
2. **OCR** on each region in sequence

This improves reading order and can increase recall at the cost of precision.

### 6. Layout-Aware Tesseract (PaddleOCR)

PaddleOCR PP-Structure layout detection → Tesseract OCR.

**Configuration:** `configs/layout-aware-tesseract.yaml`

```yaml
extractor_id: pipeline
config:
  stages:
    - extractor_id: paddleocr-layout
      config:
        lang: en
    - extractor_id: ocr-tesseract
      config:
        use_layout_metadata: true
```

**Performance (FUNSD Forms):**
- F1 Score: 0.601
- Recall: 0.732 (+22.2% vs baseline Tesseract)
- Precision: 0.503

**Strengths:**
- Higher recall than baseline Tesseract
- Better reading order
- Handles multi-column layouts

**Weaknesses:**
- Lower precision (more false positives)
- Slower than single-stage
- Requires PaddleOCR

**Best for:** Documents where missing content is costly, complex layouts

**Trade-off:** Sacrifices precision for recall - finds more text but includes more noise.

---

### 7. Heron + Tesseract

IBM Heron-101 layout detection → Tesseract OCR for maximum text extraction.

**Configuration:** `configs/heron-tesseract.yaml`

```yaml
extractor_id: pipeline
config:
  stages:
    - extractor_id: heron-layout
      config:
        model_variant: "101"
        confidence_threshold: 0.6
    - extractor_id: ocr-tesseract
      config:
        use_layout_metadata: true
```

**Performance (FUNSD Forms):**
- F1 Score: 0.519
- Recall: **0.810** ⭐ **HIGHEST RECALL**
- Precision: 0.384
- Bigram Overlap: **0.561** (best local ordering)

**Strengths:**
- Finds 81% of all words - more than any other pipeline
- Excellent local word ordering (bigrams)
- Best for completeness
- Strong layout understanding

**Weaknesses:**
- Lowest precision (38.4%)
- More false positives/noise
- Slower processing
- Lower F1 due to precision trade-off

**Best for:**
- Applications where missing content is worse than noise
- Documents requiring maximum text extraction
- When completeness matters more than accuracy
- Legal/compliance where you can't miss text

**Trade-off:** Maximum recall at the cost of precision - extracts everything but includes more errors.

See [Heron Implementation Guide](heron-implementation.md) for detailed information.

---

## Vision-Language Models

### Docling-Granite

Docling with IBM Granite Docling-258M VLM for high-accuracy extraction.

**Configuration:** `configs/docling-granite.yaml`

```yaml
extractor_id: docling-granite
config:
  output_format: markdown
```

**Strengths:**
- Higher accuracy than SmolDocling
- Excellent for technical documents
- Strong table understanding

**Weaknesses:**
- Slower than SmolDocling
- Higher resource requirements

**Best for:** When maximum VLM accuracy is needed, complex technical documents

**Installation:**
```bash
pip install "biblicus[docling]"
```

---

## Creating Custom Pipelines

### Single-Stage Custom Pipeline

```yaml
# configs/my-custom-ocr.yaml
extractor_id: ocr-tesseract
config:
  lang: eng
  psm: 6  # Assume uniform block of text
  min_confidence: 0.6
  oem: 3  # Default LSTM engine
```

### Multi-Stage Custom Pipeline

```yaml
# configs/my-custom-pipeline.yaml
extractor_id: pipeline
config:
  stages:
    # Stage 1: Layout detection
    - extractor_id: heron-layout
      config:
        model_variant: "101"
        confidence_threshold: 0.7

    # Stage 2: OCR
    - extractor_id: ocr-paddleocr-vl
      config:
        use_layout_metadata: true
        lang: en

    # Stage 3: Post-processing (if available)
    - extractor_id: select-longest-text
      config: {}
```

### Testing Your Custom Pipeline

```python
from pathlib import Path
from biblicus import Corpus
from biblicus.evaluation.ocr_benchmark import OCRBenchmark
from biblicus.extraction import build_extraction_snapshot
import yaml

# Load your config
with open("configs/my-custom-pipeline.yaml") as f:
    config = yaml.safe_load(f)

# Build extraction snapshot
corpus = Corpus(Path("corpora/funsd_benchmark"))
snapshot = build_extraction_snapshot(
    corpus,
    extractor_id=config["extractor_id"],
    configuration_name="my-custom-pipeline",
    configuration=config["config"]
)

# Evaluate
benchmark = OCRBenchmark(corpus)
report = benchmark.evaluate_extraction(
    snapshot_reference=snapshot.snapshot_id,
    pipeline_config=config
)

# View results
report.print_summary()
```

### Adding to Benchmark Suite

Edit `scripts/benchmark_all_pipelines.py`:

```python
PIPELINE_CONFIGS = [
    # ... existing configs ...
    "configs/my-custom-pipeline.yaml",
]
```

Then run:

```bash
python scripts/benchmark_all_pipelines.py
```

## Pipeline Selection Guide

### By Use Case

**Maximum Accuracy (F1):** Use [PaddleOCR](#2-paddleocr)
- Best: Forms, receipts, general documents
- F1: 0.787

**Maximum Recall (Completeness):** Use [Heron + Tesseract](#7-heron--tesseract)
- Best: Legal, compliance, when missing text is critical
- Recall: 0.810

**Speed-Critical:** Use [RapidOCR](#4-rapidocr) or [Baseline Tesseract](#1-baseline-tesseract)
- Best: Real-time, embedded systems
- Fast processing

**Tables & Formulas:** Use [Docling-Smol](#3-docling-smol) or [Docling-Granite](#docling-granite)
- Best: Academic papers, technical documents
- VLM-based understanding

**Multi-Format Documents:** Use [Unstructured](#5-unstructured)
- Best: PDF, Word, HTML, mixed formats
- General-purpose parser

### By Document Type

**Forms (FUNSD-like):**
1. PaddleOCR (F1: 0.787)
2. Docling-Smol (F1: 0.728)
3. Layout-Aware Tesseract (F1: 0.601, Recall: 0.732)

**Receipts (dense text):**
1. PaddleOCR (best for entity extraction)
2. Docling-Smol (good structure preservation)

**Academic Papers (multi-column):**
1. Docling-Granite (best layout understanding)
2. Docling-Smol (good tables/formulas)
3. Heron + Tesseract (strong reading order)

**Simple Text Documents:**
1. Baseline Tesseract (fast, sufficient)
2. RapidOCR (lightweight alternative)

## Performance Tuning

### Improving Recall

If you're missing too much text:
- Try Heron + Tesseract (highest recall: 0.810)
- Lower confidence thresholds
- Use layout-aware pipelines
- Consider multi-model ensembles

### Improving Precision

If you're getting too much noise:
- Use PaddleOCR (best balance)
- Increase confidence thresholds
- Add post-processing filters
- Use VLM-based models for cleaner output

### Improving Speed

If processing is too slow:
- Use RapidOCR or Tesseract baseline
- Reduce image resolution
- Skip layout detection stage
- Process in parallel batches

## Next Steps

- **[Run benchmarks](quickstart-benchmarking.md)** to compare pipelines on your data
- **[Understand metrics](metrics-reference.md)** to interpret results
- **[View current results](benchmark-results.md)** to see how pipelines compare
- **[OCR Benchmarking Guide](ocr-benchmarking.md)** for practical how-to

## References

- Pipeline configurations: `configs/`
- Benchmark scripts: `scripts/benchmark_*.py`
- Evaluation module: `src/biblicus/evaluation/ocr_benchmark.py`
- [Heron Implementation Details](heron-implementation.md)
- [Layout-Aware OCR Analysis](layout-aware-ocr-results.md)
