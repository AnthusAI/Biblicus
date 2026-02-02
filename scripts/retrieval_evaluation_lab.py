"""
Run a small, deterministic retrieval evaluation lab.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from biblicus.backends import get_backend
from biblicus.corpus import Corpus
from biblicus.evaluation import EvaluationDataset, EvaluationQuery, evaluate_run
from biblicus.extraction import build_extraction_run
from biblicus.models import QueryBudget

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LAB_DIR = REPO_ROOT / "datasets" / "retrieval_lab"
LAB_ITEMS_DIR = LAB_DIR / "items"
LAB_LABELS_PATH = LAB_DIR / "labels.json"


class RetrievalEvaluationLabQuery(BaseModel):
    """
    Label entry for the retrieval evaluation lab.

    :ivar query_id: Query identifier.
    :vartype query_id: str
    :ivar query_text: Query text.
    :vartype query_text: str
    :ivar expected_filename: Expected filename for the match.
    :vartype expected_filename: str
    :ivar kind: Query kind.
    :vartype kind: str
    """

    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1)
    query_text: str = Field(min_length=1)
    expected_filename: str = Field(min_length=1)
    kind: str = Field(default="gold")


class RetrievalEvaluationLabDataset(BaseModel):
    """
    Bundled retrieval lab dataset description.

    :ivar schema_version: Dataset schema version.
    :vartype schema_version: int
    :ivar name: Dataset name.
    :vartype name: str
    :ivar description: Optional description.
    :vartype description: str or None
    :ivar queries: Label queries.
    :vartype queries: list[RetrievalEvaluationLabQuery]
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    name: str
    description: Optional[str] = None
    queries: List[RetrievalEvaluationLabQuery] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_schema_version(self) -> "RetrievalEvaluationLabDataset":
        if self.schema_version != 1:
            raise ValueError(f"Unsupported retrieval lab schema version: {self.schema_version}")
        return self


def _load_lab_dataset() -> RetrievalEvaluationLabDataset:
    """
    Load the bundled retrieval lab dataset labels.

    :return: Parsed lab dataset.
    :rtype: RetrievalEvaluationLabDataset
    """
    data = json.loads(LAB_LABELS_PATH.read_text(encoding="utf-8"))
    return RetrievalEvaluationLabDataset.model_validate(data)


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for the lab.

    :param path: Corpus path.
    :type path: Path
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :return: Corpus instance.
    :rtype: Corpus
    :raises ValueError: If the target path is non-empty without force.
    """
    if (path / ".biblicus" / "config.json").is_file():
        corpus = Corpus.open(path)
        if force:
            corpus.purge(confirm=corpus.name)
        return corpus
    if path.exists() and any(path.iterdir()) and not force:
        raise ValueError("Target corpus directory is not empty. Use --force to initialize anyway.")
    return Corpus.init(path, force=True)


def _ingest_lab_items(corpus: Corpus) -> Dict[str, str]:
    """
    Ingest bundled lab items and return filename to item identifier mapping.

    :param corpus: Corpus instance.
    :type corpus: Corpus
    :return: Mapping of filenames to item identifiers.
    :rtype: dict[str, str]
    """
    filename_map: Dict[str, str] = {}
    for item_path in sorted(LAB_ITEMS_DIR.iterdir()):
        if not item_path.is_file():
            continue
        result = corpus.ingest_source(item_path, tags=["retrieval_lab"])
        filename_map[item_path.name] = result.item_id
    return filename_map


def _build_evaluation_dataset(
    lab_dataset: RetrievalEvaluationLabDataset, *, filename_map: Dict[str, str]
) -> EvaluationDataset:
    """
    Create a retrieval evaluation dataset from lab labels.

    :param lab_dataset: Lab dataset labels.
    :type lab_dataset: RetrievalEvaluationLabDataset
    :param filename_map: Mapping of filenames to item identifiers.
    :type filename_map: dict[str, str]
    :return: Evaluation dataset.
    :rtype: EvaluationDataset
    :raises ValueError: If a label references an unknown filename.
    """
    queries: List[EvaluationQuery] = []
    for query in lab_dataset.queries:
        item_id = filename_map.get(query.expected_filename)
        if not item_id:
            raise ValueError(f"Missing lab item mapping for {query.expected_filename}")
        queries.append(
            EvaluationQuery(
                query_id=query.query_id,
                query_text=query.query_text,
                expected_item_id=item_id,
                kind=query.kind,
            )
        )
    return EvaluationDataset(
        schema_version=1,
        name=lab_dataset.name,
        description=lab_dataset.description,
        queries=queries,
    )


def run_lab(arguments: argparse.Namespace) -> Dict[str, object]:
    """
    Execute the retrieval evaluation lab workflow.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :return: Summary of the workflow results.
    :rtype: dict[str, object]
    """
    corpus_path = Path(arguments.corpus).resolve()
    corpus = _prepare_corpus(corpus_path, force=arguments.force)
    lab_dataset = _load_lab_dataset()
    filename_map = _ingest_lab_items(corpus)

    extraction_manifest = build_extraction_run(
        corpus,
        extractor_id="pipeline",
        recipe_name=arguments.extraction_recipe_name,
        config={
            "steps": [
                {
                    "extractor_id": arguments.extraction_step,
                    "config": {},
                }
            ]
        },
    )
    backend = get_backend("sqlite-full-text-search")
    retrieval_run = backend.build_run(
        corpus,
        recipe_name=arguments.retrieval_recipe_name,
        config={"extraction_run": f"pipeline:{extraction_manifest.run_id}"},
    )
    evaluation_dataset = _build_evaluation_dataset(lab_dataset, filename_map=filename_map)
    dataset_path = Path(arguments.dataset_path).resolve()
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(evaluation_dataset.model_dump_json(indent=2) + "\n", encoding="utf-8")

    budget = QueryBudget(max_total_items=arguments.max_total_items, maximum_total_characters=2000)
    result = evaluate_run(
        corpus=corpus,
        run=retrieval_run,
        dataset=evaluation_dataset,
        budget=budget,
    )

    output_dir = corpus.runs_dir / "evaluation" / "retrieval" / retrieval_run.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "output.json"
    output_path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")

    return {
        "corpus": str(corpus_path),
        "ingested_items": len(filename_map),
        "extraction_run": f"pipeline:{extraction_manifest.run_id}",
        "retrieval_run": f"{backend.backend_id}:{retrieval_run.run_id}",
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
    parser = argparse.ArgumentParser(description="Run the retrieval evaluation lab.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    parser.add_argument(
        "--extraction-step",
        default="pass-through-text",
        help="Extractor step to use for the extraction run.",
    )
    parser.add_argument(
        "--extraction-recipe-name",
        default="default",
        help="Recipe name for the extraction run.",
    )
    parser.add_argument(
        "--retrieval-recipe-name",
        default="default",
        help="Recipe name for the retrieval run.",
    )
    parser.add_argument(
        "--dataset-path",
        default="datasets/retrieval_lab_output.json",
        help="Path to write the generated evaluation dataset JSON file.",
    )
    parser.add_argument(
        "--max-total-items",
        type=int,
        default=3,
        help="Maximum evidence items per query.",
    )
    return parser


def main() -> int:
    """
    Entry point for the retrieval evaluation lab script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    summary = run_lab(args)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
