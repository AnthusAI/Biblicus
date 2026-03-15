"""
Download Scanned ArXiv papers for multi-column layout OCR testing.

This dataset contains academic papers rendered as images (not born-digital PDFs),
making them suitable for testing OCR on multi-column layouts with complex structure
like figures, tables, equations, and references.

Dataset: IAMJB/scanned-arxiv-papers
Source: HuggingFace Datasets
Purpose: Test reading order preservation and multi-column layout handling

Key challenge: Academic papers typically have:
- Two-column layout requiring correct reading order
- Abstracts, figures, tables, equations
- References section with dense text
- Section headers and captions
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional

from biblicus.corpus import Corpus

# Scanned ArXiv dataset configuration
SCANNED_ARXIV_HF_DATASET = "IAMJB/scanned-arxiv-papers"
SCANNED_ARXIV_SAMPLE_COUNT = 20  # Number of samples to ingest for testing


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for Scanned ArXiv sample downloads.

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


def download_scanned_arxiv_from_huggingface(
    temp_dir: Path, sample_count: int, split: str = "train"
) -> Path:
    """
    Download Scanned ArXiv dataset from HuggingFace.

    :param temp_dir: Temporary directory for download.
    :type temp_dir: Path
    :param sample_count: Number of samples to download.
    :type sample_count: int
    :param split: Dataset split to use.
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

    print(f"Downloading Scanned ArXiv dataset from HuggingFace ({SCANNED_ARXIV_HF_DATASET})...")

    # Load dataset from HuggingFace
    # Note: The dataset may be large, so we use streaming if available
    try:
        dataset = load_dataset(SCANNED_ARXIV_HF_DATASET, split=split, streaming=False)
        # Take only the samples we need
        if hasattr(dataset, 'select'):
            dataset = dataset.select(range(min(sample_count, len(dataset))))
        else:
            dataset = list(dataset)[:sample_count]
    except Exception as e:
        print(f"Warning: Could not load full dataset: {e}")
        print("Trying streaming mode...")
        dataset = load_dataset(SCANNED_ARXIV_HF_DATASET, split=split, streaming=True)
        dataset = list(dataset.take(sample_count))

    # Create directory structure
    images_dir = temp_dir / "images"
    ground_truth_dir = temp_dir / "ground_truth"
    metadata_dir = temp_dir / "metadata"

    images_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {len(dataset) if hasattr(dataset, '__len__') else 'streaming'} paper images...")

    processed = 0
    for idx, item in enumerate(dataset):
        if processed >= sample_count:
            break

        try:
            # The dataset structure may vary - handle common formats
            # Common fields: image, text, arxiv_id, page_num

            # Get image
            image = item.get("image")
            if image is None:
                # Try alternative field names
                for field in ["page_image", "scan", "img"]:
                    if field in item:
                        image = item[field]
                        break

            if image is None:
                print(f"  ⚠ No image found for item {idx}")
                continue

            # Generate filename
            arxiv_id = item.get("arxiv_id", item.get("paper_id", f"paper_{idx:04d}"))
            page_num = item.get("page_num", item.get("page", 0))
            filename = f"{arxiv_id}_p{page_num:02d}"

            # Save image
            image_path = images_dir / f"{filename}.png"
            if hasattr(image, 'save'):
                image.save(image_path)
            else:
                # Handle bytes or other formats
                with open(image_path, 'wb') as f:
                    f.write(image)

            # Get ground truth text (from original PDF text layer)
            text = item.get("text", item.get("ground_truth", item.get("ocr_text", "")))
            if text:
                gt_path = ground_truth_dir / f"{filename}.txt"
                gt_path.write_text(text, encoding="utf-8")

            # Save metadata
            metadata = {
                "arxiv_id": arxiv_id,
                "page_num": page_num,
                "has_ground_truth": bool(text),
                "source": "scanned-arxiv-papers",
            }
            # Include any additional metadata from the dataset
            for key in ["title", "authors", "abstract", "categories"]:
                if key in item:
                    metadata[key] = item[key]

            metadata_path = metadata_dir / f"{filename}.json"
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            processed += 1
            if processed % 10 == 0:
                print(f"  Processed {processed} papers...")

        except Exception as e:
            print(f"  ⚠ Error processing item {idx}: {e}")
            continue

    print(f"✓ Downloaded {processed} paper images to {temp_dir}")
    return temp_dir


