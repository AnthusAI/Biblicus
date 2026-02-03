"""
Run a repeatable extraction evaluation workflow on AG News.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.extraction_evaluation import (
    ExtractionEvaluationDataset,
    ExtractionEvaluationItem,
    evaluate_extraction_snapshot,
    write_extraction_evaluation_result,
)
from biblicus.frontmatter import parse_front_matter

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _select_ag_news_items(corpus: Corpus, *, limit: int) -> List[ExtractionEvaluationItem]:
    """
    Select AG News items for evaluation.

    :param corpus: Corpus to inspect.
    :type corpus: Corpus
    :param limit: Maximum number of items to include.
    :type limit: int
    :return: Evaluation items.
    :rtype: list[ExtractionEvaluationItem]
    :raises ValueError: If no labeled items are available.
    """
    catalog = corpus.load_catalog()
    items: List[ExtractionEvaluationItem] = []
    for item_id in catalog.order:
        catalog_item = catalog.items.get(item_id)
        if catalog_item is None:
            continue
        if "ag_news" not in catalog_item.tags:
            continue
        raw_path = (corpus.root / catalog_item.relpath).resolve()
        raw_text = raw_path.read_text(encoding="utf-8")
        parsed_document = parse_front_matter(raw_text)
        expected_text = parsed_document.body
        items.append(
            ExtractionEvaluationItem(
                item_id=item_id,
                expected_text=expected_text,
                kind="gold",
            )
        )
        if len(items) >= limit:
            break
    if not items:
        raise ValueError("No AG News items were found in the corpus")
    return items


def _write_dataset_file(*, dataset: ExtractionEvaluationDataset, dataset_path: Path) -> Path:
    """
    Persist the dataset to disk.

    :param dataset: Dataset to write.
    :type dataset: ExtractionEvaluationDataset
    :param dataset_path: Path to write.
    :type dataset_path: Path
    :return: Dataset path.
    :rtype: Path
    """
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(dataset.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return dataset_path


def run_demo(arguments: argparse.Namespace) -> Dict[str, object]:
    """
    Execute the extraction evaluation demo workflow.

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
    extraction_manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name=arguments.extraction_configuration_name,
        configuration={
            "steps": [
                {
                    "extractor_id": arguments.extraction_step,
                    "config": {},
                }
            ]
        },
    )
    evaluation_items = _select_ag_news_items(corpus, limit=arguments.dataset_limit)
    dataset = ExtractionEvaluationDataset(
        schema_version=1,
        name="AG News extraction evaluation",
        description="AG News extraction accuracy baseline",
        items=evaluation_items,
    )
    dataset_path = _write_dataset_file(
        dataset=dataset,
        dataset_path=Path(arguments.dataset_path).resolve(),
    )
    result = evaluate_extraction_snapshot(
        corpus=corpus,
        snapshot=extraction_manifest,
        extractor_id="pipeline",
        dataset=dataset,
    )
    output_path = write_extraction_evaluation_result(
        corpus=corpus,
        snapshot_id=extraction_manifest.snapshot_id,
        result=result,
    )
    return {
        "corpus": str(corpus_path),
        "ingestion": ingestion_stats,
        "extraction_snapshot": f"pipeline:{extraction_manifest.snapshot_id}",
        "dataset_path": str(dataset_path),
        "evaluation_output_path": str(output_path),
        "metrics": result.metrics,
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface parser.

    :return: Configured argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Run an extraction evaluation demo workflow.")
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
        "--dataset-limit",
        type=int,
        default=50,
        help="Number of items to include in the evaluation dataset.",
    )
    parser.add_argument(
        "--dataset-path",
        default="datasets/extraction_demo.json",
        help="Path to write the evaluation dataset JSON file.",
    )
    return parser


def main() -> int:
    """
    Entry point for the extraction evaluation demo script.

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
