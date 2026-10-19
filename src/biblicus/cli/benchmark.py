"""
Benchmark commands for the Biblicus command-line interface.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def cmd_benchmark_download(arguments: argparse.Namespace) -> int:
    """
    Download benchmark datasets.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    import subprocess

    if isinstance(arguments.datasets, str):
        datasets = [d.strip() for d in arguments.datasets.split(",")]
    else:
        datasets = [str(d).strip() for d in arguments.datasets]
    corpus_dir = Path(arguments.corpus_dir)
    count = arguments.count
    force = arguments.force

    print("=" * 70)
    print("BIBLICUS BENCHMARK DATASET DOWNLOAD")
    print("=" * 70)

    for dataset in datasets:
        print(f"\nDownloading {dataset}...")

        if dataset == "funsd":
            corpus_path = corpus_dir / "funsd_benchmark"
            cmd = ["python", "scripts/download_funsd_samples.py", "--corpus", str(corpus_path)]
            if count:
                cmd.extend(["--count", str(count)])
            if force:
                cmd.append("--force")

        elif dataset == "sroie":
            corpus_path = corpus_dir / "sroie_benchmark"
            cmd = ["python", "scripts/download_sroie_samples.py", "--corpus", str(corpus_path)]
            if count:
                cmd.extend(["--count", str(count)])
            if force:
                cmd.append("--force")

        elif dataset == "scanned-arxiv":
            print("  NOTICE: scanned-arxiv dataset is not yet available.")
            print("          The HuggingFace dataset lacks actual scanned images.")
            print("          This category is pending a suitable dataset source.")
            continue

        else:
            print(f"  Unknown dataset: {dataset}")
            continue

        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"  ERROR: Failed to download {dataset}")
        else:
            print(f"  Downloaded {dataset} to {corpus_path}")

    return 0


def cmd_benchmark_run(arguments: argparse.Namespace) -> int:
    """
    Run benchmark evaluation.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    from ..evaluation.benchmark_runner import BenchmarkConfig, BenchmarkRunner

    config_path = Path(arguments.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Benchmark configuration not found: {config_path}")

    config = BenchmarkConfig.load(config_path)

    # Override pipelines if specified
    if arguments.pipelines:
        config.pipelines = [Path(p.strip()) for p in arguments.pipelines.split(",")]

    runner = BenchmarkRunner(config)

    # Run specific category or all
    if arguments.category:
        if arguments.category not in config.categories:
            raise ValueError(
                f"Unknown category: {arguments.category}. "
                f"Available: {', '.join(config.categories.keys())}"
            )
        cat_config = config.categories[arguments.category]
        result = runner.run_category(cat_config)
        print(f"\n{arguments.category.upper()} Results:")
        print(
            f"  Best pipeline: {result.best_pipeline} ({result.best_score:.3f} {result.primary_metric})"
        )
    else:
        result = runner.run_all()
        result.print_summary()

        # Save results
        output_path = (
            Path(arguments.output)
            if arguments.output
            else Path(f"results/benchmark_{config.benchmark_name}.json")
        )
        result.to_json(output_path)
        print(f"\nResults saved to: {output_path}")

        # Also generate markdown report
        md_path = output_path.with_suffix(".md")
        result.to_markdown(md_path)
        print(f"Markdown report: {md_path}")

    return 0


def cmd_benchmark_report(arguments: argparse.Namespace) -> int:
    """
    Generate benchmark report from results.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    import glob

    input_pattern = arguments.input
    output_path = Path(arguments.output)

    # Find all matching result files
    result_files = glob.glob(input_pattern)
    if not result_files:
        raise FileNotFoundError(f"No result files found matching: {input_pattern}")

    print(f"Generating report from {len(result_files)} result file(s)...")

    # For now, just use the first/latest result file
    # TODO: Merge multiple results for comparison
    result_path = Path(sorted(result_files)[-1])

    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Generate markdown report
    lines = [
        "# Biblicus Document Understanding Benchmark Results",
        "",
        f"**Source:** {result_path.name}",
        f"**Benchmark:** {data.get('benchmark_name', 'unknown')}",
        f"**Date:** {data.get('timestamp', 'unknown')}",
        "",
        "## Summary",
        "",
    ]

    categories = data.get("categories", {})
    if categories:
        lines.extend(
            [
                "| Category | Dataset | Docs | Best Pipeline | Score |",
                "|----------|---------|------|---------------|-------|",
            ]
        )
        for cat_name, cat_data in categories.items():
            lines.append(
                f"| {cat_name.title()} | {cat_data.get('dataset', '')} | "
                f"{cat_data.get('documents_evaluated', 0)} | "
                f"{cat_data.get('best_pipeline', '')} | "
                f"{cat_data.get('best_score', 0):.3f} |"
            )

    recommendations = data.get("recommendations", {})
    if recommendations:
        lines.extend(["", "## Recommendations", ""])
        for rec_type, pipeline in recommendations.items():
            lines.append(f"- **{rec_type.replace('_', ' ').title()}:** {pipeline}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report generated: {output_path}")
    return 0