def ingest_scanned_arxiv_samples(
    corpus: Corpus, dataset_dir: Path, sample_count: int
) -> Dict[str, int]:
    """
    Ingest Scanned ArXiv samples into corpus.

    :param corpus: Target corpus.
    :type corpus: Corpus
    :param dataset_dir: Path to processed dataset.
    :type dataset_dir: Path
    :param sample_count: Number of samples to ingest.
    :type sample_count: int
    :return: Ingestion statistics.
    :rtype: dict
    """
    images_dir = dataset_dir / "images"
    ground_truth_dir = dataset_dir / "ground_truth"
    metadata_dir = dataset_dir / "metadata"

    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    # Get list of image files
    image_files = sorted(list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg")))[:sample_count]

    print(f"\nIngesting {len(image_files)} Scanned ArXiv samples...")

    ingested = 0
    failed = 0
    ground_truths_count = 0

    for image_file in image_files:
        try:
            stem = image_file.stem

            # Get ground truth
            gt_file = ground_truth_dir / f"{stem}.txt"
            ground_truth = None
            if gt_file.exists():
                ground_truth = gt_file.read_text(encoding="utf-8").strip()
                if ground_truth:
                    ground_truths_count += 1

            # Get metadata
            metadata_file = metadata_dir / f"{stem}.json"
            metadata = {}
            if metadata_file.exists():
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

            # Determine tags
            tags = ["scanned-arxiv", "academic", "multi-column", "ground-truth"]
            if metadata.get("categories"):
                # Add arxiv category as tag
                categories = metadata["categories"]
                if isinstance(categories, str):
                    tags.append(categories.split()[0].lower())

            # Ingest image into corpus
            result = corpus.ingest_source(image_file, tags=tags)

            # Store ground truth
            if ground_truth:
                gt_out_dir = corpus.root / ".biblicus" / "scanned_arxiv_ground_truth"
                gt_out_dir.mkdir(parents=True, exist_ok=True)
                gt_out_file = gt_out_dir / f"{result.item_id}.txt"
                gt_out_file.write_text(ground_truth, encoding="utf-8")

            # Store metadata
            if metadata:
                meta_out_dir = corpus.root / ".biblicus" / "scanned_arxiv_metadata"
                meta_out_dir.mkdir(parents=True, exist_ok=True)
                meta_out_file = meta_out_dir / f"{result.item_id}.json"
                meta_out_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            ingested += 1
            arxiv_id = metadata.get("arxiv_id", stem)
            print(f"  ✓ {arxiv_id} → {result.item_id}")

        except Exception as e:
            print(f"  ✗ Failed to ingest {image_file.name}: {e}")
            failed += 1

    return {
        "ingested": ingested,
        "failed": failed,
        "ground_truths": ground_truths_count,
    }


def download_scanned_arxiv_samples(
    *,
    corpus_path: Path,
    sample_count: int,
    force: bool,
    split: str = "train",
) -> Dict[str, int]:
    """
    Download Scanned ArXiv dataset and ingest samples into corpus.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param sample_count: Number of samples to ingest.
    :type sample_count: int
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param split: Dataset split to use.
    :type split: str
    :return: Download and ingestion statistics.
    :rtype: dict
    """
    corpus = _prepare_corpus(corpus_path, force=force)

    # Use temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Download from HuggingFace
        dataset_dir = download_scanned_arxiv_from_huggingface(temp_path, sample_count, split)

        # Ingest samples
        stats = ingest_scanned_arxiv_samples(corpus, dataset_dir, sample_count)

    corpus.reindex()
    return stats


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Download Scanned ArXiv papers for multi-column layout OCR testing."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--count",
        type=int,
        default=SCANNED_ARXIV_SAMPLE_COUNT,
        help=f"Number of samples to ingest (default: {SCANNED_ARXIV_SAMPLE_COUNT})",
    )
    parser.add_argument(
        "--split",
        default="train",
        help="Dataset split to use (default: train)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    return parser


def main() -> int:
    """
    Entry point for the Scanned ArXiv download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 70)
    print("SCANNED ARXIV DATASET DOWNLOAD")
    print("=" * 70)
    print()
    print("Dataset: Scanned ArXiv Papers (rendered as images)")
    print("Source: HuggingFace IAMJB/scanned-arxiv-papers")
    print("Purpose: Multi-column layout and reading order testing")
    print()

    stats = download_scanned_arxiv_samples(
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
    print("Ground truth text stored in:")
    print(f"  {Path(args.corpus).resolve() / '.biblicus' / 'scanned_arxiv_ground_truth'}")
    print("Paper metadata stored in:")
    print(f"  {Path(args.corpus).resolve() / '.biblicus' / 'scanned_arxiv_metadata'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
