#!/usr/bin/env python3
"""
Comprehensive OCR Pipeline Benchmark

Runs evaluation across ALL available pipeline configurations and generates
a comparative analysis showing which pipelines perform best on different metrics.

Usage:
    # Benchmark all pipelines on FUNSD dataset
    python scripts/benchmark_all_pipelines.py \
        --corpus corpora/funsd_benchmark \
        --output results/pipeline_comparison.json

    # Benchmark specific pipelines only
    python scripts/benchmark_all_pipelines.py \
        --corpus corpora/funsd_benchmark \
        --configs configs/baseline-ocr.yaml configs/docling-smol.yaml \
        --output results/custom_comparison.json

    # Quick test with fewer documents
    python scripts/benchmark_all_pipelines.py \
        --corpus corpora/funsd_benchmark \
        --limit 5 \
        --output results/quick_test.json
"""

import argparse
import sys
from pathlib import Path
import yaml
import json
from typing import List, Dict, Any
from datetime import datetime
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.evaluation import OCRBenchmark


# Default pipeline configurations to test
DEFAULT_CONFIGS = [
    "configs/baseline-ocr.yaml",
    "configs/ocr-rapidocr.yaml",
    "configs/ocr-paddleocr.yaml",
    "configs/docling-smol.yaml",
    "configs/docling-granite.yaml",
    "configs/unstructured.yaml",
]


