#!/usr/bin/env python3
"""
Download and ingest TED-LIUM 3 dataset samples for STT benchmarking.

TED-LIUM contains TED talk presentations with spontaneous speech, technical
vocabulary, and natural disfluencies. Good for testing real-world performance.

Usage:
    python scripts/download_tedlium_samples.py \\
        --corpus corpora/tedlium_benchmark \\
        --count 100
"""

import argparse
import sys
from pathlib import Path
import tarfile
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus


def download_tedlium(download_dir: Path) -> Path:
    """
    Download TED-LIUM 3 dataset.

    :param download_dir: Directory to download dataset to.
    :type download_dir: Path
    :return: Path to extracted dataset directory.
    :rtype: Path
    """
    import urllib.request
    import shutil

    download_dir.mkdir(parents=True, exist_ok=True)

    # TED-LIUM 3 test set URL
    url = "https://www.openslr.org/resources/51/TEDLIUM_release-3.tgz"
    tar_file = download_dir / "TEDLIUM_release-3.tgz"
    extracted_dir = download_dir / "TEDLIUM_release-3"

    if extracted_dir.exists():
        print(f"Dataset already extracted at {extracted_dir}")
        return extracted_dir

    if not tar_file.exists():
        print(f"Downloading TED-LIUM 3 from {url}...")
        print("(This may take a while - ~20 GB)")

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
                            print(f"\r  Progress: {pct:.1f}% ({downloaded // (1024**2)} MB)", end='')

            print("\n✓ Download complete")

        except Exception as e:
            print(f"\n✗ Download failed: {e}")
            if tar_file.exists():
                tar_file.unlink()
            raise

    print(f"Extracting {tar_file}...")
    with tarfile.open(tar_file, "r:gz") as tar:
        tar.extractall(download_dir)

    print(f"✓ Extracted to {extracted_dir}")
    return extracted_dir


def parse_stm_file(stm_path: Path) -> List[Tuple[str, float, float, str]]:
    """
    Parse TED-LIUM STM transcription file.

    STM format: <filename> <channel> <speaker> <start_time> <end_time> <transcript>

    :param stm_path: Path to STM file.
    :type stm_path: Path
    :return: List of (filename, start, end, transcript) tuples.
    :rtype: list[tuple[str, float, float, str]]
    """
    segments = []

    with stm_path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';;'):
                continue

            parts = line.split(None, 6)
            if len(parts) < 7:
                continue

            filename = parts[0]
            start_time = float(parts[3])
            end_time = float(parts[4])
            transcript = parts[6]

            # Skip segments with <unk> or ignore markers
            if '<unk>' in transcript.lower() or 'ignore_time_segment' in transcript:
                continue

            segments.append((filename, start_time, end_time, transcript))

    return segments


def collect_audio_samples(
    dataset_dir: Path,
    sample_count: int
) -> List[Tuple[Path, str]]:
    """
    Collect audio samples and their transcriptions from TED-LIUM dataset.

    :param dataset_dir: Path to extracted TED-LIUM dataset.
    :type dataset_dir: Path
    :param sample_count: Number of samples to collect.
    :type sample_count: int
    :return: List of (audio_path, transcription) tuples.
    :rtype: list[tuple[Path, str]]
    """
    # TED-LIUM structure:
    # TEDLIUM_release-3/
    #   data/
    #     test/
    #       sph/
    #         *.sph (audio files)
    #       stm/
    #         *.stm (transcriptions)

    test_dir = dataset_dir / "data" / "test"
    sph_dir = test_dir / "sph"
    stm_dir = test_dir / "stm"

    if not sph_dir.exists() or not stm_dir.exists():
        # Try legacy structure
        test_dir = dataset_dir / "legacy" / "test"
        sph_dir = test_dir / "sph"
        stm_dir = test_dir / "stm"

    print(f"Reading samples from {stm_dir}...")

    samples = []
    stm_files = list(stm_dir.glob("*.stm"))

    for stm_file in stm_files:
        talk_id = stm_file.stem
        sph_file = sph_dir / f"{talk_id}.sph"

        if not sph_file.exists():
            continue

        # Parse STM file to get segments
        segments = parse_stm_file(stm_file)

        # For simplicity, concatenate all segments into full talk transcription
        # In production, you might want to segment the audio
        full_transcript = " ".join([seg[3] for seg in segments])

        samples.append((sph_file, full_transcript))

        if len(samples) >= sample_count:
            break

        if len(samples) % 10 == 0:
            print(f"  Collected {len(samples)} talks...")

    print(f"✓ Collected {len(samples)} samples")
    return samples


