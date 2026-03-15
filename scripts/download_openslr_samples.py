#!/usr/bin/env python3
"""
Download and ingest audio samples from OpenSLR datasets for STT benchmarking.

OpenSLR (Open Speech and Language Resources) hosts many free speech datasets.
This script provides a flexible interface to download various OpenSLR datasets.

Available datasets:
- SLR12: LibriSpeech ASR corpus
- SLR32: Large Russian read speech corpus (Tatoeba-Rus)
- SLR35: Large German read speech corpus (Tatoeba-Deu)
- SLR52: Tamil read speech corpus
- SLR63: Mandarin read speech corpus (THCHS-30)
- SLR69: Korean read speech corpus (KsponSpeech)

Usage:
    # Download LibriSpeech test-other (more challenging than test-clean)
    python scripts/download_openslr_samples.py \
        --corpus corpora/librispeech_test_other \
        --dataset SLR12 \
        --subset test-other \
        --count 100

    # Download Russian samples
    python scripts/download_openslr_samples.py \
        --corpus corpora/russian_benchmark \
        --dataset SLR32 \
        --count 50
"""

import argparse
import sys
from pathlib import Path
import tarfile
from typing import List, Tuple, Optional
import urllib.request
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus

# OpenSLR dataset configurations
OPENSLR_DATASETS = {
    "SLR12": {
        "name": "LibriSpeech",
        "language": "en",
        "base_url": "https://www.openslr.org/resources/12",
        "subsets": {
            "test-clean": "test-clean.tar.gz",
            "test-other": "test-other.tar.gz",
            "dev-clean": "dev-clean.tar.gz",
            "dev-other": "dev-other.tar.gz",
        }
    },
    "SLR32": {
        "name": "Russian Tatoeba",
        "language": "ru",
        "base_url": "https://www.openslr.org/resources/32",
        "file": "ru_ru.tar.gz"
    },
    "SLR35": {
        "name": "German Tatoeba",
        "language": "de",
        "base_url": "https://www.openslr.org/resources/35",
        "file": "de.tar.gz"
    },
    "SLR52": {
        "name": "Tamil Read Speech",
        "language": "ta",
        "base_url": "https://www.openslr.org/resources/52",
        "file": "ta.tar.gz"
    },
    "SLR63": {
        "name": "THCHS-30 Mandarin",
        "language": "zh",
        "base_url": "https://www.openslr.org/resources/63",
        "file": "data_thchs30.tgz"
    }
}


def download_openslr_dataset(
    dataset_id: str,
    subset: Optional[str],
    download_dir: Path
) -> Path:
    """
    Download OpenSLR dataset.

    :param dataset_id: Dataset ID (e.g., 'SLR12', 'SLR32').
    :type dataset_id: str
    :param subset: Subset name (for multi-subset datasets like LibriSpeech).
    :type subset: Optional[str]
    :param download_dir: Directory to download dataset to.
    :type download_dir: Path
    :return: Path to extracted dataset directory.
    :rtype: Path
    """
    if dataset_id not in OPENSLR_DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_id}")

    dataset_config = OPENSLR_DATASETS[dataset_id]
    download_dir.mkdir(parents=True, exist_ok=True)

    # Determine file to download
    if "subsets" in dataset_config:
        if not subset or subset not in dataset_config["subsets"]:
            raise ValueError(
                f"Subset required for {dataset_id}. "
                f"Available: {list(dataset_config['subsets'].keys())}"
            )
        filename = dataset_config["subsets"][subset]
    else:
        filename = dataset_config["file"]

    url = f"{dataset_config['base_url']}/{filename}"
    tar_file = download_dir / filename
    extract_base = download_dir

    if tar_file.exists() and not tar_file.stat().st_size == 0:
        print(f"Archive already exists: {tar_file}")
    else:
        print(f"Downloading {dataset_config['name']} from {url}...")

        try:
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('content-length', 0))

                with tar_file.open('wb') as f:
                    downloaded = 0
                    chunk_size = 8192

                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            pct = (downloaded / total_size) * 100
                            mb = downloaded // (1024 ** 2)
                            total_mb = total_size // (1024 ** 2)
                            print(f"\r  Progress: {pct:.1f}% ({mb}/{total_mb} MB)", end='')

            print("\n✓ Download complete")

        except Exception as e:
            print(f"\n✗ Download failed: {e}")
            if tar_file.exists():
                tar_file.unlink()
            raise

    # Extract
    print(f"Extracting {tar_file}...")
    with tarfile.open(tar_file, "r:gz") as tar:
        tar.extractall(extract_base)

    print(f"✓ Extracted to {extract_base}")

    # Find extracted directory
    # Most OpenSLR datasets extract to a known subdirectory
    if dataset_id == "SLR12":
        extracted_dir = extract_base / "LibriSpeech" / subset
    else:
        # Look for the first directory created
        possible_dirs = [d for d in extract_base.iterdir() if d.is_dir()]
        extracted_dir = possible_dirs[0] if possible_dirs else extract_base

    return extracted_dir


