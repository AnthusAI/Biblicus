from __future__ import annotations

"""Runtime dependency failure steps for speech-to-text extractors.

These steps intentionally invoke the extractors with their optional
dependencies removed to exercise fatal error paths that would otherwise be
skipped in normal scenarios.
"""

import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from behave import when

from biblicus.corpus import Corpus
from biblicus.errors import ExtractionSnapshotFatalError
from biblicus.extractors.audio_format_converter import (
    AudioFormatConverterConfig,
    AudioFormatConverterExtractor,
)
from biblicus.extractors.aws_transcribe_stt import (
    AwsTranscribeSpeechToTextExtractor,
    AwsTranscribeSpeechToTextExtractorConfig,
)
from biblicus.extractors.azure_speech_stt import (
    AzureSpeechToTextExtractor,
    AzureSpeechToTextExtractorConfig,
)
from biblicus.extractors.faster_whisper_stt import (
    FasterWhisperSpeechToTextExtractor,
    FasterWhisperSpeechToTextExtractorConfig,
)
from biblicus.extractors.google_speech_stt import (
    GoogleSpeechToTextExtractor,
    GoogleSpeechToTextExtractorConfig,
)
from biblicus.extractors.openai_audio_stt import (
    OpenAiAudioSpeechToTextExtractor,
    OpenAiAudioSpeechToTextExtractorConfig,
)
from biblicus.models import CatalogItem
from biblicus.time import utc_now_iso


def _sample_audio_item(relpath: str) -> CatalogItem:
    return CatalogItem(
        id="audio-item",
        relpath=relpath,
        sha256="0" * 64,
        bytes=4,
        media_type="audio/wav",
        title=None,
        tags=[],
        metadata={},
        created_at=utc_now_iso(),
        source_uri=None,
    )


class _ImportBlocker:
    """Meta path finder/loader that always raises ImportError for given module names."""

    def __init__(self, blocked: Iterable[str]) -> None:
        self.blocked = tuple(blocked)

    def find_spec(self, fullname: str, path: Optional[List[str]], target=None):  # type: ignore[override]
        if fullname in self.blocked or any(fullname.startswith(name + ".") for name in self.blocked):
            raise ImportError(f"No module named '{fullname}'")
        return None


def _call_extractor(
    extractor,
    config,
    workdir: Path,
    *,
    clear_openai_key: bool = False,
    block_modules: Optional[List[str]] = None,
) -> Exception | None:
    corpus_root = workdir / "corpus"
    corpus = Corpus.open(corpus_root) if corpus_root.exists() else Corpus.init(corpus_root)
    (corpus_root / "raw").mkdir(parents=True, exist_ok=True)
    relpath = "clip.wav"
    (corpus_root / relpath).write_bytes(b"RIFF")

    try:
        prior_openai_key = os.environ.pop("OPENAI_API_KEY", None) if clear_openai_key else None
        blocker = None
        if block_modules:
            # Remove any already-imported copies to force ImportError.
            for name in block_modules:
                if name in sys.modules:
                    sys.modules.pop(name, None)
            blocker = _ImportBlocker(block_modules)
            sys.meta_path.insert(0, blocker)
        extractor.extract_text(
            corpus=corpus,
            item=_sample_audio_item(relpath),
            config=config,
            previous_extractions=[],
        )
    except Exception as exc:  # noqa: BLE001
        return exc
    finally:
        if clear_openai_key and prior_openai_key is not None:
            os.environ["OPENAI_API_KEY"] = prior_openai_key
        if block_modules and blocker is not None:
            # Remove our blocker if still present.
            if sys.meta_path and sys.meta_path[0] is blocker:
                sys.meta_path.pop(0)
    return None


@when("I call the audio converter extract_text with dependency unavailable")
def step_audio_converter_missing_dependency(context) -> None:
    context.extraction_fatal_error = _call_extractor(
        AudioFormatConverterExtractor(),
        AudioFormatConverterConfig(target_format="wav"),
        Path(context.workdir),
    )


@when("I call the AWS Transcribe extractor extract_text with dependency unavailable")
def step_aws_transcribe_missing_dependency(context) -> None:
    context.extraction_fatal_error = _call_extractor(
        AwsTranscribeSpeechToTextExtractor(),
        AwsTranscribeSpeechToTextExtractorConfig(s3_bucket="test-bucket"),
        Path(context.workdir),
        block_modules=["boto3", "botocore"],
    )


@when("I call the Azure Speech extractor extract_text with dependency unavailable")
def step_azure_speech_missing_dependency(context) -> None:
    context.extraction_fatal_error = _call_extractor(
        AzureSpeechToTextExtractor(),
        AzureSpeechToTextExtractorConfig(language="en-US"),
        Path(context.workdir),
        block_modules=["azure", "azure.cognitiveservices", "azure.cognitiveservices.speech"],
    )


@when("I call the Faster-Whisper extractor extract_text with dependency unavailable")
def step_faster_whisper_missing_dependency(context) -> None:
    context.extraction_fatal_error = _call_extractor(
        FasterWhisperSpeechToTextExtractor(),
        FasterWhisperSpeechToTextExtractorConfig(),
        Path(context.workdir),
        block_modules=["faster_whisper"],
    )


@when("I call the Google Speech extractor extract_text with dependency unavailable")
def step_google_speech_missing_dependency(context) -> None:
    context.extraction_fatal_error = _call_extractor(
        GoogleSpeechToTextExtractor(),
        GoogleSpeechToTextExtractorConfig(),
        Path(context.workdir),
        block_modules=["google", "google.cloud", "google.cloud.speech"],
    )


@when("I call the OpenAI Audio extractor extract_text with dependency unavailable")
def step_openai_audio_missing_dependency(context) -> None:
    context.extraction_fatal_error = _call_extractor(
        OpenAiAudioSpeechToTextExtractor(),
        OpenAiAudioSpeechToTextExtractorConfig(),
        Path(context.workdir),
        block_modules=["openai"],
    )


@when("I call the OpenAI Audio extractor extract_text with no API key")
def step_openai_audio_missing_key(context) -> None:
    # Explicitly drop API key to trigger runtime validation failure.
    context.extraction_fatal_error = _call_extractor(
        OpenAiAudioSpeechToTextExtractor(),
        OpenAiAudioSpeechToTextExtractorConfig(),
        Path(context.workdir),
        clear_openai_key=True,
    )