def load_config(config_path: Path) -> Dict:
    """Load pipeline configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def run_pipeline(corpus: Corpus, config: Dict, config_name: str) -> str:
    """
    Run extraction pipeline and return snapshot ID.

    Args:
        corpus: Corpus to extract from
        config: Pipeline configuration
        config_name: Name for this configuration

    Returns:
        Snapshot ID
    """
    print(f"\n{'='*70}")
    print(f"Running: {config_name}")
    print(f"{'='*70}")

    try:
        snapshot = build_extraction_snapshot(
            corpus=corpus,
            extractor_id=config.get('extractor_id', 'pipeline'),
            configuration_name=config_name,
            configuration=config.get('config', config)
        )

        print(f"✓ Snapshot created: {snapshot.snapshot_id[:16]}...")
        return snapshot.snapshot_id

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def evaluate_pipeline(
    benchmark: OCRBenchmark,
    snapshot_id: str,
    config: Dict,
    config_name: str
) -> Dict:
    """
    Evaluate a pipeline snapshot.

    Returns:
        Dictionary with results or None if evaluation failed
    """
    if not snapshot_id:
        return None

    try:
        print(f"\nEvaluating: {config_name}")
        report = benchmark.evaluate_extraction(
            snapshot_reference=snapshot_id,
            pipeline_config=config
        )

        return {
            'name': config_name,
            'snapshot_id': snapshot_id,
            'success': True,
            'report': report,
        }

    except Exception as e:
        print(f"✗ Evaluation failed for {config_name}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'name': config_name,
            'snapshot_id': snapshot_id,
            'success': False,
            'error': str(e),
        }


def print_comparison_table(results: List[Dict]):
    """Print a formatted comparison table of all results."""
    print("\n" + "="*100)
    print("COMPREHENSIVE PIPELINE COMPARISON")
    print("="*100)

    # Table header
    print(f"\n{'Pipeline':<30} {'F1':<8} {'Recall':<8} {'WER':<8} {'Seq.Acc':<8} {'Bigram':<8} {'Status':<10}")
    print("-"*100)

    # Sort by F1 score (best first)
    successful_results = [r for r in results if r.get('success')]
    failed_results = [r for r in results if not r.get('success')]

    successful_results.sort(key=lambda x: x['report'].avg_f1, reverse=True)

    # Print successful results
    for result in successful_results:
        report = result['report']
        name = result['name'][:28]
        print(
            f"{name:<30} "
            f"{report.avg_f1:<8.3f} "
            f"{report.avg_recall:<8.3f} "
            f"{report.avg_word_error_rate:<8.3f} "
            f"{report.avg_sequence_accuracy:<8.3f} "
            f"{report.avg_bigram_overlap:<8.3f} "
            f"{'✓ OK':<10}"
        )

    # Print failed results
    for result in failed_results:
        name = result['name'][:28]
        print(
            f"{name:<30} "
            f"{'---':<8} "
            f"{'---':<8} "
            f"{'---':<8} "
            f"{'---':<8} "
            f"{'---':<8} "
            f"{'✗ FAILED':<10}"
        )

    print("-"*100)
    print(f"\nSuccessful: {len(successful_results)}/{len(results)}")

    if successful_results:
        print("\n" + "="*100)
        print("BEST PERFORMERS")
        print("="*100)

        # Best F1 score (word finding)
        best_f1 = max(successful_results, key=lambda x: x['report'].avg_f1)
        print(f"\n🏆 Best Word Finding (F1): {best_f1['name']}")
        print(f"   F1: {best_f1['report'].avg_f1:.3f}, Recall: {best_f1['report'].avg_recall:.3f}")

        # Best sequence accuracy (order preservation)
        best_seq = max(successful_results, key=lambda x: x['report'].avg_sequence_accuracy)
        print(f"\n🏆 Best Reading Order (Seq.Acc): {best_seq['name']}")
        print(f"   Seq.Acc: {best_seq['report'].avg_sequence_accuracy:.3f}, LCS: {best_seq['report'].avg_lcs_ratio:.3f}")

        # Lowest word error rate
        best_wer = min(successful_results, key=lambda x: x['report'].avg_word_error_rate)
        print(f"\n🏆 Lowest Error Rate (WER): {best_wer['name']}")
        print(f"   WER: {best_wer['report'].avg_word_error_rate:.3f}")

        # Best n-gram overlap (local ordering)
        best_bigram = max(successful_results, key=lambda x: x['report'].avg_bigram_overlap)
        print(f"\n🏆 Best Local Ordering (Bigram): {best_bigram['name']}")
        print(f"   Bigram: {best_bigram['report'].avg_bigram_overlap:.3f}, Trigram: {best_bigram['report'].avg_trigram_overlap:.3f}")

        print("\n" + "="*100)


def save_comprehensive_report(results: List[Dict], output_path: Path, corpus_path: str):
    """Save comprehensive comparison report to JSON."""
    successful_results = [r for r in results if r.get('success')]
    failed_results = [r for r in results if not r.get('success')]

    report = {
        'benchmark_timestamp': datetime.now().isoformat(),
        'corpus_path': corpus_path,
        'total_pipelines': len(results),
        'successful_pipelines': len(successful_results),
        'failed_pipelines': len(failed_results),
        'pipelines': []
    }

    # Add successful pipeline results
    for result in successful_results:
        r = result['report']
        report['pipelines'].append({
            'name': result['name'],
            'snapshot_id': result['snapshot_id'],
            'success': True,
            'metrics': {
                'set_based': {
                    'avg_f1': r.avg_f1,
                    'avg_precision': r.avg_precision,
                    'avg_recall': r.avg_recall,
                    'median_f1': r.median_f1,
                },
                'order_aware': {
                    'avg_word_error_rate': r.avg_word_error_rate,
                    'avg_sequence_accuracy': r.avg_sequence_accuracy,
                    'avg_lcs_ratio': r.avg_lcs_ratio,
                    'median_word_error_rate': r.median_word_error_rate,
                    'median_sequence_accuracy': r.median_sequence_accuracy,
                },
                'ngram': {
                    'avg_bigram_overlap': r.avg_bigram_overlap,
                    'avg_trigram_overlap': r.avg_trigram_overlap,
                }
            },
            'pipeline_configuration': r.pipeline_configuration,
            'total_documents': r.total_documents,
            'processing_time': r.processing_time_seconds,
        })

    # Add failed pipeline results
    for result in failed_results:
        report['pipelines'].append({
            'name': result['name'],
            'snapshot_id': result.get('snapshot_id'),
            'success': False,
            'error': result.get('error', 'Unknown error'),
        })

    # Identify best performers
    if successful_results:
        report['best_performers'] = {
            'best_f1': max(successful_results, key=lambda x: x['report'].avg_f1)['name'],
            'best_sequence_accuracy': max(successful_results, key=lambda x: x['report'].avg_sequence_accuracy)['name'],
            'lowest_wer': min(successful_results, key=lambda x: x['report'].avg_word_error_rate)['name'],
            'best_bigram': max(successful_results, key=lambda x: x['report'].avg_bigram_overlap)['name'],
        }

    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Comprehensive report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark all OCR pipelines and compare performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--corpus',
        required=True,
        help='Path to corpus containing documents and ground truth'
    )

    parser.add_argument(
        '--configs',
        nargs='*',
        help='Specific config files to test (default: all configs)'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output path for results (JSON)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of documents to process (for quick testing)'
    )

    args = parser.parse_args()

    # Determine which configs to test
    config_paths = args.configs if args.configs else DEFAULT_CONFIGS

    # Filter to only existing configs
    existing_configs = []
    for config_path in config_paths:
        p = Path(config_path)
        if p.exists():
            existing_configs.append(p)
        else:
            print(f"⚠️  Config not found, skipping: {config_path}")

    if not existing_configs:
        print("✗ No valid config files found!")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"COMPREHENSIVE PIPELINE BENCHMARK")
    print(f"{'='*70}")
    print(f"Corpus: {args.corpus}")
    print(f"Pipelines to test: {len(existing_configs)}")
    print(f"Output: {args.output}")
    if args.limit:
        print(f"Document limit: {args.limit}")
    print(f"{'='*70}")

    try:
        # Load corpus
        corpus = Corpus.open(Path(args.corpus))
        benchmark = OCRBenchmark(corpus)

        # Run all pipelines
        results = []

        for config_path in existing_configs:
            config = load_config(config_path)
            config_name = config_path.stem

            # Run pipeline
            snapshot_id = run_pipeline(corpus, config, config_name)

            # Evaluate
            result = evaluate_pipeline(benchmark, snapshot_id, config, config_name)

            if result:
                results.append(result)

        # Print comparison table
        print_comparison_table(results)

        # Save comprehensive report
        save_comprehensive_report(results, Path(args.output), args.corpus)

        print(f"\n✓ Benchmark complete!")
        print(f"  Tested: {len(results)} pipelines")
        print(f"  Successful: {sum(1 for r in results if r.get('success'))}")
        print(f"  Failed: {sum(1 for r in results if not r.get('success'))}")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
