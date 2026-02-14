#!/usr/bin/env python3
"""
Download and ingest CMU AN4 dataset samples for STT benchmarking.

AN4 is a small, clean speech corpus from Carnegie Mellon University.
Good for quick testing and development.

Usage:
    python scripts/download_an4_samples.py \\
        --corpus corpora/an4_benchmark
"""

import argparse
import sys
from pathlib import Path
import tarfile
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus


def download_an4(download_dir: Path) -> Path:
    """
    Download CMU AN4 dataset.

    :param download_dir: Directory to download dataset to.
    :type download_dir: Path
    :return: Path to extracted dataset directory.
    :rtype: Path
    """
    import urllib.request

    download_dir.mkdir(parents=True, exist_ok=True)

    # AN4 dataset URL
    url = "http://www.speech.cs.cmu.edu/databases/an4/an4_raw.bigendian.tar.gz"
    tar_file = download_dir / "an4_raw.bigendian.tar.gz"
    extracted_dir = download_dir / "an4"

    if extracted_dir.exists():
        print(f"Dataset already extracted at {extracted_dir}")
        return extracted_dir

    if not tar_file.exists():
        print(f"Downloading AN4 from {url}...")
        print("(Dataset size: ~90 MB)")

        try:
            urllib.request.urlretrieve(url, tar_file)
            print("✓ Download complete")
        except Exception as e:
            print(f"✗ Download failed: {e}")
            if tar_file.exists():
                tar_file.unlink()
            raise

    print(f"Extracting {tar_file}...")
    with tarfile.open(tar_file, "r:gz") as tar:
        tar.extractall(download_dir)

    print(f"✓ Extracted to {extracted_dir}")
    return extracted_dir


def parse_transcription_file(trans_file: Path) -> dict:
    """
    Parse AN4 transcription file.

    Format: <transcription> (<filename>)

    :param trans_file: Path to transcription file.
    :type trans_file: Path
    :return: Dictionary mapping filenames to transcriptions.
    :rtype: dict[str, str]
    """
    transcriptions = {}

    with trans_file.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'):
                continue

            # Format: TRANSCRIPTION (filename)
            if '(' in line and line.endswith(')'):
                transcript_part, file_part = line.rsplit('(', 1)
                transcript = transcript_part.strip()
                filename = file_part.rstrip(')').strip()

                transcriptions[filename] = transcript

    return transcriptions


def collect_audio_samples(dataset_dir: Path) -> List[Tuple[Path, str]]:
    """
    Collect audio samples and their transcriptions from AN4 dataset.

    :param dataset_dir: Path to extracted AN4 dataset.
    :type dataset_dir: Path
    :return: List of (audio_path, transcription) tuples.
    :rtype: list[tuple[Path, str]]
    """
    # AN4 structure:
    # an4/
    #   wav/
    #     an4test_clstk/
    #       *.wav
    #     an4train_clstk/
    #       *.wav
    #   etc/
    #     an4_test.transcription
    #     an4_train.transcription

    print(f"Reading samples from {dataset_dir}...")

    # Use test set
    test_wav_dir = dataset_dir / "wav" / "an4test_clstk"
    test_trans_file = dataset_dir / "etc" / "an4_test.transcription"

    if not test_wav_dir.exists() or not test_trans_file.exists():
        raise FileNotFoundError(
            f"AN4 test data not found. Expected:\n"
            f"  - {test_wav_dir}\n"
            f"  - {test_trans_file}"
        )

    transcriptions = parse_transcription_file(test_trans_file)

    samples = []
    for audio_file in test_wav_dir.glob("*.wav"):
        file_id = audio_file.stem

        if file_id in transcriptions:
            samples.append((audio_file, transcriptions[file_id]))

    print(f"✓ Collected {len(samples)} samples")
    return samples


def ingest_samples(
    corpus: Corpus,
    samples: List[Tuple[Path, str]]
) -> dict:
    """
    Ingest AN4 samples into corpus.

    :param corpus: Corpus instance.
    :type corpus: Corpus
    :param samples: List of (audio_path, transcription) tuples.
    :type samples: list[tuple[Path, str]]
    :return: Ingestion statistics.
    :rtype: dict
    """
    print(f"\nIngesting {len(samples)} AN4 samples...")

    ingested = 0
    failed = 0
    ground_truth_dir = corpus.root / "metadata" / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    for audio_file, transcription in samples:
        try:
            # Read audio data
            audio_data = audio_file.read_bytes()

            # Ingest audio into corpus
            result = corpus.ingest_item(
                data=audio_data,
                media_type="audio/wav",
                source_uri=f"file://{audio_file}",
                tags=["an4", "cmu", "test", "speech", "ground-truth"]
            )

            # Store ground truth transcription
            gt_file = ground_truth_dir / f"{result.id}.txt"
            gt_file.write_text(transcription, encoding="utf-8")

            ingested += 1
            if ingested % 20 == 0:
                print(f"  Ingested {ingested}/{len(samples)}...")

        except Exception as e:
            print(f"  Failed to ingest {audio_file.name}: {e}")
            failed += 1

    print(f"\n✓ Ingestion complete: {ingested} succeeded, {failed} failed")
    return {"ingested": ingested, "failed": failed}


def main():
    parser = argparse.ArgumentParser(
        description="Download and ingest CMU AN4 samples for STT benchmarking"
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        required=True,
        help="Path to corpus directory"
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("/tmp/an4"),
        help="Directory to download dataset to"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("CMU AN4 DATASET DOWNLOAD AND INGESTION")
    print("=" * 80)
    print(f"Corpus: {args.corpus}")
    print(f"Download directory: {args.download_dir}")
    print("=" * 80)

    # Download dataset
    dataset_dir = download_an4(download_dir=args.download_dir)

    # Collect samples
    samples = collect_audio_samples(dataset_dir=dataset_dir)

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
