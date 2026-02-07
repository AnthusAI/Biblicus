from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, Optional

from behave import given, then, when

from biblicus.user_config import load_user_config, resolve_deepgram_api_key


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

    class _Alternative:
        def __init__(self, transcript: str) -> None:
            self.transcript = transcript
            words = [
                {"word": word, "channel": 0, "speaker": 0}
                for word in transcript.split()
                if word
            ]
            self.words = words
            self.utterances = [
                {
                    "transcript": transcript,
                    "channel": 0,
                    "speaker": 0,
                }
            ]

    class _Channel:
        def __init__(self, alternatives: list) -> None:
            self.alternatives = alternatives

    class _Results:
        def __init__(self, channels: list) -> None:
            self.channels = channels
            alternatives = channels[0].alternatives if channels else []
            utterances = []
            words = []
            if alternatives:
                utterances = alternatives[0].utterances
                words = alternatives[0].words
            self.utterances = utterances
            self.words = words

    class _TranscriptionResponseNormal:
        def __init__(self, transcript: str) -> None:
            self.results = _Results([_Channel([_Alternative(transcript)])])

        def to_dict(self) -> Dict[str, Any]:
            alternatives = self.results.channels[0].alternatives if self.results.channels else []
            payload = {"results": {"channels": []}}
            if alternatives:
                alternative = alternatives[0]
                payload["results"]["channels"].append(
                    {
                        "alternatives": [
                            {
                                "transcript": alternative.transcript,
                                "words": alternative.words,
                                "utterances": alternative.utterances,
                            }
                        ]
                    }
                )
                payload["results"]["utterances"] = alternative.utterances
                payload["results"]["words"] = alternative.words
            return payload

    class _TranscriptionResponseNoResults:
        def __init__(self) -> None:
            self.results = None

        def to_dict(self) -> Dict[str, Any]:
            return {"results": None}

    class _TranscriptionResponseEmptyChannels:
        def __init__(self) -> None:
            self.results = _Results([])

        def to_dict(self) -> Dict[str, Any]:
            return {"results": {"channels": []}}

    class _TranscriptionResponseEmptyAlternatives:
        def __init__(self) -> None:
            self.results = _Results([_Channel([])])

        def to_dict(self) -> Dict[str, Any]:
            return {"results": {"channels": [{"alternatives": []}]}}

    class _TranscribeApi:
        def transcribe_file(self, *args: Any, **kwargs: Any) -> object:
            options = {key: value for key, value in kwargs.items() if key != "request"}
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

    class _ListenV1Media:
        def transcribe_file(self, *args: Any, **kwargs: Any) -> object:
            return _TranscribeApi().transcribe_file(*args, **kwargs)

    class _ListenV1:
        def __init__(self) -> None:
            self.media = _ListenV1Media()

    class _Listen:
        def __init__(self) -> None:
            self.v1 = _ListenV1()

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


@given('a fake Deepgram library is available that returns empty channels for filename "{filename}"')
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
@when("a Deepgram API key is configured for this scenario")
def step_deepgram_api_key_configured(context) -> None:
    api_key = resolve_deepgram_api_key()
    if not api_key and getattr(context, "repo_root", None) is not None:
        repo_root = context.repo_root
        candidate = repo_root / ".biblicus" / "config.yml"
        if candidate.is_file():
            loaded = load_user_config(paths=[candidate])
            if loaded.deepgram is not None:
                api_key = loaded.deepgram.api_key
    if not api_key:
        scenario = getattr(context, "scenario", None)
        tags = set(getattr(scenario, "tags", [])) if scenario else set()
        feature = getattr(context, "feature", None)
        if feature is not None:
            tags.update(getattr(feature, "tags", []))
        if "deepgram" in tags or "integration" in tags:
            if scenario is not None:
                scenario.skip("DEEPGRAM_API_KEY is required for Deepgram integration scenarios.")
            return
        api_key = "test-deepgram-key"
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env["DEEPGRAM_API_KEY"] = api_key


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
