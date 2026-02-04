"""
Evaluation and benchmarking tools for extraction pipelines.

This module provides tools for quantifying the performance of OCR and other
extraction pipelines against ground truth data.
"""

from biblicus.evaluation.ocr_benchmark import (
    OCREvaluationResult,
    BenchmarkReport,
    OCRBenchmark,
    calculate_word_metrics,
    calculate_character_accuracy,
    calculate_word_order_metrics,
    calculate_ngram_overlap,
)
from biblicus.evaluation.retrieval import (
    _snapshot_artifact_bytes,
    evaluate_snapshot,
    load_dataset,
)

__all__ = [
    "OCREvaluationResult",
    "BenchmarkReport",
    "OCRBenchmark",
    "calculate_word_metrics",
    "calculate_character_accuracy",
    "calculate_word_order_metrics",
    "calculate_ngram_overlap",
    "evaluate_snapshot",
    "load_dataset",
    "_snapshot_artifact_bytes",
]
