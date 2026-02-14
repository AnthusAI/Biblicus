from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, Optional

from behave import given, then


@dataclass
class _FakeAzureRecognitionBehavior:
    transcript: str
    reason: str = "RecognizedSpeech"
    confidence: Optional[float] = None
    cancellation_reason: Optional[str] = None
    error_details: Optional[str] = None


def _ensure_fake_azure_recognition_behaviors(
    context,
) -> Dict[str, _FakeAzureRecognitionBehavior]:
    behaviors = getattr(context, "fake_azure_recognitions", None)
    if behaviors is None:
        behaviors = {}
        context.fake_azure_recognitions = behaviors
    return behaviors


def _install_fake_azure_speech_module(context) -> None:
    already_installed = getattr(context, "_fake_azure_speech_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "azure" in sys.modules:
        original_modules["azure"] = sys.modules["azure"]
    if "azure.cognitiveservices" in sys.modules:
        original_modules["azure.cognitiveservices"] = sys.modules["azure.cognitiveservices"]
    if "azure.cognitiveservices.speech" in sys.modules:
        original_modules["azure.cognitiveservices.speech"] = sys.modules["azure.cognitiveservices.speech"]

    behaviors = _ensure_fake_azure_recognition_behaviors(context)

    # Create nested module structure
    azure_module = types.ModuleType("azure")
    cognitiveservices_module = types.ModuleType("azure.cognitiveservices")
    speechsdk_module = types.ModuleType("azure.cognitiveservices.speech")

    # Link modules
    azure_module.cognitiveservices = cognitiveservices_module
    cognitiveservices_module.speech = speechsdk_module

    # Create enums for result reasons
    class ResultReason:
        RecognizedSpeech = "RecognizedSpeech"
        NoMatch = "NoMatch"
        Canceled = "Canceled"

    speechsdk_module.ResultReason = ResultReason

    class ProfanityOption:
        Masked = "Masked"
        Removed = "Removed"
        Raw = "Raw"

    speechsdk_module.ProfanityOption = ProfanityOption

    class _CancellationDetails:
        def __init__(self, reason: str, error_details: Optional[str] = None) -> None:
            self.reason = reason
            self.error_details = error_details

    class _RecognitionResult:
        def __init__(
            self,
            text: str,
            reason: str,
            confidence: Optional[float] = None,
            cancellation_reason: Optional[str] = None,
            error_details: Optional[str] = None
        ) -> None:
            self.text = text
            self.reason = reason
            self.confidence = confidence
            if cancellation_reason:
                self.cancellation_details = _CancellationDetails(cancellation_reason, error_details)

    class _AudioConfig:
        def __init__(self, filename: str) -> None:
            speechsdk_module.last_audio_filename = filename  # type: ignore[attr-defined]

    speechsdk_module.audio = types.ModuleType("audio")
    speechsdk_module.audio.AudioConfig = _AudioConfig

    class _SpeechConfig:
        def __init__(self, subscription: str, region: Optional[str] = None, endpoint: Optional[str] = None) -> None:
            speechsdk_module.last_api_key = subscription  # type: ignore[attr-defined]
            speechsdk_module.last_region = region  # type: ignore[attr-defined]
            speechsdk_module.last_endpoint = endpoint  # type: ignore[attr-defined]
            self.speech_recognition_language = None
            self._profanity = None
            self._dictation_enabled = False

        def set_profanity(self, option: str) -> None:
            self._profanity = option
            speechsdk_module.last_profanity = option  # type: ignore[attr-defined]

        def enable_dictation(self) -> None:
            self._dictation_enabled = True
            speechsdk_module.last_dictation_enabled = True  # type: ignore[attr-defined]

    speechsdk_module.SpeechConfig = _SpeechConfig

    class _SpeechRecognizer:
        def __init__(self, speech_config: _SpeechConfig, audio_config: _AudioConfig) -> None:
            speechsdk_module.last_speech_config = speech_config  # type: ignore[attr-defined]
            speechsdk_module.last_audio_config = audio_config  # type: ignore[attr-defined]

        def recognize_once(self) -> _RecognitionResult:
            filename = getattr(speechsdk_module, "last_audio_filename", "unknown")
            base_name = filename.rsplit("/", 1)[-1]

            behavior = behaviors.get(base_name)
            if behavior is None:
                behavior = _FakeAzureRecognitionBehavior(transcript="")

            return _RecognitionResult(
                text=behavior.transcript,
                reason=behavior.reason,
                confidence=behavior.confidence,
                cancellation_reason=behavior.cancellation_reason,
                error_details=behavior.error_details
            )

    speechsdk_module.SpeechRecognizer = _SpeechRecognizer

    # Initialize module attributes
    speechsdk_module.last_api_key = None
    speechsdk_module.last_region = None
    speechsdk_module.last_endpoint = None
    speechsdk_module.last_audio_filename = None
    speechsdk_module.last_speech_config = None
    speechsdk_module.last_audio_config = None
    speechsdk_module.last_profanity = None
    speechsdk_module.last_dictation_enabled = False

    sys.modules["azure"] = azure_module
    sys.modules["azure.cognitiveservices"] = cognitiveservices_module
    sys.modules["azure.cognitiveservices.speech"] = speechsdk_module

    context._fake_azure_speech_installed = True
    context._fake_azure_speech_original_modules = original_modules


def _install_azure_speech_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_azure_speech_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = ["azure", "azure.cognitiveservices", "azure.cognitiveservices.speech"]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    # Create minimal module structure that will fail import check
    azure_module = types.ModuleType("azure")
    sys.modules["azure"] = azure_module

    context._fake_azure_speech_unavailable_installed = True
    context._fake_azure_speech_unavailable_original_modules = original_modules


@given("a fake Azure Speech library is available")
def step_fake_azure_speech_available(context) -> None:
    _install_fake_azure_speech_module(context)


@given(
    'a fake Azure Speech library is available that returns transcript "{transcript}" for filename "{filename}"'
)
def step_fake_azure_speech_returns_transcript(context, transcript: str, filename: str) -> None:
    _install_fake_azure_speech_module(context)
    behaviors = _ensure_fake_azure_recognition_behaviors(context)
    behaviors[filename] = _FakeAzureRecognitionBehavior(transcript=transcript)


@given(
    'a fake Azure Speech library is available that returns no speech for filename "{filename}"'
)
def step_fake_azure_speech_returns_no_speech(context, filename: str) -> None:
    _install_fake_azure_speech_module(context)
    behaviors = _ensure_fake_azure_recognition_behaviors(context)
    behaviors[filename] = _FakeAzureRecognitionBehavior(transcript="", reason="NoMatch")


@given(
    'a fake Azure Speech library is available that returns cancelled recognition for filename "{filename}" with reason "{reason}"'
)
def step_fake_azure_speech_returns_cancelled(context, filename: str, reason: str) -> None:
    _install_fake_azure_speech_module(context)
    behaviors = _ensure_fake_azure_recognition_behaviors(context)
    behaviors[filename] = _FakeAzureRecognitionBehavior(
        transcript="",
        reason="Canceled",
        cancellation_reason=reason,
        error_details=f"Cancellation error: {reason}"
    )


@given("the Azure Speech dependency is unavailable")
def step_azure_speech_dependency_unavailable(context) -> None:
    _install_azure_speech_unavailable_module(context)


@given("an Azure Speech API key is configured for this scenario")
def step_azure_speech_api_key_configured(context) -> None:
    api_key = os.environ.get("AZURE_SPEECH_KEY")
    if not api_key:
        api_key = "test-azure-key"
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env["AZURE_SPEECH_KEY"] = api_key


@then('the Azure Speech recognizer used region "{region}"')
def step_azure_speech_used_region(context, region: str) -> None:
    _ = context
    speechsdk_module = sys.modules.get("azure.cognitiveservices.speech")
    assert speechsdk_module is not None
    actual = getattr(speechsdk_module, "last_region", None)
    assert actual == region


@then("the Azure Speech recognizer enabled dictation")
def step_azure_speech_enabled_dictation(context) -> None:
    _ = context
    speechsdk_module = sys.modules.get("azure.cognitiveservices.speech")
    assert speechsdk_module is not None
    enabled = getattr(speechsdk_module, "last_dictation_enabled", False)
    assert enabled is True
