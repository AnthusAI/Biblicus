"""
Download a small audio corpus for integration testing.
"""

from __future__ import annotations

import argparse
import json
import struct
import time
from pathlib import Path
from typing import Dict, List, TypedDict

from biblicus.corpus import Corpus


class AudioSample(TypedDict):
    """
    Typed dictionary describing an audio sample source.

    :ivar url: Uniform resource locator for the audio sample.
    :vartype url: str
    :ivar tags: Tags associated with the sample.
    :vartype tags: list[str]
    """

    url: str
    tags: List[str]


DEFAULT_AUDIO_SPEECH_SAMPLES: List[AudioSample] = [
    {
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-hello.ogg",
        "tags": ["language-en"],
    },
    {
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Fr-bonjour.ogg",
        "tags": ["language-fr"],
    },
    {
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/De-hallo.ogg",
        "tags": ["language-de"],
    },
    {
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Ja-konnichiwa.ogg",
        "tags": ["language-ja"],
    },
    {
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Es-hola.oga",
        "tags": ["language-es"],
    },
]


def _silent_wave_bytes(*, seconds: float, sample_rate_hz: int) -> bytes:
    """
    Build a deterministic Waveform Audio File Format payload containing silence.

    This is used for repeatable non-speech test cases without relying on external downloads.

    :param seconds: Duration in seconds.
    :type seconds: float
    :param sample_rate_hz: Sample rate in Hertz.
    :type sample_rate_hz: int
    :return: Waveform Audio File Format bytes.
    :rtype: bytes
    """
    channels = 1
    bits_per_sample = 16
    bytes_per_sample = bits_per_sample // 8
    total_frames = int(max(0.0, seconds) * sample_rate_hz)
    data_bytes = b"\x00" * (total_frames * channels * bytes_per_sample)

    fmt_chunk = struct.pack(
        "<4sIHHIIHH",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate_hz,
        sample_rate_hz * channels * bytes_per_sample,
        channels * bytes_per_sample,
        bits_per_sample,
    )
    data_chunk = struct.pack("<4sI", b"data", len(data_bytes)) + data_bytes
    riff_size = 4 + len(fmt_chunk) + len(data_chunk)
    header = struct.pack("<4sI4s", b"RIFF", riff_size, b"WAVE")
    return header + fmt_chunk + data_chunk


def _prepare_corpus(path: Path, *, force: bool) -> Corpus:
    """
    Initialize or open a corpus for integration downloads.

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


def download_audio_samples(
    *, corpus_path: Path, force: bool, samples: List[AudioSample]
) -> Dict[str, int]:
    """
    Download a small set of audio items into a corpus.

    This script downloads public files at runtime. The repository does not include those files.

    :param corpus_path: Corpus path to create or reuse.
    :type corpus_path: Path
    :param force: Whether to purge existing corpus content.
    :type force: bool
    :param samples: Audio samples to download.
    :type samples: list[AudioSample]
    :return: Ingestion statistics.
    :rtype: dict[str, int]
    """
    corpus = _prepare_corpus(corpus_path, force=force)
    ingested = 0
    failed = 0

    corpus.ingest_item(
        _silent_wave_bytes(seconds=1.0, sample_rate_hz=16_000),
        filename="silence.wav",
        media_type="audio/wav",
        source_uri="generated:silence.wav",
        tags=["integration", "audio", "no-speech"],
    )
    ingested += 1

    for sample in samples:
        audio_url = sample["url"]
        extra_tags = list(sample.get("tags") or [])
        try:
            corpus.ingest_source(
                audio_url,
                tags=["integration", "audio", "speech", *extra_tags],
                source_uri=audio_url,
            )
            ingested += 1
        except Exception:
            failed += 1
        time.sleep(0.5)

    corpus.reindex()
    return {"ingested": ingested, "failed": failed}


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line interface argument parser.

    :return: Argument parser.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Download audio samples into Biblicus.")
    parser.add_argument("--corpus", required=True, help="Corpus path to initialize or reuse.")
    parser.add_argument("--force", action="store_true", help="Purge existing corpus content.")
    parser.add_argument(
        "--audio-url",
        action="append",
        dest="audio_urls",
        help="Audio uniform resource locator. Repeatable. When omitted, downloads a default speech sample set.",
    )
    return parser


def main() -> int:
    """
    Entry point for the audio sample download script.

    :return: Exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args()
    samples: List[AudioSample]
    if args.audio_urls:
        samples = [{"url": str(url), "tags": []} for url in args.audio_urls]
    else:
        samples = DEFAULT_AUDIO_SPEECH_SAMPLES
    stats = download_audio_samples(
        corpus_path=Path(args.corpus).resolve(),
        force=bool(args.force),
        samples=samples,
    )
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
