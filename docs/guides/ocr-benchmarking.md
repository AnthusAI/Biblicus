# OCR Pipeline Benchmarking Guide

Practical how-to guide for benchmarking OCR pipelines in Biblicus using labeled ground truth data.

> **New to benchmarking?** Start with the [Benchmarking Overview](benchmarking-overview.md) for a platform introduction, or jump to the [Quickstart Guide](quickstart-benchmarking.md) for step-by-step instructions.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Benchmark Dataset](#benchmark-dataset)
4. [Running Benchmarks](#running-benchmarks)
5. [Custom Pipelines](#custom-pipelines)
6. [Results Analysis](#results-analysis)
7. [Dependencies](#dependencies)
8. [Troubleshooting](#troubleshooting)

**Reference Documentation:**
- [Pipeline Catalog](pipeline-catalog.md) - All available pipelines with performance data
- [Metrics Reference](metrics-reference.md) - Detailed metric explanations
- [Current Results](benchmark-results.md) - Latest benchmark findings

---

## Overview

This guide provides practical instructions for running OCR benchmarks. It covers:
- Setting up benchmark datasets
- Running evaluation scripts
- Creating custom pipelines
- Analyzing results
- Troubleshooting common issues

For architectural details and the multi-category framework, see [Document Understanding Benchmark Framework](document-understanding-benchmark.md).

**Key Features:**
- Multiple evaluation metrics (F1, recall, precision, WER, sequence accuracy)
- Support for any extraction pipeline
- Per-document and aggregate results
- JSON/CSV export for analysis
- Comparison between pipeline configurations

---

## Quick Start

```bash
# 1. Download the FUNSD benchmark dataset
python scripts/download_funsd_samples.py

# 2. Run benchmark on all built-in pipelines
python scripts/benchmark_all_pipelines.py

# 3. View results
cat results/final_benchmark.json | jq '.pipelines[] | {name, f1: .metrics.set_based.avg_f1}'
```

For detailed step-by-step instructions, see the [Quickstart Guide](quickstart-benchmarking.md).

---

## Benchmark Dataset

### FUNSD Dataset

**What is FUNSD?**
- **F**orm **U**nderstanding in **N**oisy **S**canned **D**ocuments
- 199 annotated scanned form images
- 31,485 words with ground truth OCR text
- Real-world noisy scanned documents (not born-digital)

**Download:**
```bash
python scripts/download_funsd_samples.py
```

This will:
1. Download the FUNSD dataset from the official source
2. Extract 20 test forms into `corpora/funsd_benchmark/`
3. Create ground truth files in `metadata/funsd_ground_truth/`
4. Tag documents with `["funsd", "scanned", "ground-truth"]`

**Dataset structure:**
```
corpora/funsd_benchmark/
├── metadata/
│   ├── config.json
│   ├── catalog.json
│   └── funsd_ground_truth/
│       ├── <document-id>.txt                 # Ground truth OCR text
│       └── ...
├── <document-id>--82092117.png               # Scanned form image
└── ...
```

### Using Your Own Dataset

To benchmark on custom documents:

1. **Prepare ground truth files:**
   ```
   corpus_dir/metadata/ground_truth/
   ├── <document-id>.txt
   └── ...
   ```

2. **Ingest documents:**
   ```python
   from biblicus import Corpus
   from pathlib import Path

   corpus = Corpus(Path("my_corpus"))
   corpus.ingest_file("document.png", tags=["benchmark"])
   ```

3. **Run evaluation:**
   ```python
   from biblicus.evaluation.ocr_benchmark import OCRBenchmark

   benchmark = OCRBenchmark(corpus)
   report = benchmark.evaluate_extraction(
       snapshot_reference="<snapshot-id>",
       ground_truth_dir=corpus.root / "metadata" / "ground_truth"
   )
   ```

---

## Available Pipelines

Biblicus includes 8+ pre-configured extraction pipelines. For complete details on each pipeline including:
- Performance metrics and trade-offs
- Configuration examples
- When to use each pipeline
- Installation requirements

See the **[Pipeline Catalog](pipeline-catalog.md)**.

**Quick summary:**
- **PaddleOCR** (F1: 0.787) - Best overall accuracy
- **Docling-Smol** (F1: 0.728) - Tables & formulas
- **Heron + Tesseract** (Recall: 0.810) - Maximum extraction
- **Baseline Tesseract**, **RapidOCR**, **Unstructured**, and more

---

## Understanding Metrics

Biblicus uses three categories of metrics:
- **Set-based**: F1, Precision, Recall (word-finding accuracy)
- **Order-aware**: WER, LCS Ratio (reading order quality)
- **N-gram**: Bigram, Trigram overlap (local ordering)

For detailed explanations, interpretations, and use case recommendations, see the **[Metrics Reference](metrics-reference.md)**.

---

## Running Benchmarks

### Benchmark All Pipelines

```bash
python scripts/benchmark_all_pipelines.py
```

**What it does:**
1. Loads all pipeline configs from `configs/`
2. Builds extraction snapshots for each pipeline
3. Evaluates against FUNSD ground truth
4. Generates comprehensive comparison report

**Output:**
- `results/final_benchmark.json` - Full results with all metrics
- Console output with summary table

**Example output:**
```
========================================
FINAL BENCHMARK RESULTS
========================================

| Rank | Pipeline          | F1    | Recall | WER   | Seq Acc |
|------|-------------------|-------|--------|-------|---------|
| 1    | paddleocr         | 0.787 | 0.782  | 0.533 | 0.031   |
| 2    | docling-smol      | 0.728 | 0.675  | 0.645 | 0.021   |
| 3    | unstructured      | 0.649 | 0.626  | 0.598 | 0.014   |
| 4    | baseline-ocr      | 0.607 | 0.599  | 0.628 | 0.013   |
```

### Benchmark Single Pipeline

```bash
# Using config file
python scripts/evaluate_ocr_pipeline.py \
  --corpus corpora/funsd_benchmark \
  --config configs/heron-tesseract.yaml \
  --output results/heron_tesseract.json

# Or specify inline
python -c "
from pathlib import Path
from biblicus import Corpus
from biblicus.evaluation.ocr_benchmark import OCRBenchmark
from biblicus.extraction import build_extraction_snapshot

corpus = Corpus(Path('corpora/funsd_benchmark').resolve())

# Build snapshot
config = {
    'extractor_id': 'pipeline',
    'config': {
        'stages': [
            {'extractor_id': 'heron-layout', 'config': {'model_variant': '101'}},
            {'extractor_id': 'ocr-tesseract', 'config': {'use_layout_metadata': True}}
        ]
    }
}

snapshot = build_extraction_snapshot(
    corpus,
    extractor_id='pipeline',
    configuration_name='heron-tesseract',
    configuration=config['config']
)

# Evaluate
benchmark = OCRBenchmark(corpus)
report = benchmark.evaluate_extraction(
    snapshot_reference=snapshot.snapshot_id,
    pipeline_config=config
)

report.print_summary()
report.to_json(Path('results/heron_tesseract.json'))
"
```

### Compare Two Pipelines

```bash
python scripts/compare_pipelines.py \
  --baseline configs/baseline-ocr.yaml \
  --experimental configs/heron-tesseract.yaml \
  --corpus corpora/funsd_benchmark \
  --output results/comparison.json
```


## Custom Pipelines

### Create Custom Pipeline Config

1. **Create YAML config:**

```yaml
# configs/my-custom-pipeline.yaml
extractor_id: pipeline
config:
  stages:
    # Step 1: Layout detection (optional)
    - extractor_id: heron-layout
      config:
        model_variant: "101"
        confidence_threshold: 0.7

    # Step 2: OCR
    - extractor_id: ocr-tesseract
      config:
        use_layout_metadata: true
        min_confidence: 0.5
        lang: eng
        psm: 3

    # Step 3: Post-processing (optional)
    - extractor_id: clean-gibberish  # If implemented
      config:
        strictness: medium
```

2. **Add to benchmark script:**

```python
# Edit scripts/benchmark_all_pipelines.py
PIPELINE_CONFIGS = [
    # ... existing configs ...
    "configs/my-custom-pipeline.yaml",
]
```

3. **Run benchmark:**

```bash
python scripts/benchmark_all_pipelines.py
```

### Benchmark Custom Extractor

If you've created a new extractor:

1. **Register in `__init__.py`:**

```python
# src/biblicus/extractors/__init__.py
from .my_extractor import MyExtractor

extractors: Dict[str, TextExtractor] = {
    # ... existing extractors ...
    MyExtractor.extractor_id: MyExtractor(),
}
```

2. **Create config:**

```yaml
# configs/my-extractor.yaml
extractor_id: my-extractor
config:
  param1: value1
  param2: value2
```

3. **Benchmark:**

```bash
python scripts/evaluate_ocr_pipeline.py \
  --corpus corpora/funsd_benchmark \
  --config configs/my-extractor.yaml \
  --output results/my_extractor.json
```

---

## Results Analysis

### JSON Output Structure

```json
{
  "evaluation_timestamp": "2026-02-03T23:00:00Z",
  "corpus_path": "/path/to/corpus",
  "pipeline_configuration": { ... },
  "total_documents": 20,

  "aggregate_metrics": {
    "avg_precision": 0.625,
    "avg_recall": 0.599,
    "avg_f1": 0.607,
    "median_f1": 0.655,
    "avg_word_error_rate": 0.628,
    "avg_sequence_accuracy": 0.013,
    "avg_bigram_overlap": 0.350
  },

  "per_document_results": [
    {
      "document_id": "abc123...",
      "image_path": "abc123...png",
      "ground_truth_word_count": 134,
      "extracted_word_count": 135,
      "metrics": {
        "precision": 0.615,
        "recall": 0.619,
        "f1_score": 0.617,
        "word_error_rate": 3.056,
        "sequence_accuracy": 0.043
      }
    }
  ]
}
```

### CSV Output

Per-document results exported to CSV for spreadsheet analysis:

```csv
document_id,image_path,gt_word_count,ocr_word_count,precision,recall,f1_score,wer
abc123...,abc123.png,134,135,0.615,0.619,0.617,3.056
```

### Analyzing Results

**Find best pipeline:**
```bash
cat results/final_benchmark.json | jq '.pipelines | sort_by(-.metrics.set_based.avg_f1) | .[0] | {name, f1: .metrics.set_based.avg_f1}'
```

**Compare reading order quality:**
```bash
cat results/final_benchmark.json | jq '.pipelines[] | {name, seq_acc: .metrics.order_aware.avg_sequence_accuracy}' | sort -t: -k2 -nr
```

**Find documents with low accuracy:**
```bash
cat results/my_pipeline.json | jq '.per_document_results[] | select(.metrics.f1_score < 0.5) | {doc: .document_id[:16], f1: .metrics.f1_score}'
```

**Export to CSV for Excel:**
```python
import json
import pandas as pd

with open('results/final_benchmark.json') as f:
    data = json.load(f)

# Create DataFrame
rows = []
for pipeline in data['pipelines']:
    rows.append({
        'name': pipeline['name'],
        'f1': pipeline['metrics']['set_based']['avg_f1'],
        'recall': pipeline['metrics']['set_based']['avg_recall'],
        'precision': pipeline['metrics']['set_based']['avg_precision'],
        'wer': pipeline['metrics']['order_aware']['avg_word_error_rate'],
        'seq_acc': pipeline['metrics']['order_aware']['avg_sequence_accuracy'],
    })

df = pd.DataFrame(rows)
df.to_csv('results/summary.csv', index=False)
```

---

## Dependencies

### Installing OCR Dependencies

Different pipelines require different dependencies:

**Tesseract:**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Python
pip install pytesseract
```

**PaddleOCR:**
```bash
pip install "paddleocr" "paddlex[ocr]"
```

**Heron (IBM Research):**
```bash
pip install "transformers>=4.40.0" "torch>=2.0.0"
```

**Docling:**
```bash
pip install docling
```

**RapidOCR:**
```bash
pip install rapidocr-onnxruntime
```

**Unstructured:**
```bash
pip install "unstructured[image]"
```

**Evaluation dependencies:**
```bash
pip install editdistance  # For WER calculation
```

### Checking Dependencies

```bash
# Test Tesseract
tesseract --version

# Test PaddleOCR
python -c "from paddleocr import PPStructureV3; print('PaddleOCR OK')"

# Test Heron
python -c "from transformers import RTDetrV2ForObjectDetection; print('Heron OK')"

# Test Docling
python -c "from docling.document_converter import DocumentConverter; print('Docling OK')"
```

---

## Troubleshooting

### Common Issues

**Issue: "Ground truth directory not found"**
```
Solution: Run python scripts/download_funsd_samples.py first
```

**Issue: "No text files found in snapshot"**
```
Solution: Check that extraction succeeded. View snapshot manifest.
```

**Issue: "Model download fails"**
```
Solution: Check internet connection. Models download on first use:
- PaddleOCR: ~100MB
- Heron: ~150MB
- Docling: varies by model
```

**Issue: "Out of memory"**
```
Solution: Use smaller batch sizes or lighter models:
- Heron: Use "base" instead of "101"
- Reduce number of test documents
```

**Issue: "Results don't match expected performance"**
```
Solution: Check:
- Correct ground truth files loaded
- Document types match pipeline strengths
- Dependencies installed correctly
```

---

## See Also

**Benchmarking Documentation:**
- [Benchmarking Overview](benchmarking-overview.md) - Platform introduction
- [Quickstart Guide](quickstart-benchmarking.md) - Step-by-step instructions
- [Pipeline Catalog](pipeline-catalog.md) - All available pipelines
- [Metrics Reference](metrics-reference.md) - Metric explanations
- [Current Results](benchmark-results.md) - Latest findings
- [Document Understanding Framework](document-understanding-benchmark.md) - Architecture details
- [Heron Implementation](heron-implementation.md) - Heron-specific details
- [Layout-Aware OCR Results](layout-aware-ocr-results.md) - Layout analysis

**External References:**
- [FUNSD Dataset](https://guillaumejaume.github.io/FUNSD/)
- [Heron Models (IBM Research)](https://huggingface.co/ds4sd/docling-layout-heron-101)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
