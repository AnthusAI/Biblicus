"""
Run repeatable Markov analysis demos on AG News.

This script exists to provide tangible, inspectable outputs early and often while iterating on Markov analysis
configuration "recipes". It builds or reuses an extraction run, runs one or more Markov analyses, and prints the run
directories so you can inspect intermediate artifacts such as segments, observations, and transitions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from biblicus.analysis.markov import MarkovBackend
from biblicus.analysis.models import MarkovAnalysisRecipeConfig
from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_run
from biblicus.models import ExtractionRunReference
from biblicus.recipes import apply_dotted_overrides, load_recipe_view, parse_dotted_overrides

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


def _load_recipe_config(
    *, recipe_paths: List[str], overrides: Dict[str, object]
) -> MarkovAnalysisRecipeConfig:
    """
    Load and validate a Markov analysis recipe configuration.

    :param recipe_paths: Ordered list of recipe file paths.
    :type recipe_paths: list[str]
    :param overrides: Dotted key overrides applied after composition.
    :type overrides: dict[str, object]
    :return: Validated recipe configuration.
    :rtype: MarkovAnalysisRecipeConfig
    """
    view = load_recipe_view(recipe_paths, recipe_label="Recipe file")
    if overrides:
        view = apply_dotted_overrides(view, overrides)
    return MarkovAnalysisRecipeConfig.model_validate(view)


def _run_markov(
    *,
    corpus: Corpus,
    recipe_name: str,
    recipe_paths: List[str],
    overrides: Dict[str, object],
    extraction_run: ExtractionRunReference,
) -> Dict[str, object]:
    """
    Run Markov analysis and return a compact summary.

    :param corpus: Corpus to analyze.
    :type corpus: Corpus
    :param recipe_name: Human-readable recipe name stored in the run manifest.
    :type recipe_name: str
    :param recipe_paths: Composed recipe file paths.
    :type recipe_paths: list[str]
    :param overrides: Dotted key overrides applied after composition.
    :type overrides: dict[str, object]
    :param extraction_run: Extraction run reference to use as the text source.
    :type extraction_run: ExtractionRunReference
    :return: Result summary.
    :rtype: dict[str, object]
    """
    config = _load_recipe_config(recipe_paths=recipe_paths, overrides=overrides)
    backend = MarkovBackend()
    output = backend.run_analysis(
        corpus,
        recipe_name=recipe_name,
        config=config.model_dump(),
        extraction_run=extraction_run,
    )
    run_dir = corpus.analysis_run_dir(
        analysis_id=MarkovBackend.analysis_id, run_id=output.run.run_id
    )
    return {
        "recipe_name": recipe_name,
        "recipe_paths": recipe_paths,
        "run_id": output.run.run_id,
        "run_dir": str(run_dir),
        "output_path": str(run_dir / "output.json"),
        "transitions_dot": (
            str(run_dir / "transitions.dot") if (run_dir / "transitions.dot").is_file() else None
        ),
        "stats": dict(output.run.stats),
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
    extraction_config = {"steps": [{"extractor_id": "pass-through-text", "config": {}}]}
    extraction_manifest = build_extraction_run(
        corpus,
        extractor_id="pipeline",
        recipe_name=arguments.extraction_recipe_name,
        config=extraction_config,
    )
    extraction_run = ExtractionRunReference(
        extractor_id="pipeline",
        run_id=extraction_manifest.run_id,
    )

    overrides = parse_dotted_overrides(_parse_list(arguments.config))
    runs: List[Dict[str, object]] = []

    discovery_recipes = _parse_list(arguments.discovery_recipe) or [
        str(REPO_ROOT / "recipes" / "markov" / "base.yml"),
        str(REPO_ROOT / "recipes" / "markov" / "local-discovery.yml"),
    ]
    runs.append(
        _run_markov(
            corpus=corpus,
            recipe_name="local-discovery",
            recipe_paths=discovery_recipes,
            overrides=overrides,
            extraction_run=extraction_run,
        )
    )

    if arguments.run_openai:
        openai_enriched_recipes = _parse_list(arguments.openai_recipe) or [
            str(REPO_ROOT / "recipes" / "markov" / "openai-enriched.yml")
        ]
        runs.append(
            _run_markov(
                corpus=corpus,
                recipe_name="openai-enriched",
                recipe_paths=openai_enriched_recipes,
                overrides=overrides,
                extraction_run=extraction_run,
            )
        )
        guided_recipes = _parse_list(arguments.guided_recipe) or [
            str(REPO_ROOT / "recipes" / "markov" / "base.yml"),
            str(REPO_ROOT / "recipes" / "markov" / "guided.yml"),
        ]
        runs.append(
            _run_markov(
                corpus=corpus,
                recipe_name="guided",
                recipe_paths=guided_recipes,
                overrides=overrides,
                extraction_run=extraction_run,
            )
        )

    return {
        "corpus": str(corpus_path),
        "ingestion": ingestion_stats,
        "extraction_run": extraction_run.as_string(),
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
        "--extraction-recipe-name",
        default="default",
        help="Recipe name for the extraction run.",
    )
    parser.add_argument(
        "--discovery-recipe",
        action="append",
        help="Discovery Markov recipe path (repeatable; later recipes override earlier ones).",
    )
    parser.add_argument(
        "--run-openai",
        action="store_true",
        help="Run provider-backed recipes (requires credentials; no fallback behavior).",
    )
    parser.add_argument(
        "--openai-recipe",
        action="append",
        help="Provider-backed discovery recipe path (repeatable).",
    )
    parser.add_argument(
        "--guided-recipe",
        action="append",
        help="Provider-backed guided recipe path (repeatable).",
    )
    parser.add_argument(
        "--config",
        action="append",
        help="Dotted config override key=value (repeatable; applied after recipe composition).",
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
