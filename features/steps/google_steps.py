from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from behave import given, then


@dataclass
class _FakeGoogleRecognitionBehavior:
    transcript: str
    confidence: Optional[float] = None


def _ensure_fake_google_recognition_behaviors(
    context,
) -> Dict[str, _FakeGoogleRecognitionBehavior]:
    behaviors = getattr(context, "fake_google_recognitions", None)
    if behaviors is None:
        behaviors = {}
        context.fake_google_recognitions = behaviors
    return behaviors


def _install_fake_google_speech_module(context) -> None:
    already_installed = getattr(context, "_fake_google_speech_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = ["google", "google.cloud", "google.cloud.speech"]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    behaviors = _ensure_fake_google_recognition_behaviors(context)

    # Create nested module structure
    google_module = types.ModuleType("google")
    cloud_module = types.ModuleType("google.cloud")
    speech_module = types.ModuleType("google.cloud.speech")

    # Link modules
    google_module.cloud = cloud_module
    cloud_module.speech = speech_module

    # Create enums for audio encoding as module-level first
    class _AudioEncoding:
        LINEAR16 = 1
        FLAC = 2
        MP3 = 3
        OGG_OPUS = 7
        WEBM_OPUS = 9

    class RecognitionConfig:
        AudioEncoding = _AudioEncoding

        def __init__(
            self,
            encoding: int,
            language_code: str,
            model: str,
            enable_automatic_punctuation: bool,
            profanity_filter: bool,
            enable_word_time_offsets: bool = False,
            diarization_config: Optional[Any] = None
        ) -> None:
            speech_module.last_encoding = encoding  # type: ignore[attr-defined]
            speech_module.last_language_code = language_code  # type: ignore[attr-defined]
            speech_module.last_model = model  # type: ignore[attr-defined]
            speech_module.last_automatic_punctuation = enable_automatic_punctuation  # type: ignore[attr-defined]
            speech_module.last_profanity_filter = profanity_filter  # type: ignore[attr-defined]
            self.enable_word_time_offsets = enable_word_time_offsets
            self.diarization_config = diarization_config

    speech_module.RecognitionConfig = RecognitionConfig

    class SpeakerDiarizationConfig:
        def __init__(
            self,
            enable_speaker_diarization: bool,
            min_speaker_count: Optional[int] = None,
            max_speaker_count: Optional[int] = None
        ) -> None:
            speech_module.last_diarization_enabled = enable_speaker_diarization  # type: ignore[attr-defined]
            speech_module.last_min_speakers = min_speaker_count  # type: ignore[attr-defined]
            speech_module.last_max_speakers = max_speaker_count  # type: ignore[attr-defined]
            self.enable_speaker_diarization = enable_speaker_diarization
            self.min_speaker_count = min_speaker_count
            self.max_speaker_count = max_speaker_count

    speech_module.SpeakerDiarizationConfig = SpeakerDiarizationConfig

    class RecognitionAudio:
        def __init__(self, content: bytes) -> None:
            speech_module.last_audio_content = content  # type: ignore[attr-defined]
            speech_module.last_audio_size = len(content)  # type: ignore[attr-defined]

    speech_module.RecognitionAudio = RecognitionAudio

    class _SpeechAlternative:
        def __init__(self, transcript: str, confidence: Optional[float] = None) -> None:
            self.transcript = transcript
            self.confidence = confidence

    class _RecognitionResult:
        def __init__(self, alternatives: List[_SpeechAlternative]) -> None:
            self.alternatives = alternatives

    class _RecognitionResponse:
        def __init__(self, results: List[_RecognitionResult]) -> None:
            self.results = results

    class SpeechClient:
        def __init__(self) -> None:
            speech_module.client_initialized = True  # type: ignore[attr-defined]

        def recognize(self, config: RecognitionConfig, audio: RecognitionAudio) -> _RecognitionResponse:
            # Extract filename hint from audio size or use default behavior
            audio_size = getattr(speech_module, "last_audio_size", 0)
            filename_hint = getattr(speech_module, "current_filename_hint", f"audio_{audio_size}")

            behavior = behaviors.get(filename_hint)
            if behavior is None:
                behavior = _FakeGoogleRecognitionBehavior(transcript="")

            alternative = _SpeechAlternative(
                transcript=behavior.transcript,
                confidence=behavior.confidence
            )
            result = _RecognitionResult(alternatives=[alternative])
            return _RecognitionResponse(results=[result])

    speech_module.SpeechClient = SpeechClient

    # Initialize module attributes
    speech_module.last_encoding = None
    speech_module.last_language_code = None
    speech_module.last_model = None
    speech_module.last_automatic_punctuation = None
    speech_module.last_profanity_filter = None
    speech_module.last_audio_content = None
    speech_module.last_audio_size = None
    speech_module.last_diarization_enabled = False
    speech_module.last_min_speakers = None
    speech_module.last_max_speakers = None
    speech_module.client_initialized = False
    speech_module.current_filename_hint = None

    sys.modules["google"] = google_module
    sys.modules["google.cloud"] = cloud_module
    sys.modules["google.cloud.speech"] = speech_module

    context._fake_google_speech_installed = True
    context._fake_google_speech_original_modules = original_modules


def _install_google_speech_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_google_speech_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = ["google", "google.cloud", "google.cloud.speech"]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    # Create minimal module structure that will fail import check
    google_module = types.ModuleType("google")
    sys.modules["google"] = google_module

    context._fake_google_speech_unavailable_installed = True
    context._fake_google_speech_unavailable_original_modules = original_modules


@given("a fake Google Speech library is available")
def step_fake_google_speech_available(context) -> None:
    _install_fake_google_speech_module(context)


@given(
    'a fake Google Speech library is available that returns transcript "{transcript}" for filename "{filename}"'
)
def step_fake_google_speech_returns_transcript(context, transcript: str, filename: str) -> None:
    _install_fake_google_speech_module(context)
    behaviors = _ensure_fake_google_recognition_behaviors(context)
    behaviors[filename] = _FakeGoogleRecognitionBehavior(transcript=transcript)
    # Set filename hint for the module
    speech_module = sys.modules.get("google.cloud.speech")
    if speech_module:
        speech_module.current_filename_hint = filename  # type: ignore[attr-defined]


@given("the Google Speech dependency is unavailable")
def step_google_speech_dependency_unavailable(context) -> None:
    _install_google_speech_unavailable_module(context)


@given("a Google Cloud credentials file is configured for this scenario")
def step_google_credentials_configured(context) -> None:
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        # Create a fake credentials path for testing
        credentials_path = "/tmp/fake-google-credentials.json"
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path


@then('the Google Speech request used language code "{language_code}"')
def step_google_speech_used_language_code(context, language_code: str) -> None:
    _ = context
    speech_module = sys.modules.get("google.cloud.speech")
    assert speech_module is not None
    actual = getattr(speech_module, "last_language_code", None)
    assert actual == language_code


@then('the Google Speech request used model "{model}"')
def step_google_speech_used_model(context, model: str) -> None:
    _ = context
    speech_module = sys.modules.get("google.cloud.speech")
    assert speech_module is not None
    actual = getattr(speech_module, "last_model", None)
    assert actual == model


@then("the Google Speech request enabled automatic punctuation")
def step_google_speech_enabled_punctuation(context) -> None:
    _ = context
    speech_module = sys.modules.get("google.cloud.speech")
    assert speech_module is not None
    enabled = getattr(speech_module, "last_automatic_punctuation", False)
    assert enabled is True


@then("the Google Speech request enabled speaker diarization")
def step_google_speech_enabled_diarization(context) -> None:
    _ = context
    speech_module = sys.modules.get("google.cloud.speech")
    assert speech_module is not None
    enabled = getattr(speech_module, "last_diarization_enabled", False)
    assert enabled is True