def cmd_benchmark_status(arguments: argparse.Namespace) -> int:
    """
    Show status of benchmark datasets.

    :param arguments: Parsed command-line interface arguments.
    :type arguments: argparse.Namespace
    :return: Exit code.
    :rtype: int
    """
    corpus_dir = Path(arguments.corpus_dir)

    print("=" * 70)
    print("BIBLICUS BENCHMARK DATASET STATUS")
    print("=" * 70)

    datasets = [
        ("funsd", "funsd_benchmark", "funsd_ground_truth"),
        ("sroie", "sroie_benchmark", "sroie_ground_truth"),
        # ("scanned-arxiv", "scanned_arxiv_benchmark", "scanned_arxiv_ground_truth"),  # Pending - need dataset with images
    ]

    for name, corpus_name, gt_subdir in datasets:
        corpus_path = corpus_dir / corpus_name
        status = "NOT DOWNLOADED"
        doc_count = 0

        if corpus_path.exists():
            # Check both .biblicus (standard) and metadata (legacy) locations
            meta_dir = corpus_path / ".biblicus"
            if not meta_dir.exists():
                meta_dir = corpus_path / "metadata"

            config_file = meta_dir / "config.json"
            gt_dir = meta_dir / gt_subdir

            if config_file.exists():
                status = "DOWNLOADED"
                if gt_dir.exists():
                    doc_count = len(list(gt_dir.glob("*.txt")))
                    status = f"READY ({doc_count} docs)"

        print(f"  {name:15} {status}")

    print()
    print("To download datasets:")
    print("  biblicus benchmark download --datasets funsd,sroie")

    return 0


def register_benchmark_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register the benchmark commands on the top-level subparser collection.

    :param subparsers: Top-level subparser collection of the command-line interface.
    :type subparsers: argparse._SubParsersAction
    :return: None.
    :rtype: None
    """
    p_benchmark = subparsers.add_parser("benchmark", help="Run document understanding benchmarks.")
    benchmark_sub = p_benchmark.add_subparsers(dest="benchmark_command", required=True)

    p_benchmark_download = benchmark_sub.add_parser("download", help="Download benchmark datasets.")
    p_benchmark_download.add_argument(
        "--datasets",
        required=True,
        help="Comma-separated list of datasets to download (funsd, sroie, scanned-arxiv).",
    )
    p_benchmark_download.add_argument(
        "--corpus-dir",
        default="corpora",
        help="Base directory for benchmark corpora (default: corpora).",
    )
    p_benchmark_download.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of samples to download per dataset (default: dataset-specific).",
    )
    p_benchmark_download.add_argument(
        "--force", action="store_true", help="Overwrite existing corpus if present."
    )
    p_benchmark_download.set_defaults(func=cmd_benchmark_download)

    p_benchmark_run = benchmark_sub.add_parser("run", help="Run benchmark evaluation.")
    p_benchmark_run.add_argument(
        "--config",
        default="configs/benchmark/standard.yaml",
        help="Path to benchmark configuration file (default: configs/benchmark/standard.yaml).",
    )
    p_benchmark_run.add_argument(
        "--category",
        default=None,
        help="Run only a specific category (forms, academic, receipts).",
    )
    p_benchmark_run.add_argument(
        "--pipelines",
        default=None,
        help="Comma-separated list of pipeline config paths to benchmark.",
    )
    p_benchmark_run.add_argument(
        "--output",
        default=None,
        help="Output path for results JSON (default: results/benchmark_<name>.json).",
    )
    p_benchmark_run.set_defaults(func=cmd_benchmark_run)

    p_benchmark_report = benchmark_sub.add_parser(
        "report", help="Generate benchmark report from results."
    )
    p_benchmark_report.add_argument(
        "--input",
        required=True,
        help="Path to benchmark results JSON file(s). Supports glob patterns.",
    )
    p_benchmark_report.add_argument(
        "--output",
        default="docs/guides/benchmark-results.md",
        help="Output path for markdown report.",
    )
    p_benchmark_report.set_defaults(func=cmd_benchmark_report)

    p_benchmark_status = benchmark_sub.add_parser(
        "status", help="Show status of benchmark datasets."
    )
    p_benchmark_status.add_argument(
        "--corpus-dir",
        default="corpora",
        help="Base directory for benchmark corpora (default: corpora).",
    )
    p_benchmark_status.set_defaults(func=cmd_benchmark_status)

    # Dashboard commands
