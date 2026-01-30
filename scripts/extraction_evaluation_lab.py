"""
Run a small, deterministic extraction evaluation lab.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_run
from biblicus.extraction_evaluation import (
    ExtractionEvaluationDataset,
    ExtractionEvaluationItem,
    evaluate_extraction_run,
    write_extraction_evaluation_result,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LAB_DIR = REPO_ROOT / "datasets" / "extraction_lab"
LAB_ITEMS_DIR = LAB_DIR / "items"
LAB_LABELS_PATH = LAB_DIR / "labels.json"


class ExtractionEvaluationLabLabel(BaseModel):
    """
    Label entry for the extraction evaluation lab.

    :ivar filename: Relative filename for the lab item.
    :vartype filename: str
    :ivar expected_text: Expected extracted text.
    :vartype expected_text: str
    """

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1)
    expected_text: str


class ExtractionEvaluationLabDataset(BaseModel):
    """
    Bundled lab dataset description.

    :ivar schema_version: Dataset schema version.
    :vartype schema_version: int
    :ivar name: Dataset name.
    :vartype name: str
    :ivar description: Optional description.
    :vartype description: str or None
    :ivar items: Label entries.
    :vartype items: list[ExtractionEvaluationLabLabel]
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    name: str
    description: Optional[str] = None
    items: List[ExtractionEvaluationLabLabel] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_schema_version(self) -> "ExtractionEvaluationLabDataset":
        if self.schema_version != 1:
            raise ValueError(f"Unsupported extraction lab schema version: {self.schema_version}")
        return self


def _load_lab_dataset() -> ExtractionEvaluationLabDataset:
    """
    Load the bundled extraction lab dataset labels.

    :return: Parsed lab dataset.
    :rtype: ExtractionEvaluationLabDataset
    """
    data = json.loads(LAB_LABELS_PATH.read_text(encoding="utf-8"))
    return ExtractionEvaluationLabDataset.model_validate(data)


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


def run_lab(arguments: argparse.Namespace) -> Dict[str, object]:
    """
    Execute the extraction evaluation lab workflow.

    :param arguments: Parsed command-line arguments.
    :type arguments: argparse.Namespace
    :return: Summary of the workflow results.
    :rtype: dict[str, object]
    """
    corpus_path = Path(arguments.corpus).resolve()
    corpus = _prepare_corpus(corpus_path, force=arguments.force)
    lab_dataset = _load_lab_dataset()
    ingested_ids: List[str] = []

    for label in lab_dataset.items:
        source_path = (LAB_ITEMS_DIR / label.filename).resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing lab item: {source_path}")
        result = corpus.ingest_source(source_path, tags=["extraction_lab"])
        ingested_ids.append(result.item_id)

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

    evaluation_items = [
        ExtractionEvaluationItem(
            item_id=item_id,
            expected_text=label.expected_text,
            kind="gold",
        )
        for item_id, label in zip(ingested_ids, lab_dataset.items)
    ]
    dataset = ExtractionEvaluationDataset(
        schema_version=1,
        name=lab_dataset.name,
        description=lab_dataset.description,
        items=evaluation_items,
    )
    dataset_path = Path(arguments.dataset_path).resolve()
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(dataset.model_dump_json(indent=2) + "\n", encoding="utf-8")

    result = evaluate_extraction_run(
        corpus=corpus,
        run=extraction_manifest,
        extractor_id="pipeline",
        dataset=dataset,
    )
    output_path = write_extraction_evaluation_result(
        corpus=corpus,
        run_id=extraction_manifest.run_id,
        result=result,
    )
    return {
        "corpus": str(corpus_path),
        "ingested_items": len(ingested_ids),
        "extraction_run": f"pipeline:{extraction_manifest.run_id}",
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
    parser = argparse.ArgumentParser(description="Run the extraction evaluation lab.")
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
        "--dataset-path",
        default="datasets/extraction_lab_output.json",
        help="Path to write the generated evaluation dataset JSON file.",
    )
    return parser


def main() -> int:
    """
    Entry point for the extraction evaluation lab script.

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
