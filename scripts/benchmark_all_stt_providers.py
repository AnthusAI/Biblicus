#!/usr/bin/env python3
"""
Comprehensive STT Provider Benchmark

Runs evaluation across ALL available STT provider configurations and generates
a comparative analysis showing which providers perform best on different metrics.

Usage:
    # Benchmark all STT providers on LibriSpeech dataset
    python scripts/benchmark_all_stt_providers.py \
        --corpus corpora/librispeech_benchmark \
        --output results/stt_provider_comparison.json

    # Benchmark specific providers only
    python scripts/benchmark_all_stt_providers.py \
        --corpus corpora/librispeech_benchmark \
        --providers stt-openai stt-deepgram \
        --output results/custom_stt_comparison.json

    # Quick test with fewer audio files
    python scripts/benchmark_all_stt_providers.py \
        --corpus corpora/librispeech_benchmark \
        --limit 5 \
        --output results/quick_stt_test.json
"""

import argparse
import sys
from pathlib import Path
import json
from typing import List, Dict, Any
from datetime import datetime
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.evaluation.stt_benchmark import STTBenchmark


# Default STT provider configurations to test
DEFAULT_PROVIDERS = [
    {
        'name': 'OpenAI Whisper',
        'extractor_id': 'stt-openai',
        'config': {
            'model': 'whisper-1',
            'response_format': 'json'
        }
    },
    {
        'name': 'Deepgram Nova-3',
        'extractor_id': 'stt-deepgram',
        'config': {
            'model': 'nova-3',
            'punctuate': True,
            'smart_format': True
        }
    },
    {
        'name': 'Aldea',
        'extractor_id': 'stt-aldea',
        'config': {}
    },
]


def run_stt_provider(corpus: Corpus, provider: Dict, provider_name: str) -> str:
    """
    Run STT extraction and return snapshot ID.

    Args:
        corpus: Corpus containing audio files
        provider: Provider configuration
        provider_name: Name for this provider

    Returns:
        Snapshot ID or None if extraction failed
    """
    print(f"\n{'='*70}")
    print(f"Running: {provider_name}")
    print(f"{'='*70}")

    try:
        # Wrap single STT extractor in pipeline
        pipeline_config = {
            'stages': [
                {
                    'extractor_id': provider['extractor_id'],
                    'config': provider['config']
                }
            ]
        }

        snapshot = build_extraction_snapshot(
            corpus=corpus,
            extractor_id='pipeline',
            configuration_name=provider_name,
            configuration=pipeline_config
        )

        print(f"✓ Snapshot created: {snapshot.snapshot_id[:16]}...")
        return snapshot.snapshot_id

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def evaluate_provider(
    benchmark: STTBenchmark,
    snapshot_id: str,
    provider: Dict,
    provider_name: str
) -> Dict:
    """
    Evaluate an STT provider snapshot.

    Returns:
        Dictionary with results or None if evaluation failed
    """
    if not snapshot_id:
        return None

    try:
        print(f"\nEvaluating: {provider_name}")
        report = benchmark.evaluate_extraction(
            snapshot_reference=snapshot_id,
            ground_truth_dir=benchmark.corpus.root / "metadata" / "ground_truth",
            provider_config={
                'provider': provider_name,
                'extractor_id': provider['extractor_id'],
                **provider['config']
            }
        )

        return {
            'name': provider_name,
            'snapshot_id': snapshot_id,
            'success': True,
            'report': report,
        }

    except Exception as e:
        print(f"✗ Evaluation failed for {provider_name}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'name': provider_name,
            'snapshot_id': snapshot_id,
            'success': False,
            'error': str(e),
        }


def print_comparison_table(results: List[Dict]):
    """Print a formatted comparison table of all results."""
    print("\n" + "="*100)
    print("COMPREHENSIVE STT PROVIDER COMPARISON")
    print("="*100)

    # Table header
    print(f"\n{'Provider':<30} {'WER':<8} {'CER':<8} {'Precision':<10} {'Recall':<10} {'F1':<8} {'Status':<10}")
    print("-"*100)

    # Sort by WER (lower is better)
    successful_results = [r for r in results if r.get('success')]
    failed_results = [r for r in results if not r.get('success')]

    successful_results.sort(key=lambda x: x['report'].avg_wer)

    # Print successful results
    for result in successful_results:
        report = result['report']
        name = result['name'][:28]
        print(
            f"{name:<30} "
            f"{report.avg_wer:<8.3f} "
            f"{report.avg_cer:<8.3f} "
            f"{report.avg_precision:<10.3f} "
            f"{report.avg_recall:<10.3f} "
            f"{report.avg_f1:<8.3f} "
            f"{'✓ OK':<10}"
        )

    # Print failed results
    for result in failed_results:
        name = result['name'][:28]
        print(
            f"{name:<30} "
            f"{'---':<8} "
            f"{'---':<8} "
            f"{'---':<10} "
            f"{'---':<10} "
            f"{'---':<8} "
            f"{'✗ FAILED':<10}"
        )

    print("-"*100)
    print(f"\nSuccessful: {len(successful_results)}/{len(results)}")

    if successful_results:
        print("\n" + "="*100)
        print("BEST PERFORMERS")
        print("="*100)

        # Lowest WER (word accuracy)
        best_wer = min(successful_results, key=lambda x: x['report'].avg_wer)
        print(f"\n🏆 Best Word Accuracy (Lowest WER): {best_wer['name']}")
        print(f"   WER: {best_wer['report'].avg_wer:.3f}, Median: {best_wer['report'].median_wer:.3f}")

        # Lowest CER (character accuracy)
        best_cer = min(successful_results, key=lambda x: x['report'].avg_cer)
        print(f"\n🏆 Best Character Accuracy (Lowest CER): {best_cer['name']}")
        print(f"   CER: {best_cer['report'].avg_cer:.3f}, Median: {best_cer['report'].median_cer:.3f}")

        # Best F1 score (word finding)
        best_f1 = max(successful_results, key=lambda x: x['report'].avg_f1)
        print(f"\n🏆 Best Word Finding (F1): {best_f1['name']}")
        print(f"   F1: {best_f1['report'].avg_f1:.3f}, Precision: {best_f1['report'].avg_precision:.3f}, Recall: {best_f1['report'].avg_recall:.3f}")

        print("\n" + "="*100)


