from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from behave import given, then


@dataclass
class _FakeOpenAiTranscriptionBehavior:
    transcript: Optional[str]
    result_kind: str = "object"
    no_speech_probabilities: Optional[List[float]] = None
    segments_payload: Optional[List[Any]] = None


@dataclass
class _FakeOpenAiChatBehavior:
    response: str
    match_text: Optional[str] = None


def _ensure_fake_openai_transcription_behaviors(
    context,
) -> Dict[str, _FakeOpenAiTranscriptionBehavior]:
    behaviors = getattr(context, "fake_openai_transcriptions", None)
    if behaviors is None:
        behaviors = {}
        context.fake_openai_transcriptions = behaviors
    return behaviors


def _ensure_fake_openai_chat_behaviors(context) -> List[_FakeOpenAiChatBehavior]:
    behaviors = getattr(context, "fake_openai_chat_behaviors", None)
    if behaviors is None:
        behaviors = []
        context.fake_openai_chat_behaviors = behaviors
    return behaviors


def _install_fake_openai_module(context) -> None:
    already_installed = getattr(context, "_fake_openai_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "openai",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    behaviors = _ensure_fake_openai_transcription_behaviors(context)
    chat_behaviors = _ensure_fake_openai_chat_behaviors(context)

    class _TranscriptionResult:
        def __init__(self, text: str) -> None:
            self.text = text

    class _TranscriptionsApi:
        def create(self, *, file, model: str, **kwargs):  # type: ignore[no-untyped-def]
            openai_module.last_transcription_model = model  # type: ignore[attr-defined]
            openai_module.last_transcription_kwargs = dict(kwargs)  # type: ignore[attr-defined]
            filename = getattr(file, "name", "unknown")
            base_name = filename.rsplit("/", 1)[-1]
            normalized_name = base_name.split("--", 1)[-1] if "--" in base_name else base_name
            openai_module.last_transcription_filename = normalized_name  # type: ignore[attr-defined]
            behavior = behaviors.get(normalized_name)
            transcript = behavior.transcript if behavior is not None else ""
            transcript_text = str(transcript or "")
            if behavior is not None and behavior.result_kind == "dict":
                return {"text": transcript_text}
            if behavior is not None and behavior.result_kind == "verbose_json":
                if behavior.segments_payload is not None:
                    return {"text": transcript_text, "segments": behavior.segments_payload}
                probabilities = behavior.no_speech_probabilities or []
                segments = [{"no_speech_prob": float(value)} for value in probabilities]
                return {"text": transcript_text, "segments": segments}
            return _TranscriptionResult(transcript_text)

    class _AudioApi:
        def __init__(self) -> None:
            self.transcriptions = _TranscriptionsApi()

    class _ChatCompletionMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class _ChatCompletionChoice:
        def __init__(self, content: str) -> None:
            self.message = _ChatCompletionMessage(content)

    class _ChatCompletionResult:
        def __init__(self, content: str) -> None:
            self.choices = [_ChatCompletionChoice(content)]

    class _ChatCompletionsApi:
        def create(self, *, model: str, messages: List[Dict[str, Any]], **kwargs):  # type: ignore[no-untyped-def]
            openai_module.last_chat_model = model  # type: ignore[attr-defined]
            openai_module.last_chat_messages = list(messages)  # type: ignore[attr-defined]
            openai_module.last_chat_kwargs = dict(kwargs)  # type: ignore[attr-defined]
            prompt_text = "\n".join(str(message.get("content", "")) for message in messages)
            openai_module.last_chat_prompt = prompt_text  # type: ignore[attr-defined]
            response_text = ""
            for behavior in chat_behaviors:
                if behavior.match_text is None or behavior.match_text in prompt_text:
                    response_text = behavior.response
                    break
            return _ChatCompletionResult(response_text)

    class _ChatApi:
        def __init__(self) -> None:
            self.completions = _ChatCompletionsApi()

    class OpenAI:  # noqa: N801 - external dependency uses PascalCase
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            openai_module.last_api_key = kwargs.get("api_key")  # type: ignore[attr-defined]
            self.audio = _AudioApi()
            self.chat = _ChatApi()

    openai_module = types.ModuleType("openai")
    openai_module.OpenAI = OpenAI
    openai_module.last_api_key = None
    openai_module.last_transcription_filename = None
    openai_module.last_transcription_model = None
    openai_module.last_transcription_kwargs = {}
    openai_module.last_chat_model = None
    openai_module.last_chat_messages = []
    openai_module.last_chat_kwargs = {}
    openai_module.last_chat_prompt = None

    sys.modules["openai"] = openai_module

    context._fake_openai_installed = True
    context._fake_openai_original_modules = original_modules


def _install_openai_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_openai_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "openai",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    openai_module = types.ModuleType("openai")
    sys.modules["openai"] = openai_module

    context._fake_openai_unavailable_installed = True
    context._fake_openai_unavailable_original_modules = original_modules


@given("a fake OpenAI library is available")
def step_fake_openai_available(context) -> None:
    _install_fake_openai_module(context)


@given(
    'a fake OpenAI library is available that returns chat completion "{response}" for any prompt'
)
def step_fake_openai_returns_chat_completion(context, response: str) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_chat_behaviors(context)
    behaviors.append(_FakeOpenAiChatBehavior(response=response))


@given('a fake OpenAI library is available that returns chat completion "" for any prompt')
def step_fake_openai_returns_empty_chat_completion(context) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_chat_behaviors(context)
    behaviors.append(_FakeOpenAiChatBehavior(response=""))


@given(
    'a fake OpenAI library is available that returns chat completion "{response}" '
    'for prompt containing "{match_text}"'
)
def step_fake_openai_returns_chat_completion_for_prompt(
    context, response: str, match_text: str
) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_chat_behaviors(context)
    behaviors.append(_FakeOpenAiChatBehavior(response=response, match_text=match_text))


@given(
    'a fake OpenAI library is available that returns transcript "{transcript}" for filename "{filename}"'
)
def step_fake_openai_returns_transcript(context, transcript: str, filename: str) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_transcription_behaviors(context)
    behaviors[filename] = _FakeOpenAiTranscriptionBehavior(transcript=transcript)


@given(
    'a fake OpenAI library is available that returns a dict transcript "{transcript}" for filename "{filename}"'
)
def step_fake_openai_returns_dict_transcript(context, transcript: str, filename: str) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_transcription_behaviors(context)
    behaviors[filename] = _FakeOpenAiTranscriptionBehavior(
        transcript=transcript, result_kind="dict"
    )


@given(
    'a fake OpenAI library is available that returns verbose transcript "{transcript}" '
    'with no speech probabilities "{no_speech_probabilities}" for filename "{filename}"'
)
def step_fake_openai_returns_verbose_json_transcript(
    context,
    transcript: str,
    no_speech_probabilities: str,
    filename: str,
) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_transcription_behaviors(context)
    parsed: list[float] = []
    for token in (no_speech_probabilities or "").split(","):
        token = token.strip()
        if not token:
            continue
        parsed.append(float(token))
    behaviors[filename] = _FakeOpenAiTranscriptionBehavior(
        transcript=transcript,
        result_kind="verbose_json",
        no_speech_probabilities=parsed,
    )


@given(
    'a fake OpenAI library is available that returns verbose transcript "{transcript}" '
    'with segments "{segments_json}" for filename "{filename}"'
)
def step_fake_openai_returns_verbose_json_with_segments(
    context,
    transcript: str,
    segments_json: str,
    filename: str,
) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_transcription_behaviors(context)
    parsed = json.loads(segments_json)
    if not isinstance(parsed, list):
        raise AssertionError("segments_json must decode to a list")
    behaviors[filename] = _FakeOpenAiTranscriptionBehavior(
        transcript=transcript,
        result_kind="verbose_json",
        segments_payload=parsed,
    )


@given(
    'a fake OpenAI library is available that returns verbose transcript "{transcript}" '
    'for filename "{filename}" with segments:'
)
def step_fake_openai_returns_verbose_json_with_segments_block(
    context,
    transcript: str,
    filename: str,
) -> None:
    _install_fake_openai_module(context)
    behaviors = _ensure_fake_openai_transcription_behaviors(context)
    raw = (context.text or "").strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise AssertionError("segments JSON must decode to a list")
    behaviors[filename] = _FakeOpenAiTranscriptionBehavior(
        transcript=transcript,
        result_kind="verbose_json",
        segments_payload=parsed,
    )


@then('the OpenAI transcription request used response format "{response_format}"')
def step_openai_transcription_used_response_format(context, response_format: str) -> None:
    _ = context
    openai_module = sys.modules.get("openai")
    assert openai_module is not None
    kwargs: Dict[str, Any] = getattr(openai_module, "last_transcription_kwargs", {})
    assert kwargs.get("response_format") == response_format


@given("an OpenAI API key is configured for this scenario")
def step_openai_api_key_configured(context) -> None:
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env["OPENAI_API_KEY"] = "test-openai-key"


@given("the OpenAI dependency is unavailable")
def step_openai_dependency_unavailable(context) -> None:
    _install_openai_unavailable_module(context)


@given('the OpenAI client was configured with API key "{expected_api_key}"')
@then('the OpenAI client was configured with API key "{expected_api_key}"')
def step_openai_client_configured_with_api_key(context, expected_api_key: str) -> None:
    _ = context
    openai_module = sys.modules.get("openai")
    assert openai_module is not None
    configured = getattr(openai_module, "last_api_key", None)
    assert configured == expected_api_key