def convert_sph_to_flac(sph_path: Path, output_path: Path) -> None:
    """
    Convert SPH audio to FLAC format using sox.

    :param sph_path: Path to input SPH file.
    :type sph_path: Path
    :param output_path: Path to output FLAC file.
    :type output_path: Path
    """
    import subprocess

    subprocess.run(
        ["sox", str(sph_path), str(output_path)],
        check=True,
        capture_output=True
    )


def ingest_samples(
    corpus: Corpus,
    samples: List[Tuple[Path, str]]
) -> dict:
    """
    Ingest TED-LIUM samples into corpus.

    :param corpus: Corpus instance.
    :type corpus: Corpus
    :param samples: List of (audio_path, transcription) tuples.
    :type samples: list[tuple[Path, str]]
    :return: Ingestion statistics.
    :rtype: dict
    """
    import tempfile

    print(f"\nIngesting {len(samples)} TED-LIUM samples...")
    print("Note: Converting SPH to FLAC format (requires sox)...")

    ingested = 0
    failed = 0
    ground_truth_dir = corpus.root / "metadata" / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        for sph_file, transcription in samples:
            try:
                # Convert SPH to FLAC
                flac_file = Path(tmpdir) / f"{sph_file.stem}.flac"
                convert_sph_to_flac(sph_file, flac_file)

                # Read audio data
                audio_data = flac_file.read_bytes()

                # Ingest audio into corpus
                result = corpus.ingest_item(
                    data=audio_data,
                    media_type="audio/flac",
                    source_uri=f"file://{sph_file}",
                    tags=["tedlium", "test", "speech", "ground-truth"]
                )

                # Store ground truth transcription
                gt_file = ground_truth_dir / f"{result.id}.txt"
                gt_file.write_text(transcription, encoding="utf-8")

                ingested += 1
                print(f"  Ingested {ingested}/{len(samples)}: {sph_file.stem}")

            except Exception as e:
                print(f"  Failed to ingest {sph_file.name}: {e}")
                failed += 1

    print(f"\n✓ Ingestion complete: {ingested} succeeded, {failed} failed")
    return {"ingested": ingested, "failed": failed}


def main():
    parser = argparse.ArgumentParser(
        description="Download and ingest TED-LIUM 3 samples for STT benchmarking"
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        required=True,
        help="Path to corpus directory"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Number of samples to ingest"
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("/tmp/tedlium"),
        help="Directory to download dataset to"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("TED-LIUM 3 DATASET DOWNLOAD AND INGESTION")
    print("=" * 80)
    print(f"Sample count: {args.count}")
    print(f"Corpus: {args.corpus}")
    print(f"Download directory: {args.download_dir}")
    print("=" * 80)

    # Check for sox
    import shutil
    if not shutil.which("sox"):
        print("✗ Error: sox is required for audio conversion")
        print("  Install it with: brew install sox  (macOS)")
        print("  Or: apt-get install sox  (Linux)")
        sys.exit(1)

    # Download dataset
    dataset_dir = download_tedlium(download_dir=args.download_dir)

    # Collect samples
    samples = collect_audio_samples(
        dataset_dir=dataset_dir,
        sample_count=args.count
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
