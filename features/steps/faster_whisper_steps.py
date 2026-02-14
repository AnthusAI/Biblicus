from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from behave import given, then


@dataclass
class _FakeWhisperSegment:
    text: str


@dataclass
class _FakeWhisperInfo:
    language: str
    language_probability: float
    duration: float


@dataclass
class _FakeWhisperBehavior:
    segments: List[_FakeWhisperSegment]
    info: _FakeWhisperInfo


def _ensure_fake_whisper_behaviors(context) -> Dict[str, _FakeWhisperBehavior]:
    behaviors = getattr(context, "fake_whisper_behaviors", None)
    if behaviors is None:
        behaviors = {}
        context.fake_whisper_behaviors = behaviors
    return behaviors


def _install_fake_faster_whisper_module(context) -> None:
    already_installed = getattr(context, "_fake_faster_whisper_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "faster_whisper" in sys.modules:
        original_modules["faster_whisper"] = sys.modules["faster_whisper"]

    behaviors = _ensure_fake_whisper_behaviors(context)

    class WhisperModel:
        def __init__(self, model_size: str, device: str = "auto", compute_type: str = "int8") -> None:
            faster_whisper_module.last_model_size = model_size  # type: ignore[attr-defined]
            faster_whisper_module.last_device = device  # type: ignore[attr-defined]
            faster_whisper_module.last_compute_type = compute_type  # type: ignore[attr-defined]

        def transcribe(
            self,
            audio_path: str,
            language: Optional[str] = None,
            beam_size: int = 5
        ) -> tuple[List[Any], Any]:
            faster_whisper_module.last_audio_path = audio_path  # type: ignore[attr-defined]
            faster_whisper_module.last_language = language  # type: ignore[attr-defined]
            faster_whisper_module.last_beam_size = beam_size  # type: ignore[attr-defined]

            # Extract filename from path
            filename = audio_path.rsplit("/", 1)[-1]

            # Find behavior for this filename
            behavior = behaviors.get(filename)
            if behavior is None:
                # Default behavior: empty transcript
                behavior = _FakeWhisperBehavior(
                    segments=[],
                    info=_FakeWhisperInfo(
                        language="en",
                        language_probability=0.99,
                        duration=0.0
                    )
                )

            return behavior.segments, behavior.info

    faster_whisper_module = types.ModuleType("faster_whisper")
    faster_whisper_module.WhisperModel = WhisperModel
    faster_whisper_module.last_model_size = None
    faster_whisper_module.last_device = None
    faster_whisper_module.last_compute_type = None
    faster_whisper_module.last_audio_path = None
    faster_whisper_module.last_language = None
    faster_whisper_module.last_beam_size = None

    sys.modules["faster_whisper"] = faster_whisper_module

    context._fake_faster_whisper_installed = True
    context._fake_faster_whisper_original_modules = original_modules


def _install_faster_whisper_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_faster_whisper_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "faster_whisper" in sys.modules:
        original_modules["faster_whisper"] = sys.modules["faster_whisper"]

    faster_whisper_module = types.ModuleType("faster_whisper")
    sys.modules["faster_whisper"] = faster_whisper_module

    context._fake_faster_whisper_unavailable_installed = True
    context._fake_faster_whisper_unavailable_original_modules = original_modules


@given("a fake faster-whisper library is available")
def step_fake_faster_whisper_available(context) -> None:
    _install_fake_faster_whisper_module(context)


@given(
    'a fake faster-whisper library is available that returns transcript "{transcript}" for filename "{filename}"'
)
def step_fake_faster_whisper_returns_transcript(context, transcript: str, filename: str) -> None:
    _install_fake_faster_whisper_module(context)
    behaviors = _ensure_fake_whisper_behaviors(context)

    # Split transcript into segments (by sentence)
    segments = [_FakeWhisperSegment(text=transcript)]

    info = _FakeWhisperInfo(
        language="en",
        language_probability=0.99,
        duration=5.0
    )

    behaviors[filename] = _FakeWhisperBehavior(segments=segments, info=info)


@given(
    'a fake faster-whisper library is available that returns transcript "{transcript}" with detected language "{language}" for file "{filename}"'
)
def step_fake_faster_whisper_returns_transcript_with_language(
    context, transcript: str, language: str, filename: str
) -> None:
    _install_fake_faster_whisper_module(context)
    behaviors = _ensure_fake_whisper_behaviors(context)

    segments = [_FakeWhisperSegment(text=transcript)]
    info = _FakeWhisperInfo(
        language=language,
        language_probability=0.95,
        duration=5.0
    )

    behaviors[filename] = _FakeWhisperBehavior(segments=segments, info=info)


@given("the faster-whisper dependency is unavailable")
def step_faster_whisper_dependency_unavailable(context) -> None:
    _install_faster_whisper_unavailable_module(context)


@then('the faster-whisper model used model size "{model_size}"')
def step_faster_whisper_used_model_size(context, model_size: str) -> None:
    _ = context
    faster_whisper_module = sys.modules.get("faster_whisper")
    assert faster_whisper_module is not None
    actual = getattr(faster_whisper_module, "last_model_size", None)
    assert actual == model_size


@then('the faster-whisper transcription used language "{language}"')
def step_faster_whisper_used_language(context, language: str) -> None:
    _ = context
    faster_whisper_module = sys.modules.get("faster_whisper")
    assert faster_whisper_module is not None
    actual = getattr(faster_whisper_module, "last_language", None)
    assert actual == language


@then('the faster-whisper transcription used beam size {beam_size:d}')
def step_faster_whisper_used_beam_size(context, beam_size: int) -> None:
    _ = context
    faster_whisper_module = sys.modules.get("faster_whisper")
    assert faster_whisper_module is not None
    actual = getattr(faster_whisper_module, "last_beam_size", None)
    assert actual == beam_size
