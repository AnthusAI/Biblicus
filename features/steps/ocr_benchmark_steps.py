from __future__ import annotations

import builtins
import sys
import types
from pathlib import Path
from typing import Any, Dict

from behave import given, when, then

from biblicus import Corpus
from biblicus.evaluation.ocr_benchmark import (
    BenchmarkReport,
    OCREvaluationResult,
    OCRBenchmark,
    calculate_character_accuracy,
    calculate_ngram_overlap,
    calculate_word_metrics,
    calculate_word_order_metrics,
)


def _ensure_editdistance_module(context, *, distance: int = 0) -> None:
    original_module = sys.modules.get("editdistance")
    context._editdistance_original_module = original_module

    class _FakeEditDistance:
        @staticmethod
        def eval(_a: Any, _b: Any) -> int:
            return distance

    sys.modules["editdistance"] = _FakeEditDistance()


def _block_editdistance_import(context) -> None:
    original_import = builtins.__import__
    context._editdistance_original_import = original_import

    def _blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "editdistance":
            raise ImportError("editdistance blocked")
        return original_import(name, *args, **kwargs)

    if "editdistance" in sys.modules:
        context._editdistance_original_module = sys.modules.get("editdistance")
        del sys.modules["editdistance"]

    import_patcher = types.SimpleNamespace()
    import_patcher.stop = lambda: None
    builtins.__import__ = _blocked_import
    context._editdistance_import_patcher = import_patcher


def _restore_editdistance_import(context) -> None:
    original_import = getattr(context, "_editdistance_original_import", None)
    if original_import is not None:
        builtins.__import__ = original_import
        context._editdistance_original_import = None


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _normalize_text_token(value: str) -> str:
    if value == "<empty>":
        return ""
    return value


def _prepare_ocr_benchmark_corpus(context, snapshot_id: str) -> Path:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    item_id = "item-1"
    raw_path = corpus.root / f"{item_id}--file%3A%2F%2Fexample.png"
    raw_path.write_text("raw", encoding="utf-8")

    snapshot_dir = (
        corpus.root
        / "extracted"
        / "pipeline"
        / snapshot_id
        / "text"
    )
    _write_text(snapshot_dir / f"{item_id}.txt", "Hello world")

    ground_truth_dir = corpus.root / "metadata" / "funsd_ground_truth"
    _write_text(ground_truth_dir / f"{item_id}.txt", "Hello world")

    context._ocr_benchmark_corpus = corpus
    context._ocr_benchmark_snapshot_id = snapshot_id
    return corpus.root


def _prepare_ocr_snapshot(
    context,
    snapshot_id: str,
    *,
    include_ground_truth_dir: bool = True,
    include_ground_truth_file: bool = True,
    include_snapshot_dir: bool = True,
    include_text_dir: bool = True,
    include_text_files: bool = True,
) -> Corpus:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    item_id = "item-1"
    raw_path = corpus.root / f"{item_id}--file%3A%2F%2Fexample.png"
    raw_path.write_text("raw", encoding="utf-8")

    if include_snapshot_dir:
        snapshot_dir = (
            corpus.root / "extracted" / "pipeline" / snapshot_id
        )
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        if include_text_dir:
            text_dir = snapshot_dir / "text"
            text_dir.mkdir(parents=True, exist_ok=True)
            if include_text_files:
                _write_text(text_dir / f"{item_id}.txt", "Hello world")

    if include_ground_truth_dir:
        ground_truth_dir = corpus.root / "metadata" / "funsd_ground_truth"
        ground_truth_dir.mkdir(parents=True, exist_ok=True)
        if include_ground_truth_file:
            _write_text(ground_truth_dir / f"{item_id}.txt", "Hello world")

    context._ocr_benchmark_corpus = corpus
    context._ocr_benchmark_snapshot_id = snapshot_id
    return corpus


@given("a fake editdistance module is installed")
def step_fake_editdistance_installed(context) -> None:
    _ensure_editdistance_module(context, distance=0)


@given("editdistance import is blocked")
def step_block_editdistance(context) -> None:
    _block_editdistance_import(context)


