# Benchmarking Quickstart Guide

Get started with benchmarking Biblicus extraction pipelines in under 10 minutes.

## Prerequisites

- Biblicus installed: `pip install -e .`
- Python 3.9 or higher
- Optional dependencies based on pipelines you want to test:
  - `pip install "biblicus[paddleocr]"` for PaddleOCR
  - `pip install "biblicus[docling]"` for Docling VLMs
  - `pip install "biblicus[unstructured]"` for Unstructured.io

## Quick Start (5 minutes)

### Step 1: Download Benchmark Dataset

```bash
python scripts/download_funsd_samples.py
```

This downloads 20 FUNSD form images into `corpora/funsd_benchmark/` with ground truth text files.

**What is FUNSD?**
- Form Understanding in Noisy Scanned Documents
- 199 annotated scanned forms
- Real-world documents with noise and handwriting
- Industry-standard OCR benchmark

### Step 2: Run Quick Benchmark

Run a quick benchmark on a subset of pipelines:

```bash
python scripts/benchmark_all_pipelines.py \
  --corpus-path corpora/funsd_benchmark \
  --config configs/benchmark/quick.yaml \
  --output results/quick_benchmark.json
```

**What this does:**
- Tests 8+ extraction pipelines
- Evaluates on 20 documents (~5-10 minutes)
- Generates comprehensive comparison report
- Outputs results to `results/quick_benchmark.json`

### Step 3: View Results

**Console summary:**
```bash
cat results/quick_benchmark.json | jq '.pipelines[] | {name, f1: .metrics.set_based.avg_f1, recall: .metrics.set_based.avg_recall}'
```

**Full report:**
```bash
cat results/quick_benchmark.json | jq '.'
```

**Example output:**
```json
{
  "name": "paddleocr",
  "f1": 0.787,
  "recall": 0.782
}
{
  "name": "docling-smol",
  "f1": 0.728,
  "recall": 0.675
}
```

**Interpretation:**
- **PaddleOCR** has the highest F1 (0.787) → Best overall accuracy
- **Recall** shows how much text each pipeline finds

See [Metrics Reference](metrics-reference.md) for detailed explanations.

---

## Standard Benchmark (30-60 minutes)

For more thorough validation before release:

```bash
python scripts/benchmark_all_pipelines.py \
  --corpus-path corpora/funsd_benchmark \
  --config configs/benchmark/standard.yaml \
  --output results/standard_benchmark.json
```

**Differences from quick:**
- Tests on 50 forms (vs 20)
- More iterations for stable results
- Takes 30-60 minutes
- Recommended before major releases

---

## Full Benchmark (2-4 hours)

For comprehensive evaluation:

```bash
python scripts/benchmark_all_pipelines.py \
  --corpus-path corpora/funsd_benchmark \
  --config configs/benchmark/full.yaml \
  --output results/full_benchmark.json
```

**Differences:**
- All 199 FUNSD documents
- Exhaustive evaluation
- Takes 2-4 hours
- For research and paper publication

---

## Benchmark Specific Pipelines

### Single Pipeline Benchmark

Test just one pipeline:

```bash
python scripts/evaluate_ocr_pipeline.py \
  --corpus corpora/funsd_benchmark \
  --config configs/ocr-paddleocr.yaml \
  --output results/paddleocr_results.json
```

### Compare Two Pipelines

Direct comparison between two approaches:

```bash
python scripts/benchmark_heron_vs_paddleocr.py \
  --corpus corpora/funsd_benchmark \
  --output results/heron_vs_paddleocr.json
```

This script specifically compares:
- **Heron + Tesseract**: Maximum recall, more noise
- **PaddleOCR**: Best F1, balanced accuracy

### Quick Layout-Aware Validation

Test layout-aware pipeline quickly:

```bash
python scripts/quick_benchmark_layout_aware.py
```

Validates the layout-aware Tesseract pipeline on a small subset.

---

## Understanding Results

### Key Metrics to Check

**For Forms (FUNSD):**
1. **F1 Score** - Overall accuracy (target: ≥0.75)
2. **Recall** - Completeness (target: ≥0.70)
3. **WER** - Reading order quality (target: ≤0.60)

**For Receipts:**
1. **F1 Score** - Entity extraction accuracy (target: ≥0.80)
2. **Precision** - Clean output (target: ≥0.75)

