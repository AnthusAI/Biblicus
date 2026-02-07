# Biblicus Document Understanding Benchmark Results

**Last Updated:** 2026-02-05
**Benchmark Version:** 1.0.0

## Executive Summary

The Biblicus Document Understanding Benchmark evaluates OCR and document extraction pipelines across multiple document categories. This page presents results from benchmark runs on available datasets.

### Current Categories

| Category | Dataset | Documents | Status |
|----------|---------|-----------|--------|
| **Forms** | FUNSD | 199 total (20-50 for quick/standard) | Active |
| **Receipts** | SROIE | 626 total (50-100 for quick/standard) | Active |
| **Academic** | (pending) | - | Awaiting dataset |

---

## Forms Category (FUNSD)

**Dataset:** FUNSD - 199 scanned form documents with word-level ground truth
**Challenge:** Noisy scans, handwriting, field extraction
**Primary Metric:** F1 Score

### Results (20 documents)

| Rank | Pipeline | F1 Score | Precision | Recall | WER | Bigram |
|------|----------|----------|-----------|--------|-----|--------|
| 1 | **PaddleOCR** | **0.787** | 0.792 | 0.782 | 0.533 | 0.466 |
| 2 | Docling-Smol | 0.728 | 0.821 | 0.675 | 0.645 | 0.430 |
| 3 | Unstructured | 0.649 | 0.673 | 0.626 | 0.598 | 0.383 |
| 4 | Baseline (Tesseract) | 0.607 | 0.616 | 0.599 | 0.628 | 0.350 |
| 5 | Heron + Tesseract | 0.519 | 0.384 | **0.810** | 5.324 | **0.561** |
| 6 | RapidOCR | 0.507 | 0.556 | 0.467 | 0.748 | 0.206 |

### Key Findings - Forms

- **PaddleOCR** achieves best overall F1 (0.787) with balanced precision/recall
- **Heron + Tesseract** has highest recall (0.810) - best for finding all text
- **Docling-Smol** has highest precision (0.821) - fewest false positives
- Layout-aware approaches show mixed results on single-column forms

---

## Receipts Category (SROIE)

**Dataset:** SROIE - 626 receipt images with OCR text ground truth
**Challenge:** Dense text, small fonts, entity extraction
**Primary Metric:** F1 Score

### Results (50 documents)

| Rank | Pipeline | F1 Score | Precision | Recall | WER | LCS Ratio |
|------|----------|----------|-----------|--------|-----|-----------|
| 1 | **PaddleOCR** | **0.897** | - | - | - | - |
| 2 | Docling-Smol | 0.856 | - | - | - | - |
| 3 | Heron + Tesseract | 0.589 | 0.509 | 0.756 | 2.808 | 0.677 |
| 4 | RapidOCR | 0.589 | - | - | - | - |

### Key Findings - Receipts

- **PaddleOCR** dominates on receipts with F1 of 0.897
- **Docling-Smol** performs excellently (0.856) - strong VLM approach
- **Heron + Tesseract** underperforms (0.589) - layout detection less beneficial for single-column receipts
- Receipt OCR benefits from dense text recognition capabilities

---

## Pipeline Comparison Across Categories

| Pipeline | Forms F1 | Receipts F1 | Best For |
|----------|----------|-------------|----------|
| **PaddleOCR** | 0.787 | 0.897 | General-purpose, best overall |
| **Docling-Smol** | 0.728 | 0.856 | High precision needs |
| **Heron + Tesseract** | 0.519 | 0.589 | Multi-column layouts (not receipts/forms) |
| **RapidOCR** | 0.507 | 0.589 | Lightweight/CPU-only |

### Recommendations by Use Case

| Use Case | Recommended Pipeline | Why |
|----------|---------------------|-----|
| General OCR | PaddleOCR | Best F1 across all categories |
| High precision | Docling-Smol | Highest precision, fewest false positives |
| Find all text | Heron + Tesseract | Highest recall on forms (0.810) |
| CPU-only/lightweight | RapidOCR | Fast, no GPU required |
| Multi-column documents | Heron + Tesseract | Layout-aware reading order |

---

## Metrics Reference

### Set-Based Metrics (Position Agnostic)
- **F1 Score:** Harmonic mean of precision and recall
- **Precision:** Percentage of extracted words that are correct
- **Recall:** Percentage of ground truth words that were found

### Order-Aware Metrics (Sequence Quality)
- **WER (Word Error Rate):** Edit distance normalized - lower is better
- **LCS Ratio:** Longest common subsequence ratio - higher is better
- **Sequence Accuracy:** Percentage of words in correct sequential position

### N-gram Overlap (Local Ordering)
- **Bigram/Trigram:** Local word pair/triple ordering quality

---

## Running Benchmarks

### Quick Benchmark (~5-10 minutes)
```bash
biblicus benchmark run --config configs/benchmark/quick.yaml
```

### Standard Benchmark (~30-60 minutes)
```bash
biblicus benchmark run --config configs/benchmark/standard.yaml
```

### Full Benchmark (~2-4 hours)
```bash
biblicus benchmark run --config configs/benchmark/full.yaml
```

### Download Datasets
```bash
# Download all available datasets
biblicus benchmark download --datasets funsd,sroie

# Check dataset status
biblicus benchmark status
```

---

## Future Work

### Planned Categories

- **Academic Papers** - Multi-column layouts, reading order preservation
  - Blocked on finding dataset with actual scanned images
  - Candidates: ArXiv PDFs rendered as images, PubLayNet

### Additional Pipelines to Evaluate

- docling-granite (higher accuracy VLM)
- markitdown (image captioning approach)
- Additional layout-aware combinations

---

## See Also

- [Document Understanding Benchmark Guide](document-understanding-benchmark.md) - Full benchmark documentation
- [OCR Benchmarking Guide](ocr-benchmarking.md) - How to run your own benchmarks
- [Heron Implementation](heron-implementation.md) - Layout detection details
- [Layout-Aware OCR Results](layout-aware-ocr-results.md) - Detailed layout analysis
