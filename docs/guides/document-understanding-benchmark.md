# Biblicus Document Understanding Benchmark

Multi-category benchmark framework architecture and design documentation.

> **Looking for practical instructions?** See the [Quickstart Guide](quickstart-benchmarking.md) or [OCR Benchmarking Guide](ocr-benchmarking.md). This document covers the architectural design of the multi-category framework.

The Biblicus Document Understanding Benchmark evaluates OCR and document extraction pipelines across diverse document types. Rather than testing on a single dataset, the benchmark measures performance across three distinct categories—forms, academic papers, and receipts—each presenting unique challenges for document processing systems.

**Related Documentation:**
- [Benchmarking Overview](benchmarking-overview.md) - Platform introduction
- [Quickstart Guide](quickstart-benchmarking.md) - Step-by-step instructions
- [Pipeline Catalog](pipeline-catalog.md) - Available pipelines
- [Metrics Reference](metrics-reference.md) - Detailed metric explanations
- [Current Results](benchmark-results.md) - Latest findings

## Why a Multi-Category Benchmark?

Document extraction pipelines often excel at one document type while struggling with others. A pipeline optimized for clean academic PDFs may fail on noisy scanned forms. A receipt parser tuned for dense text may miss content in multi-column layouts.

The Biblicus benchmark reveals these trade-offs by testing pipelines across:

| Category | Dataset | Documents | Challenge |
|----------|---------|-----------|-----------|
| **Forms** | FUNSD | 199 | Noise, handwriting, field extraction |
| **Academic** | Scanned ArXiv | 100+ | Multi-column layout, reading order |
| **Receipts** | SROIE | 626 | Dense text, entity extraction |

## Quick Start

```bash
# Download benchmark datasets
biblicus benchmark download --datasets funsd,sroie,scanned-arxiv

# Run quick benchmark (~5-10 minutes)
biblicus benchmark run --config configs/benchmark/quick.yaml

# Run standard benchmark (~30-60 minutes)
biblicus benchmark run

# Generate markdown report
biblicus benchmark report --output docs/guides/benchmark-results.md
```

## Document Categories

### Forms (FUNSD)

**Dataset:** Form Understanding in Noisy Scanned Documents (FUNSD)

FUNSD contains 199 real scanned forms from the 1980s-1990s with word-level ground truth annotations. These documents test a pipeline's ability to handle:

- **Noise and degradation** - Real scans with artifacts, skew, and varying quality
- **Structured fields** - Headers, questions, answers, checkboxes
- **Entity extraction** - Identifying form field values and their relationships

**Primary Metric:** F1 Score (balanced word finding)

**Source:** https://guillaumejaume.github.io/FUNSD/

### Academic Papers (Scanned ArXiv)

**Dataset:** Scanned ArXiv Papers

Academic papers rendered as images (not born-digital PDFs) test layout-aware extraction:

- **Multi-column layouts** - Two-column academic paper format
- **Reading order** - Correct sequencing across columns
- **Mixed content** - Text, figures, tables, equations, references

**Primary Metric:** LCS Ratio (Longest Common Subsequence ratio measuring reading order preservation)

**Source:** HuggingFace `IAMJB/scanned-arxiv-papers`

### Receipts (SROIE)

**Dataset:** Scanned Receipts OCR and Information Extraction (SROIE)

626 receipt images from ICDAR 2019 with both OCR text and structured entity annotations:

- **Dense text** - Compact layouts with small fonts
- **Entity extraction** - Company name, date, address, total amount
- **Semantic understanding** - Beyond raw OCR to structured data

**Primary Metrics:** F1 Score + Entity F1 (per-entity-type accuracy)