def collect_librispeech_samples(
    dataset_dir: Path,
    sample_count: int
) -> List[Tuple[Path, str]]:
    """
    Collect LibriSpeech audio samples and transcriptions.

    LibriSpeech structure:
    LibriSpeech/
      test-clean/
        <speaker_id>/
          <chapter_id>/
            *.flac
            <speaker_id>-<chapter_id>.trans.txt

    :param dataset_dir: Path to LibriSpeech test-clean directory.
    :type dataset_dir: Path
    :param sample_count: Number of samples to collect.
    :type sample_count: int
    :return: List of (audio_path, transcription) tuples.
    :rtype: list[tuple[Path, str]]
    """
    samples = []

    for speaker_dir in sorted(dataset_dir.iterdir()):
        if not speaker_dir.is_dir():
            continue

        for chapter_dir in sorted(speaker_dir.iterdir()):
            if not chapter_dir.is_dir():
                continue

            # Find transcript file
            trans_file = next(chapter_dir.glob("*.trans.txt"), None)
            if not trans_file:
                continue

            # Parse transcripts
            transcripts = {}
            with trans_file.open('r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2:
                        file_id, text = parts
                        transcripts[file_id] = text

            # Collect audio files
            for flac_file in sorted(chapter_dir.glob("*.flac")):
                file_id = flac_file.stem

                if file_id in transcripts:
                    samples.append((flac_file, transcripts[file_id]))

                    if len(samples) >= sample_count:
                        return samples

    return samples


def ingest_samples(
    corpus: Corpus,
    samples: List[Tuple[Path, str]],
    dataset_name: str,
    language: str
) -> dict:
    """
    Ingest audio samples into corpus.

    :param corpus: Corpus instance.
    :type corpus: Corpus
    :param samples: List of (audio_path, transcription) tuples.
    :type samples: list[tuple[Path, str]]
    :param dataset_name: Name of dataset for tagging.
    :type dataset_name: str
    :param language: Language code for tagging.
    :type language: str
    :return: Ingestion statistics.
    :rtype: dict
    """
    print(f"\nIngesting {len(samples)} samples from {dataset_name}...")

    ingested = 0
    failed = 0
    ground_truth_dir = corpus.root / "metadata" / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    for audio_file, transcription in samples:
        try:
            # Read audio data
            audio_data = audio_file.read_bytes()

            # Detect media type
            suffix = audio_file.suffix.lower()
            media_types = {
                '.flac': 'audio/flac',
                '.wav': 'audio/wav',
                '.mp3': 'audio/mp3',
                '.ogg': 'audio/ogg',
            }
            media_type = media_types.get(suffix, 'audio/wav')

            # Ingest audio into corpus
            result = corpus.ingest_item(
                data=audio_data,
                media_type=media_type,
                source_uri=f"file://{audio_file}",
                tags=[dataset_name.lower(), language, "speech", "ground-truth"]
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
        description="Download and ingest OpenSLR dataset samples for STT benchmarking"
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        required=True,
        help="Path to corpus directory"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=list(OPENSLR_DATASETS.keys()),
        help="OpenSLR dataset ID (SLR12, SLR32, etc.)"
    )
    parser.add_argument(
        "--subset",
        type=str,
        help="Dataset subset (for multi-subset datasets)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of samples to ingest"
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("/tmp/openslr"),
        help="Directory to download dataset to"
    )

    args = parser.parse_args()

    dataset_config = OPENSLR_DATASETS[args.dataset]

    print("=" * 80)
    print(f"OPENSLR DATASET DOWNLOAD: {dataset_config['name']}")
    print("=" * 80)
    print(f"Dataset: {args.dataset}")
    print(f"Language: {dataset_config['language']}")
    if args.subset:
        print(f"Subset: {args.subset}")
    print(f"Sample count: {args.count}")
    print(f"Corpus: {args.corpus}")
    print(f"Download directory: {args.download_dir}")
    print("=" * 80)

    # Download dataset
    dataset_dir = download_openslr_dataset(
        dataset_id=args.dataset,
        subset=args.subset,
        download_dir=args.download_dir
    )

    # Collect samples (currently only supports LibriSpeech format)
    if args.dataset == "SLR12":
        samples = collect_librispeech_samples(
            dataset_dir=dataset_dir,
            sample_count=args.count
        )
    else:
        print("\n✗ Sample collection not yet implemented for this dataset")
        print("   Dataset downloaded but ingestion requires manual implementation")
        sys.exit(1)

    if not samples:
        print("✗ No samples collected")
        sys.exit(1)

    # Initialize corpus
    corpus = Corpus(args.corpus)

    # Ingest samples
    stats = ingest_samples(
        corpus=corpus,
        samples=samples,
        dataset_name=dataset_config["name"],
        language=dataset_config["language"]
    )

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
