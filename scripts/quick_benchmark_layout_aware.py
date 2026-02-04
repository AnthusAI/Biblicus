#!/usr/bin/env python3
"""
Quick benchmark comparing layout-aware Tesseract with other pipelines.

This validates production's layout-aware OCR workflow against baseline approaches.
"""

from pathlib import Path
from biblicus import Corpus
from biblicus.evaluation.ocr_benchmark import OCRBenchmark
import json

# Initialize corpus
corpus = Corpus(Path("corpora/funsd_demo").resolve())
benchmark = OCRBenchmark(corpus)

# Get the layout-aware snapshot we just created
snapshot_id = "49d1d1defc0d35af1314d4757c3ccf73657fa7a7af909e13d69cdfffc7473a33"

config = {
    "extractor_id": "pipeline",
    "config": {
        "steps": [
            {"extractor_id": "paddleocr-layout", "config": {"lang": "en"}},
            {"extractor_id": "ocr-tesseract", "config": {"use_layout_metadata": True}},
        ]
    }
}

print("=" * 70)
print("EVALUATING LAYOUT-AWARE TESSERACT PIPELINE")
print("=" * 70)
print()

# Evaluate
report = benchmark.evaluate_extraction(
    snapshot_reference=snapshot_id,
    pipeline_config=config
)

# Print summary
report.print_summary()

# Save results
output_dir = Path("results")
output_dir.mkdir(exist_ok=True)

json_path = output_dir / "layout_aware_tesseract.json"
csv_path = output_dir / "layout_aware_tesseract.csv"

report.to_json(json_path)
report.to_csv(csv_path)

print()
print("=" * 70)
print("COMPARISON WITH BASELINE")
print("=" * 70)
print()

# Load baseline results from previous benchmark
baseline_path = Path("results/final_benchmark.json")
if baseline_path.exists():
    with open(baseline_path) as f:
        all_results = json.load(f)

    # Find baseline Tesseract results
    baseline_tesseract = None
    paddleocr = None

    for pipeline_result in all_results.get("pipelines", []):
        pipeline_name = pipeline_result.get("name", "")
        metrics = pipeline_result.get("metrics", {})

        if pipeline_name == "baseline-ocr":
            baseline_tesseract = {
                "f1": metrics.get("set_based", {}).get("avg_f1", 0),
                "recall": metrics.get("set_based", {}).get("avg_recall", 0),
                "wer": metrics.get("order_aware", {}).get("avg_word_error_rate", 0),
                "sequence_accuracy": metrics.get("order_aware", {}).get("avg_sequence_accuracy", 0),
            }
        elif pipeline_name == "paddleocr":
            paddleocr = {
                "f1": metrics.get("set_based", {}).get("avg_f1", 0),
                "recall": metrics.get("set_based", {}).get("avg_recall", 0),
                "wer": metrics.get("order_aware", {}).get("avg_word_error_rate", 0),
                "sequence_accuracy": metrics.get("order_aware", {}).get("avg_sequence_accuracy", 0),
            }

    if baseline_tesseract:
        print("Baseline Tesseract (no layout detection):")
        print(f"  F1 Score:           {baseline_tesseract['f1']:.3f}")
        print(f"  Recall:             {baseline_tesseract['recall']:.3f}")
        print(f"  Word Error Rate:    {baseline_tesseract['wer']:.3f}")
        print(f"  Sequence Accuracy:  {baseline_tesseract['sequence_accuracy']:.3f}")
        print()

        print("Layout-Aware Tesseract (with PaddleOCR PP-Structure):")
        print(f"  F1 Score:           {report.avg_f1:.3f}")
        print(f"  Recall:             {report.avg_recall:.3f}")
        print(f"  Word Error Rate:    {report.avg_word_error_rate:.3f}")
        print(f"  Sequence Accuracy:  {report.avg_sequence_accuracy:.3f}")
        print()

        # Calculate differences
        f1_diff = report.avg_f1 - baseline_tesseract['f1']
        recall_diff = report.avg_recall - baseline_tesseract['recall']
        wer_diff = report.avg_word_error_rate - baseline_tesseract['wer']
        seq_diff = report.avg_sequence_accuracy - baseline_tesseract['sequence_accuracy']

        print("Improvement:")
        print(f"  F1 Score:           {f1_diff:+.3f} ({f1_diff/baseline_tesseract['f1']*100:+.1f}%)")
        print(f"  Recall:             {recall_diff:+.3f} ({recall_diff/baseline_tesseract['recall']*100:+.1f}%)")
        print(f"  Word Error Rate:    {wer_diff:+.3f} (lower is better)")
        print(f"  Sequence Accuracy:  {seq_diff:+.3f} ({seq_diff/baseline_tesseract['sequence_accuracy']*100:+.1f}%)")
        print()

    if paddleocr:
        print("=" * 70)
        print("COMPARISON WITH BEST PERFORMER (PaddleOCR)")
        print("=" * 70)
        print()
        print("PaddleOCR (direct OCR, no layout detection):")
        print(f"  F1 Score:           {paddleocr['f1']:.3f}")
        print(f"  Recall:             {paddleocr['recall']:.3f}")
        print(f"  Word Error Rate:    {paddleocr['wer']:.3f}")
        print(f"  Sequence Accuracy:  {paddleocr['sequence_accuracy']:.3f}")
        print()

        print("Layout-Aware Tesseract:")
        print(f"  F1 Score:           {report.avg_f1:.3f}")
        print(f"  Recall:             {report.avg_recall:.3f}")
        print(f"  Word Error Rate:    {report.avg_word_error_rate:.3f}")
        print(f"  Sequence Accuracy:  {report.avg_sequence_accuracy:.3f}")
        print()

        # Calculate differences
        f1_diff = report.avg_f1 - paddleocr['f1']
        recall_diff = report.avg_recall - paddleocr['recall']

        print("Difference from PaddleOCR:")
        print(f"  F1 Score:           {f1_diff:+.3f}")
        print(f"  Recall:             {recall_diff:+.3f}")
        print()
else:
    print("⚠️  Baseline benchmark results not found at results/final_benchmark.json")
    print("   Run scripts/benchmark_all_pipelines.py first to generate baseline.")

print("=" * 70)
