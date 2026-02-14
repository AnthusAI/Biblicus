"""
Download LibriSpeech test-clean dataset samples for STT testing.

LibriSpeech is a corpus of approximately 1000 hours of 16kHz read English speech,
derived from read audiobooks from the LibriVox project. The test-clean subset
contains 5.4 hours of high-quality audio with ground truth transcriptions.

Dataset: https://www.openslr.org/12
Paper: Panayotov et al., "Librispeech: An ASR corpus based on public domain audio books" (ICASSP 2015)
"""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Dict
from urllib.request import urlretrieve

from biblicus.corpus import Corpus

# LibriSpeech dataset configuration
LIBRISPEECH_TEST_CLEAN_URL = "https://www.openslr.org/resources/12/test-clean.tar.gz"
LIBRISPEECH_SAMPLE_COUNT = 20  # Number of audio files to ingest for testing


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for LibriSpeech sample downloads.

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


def download_librispeech_dataset(temp_dir: Path) -> Path:
    """
    Download and extract LibriSpeech test-clean dataset.

    :param temp_dir: Temporary directory for download.
    :type temp_dir: Path
    :return: Path to extracted dataset directory.
    :rtype: Path
    """
    print(f"Downloading LibriSpeech test-clean from {LIBRISPEECH_TEST_CLEAN_URL}...")
    tar_path = temp_dir / "test-clean.tar.gz"

    urlretrieve(LIBRISPEECH_TEST_CLEAN_URL, tar_path)
    print(f"✓ Downloaded {tar_path.stat().st_size:,} bytes (~346 MB)")

    print("Extracting dataset (this may take a minute)...")
    with tarfile.open(tar_path, "r:gz") as tar_ref:
        tar_ref.extractall(temp_dir)

    # LibriSpeech extracts to LibriSpeech/test-clean/
    extracted_dir = temp_dir / "LibriSpeech" / "test-clean"

    if not extracted_dir.exists():
        raise FileNotFoundError(f"Could not find extracted dataset at {extracted_dir}")

    print(f"✓ Extracted to {extracted_dir}")
    return extracted_dir


def parse_trans_file(trans_file: Path) -> Dict[str, str]:
    """
    Parse LibriSpeech .trans.txt file containing transcriptions.

    Format: <utterance-id> <transcription text>

    :param trans_file: Path to .trans.txt file.
    :type trans_file: Path
    :return: Dictionary mapping utterance IDs to transcriptions.
    :rtype: dict
    """
    transcriptions = {}

    with open(trans_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Split on first space: utterance-id followed by transcription
            parts = line.split(" ", 1)
            if len(parts) == 2:
                utterance_id, transcription = parts
                transcriptions[utterance_id] = transcription.strip()

    return transcriptions


def collect_audio_files(dataset_dir: Path, sample_count: int) -> list[tuple[Path, str]]:
    """
    Collect audio files and their transcriptions from LibriSpeech dataset.

    LibriSpeech structure: test-clean/<speaker-id>/<chapter-id>/<utterance-id>.flac
    Transcriptions: test-clean/<speaker-id>/<chapter-id>/<speaker-id>-<chapter-id>.trans.txt

    :param dataset_dir: Path to extracted dataset (test-clean/).
    :type dataset_dir: Path
    :param sample_count: Maximum number of samples to collect.
    :type sample_count: int
    :return: List of (audio_file, transcription) tuples.
    :rtype: list
    """
    samples = []

    # Find all .trans.txt files
    trans_files = sorted(dataset_dir.glob("*/*/*.trans.txt"))

    for trans_file in trans_files:
        if len(samples) >= sample_count:
            break

        # Parse transcriptions from this file
        transcriptions = parse_trans_file(trans_file)

        # Get corresponding audio directory
        audio_dir = trans_file.parent

        # Match audio files to transcriptions
        for utterance_id, transcription in transcriptions.items():
            if len(samples) >= sample_count:
                break

            audio_file = audio_dir / f"{utterance_id}.flac"
            if audio_file.exists():
                samples.append((audio_file, transcription))

    return samples


def ingest_librispeech_samples(
    corpus: Corpus, dataset_dir: Path, sample_count: int
) -> Dict[str, int]:
    """
    Ingest LibriSpeech samples into corpus.

    :param corpus: Target corpus.
    :type corpus: Corpus
    :param dataset_dir: Path to extracted LibriSpeech dataset.
    :type dataset_dir: Path
    :param sample_count: Number of samples to ingest.
    :type sample_count: int
    :return: Ingestion statistics.
    :rtype: dict
    """
    import shutil

    # Collect audio files and transcriptions
    samples = collect_audio_files(dataset_dir, sample_count)

    print(f"\nIngesting {len(samples)} LibriSpeech samples...")

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
                media_type="audio/flac",
                source_uri=f"file://{audio_file}",
                tags=["librispeech", "test-clean", "speech", "ground-truth"]
            )

            # Store ground truth transcription
            gt_file = ground_truth_dir / f"{result.item_id}.txt"
            gt_file.write_text(transcription, encoding="utf-8")

            ingested += 1
            print(f"  ✓ {audio_file.name} → {result.item_id}")

        except Exception as e:
            print(f"  ✗ Failed to ingest {audio_file.name}: {e}")
            failed += 1

    return {"ingested": ingested, "failed": failed, "ground_truths": ingested}


def download_librispeech_samples(
    *, corpus_path: Path, sample_count: int, force: bool
) -> Dict[str, int]:
    """
    Download LibriSpeech dataset and ingest samples into corpus.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param sample_count: Number of samples to ingest.
    :type sample_count: int
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :return: Download and ingestion statistics.
    :rtype: dict
    """
    corpus = _prepare_corpus(corpus_path, force=force)

    # Use temporary directory for download
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Download and extract dataset
        dataset_dir = download_librispeech_dataset(temp_path)

        # Ingest samples
        stats = ingest_librispeech_samples(corpus, dataset_dir, sample_count)

    corpus.reindex()
    return stats


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Download LibriSpeech test-clean dataset samples for STT testing."
    )
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument(
        "--count",
        type=int,
        default=LIBRISPEECH_SAMPLE_COUNT,
        help=f"Number of samples to ingest (default: {LIBRISPEECH_SAMPLE_COUNT})",
    )
    parser.add_argument(
        "--force", action="store_true", help="Initialize even if the directory is not empty."
    )
    return parser


def main() -> int:
    """
    Entry point for the LibriSpeech download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 70)
    print("LIBRISPEECH DATASET DOWNLOAD")
    print("=" * 70)
    print()
    print("Dataset: LibriSpeech ASR Corpus - test-clean subset")
    print("Source: https://www.openslr.org/12")
    print("Size: ~346 MB compressed, 5.4 hours of audio")
    print()

    stats = download_librispeech_samples(
        corpus_path=Path(args.corpus).resolve(),
        sample_count=args.count,
        force=bool(args.force),
    )

    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(json.dumps(stats, indent=2))
    print()
    print("Ground truth transcriptions stored in:")
    print(f"  {Path(args.corpus).resolve() / 'metadata' / 'ground_truth'}")
    print()
    print("You can now run STT benchmarks with:")
    print(f"  python scripts/benchmark_all_stt_providers.py \\")
    print(f"    --corpus {args.corpus} \\")
    print(f"    --output results/stt_benchmark.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
