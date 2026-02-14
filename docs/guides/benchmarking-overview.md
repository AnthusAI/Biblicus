# Benchmarking Overview

Biblicus is designed as a **retrieval augmented generation platform** where you can experiment with different extraction pipelines, retrieval backends, and configurations—then benchmark them against each other to find the best approach for your use case.

## Why Benchmark?

Different documents require different approaches:
- **Forms** need accurate field extraction and noise handling
- **Receipts** require dense text recognition and entity extraction
- **Academic papers** demand proper reading order across multi-column layouts
- **Handwritten content** benefits from specialized OCR models

Biblicus lets you:
1. **Compare extraction pipelines** (Tesseract, PaddleOCR, Docling VLMs, etc.)
2. **Evaluate retrieval backends** (scan, SQLite FTS, TF-vector)
3. **Measure with comprehensive metrics** (F1 score, WER, sequence accuracy, n-gram overlap)
4. **Reproduce results** with snapshot-based evaluation

## Benchmarking as a Platform

Rather than providing a single "best" configuration, Biblicus provides:
- **Multiple extraction pipelines** with different speed/accuracy trade-offs
- **Standardized benchmark datasets** (FUNSD forms, SROIE receipts, Scanned ArXiv papers)
- **Comprehensive metrics** covering both accuracy and reading order
- **Reproducible workflows** with configuration files and snapshot IDs

You can:
- Benchmark any aspect: extraction, retrieval, or end-to-end analysis
- Add custom pipelines and evaluate them against existing ones
- Use quick/standard/full benchmark modes for development vs. validation
- Export results to JSON or CSV for further analysis

## Current Benchmarks

### Document Extraction Benchmarks

Biblicus includes multi-category benchmarks for document extraction:

**1. Forms (FUNSD Dataset)**
- 199 scanned form documents with handwriting and noise
- Primary metric: F1 Score
- Tests field extraction, layout understanding, noise handling

**2. Receipts (SROIE Dataset)**
- 626 receipt images with dense text and small fonts
- Primary metric: F1 Score
- Tests entity extraction, dense text recognition

**3. Academic Papers (Scanned ArXiv)** *(dataset pending)*
- Multi-column academic papers
- Primary metric: LCS Ratio (reading order preservation)
- Tests complex layout understanding and reading order

### Evaluated Pipelines

We benchmark 8+ extraction pipelines including:
- Tesseract (baseline)
- PaddleOCR (high accuracy)
- RapidOCR (lightweight)
- Docling VLMs (SmolDocling, Granite)
- Layout-aware approaches (Heron + Tesseract, PaddleOCR layout + Tesseract)
- Unstructured.io parser
- MarkItDown

See the [Pipeline Catalog](pipeline-catalog.md) for detailed descriptions and configurations.

## Getting Started

### Quick Start (5-10 minutes)

Run a quick benchmark on a subset of documents:

```bash
python scripts/benchmark_all_pipelines.py \
  --corpus-path corpora/funsd \
  --config configs/benchmark/quick.yaml \
  --output results/quick_benchmark.json
```

See [Quickstart Guide](quickstart-benchmarking.md) for step-by-step instructions.

### Understanding Metrics

Biblicus measures extraction quality using three categories of metrics:

- **Set-based metrics**: Precision, Recall, F1 Score (position-agnostic)
- **Order-aware metrics**: WER, Sequence Accuracy, LCS Ratio (reading order quality)
- **N-gram overlap**: Bigram and trigram overlap (local ordering)

See [Metrics Reference](metrics-reference.md) for detailed explanations.

### Current Results

For the latest benchmark results and recommendations by use case:

→ [Current Benchmark Results](benchmark-results.md)

## Documentation Structure

This documentation follows a hub-and-spoke model:

**Core Guides:**
- **[Quickstart Guide](quickstart-benchmarking.md)**: Step-by-step instructions for running benchmarks
- **[Pipeline Catalog](pipeline-catalog.md)**: All available extraction pipelines with configurations
- **[Metrics Reference](metrics-reference.md)**: Detailed metric definitions and interpretation
- **[Current Results](benchmark-results.md)**: Latest benchmark findings and recommendations

**Deep Dives:**
- **[OCR Benchmarking Guide](ocr-benchmarking.md)**: Practical how-to for OCR evaluation
- **[Multi-Category Benchmark Framework](document-understanding-benchmark.md)**: Architecture and design
- **[Heron Implementation](heron-implementation.md)**: Layout detection specifics
- **[Layout-Aware OCR Results](layout-aware-ocr-results.md)**: Detailed layout-aware analysis

## Benchmark Modes

Biblicus supports three benchmark modes to balance speed vs. thoroughness:

| Mode | Duration | Use Case | Configuration |
|------|----------|----------|---------------|
| **Quick** | 5-10 min | Development iteration | `configs/benchmark/quick.yaml` |
| **Standard** | 30-60 min | Release validation | `configs/benchmark/standard.yaml` |
| **Full** | 2-4 hours | Comprehensive evaluation | `configs/benchmark/full.yaml` |

## Customization

### Adding Custom Pipelines

You can add your own extraction pipelines to benchmark:

1. Create a pipeline configuration in `configs/`
2. Add it to the benchmark runner
3. Run the benchmark to compare against existing pipelines

See [Pipeline Catalog](pipeline-catalog.md) for examples.

### Adding Custom Benchmarks

The benchmark framework is extensible:

1. Create a new `CategoryConfig` with your dataset
2. Define the primary metric for your document type
3. Add it to the `BenchmarkRunner`

See [Multi-Category Benchmark Framework](document-understanding-benchmark.md) for details.

## Architecture

Biblicus uses a three-tier benchmarking system:

**Tier 1: Individual Document Evaluation**
- `OCREvaluationResult` for single document metrics
- `BenchmarkReport` for aggregate metrics

**Tier 2: Multi-Category Orchestration**
- `CategoryConfig` defines document categories
- `CategoryResult` aggregates per-category results
- `BenchmarkResult` provides multi-category aggregation

**Tier 3: User-Facing Scripts**
- `benchmark_all_pipelines.py` - Compare all pipelines
- `benchmark_heron_vs_paddleocr.py` - Direct comparison
- `quick_benchmark_layout_aware.py` - Validate specific workflow

See [Multi-Category Benchmark Framework](document-understanding-benchmark.md) for architectural details.

## Next Steps

1. **[Run your first benchmark](quickstart-benchmarking.md)** - 5-minute quickstart
2. **[Explore pipelines](pipeline-catalog.md)** - See what's available
3. **[Understand metrics](metrics-reference.md)** - Learn how quality is measured
4. **[Review current results](benchmark-results.md)** - See how pipelines compare

## Contributing

To add new benchmarks or pipelines:

1. Follow the existing patterns in `src/biblicus/evaluation/`
2. Add documentation to the appropriate guide
3. Update this overview to link to your additions
4. Submit a pull request

For questions or issues, see the [main repository](https://github.com/AnthusAI/Biblicus).
