#!/usr/bin/env python3
"""
Download and ingest FLEURS dataset samples for STT benchmarking.

FLEURS (Few-shot Learning Evaluation of Universal Representations of Speech)
is a multilingual dataset from Google covering 102 languages with parallel audio.

Direct download from Hugging Face datasets without requiring the datasets library.

Usage:
    python scripts/download_fleurs_samples.py \
        --corpus corpora/fleurs_benchmark \
        --language en_us \
        --count 100
"""

import argparse
import sys
from pathlib import Path
import json
import tarfile
from typing import List, Tuple
import urllib.request
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus


def download_fleurs_split(
    language: str,
    split: str,
    download_dir: Path
) -> Path:
    """
    Download FLEURS dataset for specified language and split.

    FLEURS is available at: https://huggingface.co/datasets/google/fleurs

    :param language: Language code (e.g., 'en_us', 'es_419', 'fr_fr').
    :type language: str
    :param split: Dataset split (train, validation, test).
    :type split: str
    :param download_dir: Directory to download dataset to.
    :type download_dir: Path
    :return: Path to extracted dataset directory.
    :rtype: Path
    """
    download_dir.mkdir(parents=True, exist_ok=True)

    # FLEURS dataset structure on HuggingFace
    # Manual download required or use datasets library
    print("=" * 80)
    print("FLEURS DATASET DOWNLOAD")
    print("=" * 80)
    print(f"FLEURS requires the Hugging Face 'datasets' library.")
    print(f"")
    print(f"Install it with:")
    print(f"  pip3 install --user datasets")
    print(f"")
    print(f"Then this script can automatically download {language} {split} split.")
    print(f"")
    print(f"Alternatively, manually download from:")
    print(f"  https://huggingface.co/datasets/google/fleurs")
    print("=" * 80)

    # Try to use datasets library if available
    try:
        from datasets import load_dataset

        print(f"\nDownloading FLEURS {language} {split} split...")
        dataset = load_dataset("google/fleurs", language, split=split, cache_dir=str(download_dir))

        dataset_path = download_dir / f"fleurs_{language}_{split}"
        dataset_path.mkdir(parents=True, exist_ok=True)

        # Save dataset to disk
        dataset.save_to_disk(str(dataset_path))

        print(f"✓ Downloaded to {dataset_path}")
        return dataset_path

    except ImportError:
        print("\n✗ datasets library not found")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        sys.exit(1)


def collect_audio_samples(
    dataset_path: Path,
    sample_count: int
) -> List[Tuple[bytes, str, int]]:
    """
    Collect audio samples from FLEURS dataset.

    :param dataset_path: Path to FLEURS dataset.
    :type dataset_path: Path
    :param sample_count: Number of samples to collect.
    :type sample_count: int
    :return: List of (audio_data, transcription, sample_rate) tuples.
    :rtype: list[tuple[bytes, str, int]]
    """
    try:
        from datasets import load_from_disk
    except ImportError:
        print("✗ datasets library required")
        sys.exit(1)

    print(f"\nLoading samples from {dataset_path}...")
    dataset = load_from_disk(str(dataset_path))

    samples = []
    for i, item in enumerate(dataset):
        if i >= sample_count:
            break

        # FLEURS structure:
        # - audio: dict with 'array', 'path', 'sampling_rate'
        # - transcription: str
        # - raw_transcription: str
        # - gender: int
        # - lang_id: int
        # - language: str
        # - lang_group_id: int

        audio_array = item['audio']['array']
        sample_rate = item['audio']['sampling_rate']
        transcription = item['transcription']

        # Convert audio array to WAV bytes
        import numpy as np
        import io
        import wave

        # Normalize to int16
        audio_int16 = (audio_array * 32767).astype(np.int16)

        # Write to WAV in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        audio_data = wav_buffer.getvalue()

        samples.append((audio_data, transcription, sample_rate))

        if (i + 1) % 10 == 0:
            print(f"  Collected {i + 1} samples...")

    print(f"✓ Collected {len(samples)} samples")
    return samples


def ingest_samples(
    corpus: Corpus,
    samples: List[Tuple[bytes, str, int]],
    language: str
) -> dict:
    """
    Ingest FLEURS samples into corpus.

    :param corpus: Corpus instance.
    :type corpus: Corpus
    :param samples: List of (audio_data, transcription, sample_rate) tuples.
    :type samples: list[tuple[bytes, str, int]]
    :param language: Language code for tagging.
    :type language: str
    :return: Ingestion statistics.
    :rtype: dict
    """
    print(f"\nIngesting {len(samples)} FLEURS samples...")

    ingested = 0
    failed = 0
    ground_truth_dir = corpus.root / "metadata" / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    for i, (audio_data, transcription, sample_rate) in enumerate(samples):
        try:
            # Ingest audio into corpus
            result = corpus.ingest_item(
                data=audio_data,
                media_type="audio/wav",
                source_uri=f"fleurs://{language}/{i}",
                tags=["fleurs", language, "speech", "ground-truth"]
            )

            # Store ground truth transcription
            gt_file = ground_truth_dir / f"{result.id}.txt"
            gt_file.write_text(transcription, encoding="utf-8")

            ingested += 1
            if ingested % 10 == 0:
                print(f"  Ingested {ingested}/{len(samples)}...")

        except Exception as e:
            print(f"  Failed to ingest sample {i}: {e}")
            failed += 1

    print(f"\n✓ Ingestion complete: {ingested} succeeded, {failed} failed")
    return {"ingested": ingested, "failed": failed}


def main():
    parser = argparse.ArgumentParser(
        description="Download and ingest FLEURS samples for STT benchmarking"
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
        default="en_us",
        help="Language code (en_us, es_419, fr_fr, etc.)"
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
        choices=["train", "validation", "test"],
        help="Dataset split to use"
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("/tmp/fleurs"),
        help="Directory to download dataset to"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("FLEURS DATASET DOWNLOAD AND INGESTION")
    print("=" * 80)
    print(f"Language: {args.language}")
    print(f"Split: {args.split}")
    print(f"Sample count: {args.count}")
    print(f"Corpus: {args.corpus}")
    print(f"Download directory: {args.download_dir}")
    print("=" * 80)

    # Check for numpy
    try:
        import numpy
    except ImportError:
        print("✗ Error: numpy is required")
        print("  Install it with: pip3 install --user numpy")
        sys.exit(1)

    # Download dataset
    dataset_path = download_fleurs_split(
        language=args.language,
        split=args.split,
        download_dir=args.download_dir
    )

    # Collect samples
    samples = collect_audio_samples(
        dataset_path=dataset_path,
        sample_count=args.count
    )

    # Initialize corpus
    corpus = Corpus(args.corpus)

    # Ingest samples
    stats = ingest_samples(corpus=corpus, samples=samples, language=args.language)

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
