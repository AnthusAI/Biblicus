from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from behave import given, then, when

from biblicus.user_config import load_user_config, resolve_aldea_api_key


@dataclass
class _FakeAldeaTranscriptionBehavior:
    transcript: Optional[str]
    response_type: str = "normal"


def _ensure_fake_aldea_transcription_behaviors(
    context: Any,
) -> Dict[str, _FakeAldeaTranscriptionBehavior]:
    behaviors = getattr(context, "fake_aldea_transcriptions", None)
    if behaviors is None:
        behaviors = {}
        context.fake_aldea_transcriptions = behaviors
    return behaviors


def _aldea_response_json(
    context: Any,
) -> Dict[str, Any]:
    behaviors = _ensure_fake_aldea_transcription_behaviors(context)
    response_type = "normal"
    transcript = ""
    for _filename, behavior in behaviors.items():
        response_type = behavior.response_type
        transcript = behavior.transcript or ""
        break
    if response_type == "empty_results":
        return {"results": None}
    if response_type == "empty_channels":
        return {"results": {"channels": []}}
    if response_type == "empty_alternatives":
        return {"results": {"channels": [{"alternatives": []}]}}
    return {
        "metadata": {"request_id": "test", "duration": 0.0, "channels": 1},
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {"transcript": transcript, "confidence": 0.99},
                    ]
                }
            ]
        },
    }


def _fake_post_factory(context: Any):
    def fake_post(*args: Any, **kwargs: Any) -> MagicMock:
        context.last_aldea_request_params = kwargs.get("params") or {}
        context.last_aldea_request_headers = kwargs.get("headers") or {}
        response_json = _aldea_response_json(context)
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value=response_json)
        return response

    return fake_post


def _install_fake_aldea_httpx(context: Any) -> None:
    if getattr(context, "_aldea_post_patcher", None) is not None:
        return
    context._aldea_post_patcher = patch("httpx.post", new=_fake_post_factory(context))
    context._aldea_post_patcher.start()


def _install_aldea_unavailable_module(context: Any) -> None:
    # This test scenario is skipped due to subprocess isolation limitations.
    # See stt_aldea_extractor.feature for details.
    pass


@given("a fake Aldea library is available")
def step_fake_aldea_available(context: Any) -> None:
    _install_fake_aldea_httpx(context)


@given(
    'a fake Aldea library is available that returns transcript "{transcript}" for filename "{filename}"'
)
def step_fake_aldea_returns_transcript(
    context: Any, transcript: str, filename: str
) -> None:
    _install_fake_aldea_httpx(context)
    behaviors = _ensure_fake_aldea_transcription_behaviors(context)
    behaviors[filename] = _FakeAldeaTranscriptionBehavior(transcript=transcript)


@given('a fake Aldea library is available that returns empty results for filename "{filename}"')
def step_fake_aldea_returns_empty_results(context: Any, filename: str) -> None:
    _install_fake_aldea_httpx(context)
    behaviors = _ensure_fake_aldea_transcription_behaviors(context)
    behaviors[filename] = _FakeAldeaTranscriptionBehavior(
        transcript=None, response_type="empty_results"
    )


@given('a fake Aldea library is available that returns empty channels for filename "{filename}"')
def step_fake_aldea_returns_empty_channels(context: Any, filename: str) -> None:
    _install_fake_aldea_httpx(context)
    behaviors = _ensure_fake_aldea_transcription_behaviors(context)
    behaviors[filename] = _FakeAldeaTranscriptionBehavior(
        transcript=None, response_type="empty_channels"
    )


@given(
    'a fake Aldea library is available that returns empty alternatives for filename "{filename}"'
)
def step_fake_aldea_returns_empty_alternatives(context: Any, filename: str) -> None:
    _install_fake_aldea_httpx(context)
    behaviors = _ensure_fake_aldea_transcription_behaviors(context)
    behaviors[filename] = _FakeAldeaTranscriptionBehavior(
        transcript=None, response_type="empty_alternatives"
    )


@given("an Aldea API key is configured for this scenario")
@when("an Aldea API key is configured for this scenario")
def step_aldea_api_key_configured(context: Any) -> None:
    api_key = resolve_aldea_api_key()
    if not api_key and getattr(context, "repo_root", None) is not None:
        repo_root = context.repo_root
        candidate = repo_root / ".biblicus" / "config.yml"
        if candidate.is_file():
            loaded = load_user_config(paths=[candidate])
            if loaded.aldea is not None:
                api_key = loaded.aldea.api_key
    if not api_key:
        api_key = "test-aldea-key"
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env["ALDEA_API_KEY"] = api_key


@given("the Aldea dependency is unavailable")
def step_aldea_dependency_unavailable(context: Any) -> None:
    _install_aldea_unavailable_module(context)


@then('the Aldea transcription request used language "{language}"')
def step_aldea_transcription_used_language(context: Any, language: str) -> None:
    params: Dict[str, Any] = getattr(context, "last_aldea_request_params", {})
    assert params.get("language") == language