def save_comprehensive_report(results: List[Dict], output_path: Path, corpus_path: str):
    """Save comprehensive comparison report to JSON."""
    successful_results = [r for r in results if r.get('success')]
    failed_results = [r for r in results if not r.get('success')]

    report = {
        'benchmark_timestamp': datetime.now().isoformat(),
        'corpus_path': corpus_path,
        'total_providers': len(results),
        'successful_providers': len(successful_results),
        'failed_providers': len(failed_results),
        'providers': []
    }

    # Add successful provider results
    for result in successful_results:
        r = result['report']
        report['providers'].append({
            'name': result['name'],
            'snapshot_id': result['snapshot_id'],
            'success': True,
            'metrics': {
                'wer': {
                    'avg': r.avg_wer,
                    'median': r.median_wer,
                    'avg_substitutions': r.avg_substitutions,
                    'avg_deletions': r.avg_deletions,
                    'avg_insertions': r.avg_insertions,
                },
                'cer': {
                    'avg': r.avg_cer,
                    'median': r.median_cer,
                },
                'word_level': {
                    'avg_precision': r.avg_precision,
                    'avg_recall': r.avg_recall,
                    'avg_f1': r.avg_f1,
                    'median_f1': r.median_f1,
                }
            },
            'provider_configuration': r.provider_configuration,
            'total_audio_files': r.total_audio_files,
        })

    # Add failed provider results
    for result in failed_results:
        report['providers'].append({
            'name': result['name'],
            'snapshot_id': result.get('snapshot_id'),
            'success': False,
            'error': result.get('error', 'Unknown error'),
        })

    # Identify best performers
    if successful_results:
        report['best_performers'] = {
            'lowest_wer': min(successful_results, key=lambda x: x['report'].avg_wer)['name'],
            'lowest_cer': min(successful_results, key=lambda x: x['report'].avg_cer)['name'],
            'best_f1': max(successful_results, key=lambda x: x['report'].avg_f1)['name'],
        }

    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Comprehensive report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Benchmark all STT providers and compare performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--corpus',
        required=True,
        help='Path to corpus containing audio files and ground truth transcripts'
    )

    parser.add_argument(
        '--providers',
        nargs='*',
        help='Specific provider extractor IDs to test (e.g., stt-openai stt-deepgram)'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output path for results (JSON)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of audio files to process (for quick testing)'
    )

    args = parser.parse_args()

    # Determine which providers to test
    if args.providers:
        # Filter to only requested providers
        providers_to_test = [
            p for p in DEFAULT_PROVIDERS
            if p['extractor_id'] in args.providers
        ]
        if not providers_to_test:
            print(f"✗ No matching providers found for: {args.providers}")
            print(f"Available providers: {[p['extractor_id'] for p in DEFAULT_PROVIDERS]}")
            sys.exit(1)
    else:
        providers_to_test = DEFAULT_PROVIDERS

    print(f"\n{'='*70}")
    print(f"COMPREHENSIVE STT PROVIDER BENCHMARK")
    print(f"{'='*70}")
    print(f"Corpus: {args.corpus}")
    print(f"Providers to test: {len(providers_to_test)}")
    print(f"Output: {args.output}")
    if args.limit:
        print(f"Audio file limit: {args.limit}")
    print(f"{'='*70}")

    try:
        # Load corpus
        corpus = Corpus.open(Path(args.corpus))
        benchmark = STTBenchmark(corpus)

        # Run all providers
        results = []

        for provider in providers_to_test:
            provider_name = provider['name']

            # Run provider
            snapshot_id = run_stt_provider(corpus, provider, provider_name)

            # Evaluate
            result = evaluate_provider(benchmark, snapshot_id, provider, provider_name)

            # Always append result (even if None or failed)
            if result:
                results.append(result)
            else:
                # Add failed entry if evaluate returned None
                results.append({
                    'name': provider_name,
                    'snapshot_id': snapshot_id,
                    'success': False,
                    'error': 'Evaluation failed'
                })

        # Print comparison table
        print_comparison_table(results)

        # Save comprehensive report
        save_comprehensive_report(results, Path(args.output), args.corpus)

        print(f"\n✓ Benchmark complete!")
        print(f"  Tested: {len(results)} providers")
        print(f"  Successful: {sum(1 for r in results if r.get('success'))}")
        print(f"  Failed: {sum(1 for r in results if not r.get('success'))}")

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
