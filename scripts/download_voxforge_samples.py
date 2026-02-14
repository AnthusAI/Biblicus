#!/usr/bin/env python3
"""
Download and ingest VoxForge dataset samples for STT benchmarking.

VoxForge is a free speech corpus with diverse accents and speakers.
Smaller and faster to download than LibriSpeech or TED-LIUM.

Usage:
    python scripts/download_voxforge_samples.py \\
        --corpus corpora/voxforge_benchmark \\
        --count 50
"""

import argparse
import sys
from pathlib import Path
import tarfile
from typing import List, Tuple
import urllib.request
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from biblicus import Corpus


def get_voxforge_archive_urls(count: int = 50) -> List[str]:
    """
    Get URLs for VoxForge speech archives.

    :param count: Number of archives to download.
    :type count: int
    :return: List of archive URLs.
    :rtype: list[str]
    """
    # VoxForge archives are at http://www.repository.voxforge1.org/downloads/SpeechCorpus/Trunk/Audio/Main/16kHz_16bit/
    base_url = "http://www.repository.voxforge1.org/downloads/SpeechCorpus/Trunk/Audio/Main/16kHz_16bit/"

    # List of known archives (partial - there are hundreds)
    # In practice, you'd scrape the index page for all available archives
    archives = [
        "Aaron-20080318-kdl.tgz",
        "Acowen-20071119-duv.tgz",
        "Adam-20090415-csr.tgz",
        "Adrian-20100313-jbr.tgz",
        "Aideen-20090616-qns.tgz",
        "Alan-20091102-ixm.tgz",
        "Alex-20080303-woc.tgz",
        "Alix-20080215-glj.tgz",
        "Andrew-20090330-aej.tgz",
        "Andy-20080424-fad.tgz",
        "Angela-20080215-acl.tgz",
        "Angie-20090616-qns.tgz",
        "anonymous-20080122-lcy.tgz",
        "anonymous-20080207-lmx.tgz",
        "anonymous-20080222-mur.tgz",
        "Anthony-20080401-xyx.tgz",
        "Arjun-20090616-qns.tgz",
        "Ashely-20071119-duv.tgz",
        "Barry-20091124-vvq.tgz",
        "Ben-20091124-vvq.tgz",
    ]

    return [base_url + archive for archive in archives[:count]]


def download_and_extract_archive(url: str, download_dir: Path) -> Path:
    """
    Download and extract a VoxForge archive.

    :param url: URL to archive.
    :type url: str
    :param download_dir: Directory to download to.
    :type download_dir: Path
    :return: Path to extracted directory.
    :rtype: Path
    """
    filename = url.split('/')[-1]
    tar_file = download_dir / filename
    extract_dir = download_dir / filename.replace('.tgz', '')

    if extract_dir.exists():
        return extract_dir

    if not tar_file.exists():
        print(f"  Downloading {filename}...")
        try:
            urllib.request.urlretrieve(url, tar_file)
        except Exception as e:
            print(f"    Failed: {e}")
            return None

    print(f"  Extracting {filename}...")
    try:
        with tarfile.open(tar_file, "r:gz") as tar:
            tar.extractall(download_dir)
        tar_file.unlink()  # Remove tar file to save space
    except Exception as e:
        print(f"    Failed: {e}")
        return None

    return extract_dir


def parse_prompts_file(prompts_path: Path) -> dict:
    """
    Parse VoxForge PROMPTS file containing transcriptions.

    Format: <filename> <transcription>

    :param prompts_path: Path to PROMPTS file.
    :type prompts_path: Path
    :return: Dictionary mapping filenames to transcriptions.
    :rtype: dict[str, str]
    """
    transcriptions = {}

    with prompts_path.open('r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(None, 1)
            if len(parts) == 2:
                filename, transcript = parts
                transcriptions[filename] = transcript

    return transcriptions


def collect_audio_samples(
    download_dir: Path,
    sample_count: int
) -> List[Tuple[Path, str]]:
    """
    Download and collect audio samples from VoxForge.

    :param download_dir: Directory to download archives to.
    :type download_dir: Path
    :param sample_count: Number of archives to process.
    :type sample_count: int
    :return: List of (audio_path, transcription) tuples.
    :rtype: list[tuple[Path, str]]
    """
    download_dir.mkdir(parents=True, exist_ok=True)

    urls = get_voxforge_archive_urls(count=sample_count)
    samples = []

    for url in urls:
        extract_dir = download_and_extract_archive(url, download_dir)
        if not extract_dir or not extract_dir.exists():
            continue

        # VoxForge structure varies, but typically:
        # <archive>/
        #   wav/ or flac/
        #     *.wav or *.flac
        #   etc/
        #     PROMPTS (transcriptions)

        prompts_file = extract_dir / "etc" / "PROMPTS"
        if not prompts_file.exists():
            # Try alternate location
            prompts_file = extract_dir / "etc" / "prompts-original"

        if not prompts_file.exists():
            print(f"    No PROMPTS file found in {extract_dir.name}")
            continue

        transcriptions = parse_prompts_file(prompts_file)

        # Find audio directory
        audio_dir = None
        for possible_dir in ["wav", "flac", "audio"]:
            candidate = extract_dir / possible_dir
            if candidate.exists():
                audio_dir = candidate
                break

        if not audio_dir:
            print(f"    No audio directory found in {extract_dir.name}")
            continue

        # Collect audio files
        for audio_file in audio_dir.glob("*.wav"):
            file_id = audio_file.stem
            if file_id in transcriptions:
                samples.append((audio_file, transcriptions[file_id]))

        for audio_file in audio_dir.glob("*.flac"):
            file_id = audio_file.stem
            if file_id in transcriptions:
                samples.append((audio_file, transcriptions[file_id]))

        print(f"    Collected {len(samples)} total samples so far")

    return samples


def ingest_samples(
    corpus: Corpus,
    samples: List[Tuple[Path, str]]
) -> dict:
    """
    Ingest VoxForge samples into corpus.

    :param corpus: Corpus instance.
    :type corpus: Corpus
    :param samples: List of (audio_path, transcription) tuples.
    :type samples: list[tuple[Path, str]]
    :return: Ingestion statistics.
    :rtype: dict
    """
    print(f"\nIngesting {len(samples)} VoxForge samples...")

    ingested = 0
    failed = 0
    ground_truth_dir = corpus.root / "metadata" / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    for audio_file, transcription in samples:
        try:
            # Read audio data
            audio_data = audio_file.read_bytes()

            # Detect media type
            if audio_file.suffix == '.wav':
                media_type = "audio/wav"
            elif audio_file.suffix == '.flac':
                media_type = "audio/flac"
            else:
                continue

            # Ingest audio into corpus
            result = corpus.ingest_item(
                data=audio_data,
                media_type=media_type,
                source_uri=f"file://{audio_file}",
                tags=["voxforge", "speech", "ground-truth"]
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
        description="Download and ingest VoxForge samples for STT benchmarking"
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
        default=20,
        help="Number of speaker archives to download"
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=Path("/tmp/voxforge"),
        help="Directory to download dataset to"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("VOXFORGE DATASET DOWNLOAD AND INGESTION")
    print("=" * 80)
    print(f"Archives to download: {args.count}")
    print(f"Corpus: {args.corpus}")
    print(f"Download directory: {args.download_dir}")
    print("=" * 80)

    # Collect samples
    samples = collect_audio_samples(
        download_dir=args.download_dir,
        sample_count=args.count
    )

    if not samples:
        print("✗ No samples collected")
        sys.exit(1)

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
