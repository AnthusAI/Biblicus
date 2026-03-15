#!/usr/bin/env python3
"""
Benchmark Heron vs PaddleOCR layout detection.

Compares:
1. Heron-101 + Tesseract (two-stage layout-aware workflow)
2. PaddleOCR PP-Structure + Tesseract
3. Baseline Tesseract (no layout)
"""

from pathlib import Path
from biblicus import Corpus
from biblicus.evaluation.ocr_benchmark import OCRBenchmark
import json

print("=" * 70)
print("BENCHMARKING: HERON VS PADDLEOCR LAYOUT DETECTION")
print("=" * 70)
print()

# Initialize corpus and benchmark
corpus = Corpus(Path("corpora/funsd_demo").resolve())
benchmark = OCRBenchmark(corpus)

# Snapshot IDs (from previous runs)
heron_snapshot = "9df4310b153a8415451fa429255c706c6247ab1160e206af7dc7c7a063b7dda0"
paddleocr_snapshot = "49d1d1defc0d35af1314d4757c3ccf73657fa7a7af909e13d69cdfffc7473a33"

configs = {
    "heron": {
        "extractor_id": "pipeline",
        "config": {
            "stages": [
                {"extractor_id": "heron-layout", "config": {"model_variant": "101"}},
                {"extractor_id": "ocr-tesseract", "config": {"use_layout_metadata": True}}
            ]
        }
    },
    "paddleocr": {
        "extractor_id": "pipeline",
        "config": {
            "stages": [
                {"extractor_id": "paddleocr-layout", "config": {"lang": "en"}},
                {"extractor_id": "ocr-tesseract", "config": {"use_layout_metadata": True}}
            ]
        }
    }
}

results = {}

# Evaluate Heron pipeline
print("=" * 70)
print("1. HERON-101 + TESSERACT (Two-Stage Layout-Aware Workflow)")
print("=" * 70)
print()

heron_report = benchmark.evaluate_extraction(
    snapshot_reference=heron_snapshot,
    pipeline_config=configs["heron"]
)

heron_report.print_summary()
heron_report.to_json(Path("results/heron_tesseract.json"))
heron_report.to_csv(Path("results/heron_tesseract.csv"))

results["heron"] = {
    "f1": heron_report.avg_f1,
    "recall": heron_report.avg_recall,
    "precision": heron_report.avg_precision,
    "wer": heron_report.avg_word_error_rate,
    "seq_acc": heron_report.avg_sequence_accuracy,
    "bigram": heron_report.avg_bigram_overlap,
}

print()

# Evaluate PaddleOCR pipeline
print("=" * 70)
print("2. PADDLEOCR PP-STRUCTURE + TESSERACT")
print("=" * 70)
print()

paddleocr_report = benchmark.evaluate_extraction(
    snapshot_reference=paddleocr_snapshot,
    pipeline_config=configs["paddleocr"]
)

paddleocr_report.print_summary()

results["paddleocr"] = {
    "f1": paddleocr_report.avg_f1,
    "recall": paddleocr_report.avg_recall,
    "precision": paddleocr_report.avg_precision,
    "wer": paddleocr_report.avg_word_error_rate,
    "seq_acc": paddleocr_report.avg_sequence_accuracy,
    "bigram": paddleocr_report.avg_bigram_overlap,
}

print()

# Load baseline results
baseline_path = Path("results/final_benchmark.json")
if baseline_path.exists():
    with open(baseline_path) as f:
        all_results = json.load(f)

    for pipeline in all_results.get("pipelines", []):
        if pipeline.get("name") == "baseline-ocr":
            metrics = pipeline.get("metrics", {})
            results["baseline"] = {
                "f1": metrics.get("set_based", {}).get("avg_f1", 0),
                "recall": metrics.get("set_based", {}).get("avg_recall", 0),
                "precision": metrics.get("set_based", {}).get("avg_precision", 0),
                "wer": metrics.get("order_aware", {}).get("avg_word_error_rate", 0),
                "seq_acc": metrics.get("order_aware", {}).get("avg_sequence_accuracy", 0),
                "bigram": metrics.get("ngram", {}).get("avg_bigram_overlap", 0),
            }

# Final comparison
print("=" * 70)
print("FINAL COMPARISON")
print("=" * 70)
print()

print("| Pipeline | F1 | Recall | Precision | WER | Seq Acc | Bigram |")
print("|----------|-----|--------|-----------|-----|---------|--------|")

for name in ["heron", "paddleocr", "baseline"]:
    if name in results:
        r = results[name]
        print(f"| {name:15} | {r['f1']:.3f} | {r['recall']:.3f} | {r['precision']:.3f} | {r['wer']:.3f} | {r['seq_acc']:.3f} | {r['bigram']:.3f} |")

print()

# Analysis
if "heron" in results and "paddleocr" in results:
    print("=" * 70)
    print("ANALYSIS: HERON VS PADDLEOCR")
    print("=" * 70)
    print()

    h = results["heron"]
    p = results["paddleocr"]

    print("F1 Score:")
    diff = h["f1"] - p["f1"]
    pct = (diff / p["f1"] * 100) if p["f1"] > 0 else 0
    print(f"  Heron:      {h['f1']:.3f}")
    print(f"  PaddleOCR:  {p['f1']:.3f}")
    print(f"  Difference: {diff:+.3f} ({pct:+.1f}%)")
    print()

    print("Recall:")
    diff = h["recall"] - p["recall"]
    pct = (diff / p["recall"] * 100) if p["recall"] > 0 else 0
    print(f"  Heron:      {h['recall']:.3f}")
    print(f"  PaddleOCR:  {p['recall']:.3f}")
    print(f"  Difference: {diff:+.3f} ({pct:+.1f}%)")
    print()

    print("Sequence Accuracy (reading order):")
    diff = h["seq_acc"] - p["seq_acc"]
    pct = (diff / p["seq_acc"] * 100) if p["seq_acc"] > 0 else 0
    print(f"  Heron:      {h['seq_acc']:.3f}")
    print(f"  PaddleOCR:  {p['seq_acc']:.3f}")
    print(f"  Difference: {diff:+.3f} ({pct:+.1f}%)")
    print()

    print("Bigram Overlap (local ordering):")
    diff = h["bigram"] - p["bigram"]
    pct = (diff / p["bigram"] * 100) if p["bigram"] > 0 else 0
    print(f"  Heron:      {h['bigram']:.3f}")
    print(f"  PaddleOCR:  {p['bigram']:.3f}")
    print(f"  Difference: {diff:+.3f} ({pct:+.1f}%)")
    print()

# Save comparison
comparison_output = Path("results/heron_vs_paddleocr_comparison.json")
with open(comparison_output, "w") as f:
    json.dump({
        "timestamp": heron_report.evaluation_timestamp,
        "corpus": str(corpus.root),
        "results": results,
    }, f, indent=2)

print(f"✓ Detailed comparison saved to: {comparison_output}")
print("=" * 70)