**For Academic Papers:**
1. **LCS Ratio** - Reading order preservation (target: ≥0.75)
2. **Bigram Overlap** - Column mixing detection (target: ≥0.60)

See [Metrics Reference](metrics-reference.md) for detailed explanations.

### Result Structure

```json
{
  "benchmark_timestamp": "2026-02-13T12:00:00Z",
  "corpus_path": "corpora/funsd_benchmark",
  "total_pipelines": 8,
  "successful_pipelines": 8,
  "failed_pipelines": 0,
  "pipelines": [
    {
      "name": "paddleocr",
      "snapshot_id": "abc123...",
      "success": true,
      "metrics": {
        "set_based": {
          "avg_f1": 0.787,
          "avg_precision": 0.792,
          "avg_recall": 0.782
        },
        "order_aware": {
          "avg_wer": 0.533,
          "avg_sequence_accuracy": 0.031,
          "avg_lcs_ratio": 0.621
        },
        "ngram": {
          "avg_bigram_overlap": 0.521,
          "avg_trigram_overlap": 0.412
        }
      },
      "total_documents": 20,
      "processing_time": 145.3
    }
  ],
  "best_performers": {
    "best_f1": "paddleocr",
    "best_sequence_accuracy": "docling-smol",
    "lowest_wer": "paddleocr",
    "best_bigram": "heron-tesseract"
  }
}
```

### Exporting Results

**To CSV for spreadsheet analysis:**

```python
from pathlib import Path
from biblicus.evaluation.ocr_benchmark import OCRBenchmark
import json

# Load benchmark results
with open("results/quick_benchmark.json") as f:
    results = json.load(f)

# Export to CSV
for pipeline in results["pipelines"]:
    name = pipeline["name"]
    # Access per-document results if needed
    # report.to_csv(Path(f"results/{name}_per_document.csv"))
```

**To JSON for programmatic access:**

Results are already in JSON format. Use `jq` for filtering:

```bash
# Get F1 scores only
jq '.pipelines[] | {name, f1: .metrics.set_based.avg_f1}' results/quick_benchmark.json

# Filter by F1 > 0.70
jq '.pipelines[] | select(.metrics.set_based.avg_f1 > 0.70)' results/quick_benchmark.json

# Best performer
jq '.best_performers' results/quick_benchmark.json
```

---

## Customizing Benchmarks

### Create Custom Benchmark Config

Create `configs/benchmark/my-benchmark.yaml`:

```yaml
# Benchmark configuration
mode: custom
categories:
  - name: forms
    corpus_path: corpora/funsd_benchmark
    ground_truth_dir: metadata/funsd_ground_truth
    primary_metric: f1
    document_count: 30  # Subset of documents

pipelines:
  - configs/baseline-ocr.yaml
  - configs/ocr-paddleocr.yaml
  - configs/my-custom-pipeline.yaml
```

Run with:

```bash
python scripts/benchmark_all_pipelines.py \
  --config configs/benchmark/my-benchmark.yaml \
  --output results/my_benchmark.json
```

### Add Custom Pipeline

1. **Create pipeline config** in `configs/my-custom-pipeline.yaml`:

```yaml
extractor_id: pipeline
config:
  stages:
    - extractor_id: heron-layout
      config:
        model_variant: "101"
        confidence_threshold: 0.7
    - extractor_id: ocr-paddleocr-vl
      config:
        use_layout_metadata: true
        lang: en
```

2. **Test pipeline manually:**

```python
from pathlib import Path
from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.evaluation.ocr_benchmark import OCRBenchmark
import yaml

# Load config
with open("configs/my-custom-pipeline.yaml") as f:
    config = yaml.safe_load(f)

# Build extraction
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

# Print results
report.print_summary()
```

3. **Add to benchmark suite:**

Edit `scripts/benchmark_all_pipelines.py`:

```python
PIPELINE_CONFIGS = [
    "configs/baseline-ocr.yaml",
    "configs/ocr-paddleocr.yaml",
    # ... existing configs ...
    "configs/my-custom-pipeline.yaml",  # Add yours
]
```

---

## Benchmarking Custom Datasets

### Prepare Your Dataset

1. **Create corpus directory:**

```bash
mkdir -p my_corpus/metadata/ground_truth
```

2. **Add documents:**

```bash
# Copy your images/PDFs
cp /path/to/documents/* my_corpus/
```

3. **Create ground truth files:**

For each document, create a text file with the expected extracted text:

