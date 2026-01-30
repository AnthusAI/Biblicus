from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, Optional

from behave import given, then


@dataclass
class _FakeDeepgramTranscriptionBehavior:
    transcript: Optional[str]
    response_type: str = "normal"


def _ensure_fake_deepgram_transcription_behaviors(
    context,
) -> Dict[str, _FakeDeepgramTranscriptionBehavior]:
    behaviors = getattr(context, "fake_deepgram_transcriptions", None)
    if behaviors is None:
        behaviors = {}
        context.fake_deepgram_transcriptions = behaviors
    return behaviors


def _install_fake_deepgram_module(context) -> None:
    deepgram_module = sys.modules.get("deepgram")
    if deepgram_module is not None and hasattr(deepgram_module, "DeepgramClient"):
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "deepgram",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    behaviors = _ensure_fake_deepgram_transcription_behaviors(context)

    class _Alternative:
        def __init__(self, transcript: str) -> None:
            self.transcript = transcript

    class _Channel:
        def __init__(self, alternatives: list) -> None:
            self.alternatives = alternatives

    class _Results:
        def __init__(self, channels: list) -> None:
            self.channels = channels

    class _TranscriptionResponseNormal:
        def __init__(self, transcript: str) -> None:
            self.results = _Results([_Channel([_Alternative(transcript)])])

    class _TranscriptionResponseNoResults:
        def __init__(self) -> None:
            self.results = None

    class _TranscriptionResponseEmptyChannels:
        def __init__(self) -> None:
            self.results = _Results([])

    class _TranscriptionResponseEmptyAlternatives:
        def __init__(self) -> None:
            self.results = _Results([_Channel([])])

    class _TranscribeApi:
        def transcribe_file(
            self, audio_data: Dict[str, Any], options: Dict[str, Any]
        ) -> object:
            deepgram_module.last_transcription_model = options.get("model")
            deepgram_module.last_transcription_options = dict(options)
            behaviors_map = _ensure_fake_deepgram_transcription_behaviors(context)
            for _filename, behavior in behaviors_map.items():
                if behavior.response_type == "empty_results":
                    return _TranscriptionResponseNoResults()
                if behavior.response_type == "empty_channels":
                    return _TranscriptionResponseEmptyChannels()
                if behavior.response_type == "empty_alternatives":
                    return _TranscriptionResponseEmptyAlternatives()
                if behavior.transcript is not None:
                    return _TranscriptionResponseNormal(behavior.transcript)
            return _TranscriptionResponseNormal("")

    class _ListenRestVersion:
        def __init__(self) -> None:
            pass

        def transcribe_file(
            self, audio_data: Dict[str, Any], options: Dict[str, Any]
        ) -> object:
            return _TranscribeApi().transcribe_file(audio_data, options)

    class _ListenRest:
        def v(self, version: str) -> _ListenRestVersion:
            return _ListenRestVersion()

    class _Listen:
        def __init__(self) -> None:
            self.rest = _ListenRest()

    class DeepgramClient:
        def __init__(self, api_key: str = "", **kwargs: Any) -> None:
            deepgram_module.last_api_key = api_key
            self.listen = _Listen()

    deepgram_module = types.ModuleType("deepgram")
    deepgram_module.DeepgramClient = DeepgramClient
    deepgram_module.last_api_key = None
    deepgram_module.last_transcription_model = None
    deepgram_module.last_transcription_options = {}

    sys.modules["deepgram"] = deepgram_module

    context._fake_deepgram_original_modules = original_modules


def _install_deepgram_unavailable_module(context) -> None:
    deepgram_module = sys.modules.get("deepgram")
    if deepgram_module is not None and not hasattr(deepgram_module, "DeepgramClient"):
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "deepgram",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    deepgram_module = types.ModuleType("deepgram")
    sys.modules["deepgram"] = deepgram_module

    context._fake_deepgram_unavailable_original_modules = original_modules


@given("a fake Deepgram library is available")
def step_fake_deepgram_available(context) -> None:
    _install_fake_deepgram_module(context)


@given(
    'a fake Deepgram library is available that returns transcript "{transcript}" for filename "{filename}"'
)
def step_fake_deepgram_returns_transcript(context, transcript: str, filename: str) -> None:
    _install_fake_deepgram_module(context)
    behaviors = _ensure_fake_deepgram_transcription_behaviors(context)
    behaviors[filename] = _FakeDeepgramTranscriptionBehavior(transcript=transcript)


@given('a fake Deepgram library is available that returns empty results for filename "{filename}"')
def step_fake_deepgram_returns_empty_results(context, filename: str) -> None:
    _install_fake_deepgram_module(context)
    behaviors = _ensure_fake_deepgram_transcription_behaviors(context)
    behaviors[filename] = _FakeDeepgramTranscriptionBehavior(
        transcript=None, response_type="empty_results"
    )


@given(
    'a fake Deepgram library is available that returns empty channels for filename "{filename}"'
)
def step_fake_deepgram_returns_empty_channels(context, filename: str) -> None:
    _install_fake_deepgram_module(context)
    behaviors = _ensure_fake_deepgram_transcription_behaviors(context)
    behaviors[filename] = _FakeDeepgramTranscriptionBehavior(
        transcript=None, response_type="empty_channels"
    )


@given(
    'a fake Deepgram library is available that returns empty alternatives for filename "{filename}"'
)
def step_fake_deepgram_returns_empty_alternatives(context, filename: str) -> None:
    _install_fake_deepgram_module(context)
    behaviors = _ensure_fake_deepgram_transcription_behaviors(context)
    behaviors[filename] = _FakeDeepgramTranscriptionBehavior(
        transcript=None, response_type="empty_alternatives"
    )


@given("a Deepgram API key is configured for this scenario")
def step_deepgram_api_key_configured(context) -> None:
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env["DEEPGRAM_API_KEY"] = "test-deepgram-key"


@given("the Deepgram dependency is unavailable")
def step_deepgram_dependency_unavailable(context) -> None:
    _install_deepgram_unavailable_module(context)


@then('the Deepgram transcription request used model "{model}"')
def step_deepgram_transcription_used_model(context, model: str) -> None:
    _ = context
    deepgram_module = sys.modules.get("deepgram")
    assert deepgram_module is not None
    assert getattr(deepgram_module, "last_transcription_model", None) == model


@then("the Deepgram transcription request used smart format true")
def step_deepgram_transcription_used_smart_format_true(context) -> None:
    _ = context
    deepgram_module = sys.modules.get("deepgram")
    assert deepgram_module is not None
    options: Dict[str, Any] = getattr(deepgram_module, "last_transcription_options", {})
    assert options.get("smart_format") is True


@then("the Deepgram transcription request used punctuate true")
def step_deepgram_transcription_used_punctuate_true(context) -> None:
    _ = context
    deepgram_module = sys.modules.get("deepgram")
    assert deepgram_module is not None
    options: Dict[str, Any] = getattr(deepgram_module, "last_transcription_options", {})
    assert options.get("punctuate") is True
