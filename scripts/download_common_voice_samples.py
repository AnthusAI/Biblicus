#!/usr/bin/env python3
"""
Download and ingest Mozilla Common Voice dataset samples for STT benchmarking.

Common Voice is a crowd-sourced multilingual speech dataset with diverse speakers
and accents. This script downloads a subset for benchmarking purposes.

Usage:
    python scripts/download_common_voice_samples.py \\
        --corpus corpora/common_voice_benchmark \\
        --language en \\
        --count 100

    # Download specific version
    python scripts/download_common_voice_samples.py \\
        --corpus corpora/common_voice_benchmark \\
        --language en \\
        --version 11.0 \\
        --count 100
"""

import argparse
import sys
from pathlib import Path
import tarfile
import csv
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus


def download_common_voice(
    language: str,
    version: str,
    download_dir: Path
) -> Path:
    """
    Download Common Voice dataset for specified language.

    :param language: Language code (e.g., 'en', 'es', 'fr').
    :type language: str
    :param version: Dataset version (e.g., '11.0', '12.0').
    :type version: str
    :param download_dir: Directory to download dataset to.
    :type download_dir: Path
    :return: Path to extracted dataset directory.
    :rtype: Path
    """
    import urllib.request
    import shutil

    download_dir.mkdir(parents=True, exist_ok=True)

    # Common Voice download URL pattern
    # Note: Common Voice requires accepting terms at https://commonvoice.mozilla.org/
    # Direct downloads are available but require authentication token
    # For now, we'll provide instructions for manual download

    dataset_name = f"cv-corpus-{version}-{language}"
    tar_file = download_dir / f"{dataset_name}.tar.gz"
    extracted_dir = download_dir / dataset_name

    if extracted_dir.exists():
        print(f"Dataset already extracted at {extracted_dir}")
        return extracted_dir

    if not tar_file.exists():
        print("=" * 80)
        print("COMMON VOICE DOWNLOAD INSTRUCTIONS")
        print("=" * 80)
        print(f"1. Visit https://commonvoice.mozilla.org/datasets")
        print(f"2. Accept the terms and conditions")
        print(f"3. Download the dataset for language: {language}")
        print(f"4. Save it to: {tar_file}")
        print(f"5. Re-run this script")
        print("=" * 80)
        sys.exit(1)

    print(f"Extracting {tar_file}...")
    with tarfile.open(tar_file, "r:gz") as tar:
        tar.extractall(download_dir)

    print(f"Extracted to {extracted_dir}")
    return extracted_dir


def collect_audio_samples(
    dataset_dir: Path,
    sample_count: int,
    split: str = "test"
) -> List[Tuple[Path, str]]:
    """
    Collect audio samples and their transcriptions from Common Voice dataset.

    :param dataset_dir: Path to extracted Common Voice dataset.
    :type dataset_dir: Path
    :param sample_count: Number of samples to collect.
    :type sample_count: int
    :param split: Dataset split to use (train, dev, test).
    :type split: str
    :return: List of (audio_path, transcription) tuples.
    :rtype: list[tuple[Path, str]]
    """
    # Common Voice structure:
    # cv-corpus-{version}-{language}/
    #   {language}/
    #     clips/
    #       *.mp3
    #     test.tsv (or dev.tsv, train.tsv)

    language_dir = next(dataset_dir.glob("*/"))  # Get language subdirectory
    clips_dir = language_dir / "clips"
    tsv_file = language_dir / f"{split}.tsv"

    if not tsv_file.exists():
        raise FileNotFoundError(
            f"TSV file not found: {tsv_file}. "
            f"Available splits: {[f.stem for f in language_dir.glob('*.tsv')]}"
        )

    print(f"Reading samples from {tsv_file}...")

    samples = []
    with tsv_file.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            # Common Voice TSV columns: client_id, path, sentence, up_votes, down_votes, etc.
            audio_filename = row['path']
            transcription = row['sentence']

            audio_path = clips_dir / audio_filename

            if not audio_path.exists():
                continue

            samples.append((audio_path, transcription))

            if len(samples) >= sample_count:
                break

    print(f"Collected {len(samples)} samples")
    return samples


def ingest_samples(
    corpus: Corpus,
    samples: List[Tuple[Path, str]]
) -> dict:
    """
    Ingest Common Voice samples into corpus.

    :param corpus: Corpus instance.
    :type corpus: Corpus
    :param samples: List of (audio_path, transcription) tuples.
    :type samples: list[tuple[Path, str]]
    :return: Ingestion statistics.
    :rtype: dict
    """
    print(f"\nIngesting {len(samples)} Common Voice samples...")

    ingested = 0
    failed = 0
    ground_truth_dir = corpus.root / "metadata" / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    for audio_file, transcription in samples:
        try:
            # Read audio data
            audio_data = audio_file.read_bytes()

            # Ingest audio into corpus with source URI to avoid deduplication
            result = corpus.ingest_item(
                data=audio_data,
                media_type="audio/mp3",
                source_uri=f"file://{audio_file}",
                tags=["common-voice", "test", "speech", "ground-truth"]
            )

            # Store ground truth transcription
            gt_file = ground_truth_dir / f"{result.id}.txt"
            gt_file.write_text(transcription, encoding="utf-8")

            ingested += 1
            if ingested % 10 == 0:
                print(f"  Ingested {ingested}/{len(samples)}...")

        except Exception as e:
            print(f"  Failed to ingest {audio_file.name}: {e}")
            failed += 1

    print(f"\n✓ Ingestion complete: {ingested} succeeded, {failed} failed")
    return {"ingested": ingested, "failed": failed}


def main():
    parser = argparse.ArgumentParser(
        description="Download and ingest Mozilla Common Voice samples for STT benchmarking"
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        required=True,
        help="Path to corpus directory"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code (en, es, fr, etc.)"
    )
    parser.add_argument(
        "--version",
        type=str,
        default="11.0",
        help="Common Voice version (11.0, 12.0, etc.)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of samples to ingest"
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        choices=["train", "dev", "test"],
        help="Dataset split to use"
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("/tmp/common_voice"),
        help="Directory to download dataset to"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("COMMON VOICE DATASET DOWNLOAD AND INGESTION")
    print("=" * 80)
    print(f"Language: {args.language}")
    print(f"Version: {args.version}")
    print(f"Split: {args.split}")
    print(f"Sample count: {args.count}")
    print(f"Corpus: {args.corpus}")
    print(f"Download directory: {args.download_dir}")
    print("=" * 80)

    # Download dataset
    dataset_dir = download_common_voice(
        language=args.language,
        version=args.version,
        download_dir=args.download_dir
    )

    # Collect samples
    samples = collect_audio_samples(
        dataset_dir=dataset_dir,
        sample_count=args.count,
        split=args.split
    )

    # Initialize corpus
    corpus = Corpus(args.corpus)

    # Ingest samples
    stats = ingest_samples(corpus=corpus, samples=samples)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total samples: {len(samples)}")
    print(f"Ingested: {stats['ingested']}")
    print(f"Failed: {stats['failed']}")
    print(f"Ground truth directory: {corpus.root / 'metadata' / 'ground_truth'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
