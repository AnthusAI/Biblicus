"""
Run a repeatable profiling analysis workflow on AG News.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from biblicus.analysis.models import ProfilingConfiguration
from biblicus.analysis.profiling import ProfilingBackend
from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.models import ExtractionSnapshotReference

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _parse_percentiles(raw: Optional[str]) -> List[int]:
    """
    Parse comma-separated percentiles into a list of integers.

    :param raw: Comma-separated percentiles string.
    :type raw: str or None
    :return: Percentile list.
    :rtype: list[int]
    :raises ValueError: If any percentile is not an integer.
    """
    if raw is None:
        return [50, 90, 99]
    values: List[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(int(token))
    return values


def _parse_tag_filters(raw: Optional[Iterable[str]]) -> Optional[List[str]]:
    """
    Parse tag filter arguments.

    :param raw: Iterable of tag filters.
    :type raw: Iterable[str] or None
    :return: Normalized tag filters.
    :rtype: list[str] or None
    """
    if raw is None:
        return None
    tags = [tag.strip() for tag in raw if tag.strip()]
    return tags or None


def run_demo(arguments: argparse.Namespace) -> Dict[str, object]:
    """
    Execute the profiling demo workflow.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :return: Summary of the workflow results.
    :rtype: dict[str, object]
    """
    corpus_path = Path(arguments.corpus).resolve()
    from scripts.download_ag_news import download_ag_news_corpus

    ingestion_stats = download_ag_news_corpus(
        corpus_path=corpus_path,
        split=arguments.split,
        limit=arguments.limit,
        force=arguments.force,
        resume=arguments.resume,
    )
    corpus = Corpus.open(corpus_path)
    extraction_config = {
        "stages": [
            {
                "extractor_id": arguments.extraction_step,
                "config": {},
            }
        ]
    }
    extraction_manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name=arguments.extraction_configuration_name,
        configuration=extraction_config,
    )
    extraction_snapshot = ExtractionSnapshotReference(
        extractor_id="pipeline",
        snapshot_id=extraction_manifest.snapshot_id,
    )
    configuration_config = ProfilingConfiguration(
        schema_version=1,
        sample_size=arguments.sample_size,
        min_text_characters=arguments.min_text_characters,
        percentiles=_parse_percentiles(arguments.percentiles),
        top_tag_count=arguments.top_tag_count,
        tag_filters=_parse_tag_filters(arguments.tag_filter),
    )
    backend = ProfilingBackend()
    output = backend.run_analysis(
        corpus,
        configuration_name=arguments.configuration_name,
        configuration=configuration_config.model_dump(),
        extraction_snapshot=extraction_snapshot,
    )
    output_path = (
        corpus.analysis_run_dir(
            analysis_id=ProfilingBackend.analysis_id,
            snapshot_id=output.snapshot.snapshot_id,
        )
        / "output.json"
    )
    return {
        "corpus": str(corpus_path),
        "ingestion": ingestion_stats,
        "extraction_snapshot": extraction_snapshot.as_string(),
        "analysis_run": output.snapshot.snapshot_id,
        "output_path": str(output_path),
        "raw_items": output.snapshot.stats.get("raw_items"),
        "extracted_nonempty_items": output.snapshot.stats.get("extracted_nonempty_items"),
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Run a repeatable profiling analysis workflow.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--split", default="train", help="Dataset split for AG News.")
    parser.add_argument("--limit", type=int, default=1000, help="Number of documents to download.")
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip items already ingested into the corpus.",
    )
    parser.add_argument(
        "--extraction-step",
        default="pass-through-text",
        help="Extractor step to use for the extraction snapshot.",
    )
    parser.add_argument(
        "--extraction-configuration-name",
        default="default",
        help="Configuration name for the extraction snapshot.",
    )
    parser.add_argument(
        "--configuration-name",
        default="default",
        help="Configuration name for the profiling analysis.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Optional sample size for distribution metrics.",
    )
    parser.add_argument(
        "--min-text-characters",
        type=int,
        default=None,
        help="Minimum extracted text length for inclusion.",
    )
    parser.add_argument(
        "--percentiles",
        default="50,90,99",
        help="Comma-separated percentiles for distribution metrics.",
    )
    parser.add_argument(
        "--top-tag-count",
        type=int,
        default=10,
        help="Maximum number of tags to include.",
    )
    parser.add_argument(
        "--tag-filter",
        action="append",
        help="Optional tag filter (repeatable).",
    )
    return parser


def main() -> int:
    """
    Entry point for the profiling demo script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    summary = run_demo(args)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
