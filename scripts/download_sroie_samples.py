"""
Download SROIE dataset samples for receipt OCR and entity extraction testing.

SROIE (Scanned Receipts OCR and Information Extraction) is a dataset of 626 receipt
images with OCR text and structured entity annotations (company, date, address, total).

Dataset: ICDAR 2019 Robust Reading Challenge on Scanned Receipts OCR and Information Extraction
Source: https://rrc.cvc.uab.es/?ch=13
Paper: Huang et al., "ICDAR2019 Competition on Scanned Receipt OCR and Information Extraction" (2019)

Note: This script downloads from a mirror or requires manual download from the competition site.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlretrieve

from biblicus.corpus import Corpus

# SROIE dataset configuration
# Using arvindrajan92/sroie_document_understanding which has images + OCR annotations
SROIE_HF_DATASET = "arvindrajan92/sroie_document_understanding"
SROIE_SAMPLE_COUNT = 50  # Number of samples to ingest for testing


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for SROIE sample downloads.

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


def download_sroie_from_huggingface(temp_dir: Path, split: str = "train") -> Path:
    """
    Download SROIE dataset from HuggingFace.

    :param temp_dir: Temporary directory for download.
    :type temp_dir: Path
    :param split: Dataset split to use ('train' or 'test').
    :type split: str
    :return: Path to dataset directory.
    :rtype: Path
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError(
            "HuggingFace datasets library required. Install with: pip install datasets"
        )

    print(f"Downloading SROIE dataset from HuggingFace ({SROIE_HF_DATASET})...")

    # Load dataset from HuggingFace
    dataset = load_dataset(SROIE_HF_DATASET, split=split)

    # Create directory structure
    images_dir = temp_dir / "images"
    ocr_dir = temp_dir / "ocr"
    entities_dir = temp_dir / "entities"

    images_dir.mkdir(parents=True, exist_ok=True)
    ocr_dir.mkdir(parents=True, exist_ok=True)
    entities_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {len(dataset)} receipt images...")

    for idx, item in enumerate(dataset):
        # Save image
        image = item.get("image")
        if image:
            image_path = images_dir / f"receipt_{idx:04d}.jpg"
            image.save(image_path)

        # Extract OCR text from annotations
        # Format: list of {'box': [[x1,y1], ...], 'label': 'other', 'text': 'word'}
        ocr_annotations = item.get("ocr", [])
        words = []
        for ann in ocr_annotations:
            text = ann.get("text", "")
            if text:
                words.append(text)

        if words:
            ocr_path = ocr_dir / f"receipt_{idx:04d}.txt"
            ocr_path.write_text(" ".join(words), encoding="utf-8")

        # Extract entity annotations from labeled OCR items
        # Labels include: company, date, address, total, other
        entities = {"company": "", "date": "", "address": "", "total": ""}
        for ann in ocr_annotations:
            label = ann.get("label", "other").lower()
            text = ann.get("text", "")
            if label in entities and text:
                if entities[label]:
                    entities[label] += " " + text
                else:
                    entities[label] = text

        entities_path = entities_dir / f"receipt_{idx:04d}.json"
        entities_path.write_text(json.dumps(entities, indent=2), encoding="utf-8")

    print(f"✓ Downloaded {len(dataset)} receipts to {temp_dir}")
    return temp_dir


def download_sroie_from_local(local_path: Path, temp_dir: Path) -> Path:
    """
    Process SROIE dataset from local download.

    :param local_path: Path to locally downloaded SROIE data.
    :type local_path: Path
    :param temp_dir: Temporary directory for processing.
    :type temp_dir: Path
    :return: Path to processed dataset directory.
    :rtype: Path
    """
    print(f"Processing SROIE dataset from local path: {local_path}")

    # SROIE official structure varies, handle common formats
    # Task 1: Text Localization (bounding boxes)
    # Task 2: OCR (text recognition)
    # Task 3: Key Information Extraction (entities)

    images_dir = temp_dir / "images"
    ocr_dir = temp_dir / "ocr"
    entities_dir = temp_dir / "entities"

    images_dir.mkdir(parents=True, exist_ok=True)
    ocr_dir.mkdir(parents=True, exist_ok=True)
    entities_dir.mkdir(parents=True, exist_ok=True)

    # Find image files
    image_extensions = ["*.jpg", "*.jpeg", "*.png"]
    image_files = []
    for ext in image_extensions:
        image_files.extend(local_path.rglob(ext))

    print(f"Found {len(image_files)} image files")

    for image_file in image_files:
        stem = image_file.stem

        # Copy image
        shutil.copy(image_file, images_dir / image_file.name)

        # Look for corresponding OCR text file
        ocr_file = image_file.with_suffix(".txt")
        if not ocr_file.exists():
            ocr_file = image_file.parent / f"{stem}.txt"
        if ocr_file.exists():
            shutil.copy(ocr_file, ocr_dir / f"{stem}.txt")

        # Look for entity file (key information)
        entity_patterns = [
            image_file.parent / "entities" / f"{stem}.txt",
            image_file.parent / "key" / f"{stem}.txt",
            image_file.with_name(f"{stem}_entities.txt"),
        ]
        for entity_file in entity_patterns:
            if entity_file.exists():
                # Parse SROIE entity format: company\ndate\naddress\ntotal
                lines = entity_file.read_text(encoding="utf-8").strip().split("\n")
                entities = {
                    "company": lines[0] if len(lines) > 0 else "",
                    "date": lines[1] if len(lines) > 1 else "",
                    "address": lines[2] if len(lines) > 2 else "",
                    "total": lines[3] if len(lines) > 3 else "",
                }
                entities_path = entities_dir / f"{stem}.json"
                entities_path.write_text(json.dumps(entities, indent=2), encoding="utf-8")
                break

    return temp_dir