@when(
    'I compute OCR benchmark metrics for ground truth "{ground_truth}" and extracted "{extracted}"'
)
def step_compute_ocr_metrics(context, ground_truth: str, extracted: str) -> None:
    normalized_gt = _normalize_text_token(ground_truth)
    normalized_ex = _normalize_text_token(extracted)
    context._ocr_word_metrics = calculate_word_metrics(normalized_gt, normalized_ex)
    context._ocr_character_accuracy = calculate_character_accuracy(normalized_gt, normalized_ex)


@when(
    'I compute OCR benchmark order metrics for ground truth "{ground_truth}" and extracted "{extracted}"'
)
def step_compute_ocr_order_metrics(context, ground_truth: str, extracted: str) -> None:
    normalized_gt = _normalize_text_token(ground_truth)
    normalized_ex = _normalize_text_token(extracted)
    context._ocr_order_metrics = calculate_word_order_metrics(normalized_gt, normalized_ex)


@when(
    'I compute OCR benchmark ngram overlap for ground truth "{ground_truth}" and extracted "{extracted}" with n {n:d}'
)
def step_compute_ocr_ngram_overlap(context, ground_truth: str, extracted: str, n: int) -> None:
    normalized_gt = _normalize_text_token(ground_truth)
    normalized_ex = _normalize_text_token(extracted)
    context._ocr_ngram_overlap = calculate_ngram_overlap(normalized_gt, normalized_ex, n=n)


@when(
    'I compute OCR character accuracy for ground truth "{ground_truth}" and extracted "{extracted}"'
)
def step_compute_ocr_character_accuracy(context, ground_truth: str, extracted: str) -> None:
    normalized_gt = _normalize_text_token(ground_truth)
    normalized_ex = _normalize_text_token(extracted)
    context._ocr_character_accuracy = calculate_character_accuracy(normalized_gt, normalized_ex)


@when('I evaluate a tiny OCR benchmark corpus with snapshot "{snapshot_id}"')
def step_evaluate_tiny_ocr_benchmark(context, snapshot_id: str) -> None:
    corpus_path = _prepare_ocr_benchmark_corpus(context, snapshot_id)
    corpus = Corpus.open(corpus_path)
    benchmark = OCRBenchmark(corpus)
    report = benchmark.evaluate_extraction(snapshot_id)
    context._ocr_benchmark_report = report


@when("I evaluate an OCR benchmark with explicit ground truth directory")
def step_evaluate_ocr_with_explicit_ground_truth(context) -> None:
    snapshot_id = "snap-explicit-gt"
    corpus = _prepare_ocr_snapshot(context, snapshot_id)
    benchmark = OCRBenchmark(corpus)
    ground_truth_dir = corpus.root / "metadata" / "funsd_ground_truth"
    report = benchmark.evaluate_extraction(snapshot_id, ground_truth_dir=ground_truth_dir)
    context._ocr_benchmark_report = report


@when("I evaluate an OCR benchmark with missing ground truth directory")
def step_evaluate_ocr_missing_ground_truth(context) -> None:
    corpus = _prepare_ocr_snapshot(
        context,
        "snap-missing-gt",
        include_ground_truth_dir=False,
        include_snapshot_dir=True,
    )
    benchmark = OCRBenchmark(corpus)
    try:
        benchmark.evaluate_extraction("snap-missing-gt")
        context._ocr_benchmark_error = None
    except Exception as exc:
        context._ocr_benchmark_error = exc


@when("I evaluate an OCR benchmark with missing snapshot")
def step_evaluate_ocr_missing_snapshot(context) -> None:
    corpus = _prepare_ocr_snapshot(
        context,
        "snap-missing",
        include_snapshot_dir=False,
    )
    benchmark = OCRBenchmark(corpus)
    try:
        benchmark.evaluate_extraction("snap-missing")
        context._ocr_benchmark_error = None
    except Exception as exc:
        context._ocr_benchmark_error = exc


