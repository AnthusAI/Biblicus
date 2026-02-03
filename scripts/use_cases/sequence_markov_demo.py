"""Use case demo: learn a sequence graph with Markov analysis.

This demo treats each item as an ordered sequence of text segments, which covers many practical
cases: chat transcripts, email threads, meeting notes, or any long text with a recurring
structure.

It uses a bundled set of conversation-style texts and runs:

1) Ingest -> a managed folder (called a "corpus" in the docs)
2) Extraction -> derived text artifacts (pass-through for already-text items)
3) Markov analysis -> topic-driven categorical observations + state transition graph

The Markov configuration in this demo includes an optional LLM state-naming step so the graph can use
human-readable labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from biblicus.analysis.markov import MarkovBackend
from biblicus.configuration import (
    apply_dotted_overrides,
    load_configuration_view,
    parse_dotted_overrides,
)
from biblicus.corpus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.models import ExtractionSnapshotReference


def _prepare_corpus(*, corpus_path: Path, force: bool) -> Corpus:
    if (corpus_path / ".biblicus" / "config.json").is_file():
        corpus = Corpus.open(corpus_path)
        if force:
            corpus.purge(confirm=corpus.name)
        return corpus
    return Corpus.init(corpus_path, force=True)


def _demo_source_files(repo_root: Path) -> List[Path]:
    dataset_dir = repo_root / "datasets" / "aixblock" / "customer_service_general_inbound_text"
    if not dataset_dir.is_dir():
        raise FileNotFoundError(
            "Bundled demo dataset missing. Expected: "
            f"{dataset_dir}. If you removed large datasets from your clone, "
            "either restore them or point this demo at a different dataset."
        )
    return sorted(dataset_dir.glob("*.txt"))


def _load_markov_configuration(
    *, configuration_paths: List[str], overrides: Dict[str, object]
) -> Dict[str, object]:
    view = load_configuration_view(configuration_paths, configuration_label="Configuration file")
    if overrides:
        view = apply_dotted_overrides(view, overrides)
    return view


def run_demo(
    *,
    repo_root: Path,
    corpus_path: Path,
    force: bool,
    ingest_limit: int,
    configuration_paths: List[str],
    overrides: Dict[str, object],
) -> Dict[str, object]:
    """
    Run the demo workflow and return a JSON-serializable payload.

    :param repo_root: Repository root path used to locate bundled demo data.
    :type repo_root: pathlib.Path
    :param corpus_path: Path to the corpus directory to initialize/use.
    :type corpus_path: pathlib.Path
    :param force: Whether to purge the corpus before ingesting demo content.
    :type force: bool
    :param ingest_limit: Maximum number of demo source files to ingest.
    :type ingest_limit: int
    :param configuration_paths: Markov configuration paths (repeatable; later files override earlier ones).
    :type configuration_paths: list[str]
    :param overrides: Dotted key/value overrides applied after configuration composition.
    :type overrides: dict[str, object]
    :return: JSON-serializable demo output including snapshot identifiers and artifact paths.
    :rtype: dict[str, object]
    """
    corpus = _prepare_corpus(corpus_path=corpus_path, force=force)

    ingested_item_ids: List[str] = []
    for source_path in _demo_source_files(repo_root)[:ingest_limit]:
        ingest_result = corpus.ingest_source(
            str(source_path),
            tags=["use-case", "sequence-modeling"],
            source_uri=source_path.resolve().as_uri(),
        )
        ingested_item_ids.append(ingest_result.item_id)

    corpus.reindex()

    extraction_manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="Use case: pass-through text",
        configuration={"steps": [{"extractor_id": "pass-through-text", "config": {}}]},
    )
    extraction_snapshot = ExtractionSnapshotReference(
        extractor_id="pipeline",
        snapshot_id=extraction_manifest.snapshot_id,
    )

    markov_config = _load_markov_configuration(
        configuration_paths=configuration_paths, overrides=overrides
    )
    markov_output = MarkovBackend().run_analysis(
        corpus,
        configuration_name="Use case: Markov sequence graph",
        configuration=markov_config,
        extraction_snapshot=extraction_snapshot,
    )

    snapshot_id = str(markov_output.snapshot.snapshot_id)
    run_dir = corpus_path / ".biblicus" / "runs" / "analysis" / "markov" / snapshot_id
    artifact_paths = [str(run_dir / relpath) for relpath in markov_output.snapshot.artifact_paths]

    return {
        "corpus_path": str(corpus_path),
        "ingested_items": len(ingested_item_ids),
        "extraction_snapshot": f"pipeline:{extraction_manifest.snapshot_id}",
        "markov_snapshot_id": snapshot_id,
        "artifact_paths": artifact_paths,
        "transitions_dot_path": str(run_dir / "transitions.dot"),
    }


def build_parser() -> argparse.ArgumentParser:
    """
    Build an argument parser for this demo script.

    :return: Parser for command-line arguments.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Use case demo: ingest ordered text and run Markov analysis (topic-driven)."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path.")
    parser.add_argument("--force", action="store_true", help="Purge corpus before running.")
    parser.add_argument(
        "--ingest-limit",
        type=int,
        default=200,
        help="How many bundled text files to ingest into the corpus.",
    )
    parser.add_argument(
        "--configuration",
        action="append",
        default=["configurations/markov/topic-driven-named.yml"],
        help="Markov configuration path (repeatable; later files override earlier ones).",
    )
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        help="Dotted override key=value (repeatable; applied after configuration composition).",
    )
    return parser


def main() -> int:
    """
    Command-line entrypoint.

    :return: Exit code.
    :rtype: int
    """
    args = build_parser().parse_args()
    repo_root = Path(__file__).resolve().parent.parent.parent
    overrides = parse_dotted_overrides(list(args.config))
    payload = run_demo(
        repo_root=repo_root,
        corpus_path=Path(args.corpus).resolve(),
        force=bool(args.force),
        ingest_limit=int(args.ingest_limit),
        configuration_paths=list(args.configuration),
        overrides=overrides,
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
