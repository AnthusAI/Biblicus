"""
Run repeatable Markov analysis demos on AG News.

This script exists to provide tangible, inspectable outputs early and often while iterating on Markov analysis
configurations. It builds or reuses an extraction snapshot, runs one or more Markov analyses, and prints the
snapshot directories so you can inspect intermediate artifacts such as segments, observations, and transitions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from biblicus.analysis.markov import MarkovBackend
from biblicus.analysis.models import MarkovAnalysisConfiguration
from biblicus.configuration import (
    apply_dotted_overrides,
    load_configuration_view,
    parse_dotted_overrides,
)
from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.models import ExtractionSnapshotReference

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _parse_list(raw: Optional[Iterable[str]]) -> List[str]:
    """
    Parse a repeatable argument list into a normalized list.

    :param raw: Iterable of raw argument values.
    :type raw: Iterable[str] or None
    :return: Normalized list.
    :rtype: list[str]
    """
    if raw is None:
        return []
    values = [str(value).strip() for value in raw if str(value).strip()]
    return values


def _load_configuration(
    *, configuration_paths: List[str], overrides: Dict[str, object]
) -> MarkovAnalysisConfiguration:
    """
    Load and validate a Markov analysis configuration.

    :param configuration_paths: Ordered list of configuration file paths.
    :type configuration_paths: list[str]
    :param overrides: Dotted key overrides applied after composition.
    :type overrides: dict[str, object]
    :return: Validated configuration.
    :rtype: MarkovAnalysisConfiguration
    """
    view = load_configuration_view(configuration_paths, configuration_label="Configuration file")
    if overrides:
        view = apply_dotted_overrides(view, overrides)
    return MarkovAnalysisConfiguration.model_validate(view)


def _run_markov(
    *,
    corpus: Corpus,
    configuration_name: str,
    configuration_paths: List[str],
    overrides: Dict[str, object],
    extraction_snapshot: ExtractionSnapshotReference,
) -> Dict[str, object]:
    """
    Run Markov analysis and return a compact summary.

    :param corpus: Corpus to analyze.
    :type corpus: Corpus
    :param configuration_name: Human-readable configuration name stored in the snapshot manifest.
    :type configuration_name: str
    :param configuration_paths: Composed configuration file paths.
    :type configuration_paths: list[str]
    :param overrides: Dotted key overrides applied after composition.
    :type overrides: dict[str, object]
    :param extraction_snapshot: Extraction run reference to use as the text source.
    :type extraction_snapshot: ExtractionSnapshotReference
    :return: Result summary.
    :rtype: dict[str, object]
    """
    config = _load_configuration(configuration_paths=configuration_paths, overrides=overrides)
    backend = MarkovBackend()
    output = backend.run_analysis(
        corpus,
        configuration_name=configuration_name,
        configuration=config.model_dump(),
        extraction_snapshot=extraction_snapshot,
    )
    snapshot_dir = corpus.analysis_run_dir(
        analysis_id=MarkovBackend.analysis_id, snapshot_id=output.snapshot.snapshot_id
    )
    return {
        "configuration_name": configuration_name,
        "configuration_paths": configuration_paths,
        "snapshot_id": output.snapshot.snapshot_id,
        "snapshot_dir": str(snapshot_dir),
        "output_path": str(snapshot_dir / "output.json"),
        "transitions_dot": (
            str(snapshot_dir / "transitions.dot")
            if (snapshot_dir / "transitions.dot").is_file()
            else None
        ),
        "stats": dict(output.snapshot.stats),
    }


def run_demo(arguments: argparse.Namespace) -> Dict[str, object]:
    """
    Execute the Markov analysis demo workflow.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :return: Demo summary.
    :rtype: dict[str, object]
    """
    corpus_path = Path(arguments.corpus).resolve()
    ingestion_stats: Dict[str, object] = {}
    if arguments.download:
        from scripts.download_ag_news import download_ag_news_corpus

        ingestion_stats = download_ag_news_corpus(
            corpus_path=corpus_path,
            split=arguments.split,
            limit=arguments.limit,
            force=arguments.force,
            resume=arguments.resume,
        )

    corpus_config = corpus_path / ".biblicus" / "config.json"
    if not corpus_config.exists():
        message = (
            "Corpus not initialized. Pass --download to ingest AG News or initialize a corpus first. "
            f"Expected to find {corpus_config}."
        )
        raise SystemExit(message)

    corpus = Corpus.open(corpus_path)
    extraction_config = {"stages": [{"extractor_id": "pass-through-text", "config": {}}]}
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

    overrides = parse_dotted_overrides(_parse_list(arguments.config))
    runs: List[Dict[str, object]] = []

    discovery_configurations = _parse_list(arguments.discovery_configuration) or [
        str(REPO_ROOT / "configurations" / "markov" / "base.yml"),
        str(REPO_ROOT / "configurations" / "markov" / "local-discovery.yml"),
    ]
    runs.append(
        _run_markov(
            corpus=corpus,
            configuration_name="local-discovery",
            configuration_paths=discovery_configurations,
            overrides=overrides,
            extraction_snapshot=extraction_snapshot,
        )
    )

    if arguments.run_openai:
        openai_enriched_configurations = _parse_list(arguments.openai_configuration) or [
            str(REPO_ROOT / "configurations" / "markov" / "openai-enriched.yml")
        ]
        runs.append(
            _run_markov(
                corpus=corpus,
                configuration_name="openai-enriched",
                configuration_paths=openai_enriched_configurations,
                overrides=overrides,
                extraction_snapshot=extraction_snapshot,
            )
        )
        guided_configurations = _parse_list(arguments.guided_configuration) or [
            str(REPO_ROOT / "configurations" / "markov" / "base.yml"),
            str(REPO_ROOT / "configurations" / "markov" / "guided.yml"),
        ]
        runs.append(
            _run_markov(
                corpus=corpus,
                configuration_name="guided",
                configuration_paths=guided_configurations,
                overrides=overrides,
                extraction_snapshot=extraction_snapshot,
            )
        )

    return {
        "corpus": str(corpus_path),
        "ingestion": ingestion_stats,
        "extraction_snapshot": extraction_snapshot.as_string(),
        "runs": runs,
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Run Markov analysis demos on AG News.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download/ingest AG News into the corpus before running analyses (requires biblicus[datasets]).",
    )
    parser.add_argument("--split", default="train", help="Dataset split for AG News.")
    parser.add_argument("--limit", type=int, default=2000, help="Number of documents to download.")
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
        "--extraction-configuration-name",
        default="default",
        help="Configuration name for the extraction snapshot.",
    )
    parser.add_argument(
        "--discovery-configuration",
        action="append",
        help="Discovery Markov configuration path (repeatable; later configurations override earlier ones).",
    )
    parser.add_argument(
        "--run-openai",
        action="store_true",
        help="Run provider-backed configurations (requires credentials; no fallback behavior).",
    )
    parser.add_argument(
        "--openai-configuration",
        action="append",
        help="Provider-backed discovery configuration path (repeatable).",
    )
    parser.add_argument(
        "--guided-configuration",
        action="append",
        help="Provider-backed guided configuration path (repeatable).",
    )
    parser.add_argument(
        "--config",
        action="append",
        help="Dotted config override key=value (repeatable; applied after configuration composition).",
    )
    return parser


def main() -> int:
    """
    Script entry point.

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