```bash
# my_corpus/metadata/ground_truth/<document-id>.txt
echo "Expected text from document" > my_corpus/metadata/ground_truth/doc1.txt
```

4. **Ingest into corpus:**

```python
from pathlib import Path
from biblicus import Corpus

corpus = Corpus.init(Path("my_corpus"))

for doc_path in Path("my_corpus").glob("*.png"):
    if not doc_path.stem.startswith("."):
        corpus.ingest_file(doc_path, tags=["benchmark"])
```

### Run Benchmark

```bash
python scripts/benchmark_all_pipelines.py \
  --corpus-path my_corpus \
  --ground-truth-dir my_corpus/metadata/ground_truth \
  --config configs/benchmark/quick.yaml \
  --output results/my_corpus_benchmark.json
```

---

## Troubleshooting

### Common Issues

**Error: "FUNSD dataset not found"**
```bash
# Solution: Download the dataset first
python scripts/download_funsd_samples.py
```

**Error: "Pipeline failed: paddleocr not installed"**
```bash
# Solution: Install the required extra
pip install "biblicus[paddleocr]"
```

**Error: "Ground truth file not found"**
```bash
# Solution: Ensure ground truth files match document IDs
ls corpora/funsd_benchmark/metadata/funsd_ground_truth/
```

**Slow benchmark performance:**
```bash
# Solution: Use quick config for development
python scripts/benchmark_all_pipelines.py \
  --config configs/benchmark/quick.yaml  # Not standard or full
```

### Debugging Failed Pipelines

Check the detailed error:

```python
import json

with open("results/quick_benchmark.json") as f:
    results = json.load(f)

for pipeline in results["pipelines"]:
    if not pipeline["success"]:
        print(f"Failed: {pipeline['name']}")
        print(f"Error: {pipeline.get('error', 'Unknown error')}")
```

### Memory Issues

If benchmarking runs out of memory:

1. **Reduce batch size** in benchmark config
2. **Use quick config** with fewer documents
3. **Test one pipeline at a time**

```bash
# Instead of all pipelines:
python scripts/evaluate_ocr_pipeline.py \
  --corpus corpora/funsd_benchmark \
  --config configs/ocr-paddleocr.yaml
```

---

## Next Steps

Now that you've run your first benchmark:

1. **[Understand metrics](metrics-reference.md)** - Learn what each metric means
2. **[Explore pipelines](pipeline-catalog.md)** - See all available pipelines and their trade-offs
3. **[View current results](benchmark-results.md)** - Compare your results to latest benchmarks
4. **[Deep dive: OCR Benchmarking](ocr-benchmarking.md)** - Comprehensive guide to OCR evaluation
5. **[Deep dive: Multi-Category Framework](document-understanding-benchmark.md)** - Architecture and design

---

## Benchmark Modes Summary

| Mode | Duration | Documents | Use Case | Config |
|------|----------|-----------|----------|--------|
| **Quick** | 5-10 min | 20 forms | Development iteration | `configs/benchmark/quick.yaml` |
| **Standard** | 30-60 min | 50 forms | Release validation | `configs/benchmark/standard.yaml` |
| **Full** | 2-4 hours | All (199 forms) | Research/publication | `configs/benchmark/full.yaml` |

---

## CLI Reference

### Benchmark All Pipelines

```bash
python scripts/benchmark_all_pipelines.py \
  --corpus-path CORPUS_PATH \
  --config CONFIG_FILE \
  --output OUTPUT_FILE
```

### Evaluate Single Pipeline

```bash
python scripts/evaluate_ocr_pipeline.py \
  --corpus CORPUS_PATH \
  --config PIPELINE_CONFIG \
  --output OUTPUT_FILE
```

### Compare Two Pipelines

```bash
python scripts/benchmark_heron_vs_paddleocr.py \
  --corpus CORPUS_PATH \
  --output OUTPUT_FILE
```

### Quick Layout-Aware Test

```bash
python scripts/quick_benchmark_layout_aware.py
```

---

## Resources

- **[Benchmarking Overview](benchmarking-overview.md)** - Platform introduction
- **[Pipeline Catalog](pipeline-catalog.md)** - All available pipelines
- **[Metrics Reference](metrics-reference.md)** - Understanding evaluation metrics
- **[Current Results](benchmark-results.md)** - Latest benchmark findings
- **Benchmark configs:** `configs/benchmark/`
- **Scripts:** `scripts/benchmark_*.py`
- **Results:** `results/`
