"""
Download FUNSD dataset samples for layout-aware OCR testing.

FUNSD (Form Understanding in Noisy Scanned Documents) is a dataset of 199 fully
annotated scanned form documents with ground truth OCR text, perfect for testing
and validating OCR pipelines.

Dataset: https://guillaumejaume.github.io/FUNSD/
Paper: Jaume et al., "FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents" (ICDAR-OST 2019)
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List
from urllib.request import urlretrieve

from biblicus.corpus import Corpus

# FUNSD dataset configuration
FUNSD_DATASET_URL = "https://guillaumejaume.github.io/FUNSD/dataset.zip"
FUNSD_SAMPLE_COUNT = 5  # Number of samples to ingest for testing


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for FUNSD sample downloads.

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


def download_funsd_dataset(temp_dir: Path) -> Path:
    """
    Download and extract FUNSD dataset.

    :param temp_dir: Temporary directory for download.
    :type temp_dir: Path
    :return: Path to extracted dataset directory.
    :rtype: Path
    """
    print(f"Downloading FUNSD dataset from {FUNSD_DATASET_URL}...")
    zip_path = temp_dir / "dataset.zip"

    urlretrieve(FUNSD_DATASET_URL, zip_path)
    print(f"✓ Downloaded {zip_path.stat().st_size:,} bytes")

    print("Extracting dataset...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find the extracted dataset directory
    extracted_dir = temp_dir / "dataset"
    if not extracted_dir.exists():
        # Try alternative extraction paths
        alternatives = [
            temp_dir / "FUNSD",
            temp_dir / "funsd",
            list(temp_dir.glob("*/"))[0] if list(temp_dir.glob("*/")) else None,
        ]
        for alt in alternatives:
            if alt and alt.exists() and alt.is_dir():
                extracted_dir = alt
                break

    if not extracted_dir.exists():
        raise FileNotFoundError(f"Could not find extracted dataset in {temp_dir}")

    print(f"✓ Extracted to {extracted_dir}")
    return extracted_dir


def parse_funsd_annotations(annotation_file: Path) -> Dict[str, object]:
    """
    Parse FUNSD annotation JSON file.

    :param annotation_file: Path to annotation JSON file.
    :type annotation_file: Path
    :return: Parsed annotation data.
    :rtype: dict
    """
    with open(annotation_file, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_ground_truth_text(annotations: Dict[str, object]) -> str:
    """
    Extract ground truth OCR text from FUNSD annotations.

    :param annotations: Parsed FUNSD annotation data.
    :type annotations: dict
    :return: Ground truth text.
    :rtype: str
    """
    # FUNSD annotations have a "form" key with list of entities
    # Each entity has "words" list with "text" field
    words = []
    form_data = annotations.get("form", [])

    for entity in form_data:
        for word in entity.get("words", []):
            text = word.get("text", "").strip()
            if text:
                words.append(text)

    return " ".join(words)


def ingest_funsd_samples(
    corpus: Corpus, dataset_dir: Path, sample_count: int, split: str = "testing"
) -> Dict[str, int]:
    """
    Ingest FUNSD samples into corpus.

    :param corpus: Target corpus.
    :type corpus: Corpus
    :param dataset_dir: Path to extracted FUNSD dataset.
    :type dataset_dir: Path
    :param sample_count: Number of samples to ingest.
    :type sample_count: int
    :param split: Dataset split to use ('training' or 'testing').
    :type split: str
    :return: Ingestion statistics.
    :rtype: dict
    """
    # FUNSD structure: dataset/{split}_data/images/*.png and dataset/{split}_data/annotations/*.json
    images_dir = dataset_dir / f"{split}_data" / "images"
    annotations_dir = dataset_dir / f"{split}_data" / "annotations"

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    if not annotations_dir.exists():
        raise FileNotFoundError(f"Annotations directory not found: {annotations_dir}")

    # Get list of image files
    image_files = sorted(images_dir.glob("*.png"))[:sample_count]

    print(f"\nIngesting {len(image_files)} FUNSD samples from {split} set...")

    ingested = 0
    failed = 0
    ground_truths = {}

    for image_file in image_files:
        try:
            # Find corresponding annotation file
            annotation_file = annotations_dir / f"{image_file.stem}.json"

            # Parse annotations to get ground truth
            if annotation_file.exists():
                annotations = parse_funsd_annotations(annotation_file)
                ground_truth = extract_ground_truth_text(annotations)
                ground_truths[image_file.stem] = ground_truth
            else:
                print(f"  ⚠ No annotation file for {image_file.name}")
                ground_truths[image_file.stem] = None

            # Ingest image into corpus
            result = corpus.ingest_source(
                image_file, tags=["funsd", "scanned", "form", split, "ground-truth"]
            )

            # Store ground truth as metadata
            if ground_truths[image_file.stem]:
                # TODO: Store ground truth in a way that tests can access it
                # For now, we'll save it to a separate file
                gt_dir = corpus.root / ".biblicus" / "funsd_ground_truth"
                gt_dir.mkdir(parents=True, exist_ok=True)
                gt_file = gt_dir / f"{result.item_id}.txt"
                gt_file.write_text(ground_truths[image_file.stem], encoding="utf-8")

            ingested += 1
            print(f"  ✓ {image_file.name} → {result.item_id}")

        except Exception as e:
            print(f"  ✗ Failed to ingest {image_file.name}: {e}")
            failed += 1

    return {"ingested": ingested, "failed": failed, "ground_truths": len(ground_truths)}


def download_funsd_samples(
    *, corpus_path: Path, sample_count: int, force: bool, split: str = "testing"
) -> Dict[str, int]:
    """
    Download FUNSD dataset and ingest samples into corpus.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param sample_count: Number of samples to ingest.
    :type sample_count: int
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param split: Dataset split to use ('training' or 'testing').
    :type split: str
    :return: Download and ingestion statistics.
    :rtype: dict
    """
    corpus = _prepare_corpus(corpus_path, force=force)

    # Use temporary directory for download
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Download and extract dataset
        dataset_dir = download_funsd_dataset(temp_path)

        # Ingest samples
        stats = ingest_funsd_samples(corpus, dataset_dir, sample_count, split)

    corpus.reindex()
    return stats


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Download FUNSD dataset samples for layout-aware OCR testing."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--count",
        type=int,
        default=FUNSD_SAMPLE_COUNT,
        help=f"Number of samples to ingest (default: {FUNSD_SAMPLE_COUNT})",
    )
    parser.add_argument(
        "--split",
        choices=["training", "testing"],
        default="testing",
        help="Dataset split to use (default: testing)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    return parser


def main() -> int:
    """
    Entry point for the FUNSD download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 70)
    print("FUNSD DATASET DOWNLOAD")
    print("=" * 70)
    print()
    print("Dataset: Form Understanding in Noisy Scanned Documents")
    print("Source: https://guillaumejaume.github.io/FUNSD/")
    print()

    stats = download_funsd_samples(
        corpus_path=Path(args.corpus).resolve(),
        sample_count=args.count,
        force=bool(args.force),
        split=args.split,
    )

    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(json.dumps(stats, indent=2))
    print()
    print("Ground truth annotations stored in:")
    print(f"  {Path(args.corpus).resolve() / '.biblicus' / 'funsd_ground_truth'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