@when("I evaluate an OCR benchmark with missing text directory")
def step_evaluate_ocr_missing_text_dir(context) -> None:
    corpus = _prepare_ocr_snapshot(
        context,
        "snap-missing-text-dir",
        include_text_dir=False,
    )
    benchmark = OCRBenchmark(corpus)
    try:
        benchmark.evaluate_extraction("snap-missing-text-dir")
        context._ocr_benchmark_error = None
    except Exception as exc:
        context._ocr_benchmark_error = exc


@when("I evaluate an OCR benchmark with no text files")
def step_evaluate_ocr_no_text_files(context) -> None:
    corpus = _prepare_ocr_snapshot(
        context,
        "snap-empty-text",
        include_text_files=False,
    )
    benchmark = OCRBenchmark(corpus)
    try:
        benchmark.evaluate_extraction("snap-empty-text")
        context._ocr_benchmark_error = None
    except Exception as exc:
        context._ocr_benchmark_error = exc


@when("I evaluate an OCR benchmark with missing ground truth files")
def step_evaluate_ocr_missing_gt_files(context) -> None:
    corpus = _prepare_ocr_snapshot(
        context,
        "snap-missing-gt-file",
        include_ground_truth_file=False,
    )
    benchmark = OCRBenchmark(corpus)
    try:
        benchmark.evaluate_extraction("snap-missing-gt-file")
        context._ocr_benchmark_error = None
    except Exception as exc:
        context._ocr_benchmark_error = exc


@when("I export the OCR benchmark report")
def step_export_ocr_benchmark_report(context) -> None:
    report = context._ocr_benchmark_report
    report_path = context.workdir / "reports" / "ocr_benchmark.json"
    csv_path = context.workdir / "reports" / "ocr_benchmark.csv"
    report.to_json(report_path)
    report.to_csv(csv_path)
    context._ocr_benchmark_report_json = report_path
    context._ocr_benchmark_report_csv = csv_path


@when("I print the OCR benchmark summaries")
def step_print_ocr_benchmark_summaries(context) -> None:
    report = context._ocr_benchmark_report
    report.print_summary()
    first = report.per_document_results[0]
    result = OCREvaluationResult(**first)
    result.print_summary()


@when("I create an empty OCR benchmark report")
def step_create_empty_ocr_report(context) -> None:
    report = BenchmarkReport(
        evaluation_timestamp="2024-01-01T00:00:00Z",
        corpus_path="/tmp/corpus",
        pipeline_configuration={},
        total_documents=0,
        avg_precision=0.0,
        avg_recall=0.0,
        avg_f1=0.0,
        median_precision=0.0,
        median_recall=0.0,
        median_f1=0.0,
        min_f1=0.0,
        max_f1=0.0,
        avg_word_error_rate=0.0,
        avg_sequence_accuracy=0.0,
        avg_lcs_ratio=0.0,
        median_word_error_rate=0.0,
        median_sequence_accuracy=0.0,
        median_lcs_ratio=0.0,
        avg_bigram_overlap=0.0,
        avg_trigram_overlap=0.0,
        processing_time_seconds=0.0,
        per_document_results=[],
    )
    context._ocr_benchmark_report = report


@when("I export the empty OCR benchmark report to CSV")
def step_export_empty_ocr_report_csv(context) -> None:
    report = context._ocr_benchmark_report
    csv_path = context.workdir / "reports" / "ocr_benchmark_empty.csv"
    report.to_csv(csv_path)
    context._ocr_benchmark_report_csv = csv_path


@then("OCR benchmark metrics are available")
def step_ocr_metrics_available(context) -> None:
    assert getattr(context, "_ocr_word_metrics", {}) is not None


@then("the OCR benchmark error is present")
def step_ocr_benchmark_error_present(context) -> None:
    assert getattr(context, "_ocr_benchmark_error", None) is not None


@then('the OCR character accuracy equals {value:f}')
def step_ocr_character_accuracy_equals(context, value: float) -> None:
    assert context._ocr_character_accuracy == value


@then("OCR benchmark report artifacts exist")
def step_ocr_report_artifacts_exist(context) -> None:
    report_path = context._ocr_benchmark_report_json
    csv_path = context._ocr_benchmark_report_csv
    assert report_path.is_file()
    assert csv_path.is_file()