**Source:** ICDAR 2019 Competition (https://rrc.cvc.uab.es/?ch=13)

## Metrics

The benchmark uses three categories of metrics to evaluate extraction quality. For complete details on each metric including formulas, interpretations, and use case recommendations, see the **[Metrics Reference](metrics-reference.md)**.

**Quick summary:**

**Set-Based Metrics (Word Finding):**
- Precision, Recall, F1 Score
- Primary metrics for forms and receipts

**Order-Aware Metrics (Sequence Quality):**
- LCS Ratio (primary for academic papers)
- Word Error Rate (WER)
- Sequence Accuracy, Bigram Overlap

**Entity Metrics (Semantic Extraction):**
- Entity F1 (for SROIE receipts)
- Per-Type F1 (date, total, company, address)

## Scoring Strategy

### Per-Category Scores (Primary)

Each category reports its primary metric independently:

- **Forms:** F1 Score
- **Academic:** LCS Ratio
- **Receipts:** F1 Score + Entity F1

This allows comparing pipelines within each category without conflating different document types.

### Weighted Aggregate (Optional)

For quick overall comparison, an optional weighted aggregate combines category scores:

```
Aggregate = 0.40 × Forms F1 + 0.35 × Academic LCS + 0.25 × Receipts F1
```

Weights are configurable in benchmark configuration files. Adjust based on your document mix.

## Running Benchmarks

### Benchmark Modes

| Mode | Forms | Academic | Receipts | Runtime |
|------|-------|----------|----------|---------|
| `quick` | 20 docs | 20 docs | 50 docs | ~5-10 min |
| `standard` | 50 docs | 100 docs | 100 docs | ~30-60 min |
| `full` | 199 docs | All | 626 docs | ~2-4 hours |

### Command Examples

```bash
# Quick benchmark for development iteration
biblicus benchmark run --config configs/benchmark/quick.yaml

# Standard benchmark (default)
biblicus benchmark run

# Full benchmark for release validation
biblicus benchmark run --config configs/benchmark/full.yaml

# Single category
biblicus benchmark run --category forms

# Specific pipelines
biblicus benchmark run --pipelines paddleocr,heron-tesseract,baseline-ocr

# Check dataset status
biblicus benchmark status
```

### Configuration Files

Benchmark configurations in `configs/benchmark/`:

```yaml
# configs/benchmark/quick.yaml
benchmark_name: quick
categories:
  forms:
    dataset: funsd
    subset_size: 20
    primary_metric: f1_score
  academic:
    dataset: scanned-arxiv
    subset_size: 20
    primary_metric: lcs_ratio
  receipts:
    dataset: sroie
    subset_size: 50
    primary_metric: f1_score
pipelines:
  - configs/baseline-ocr.yaml
  - configs/ocr-paddleocr.yaml
  - configs/heron-tesseract.yaml
aggregate_weights:
  forms: 0.40
  academic: 0.35
  receipts: 0.25
```

## Understanding Results

### JSON Output Structure

```json
{
  "benchmark_version": "1.0.0",
  "timestamp": "2026-02-05T12:00:00Z",
  "categories": {
    "forms": {
      "dataset": "funsd",
      "documents_evaluated": 50,
      "pipelines": [
        {
          "name": "paddleocr",
          "metrics": {
            "f1": 0.787,
            "recall": 0.782,
            "precision": 0.792,
            "wer": 0.533
          }
        }
      ],
      "best_pipeline": "paddleocr"
    },
    "academic": {
      "dataset": "scanned-arxiv",
      "pipelines": [...],
      "best_pipeline": "heron-tesseract"
    },
    "receipts": {
      "dataset": "sroie",
      "pipelines": [...],
      "best_pipeline": "paddleocr"
    }
  },
  "aggregate": {
    "weighted_score": 0.72,
    "weights": {"forms": 0.40, "academic": 0.35, "receipts": 0.25}
  },
  "recommendations": {
    "best_overall": "paddleocr",
    "best_for_layout": "heron-tesseract",
    "best_for_speed": "rapidocr"
  }
}
```

### Interpreting Trade-offs

**High Recall, Lower Precision (e.g., Heron + Tesseract)**
- Finds more words but includes more noise
- Best when missing content is costly
- Use for: Completeness-critical applications, legal discovery

**High Precision, Lower Recall (e.g., Docling-Smol)**
- Fewer false positives but may miss some text
- Best when accuracy matters more than completeness
- Use for: Automated data entry, structured extraction

**High LCS Ratio (e.g., Layout-Aware Pipelines)**
- Preserves reading order in multi-column documents
- May have higher WER due to region boundary effects
- Use for: Academic papers, newspapers, reports

## Pipeline Recommendations

Based on benchmark results:

| Use Case | Recommended Pipeline | Why |
|----------|---------------------|-----|
| **General accuracy** | PaddleOCR | Highest F1 across document types |
| **Multi-column documents** | Heron + Tesseract | Best reading order preservation |
| **Receipts/forms** | PaddleOCR | Strong entity extraction |
| **Speed priority** | RapidOCR | Fastest inference, acceptable accuracy |
| **Completeness critical** | Heron + Tesseract | Highest recall (0.810) |
| **Low noise tolerance** | Docling-Smol | Highest precision |

## Adding Custom Pipelines

To benchmark your own pipeline:

1. Create a pipeline configuration in `configs/`:

```yaml
# configs/my-custom-pipeline.yaml
extractor_id: pipeline
config:
  stages:
    - extractor_id: my-layout-detector
      config:
        threshold: 0.7
    - extractor_id: ocr-tesseract
      config:
        use_layout_metadata: true
```

2. Run benchmark with your pipeline:

```bash
biblicus benchmark run --pipelines my-custom-pipeline
```

3. Compare results:

```bash
biblicus benchmark report --input results/benchmark_*.json
```

## Dataset Downloads

### Automatic Download

```bash
# Download all datasets
biblicus benchmark download --datasets funsd,sroie,scanned-arxiv

# Download specific dataset
biblicus benchmark download --datasets sroie
```

### Manual Download

If automatic download fails:

**FUNSD:**
1. Visit https://guillaumejaume.github.io/FUNSD/
2. Download `dataset.zip`
3. Extract to `corpora/funsd_benchmark/`

**SROIE:**
1. Register at https://rrc.cvc.uab.es/?ch=13
2. Download task files
3. Run `python scripts/download_sroie_samples.py --from-local /path/to/sroie`

**Scanned ArXiv:**
```python
from datasets import load_dataset
dataset = load_dataset("IAMJB/scanned-arxiv-papers")
```

## Licensing

| Dataset | License | Usage |
|---------|---------|-------|
| FUNSD | CC BY-NC-SA 4.0 | Non-commercial research |
| SROIE | Research only | ICDAR competition terms |
| Scanned ArXiv | Varies | Check per-paper license |

## See Also

- [OCR Benchmarking Guide](ocr-benchmarking.md) - Detailed OCR pipeline evaluation
- [Benchmark Results](benchmark-results.md) - Current benchmark results
- [Heron Implementation](heron-implementation.md) - Layout detection details
- [Extractors Overview](../extractors/index.md) - Available extraction pipelines
