#!/usr/bin/env python3
"""
OCR Pipeline Evaluation Tool

Evaluates OCR pipeline performance against ground truth data (e.g., FUNSD dataset).
Generates detailed reports with per-document and aggregate metrics.

Usage:
    # Evaluate a single configuration
    python scripts/evaluate_ocr_pipeline.py \\
        --corpus corpora/funsd_test \\
        --config configs/baseline-ocr.yaml \\
        --output results/baseline.json

    # Compare multiple configurations
    python scripts/evaluate_ocr_pipeline.py \\
        --corpus corpora/funsd_test \\
        --compare configs/baseline-ocr.yaml configs/layout-aware-ocr.yaml \\
        --output results/comparison.json
"""

import argparse
import sys
from pathlib import Path
import yaml
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.evaluation import OCRBenchmark


def load_config(config_path: Path) -> dict:
    """Load pipeline configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def run_pipeline(corpus: Corpus, config: dict, config_name: str) -> str:
    """
    Run extraction pipeline and return snapshot ID.

    Args:
        corpus: Corpus to extract from
        config: Pipeline configuration
        config_name: Name for this configuration

    Returns:
        Snapshot ID
    """
    print(f"\nRunning pipeline: {config_name}")
    print(f"  Configuration: {config}")

    snapshot = build_extraction_snapshot(
        corpus=corpus,
        extractor_id=config.get('extractor_id', 'pipeline'),
        configuration_name=config_name,
        configuration=config.get('config', config)
    )

    print(f"  ✓ Snapshot created: {snapshot.snapshot_id[:16]}...")
    return snapshot.snapshot_id


def evaluate_single(args):
    """Evaluate a single pipeline configuration."""
    corpus = Corpus.open(Path(args.corpus))
    benchmark = OCRBenchmark(corpus)

    # Load configuration
    config = load_config(Path(args.config))
    config_name = Path(args.config).stem

    # Run pipeline
    snapshot_id = run_pipeline(corpus, config, config_name)

    # Evaluate
    print(f"\nEvaluating snapshot against ground truth...")
    report = benchmark.evaluate_extraction(
        snapshot_reference=snapshot_id,
        pipeline_config=config
    )

    # Print summary
    print()
    report.print_summary()

    # Save outputs
    output_path = Path(args.output)
    report.to_json(output_path)

    # Also save CSV
    csv_path = output_path.with_suffix('.csv')
    report.to_csv(csv_path)

    print(f"\n✓ Evaluation complete!")
    print(f"  JSON: {output_path}")
    print(f"  CSV: {csv_path}")


def compare_configurations(args):
    """Compare multiple pipeline configurations."""
    corpus = Corpus.open(Path(args.corpus))
    benchmark = OCRBenchmark(corpus)

    # Load all configs
    configs = []
    for config_path in args.compare:
        config = load_config(Path(config_path))
        config_name = Path(config_path).stem
        configs.append({
            'name': config_name,
            'path': config_path,
            'config': config
        })

    # Run all pipelines
    snapshots = []
    for cfg in configs:
        snapshot_id = run_pipeline(corpus, cfg['config'], cfg['name'])
        snapshots.append({
            'name': cfg['name'],
            'snapshot_id': snapshot_id,
            'config': cfg['config']
        })

    # Evaluate all
    print(f"\nEvaluating {len(snapshots)} configurations...")
    reports = []
    for snap in snapshots:
        print(f"\n  Evaluating: {snap['name']}")
        report = benchmark.evaluate_extraction(
            snapshot_reference=snap['snapshot_id'],
            pipeline_config=snap['config']
        )
        reports.append({
            'name': snap['name'],
            'report': report
        })

    # Compare results
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)

    for item in reports:
        print(f"\n{item['name']}:")
        print(f"  Set-based (position-agnostic):")
        print(f"    Avg F1:        {item['report'].avg_f1:.3f}")
        print(f"    Avg Precision: {item['report'].avg_precision:.3f}")
        print(f"    Avg Recall:    {item['report'].avg_recall:.3f}")
        print(f"  Order-aware (sequence quality):")
        print(f"    Word Error Rate:    {item['report'].avg_word_error_rate:.3f} (lower=better)")
        print(f"    Sequence Accuracy:  {item['report'].avg_sequence_accuracy:.3f}")
        print(f"    LCS Ratio:          {item['report'].avg_lcs_ratio:.3f}")
        print(f"  N-gram Overlap:")
        print(f"    Bigram:  {item['report'].avg_bigram_overlap:.3f}")
        print(f"    Trigram: {item['report'].avg_trigram_overlap:.3f}")

    # Calculate improvements
    if len(reports) == 2:
        baseline = reports[0]['report']
        improved = reports[1]['report']

        f1_diff = improved.avg_f1 - baseline.avg_f1
        f1_pct = (f1_diff / baseline.avg_f1 * 100) if baseline.avg_f1 > 0 else 0
        wer_diff = improved.avg_word_error_rate - baseline.avg_word_error_rate
        seq_acc_diff = improved.avg_sequence_accuracy - baseline.avg_sequence_accuracy
        lcs_diff = improved.avg_lcs_ratio - baseline.avg_lcs_ratio

        print(f"\n" + "=" * 70)
        print(f"Improvement from {reports[0]['name']} → {reports[1]['name']}:")
        print(f"\n  Set-based Metrics:")
        print(f"    F1 Score:   {f1_diff:+.3f} ({f1_pct:+.1f}%)")
        print(f"    Precision:  {improved.avg_precision - baseline.avg_precision:+.3f}")
        print(f"    Recall:     {improved.avg_recall - baseline.avg_recall:+.3f}")
        print(f"\n  Order-aware Metrics:")
        print(f"    Word Error Rate:   {wer_diff:+.3f} (negative=better)")
        print(f"    Sequence Accuracy: {seq_acc_diff:+.3f}")
        print(f"    LCS Ratio:         {lcs_diff:+.3f}")
        print(f"\n  N-gram Overlap:")
        print(f"    Bigram:  {improved.avg_bigram_overlap - baseline.avg_bigram_overlap:+.3f}")
        print(f"    Trigram: {improved.avg_trigram_overlap - baseline.avg_trigram_overlap:+.3f}")

        # Count improvements/degradations per document
        improved_docs = 0
        degraded_docs = 0
        for i, baseline_result in enumerate(baseline.per_document_results):
            improved_result = improved.per_document_results[i]
            if improved_result['f1_score'] > baseline_result['f1_score']:
                improved_docs += 1
            elif improved_result['f1_score'] < baseline_result['f1_score']:
                degraded_docs += 1

        print(f"\n  Documents improved:  {improved_docs}")
        print(f"  Documents degraded:  {degraded_docs}")
        print(f"  Documents unchanged: {baseline.total_documents - improved_docs - degraded_docs}")

    # Save comparison report
    output_path = Path(args.output)
    comparison_data = {
        'comparison_timestamp': reports[0]['report'].evaluation_timestamp,
        'corpus_path': reports[0]['report'].corpus_path,
        'configurations': [
            {
                'name': item['name'],
                'avg_f1': item['report'].avg_f1,
                'avg_precision': item['report'].avg_precision,
                'avg_recall': item['report'].avg_recall,
                'total_documents': item['report'].total_documents,
            }
            for item in reports
        ]
    }

    if len(reports) == 2:
        comparison_data['improvements'] = {
            'f1_improvement': f1_diff,
            'f1_improvement_pct': f1_pct,
            'documents_improved': improved_docs,
            'documents_degraded': degraded_docs,
            'documents_unchanged': baseline.total_documents - improved_docs - degraded_docs
        }

    # Add all per-document results
    comparison_data['per_configuration_results'] = [
        {
            'name': item['name'],
            'report': item['report'].to_dict() if hasattr(item['report'], 'to_dict') else vars(item['report'])
        }
        for item in reports
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(comparison_data, f, indent=2)

    print(f"\n✓ Comparison saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate OCR pipeline performance against ground truth',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--corpus',
        required=True,
        help='Path to corpus containing documents and ground truth'
    )

    # Single config evaluation
    parser.add_argument(
        '--config',
        help='Pipeline configuration file (YAML) to evaluate'
    )

    # Multi-config comparison
    parser.add_argument(
        '--compare',
        nargs='+',
        help='Multiple configuration files to compare'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output path for results (JSON)'
    )

    parser.add_argument(
        '--ground-truth-dir',
        help='Directory containing ground truth files (default: corpus/.biblicus/funsd_ground_truth)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.config and not args.compare:
        parser.error('Must specify either --config or --compare')

    if args.config and args.compare:
        parser.error('Cannot specify both --config and --compare')

    try:
        if args.config:
            evaluate_single(args)
        else:
            compare_configurations(args)

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
