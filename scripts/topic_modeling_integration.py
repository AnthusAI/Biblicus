"""
Run a repeatable topic modeling integration workflow on a Wikipedia corpus.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from biblicus.analysis.topic_modeling import TopicModelingBackend
from biblicus.analysis.models import (
    TopicModelingBerTopicConfig,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmFineTuningConfig,
    TopicModelingLexicalProcessingConfig,
    TopicModelingRecipeConfig,
    TopicModelingTextSourceConfig,
)
from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_run
from biblicus.models import ExtractionRunReference
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.download_wikipedia import download_wikipedia_corpus


def _parse_config_pairs(pairs: Optional[Iterable[str]]) -> Dict[str, object]:
    """
    Parse key=value pairs into a configuration mapping.

    :param pairs: Iterable of key=value strings.
    :type pairs: Iterable[str] or None
    :return: Parsed configuration mapping.
    :rtype: dict[str, object]
    :raises ValueError: If any entry is not a key=value pair or values are invalid.
    """
    config: Dict[str, object] = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"Config values must be key=value (got {item!r})")
        key, raw = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("Config keys must be non-empty")
        raw = raw.strip()
        value: object = raw
        if raw.startswith("{") or raw.startswith("["):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Config value must be valid JSON for key {key!r}") from exc
        elif raw.isdigit():
            value = int(raw)
        else:
            try:
                value = float(raw)
            except ValueError:
                value = raw
        config[key] = value
    return config


def _build_recipe_config(
    arguments: argparse.Namespace, document_count: Optional[int]
) -> TopicModelingRecipeConfig:
    """
    Build a validated topic modeling recipe from parsed arguments.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :return: Topic modeling recipe configuration.
    :rtype: TopicModelingRecipeConfig
    """
    text_source = TopicModelingTextSourceConfig(
        sample_size=arguments.sample_size,
        min_text_characters=arguments.min_text_characters,
    )
    lexical_processing = TopicModelingLexicalProcessingConfig(
        enabled=arguments.lexical_enabled,
        lowercase=arguments.lexical_lowercase,
        strip_punctuation=arguments.lexical_strip_punctuation,
        collapse_whitespace=arguments.lexical_collapse_whitespace,
    )
    bertopic_config = TopicModelingBerTopicConfig(
        parameters=_parse_config_pairs(arguments.bertopic_param),
    )
    llm_extraction = TopicModelingLlmExtractionConfig(enabled=False)
    llm_fine_tuning = TopicModelingLlmFineTuningConfig(enabled=False)
    return TopicModelingRecipeConfig(
        schema_version=1,
        text_source=text_source,
        llm_extraction=llm_extraction,
        lexical_processing=lexical_processing,
        bertopic_analysis=bertopic_config,
        llm_fine_tuning=llm_fine_tuning,
    )


def run_integration(arguments: argparse.Namespace) -> Dict[str, object]:
    """
    Execute the full integration workflow.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :return: Summary of the workflow results.
    :rtype: dict[str, object]
    """
    corpus_path = Path(arguments.corpus).resolve()
    ingestion_stats = download_wikipedia_corpus(
        corpus_path=corpus_path,
        limit=arguments.limit,
        force=arguments.force,
    )
    corpus = Corpus.open(corpus_path)
    extraction_config = {
        "steps": [
            {
                "extractor_id": arguments.extraction_step,
                "config": {},
            }
        ]
    }
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
    document_count = extraction_manifest.stats.get("extracted_nonempty_items")
    if document_count is not None and document_count < 16:
        raise ValueError(
            "BERTopic defaults require at least 16 documents. Increase --limit or use a larger corpus."
        )
    recipe_config = _build_recipe_config(arguments, document_count)
    backend = TopicModelingBackend()
    output = backend.run_analysis(
        corpus,
        recipe_name=arguments.recipe_name,
        config=recipe_config.model_dump(),
        extraction_run=extraction_run,
    )
    output_path = corpus.analysis_run_dir(
        analysis_id=TopicModelingBackend.analysis_id,
        run_id=output.run.run_id,
    ) / "output.json"
    return {
        "corpus": str(corpus_path),
        "ingestion": ingestion_stats,
        "extraction_run": extraction_run.as_string(),
        "analysis_run": output.run.run_id,
        "output_path": str(output_path),
        "topics": output.run.stats.get("topics"),
        "documents": output.run.stats.get("documents"),
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Run a repeatable topic modeling integration workflow."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--limit", type=int, default=20, help="Number of pages to download.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Purge the corpus before downloading Wikipedia summaries.",
    )
    parser.add_argument(
        "--extraction-step",
        default="pass-through-text",
        help="Extractor step to use inside the pipeline run.",
    )
    parser.add_argument(
        "--extraction-recipe-name",
        default="integration",
        help="Recipe name for the extraction run.",
    )
    parser.add_argument(
        "--recipe-name",
        default="integration",
        help="Recipe name for the topic modeling run.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Maximum number of documents to analyze.",
    )
    parser.add_argument(
        "--min-text-characters",
        type=int,
        default=None,
        help="Minimum extracted text length required for analysis.",
    )
    parser.add_argument(
        "--lexical-enabled",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable lexical processing stage.",
    )
    parser.add_argument(
        "--lexical-lowercase",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Lowercase text during lexical processing.",
    )
    parser.add_argument(
        "--lexical-strip-punctuation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Remove punctuation during lexical processing.",
    )
    parser.add_argument(
        "--lexical-collapse-whitespace",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Collapse whitespace during lexical processing.",
    )
    parser.add_argument(
        "--bertopic-param",
        action="append",
        default=[],
        help="BERTopic constructor parameter (key=value).",
    )
    return parser


def main() -> int:
    """
    Entry point for the integration runner.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    result = run_integration(args)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
