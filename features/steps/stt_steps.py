from __future__ import annotations

import os
from pathlib import Path

from behave import when

from biblicus.corpus import Corpus
from biblicus.extractors.openai_stt import (
    OpenAiSpeechToTextExtractor,
    OpenAiSpeechToTextExtractorConfig,
)
from biblicus.models import CatalogItem
from biblicus.time import utc_now_iso


def _sample_audio_catalog_item(*, relpath: str) -> CatalogItem:
    return CatalogItem(
        id="audio-item",
        relpath=relpath,
        sha256="0" * 64,
        bytes=0,
        media_type="audio/x-wav",
        title=None,
        tags=[],
        metadata={},
        created_at=utc_now_iso(),
        source_uri=None,
    )


def _call_stt_extractor(
    *,
    workdir: Path,
    openai_api_key: str | None,
) -> Exception | None:
    corpus_root = workdir / "corpus"
    corpus = Corpus.init(corpus_root)
    (corpus_root / "raw").mkdir(parents=True, exist_ok=True)
    audio_relpath = "raw/clip.wav"
    (corpus_root / audio_relpath).write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

    extractor = OpenAiSpeechToTextExtractor()
    parsed_config = OpenAiSpeechToTextExtractorConfig()

    isolated_root = workdir / "isolated"
    isolated_home = isolated_root / "home"
    isolated_root.mkdir(parents=True, exist_ok=True)
    isolated_home.mkdir(parents=True, exist_ok=True)

    prior_openai_key = os.environ.pop("OPENAI_API_KEY", None)
    prior_home = os.environ.get("HOME")
    prior_cwd = os.getcwd()
    try:
        if openai_api_key is not None:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        os.environ["HOME"] = str(isolated_home)
        os.chdir(str(isolated_root))
        extractor.extract_text(
            corpus=corpus,
            item=_sample_audio_catalog_item(relpath=audio_relpath),
            config=parsed_config,
            previous_extractions=[],
        )
    except Exception as exc:
        return exc
    finally:
        os.chdir(prior_cwd)
        if prior_home is not None:
            os.environ["HOME"] = prior_home
        else:
            os.environ.pop("HOME", None)
        if prior_openai_key is not None:
            os.environ["OPENAI_API_KEY"] = prior_openai_key
        else:
            os.environ.pop("OPENAI_API_KEY", None)
    return None


@when("I call the speech to text extractor without an API key")
def step_call_stt_extractor_without_api_key(context) -> None:
    context.extraction_fatal_error = _call_stt_extractor(
        workdir=Path(context.workdir),
        openai_api_key=None,
    )


@when("I call the speech to text extractor with an API key")
def step_call_stt_extractor_with_api_key(context) -> None:
    context.extraction_fatal_error = _call_stt_extractor(
        workdir=Path(context.workdir),
        openai_api_key="test-openai-key",
    )