def ingest_sroie_samples(
    corpus: Corpus, dataset_dir: Path, sample_count: int
) -> Dict[str, int]:
    """
    Ingest SROIE samples into corpus.

    :param corpus: Target corpus.
    :type corpus: Corpus
    :param dataset_dir: Path to processed SROIE dataset.
    :type dataset_dir: Path
    :param sample_count: Number of samples to ingest.
    :type sample_count: int
    :return: Ingestion statistics.
    :rtype: dict
    """
    images_dir = dataset_dir / "images"
    ocr_dir = dataset_dir / "ocr"
    entities_dir = dataset_dir / "entities"

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    # Get list of image files
    image_files = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")))[:sample_count]

    print(f"\nIngesting {len(image_files)} SROIE samples...")

    ingested = 0
    failed = 0
    ground_truths = {}
    entities_count = 0

    for image_file in image_files:
        try:
            stem = image_file.stem

            # Get OCR ground truth
            ocr_file = ocr_dir / f"{stem}.txt"
            if ocr_file.exists():
                ground_truth = ocr_file.read_text(encoding="utf-8").strip()
                ground_truths[stem] = ground_truth
            else:
                ground_truths[stem] = None

            # Get entity annotations
            entities_file = entities_dir / f"{stem}.json"
            entities = None
            if entities_file.exists():
                entities = json.loads(entities_file.read_text(encoding="utf-8"))
                entities_count += 1

            # Ingest image into corpus
            result = corpus.ingest_source(
                image_file, tags=["sroie", "receipt", "scanned", "ground-truth"]
            )

            # Store ground truth
            gt_dir = corpus.root / ".biblicus" / "sroie_ground_truth"
            gt_dir.mkdir(parents=True, exist_ok=True)

            if ground_truths[stem]:
                gt_file = gt_dir / f"{result.item_id}.txt"
                gt_file.write_text(ground_truths[stem], encoding="utf-8")

            # Store entity annotations
            if entities:
                entities_out_dir = corpus.root / ".biblicus" / "sroie_entities"
                entities_out_dir.mkdir(parents=True, exist_ok=True)
                entities_file = entities_out_dir / f"{result.item_id}.json"
                entities_file.write_text(json.dumps(entities, indent=2), encoding="utf-8")

            ingested += 1
            print(f"  ✓ {image_file.name} → {result.item_id}")

        except Exception as e:
            print(f"  ✗ Failed to ingest {image_file.name}: {e}")
            failed += 1

    return {
        "ingested": ingested,
        "failed": failed,
        "ground_truths": len([g for g in ground_truths.values() if g]),
        "entities": entities_count,
    }


def download_sroie_samples(
    *,
    corpus_path: Path,
    sample_count: int,
    force: bool,
    local_path: Optional[Path] = None,
    split: str = "train",
) -> Dict[str, int]:
    """
    Download SROIE dataset and ingest samples into corpus.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param sample_count: Number of samples to ingest.
    :type sample_count: int
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param local_path: Path to locally downloaded SROIE data (optional).
    :type local_path: Path or None
    :param split: Dataset split to use ('train' or 'test').
    :type split: str
    :return: Download and ingestion statistics.
    :rtype: dict
    """
    corpus = _prepare_corpus(corpus_path, force=force)

    # Use temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        if local_path:
            # Process from local download
            dataset_dir = download_sroie_from_local(local_path, temp_path)
        else:
            # Download from HuggingFace
            dataset_dir = download_sroie_from_huggingface(temp_path, split)

        # Ingest samples
        stats = ingest_sroie_samples(corpus, dataset_dir, sample_count)

    corpus.reindex()
    return stats


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Download SROIE dataset samples for receipt OCR and entity extraction testing."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--count",
        type=int,
        default=SROIE_SAMPLE_COUNT,
        help=f"Number of samples to ingest (default: {SROIE_SAMPLE_COUNT})",
    )
    parser.add_argument(
        "--split",
        choices=["train", "test"],
        default="train",
        help="Dataset split to use (default: train)",
    )
    parser.add_argument(
        "--from-local",
        type=Path,
        help="Path to locally downloaded SROIE data (skip HuggingFace download)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    return parser


def main() -> int:
    """
    Entry point for the SROIE download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 70)
    print("SROIE DATASET DOWNLOAD")
    print("=" * 70)
    print()
    print("Dataset: Scanned Receipts OCR and Information Extraction")
    print("Source: ICDAR 2019 Competition")
    print("Entities: company, date, address, total")
    print()

    stats = download_sroie_samples(
        corpus_path=Path(args.corpus).resolve(),
        sample_count=args.count,
        force=bool(args.force),
        local_path=args.from_local,
        split=args.split,
    )

    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(json.dumps(stats, indent=2))
    print()
    print("Ground truth text stored in:")
    print(f"  {Path(args.corpus).resolve() / '.biblicus' / 'sroie_ground_truth'}")
    print("Entity annotations stored in:")
    print(f"  {Path(args.corpus).resolve() / '.biblicus' / 'sroie_entities'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
