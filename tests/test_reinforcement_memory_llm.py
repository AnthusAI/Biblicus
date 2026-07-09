from __future__ import annotations

import sys
import types

import biblicus.analysis.reinforcement_memory._llm as llm
from biblicus.analysis.reinforcement_memory import (
    openai_causal,
    openai_labeler,
    openai_synthesizer,
    resolve_llm_helpers,
)


def test_openai_labeler_uses_responses_api(monkeypatch):
    calls = []
    client_kwargs = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(output_text=" Medication Confirmation ")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            client_kwargs.append(kwargs)
            self.responses = FakeResponses()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(llm, "resolve_openai_api_key", lambda: "test-key")

    label = openai_labeler("gpt-test")(["medication", "confirmation"], ["example text"])

    assert label == "Medication Confirmation"
    assert client_kwargs == [{"api_key": "test-key", "timeout": 60.0, "max_retries": 1}]
    assert calls[0]["model"] == "gpt-test"
    assert calls[0]["instructions"] == llm._LABEL_SYSTEM
    assert calls[0]["reasoning"] == {"effort": "low"}
    assert calls[0]["max_output_tokens"] >= 200


def test_openai_causal_returns_none_when_provider_fails(monkeypatch):
    class FakeResponses:
        def create(self, **_kwargs):
            raise RuntimeError("provider down")

    class FakeOpenAI:
        def __init__(self, **_kwargs):
            self.responses = FakeResponses()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(llm, "resolve_openai_api_key", lambda: "test-key")

    cause = openai_causal("gpt-test")("reviewer comment", {"score_value": "No"})

    assert cause is None


def test_openai_synthesizer_uses_prompt_template(monkeypatch):
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return types.SimpleNamespace(output_text="Root cause summary")

    class FakeOpenAI:
        def __init__(self, **_kwargs):
            self.responses = FakeResponses()

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(llm, "resolve_openai_api_key", lambda: "test-key")

    summary = openai_synthesizer("gpt-test")(
        "Medication Topic",
        ["medication", "review"],
        ["Cause one", "Cause two"],
    )

    assert summary == "Root cause summary"
    prompt = calls[0]["input"][0]["content"]
    assert 'Cluster: "Medication Topic"' in prompt
    assert "Cause one" in prompt


def test_resolve_llm_helpers_prefers_openai_for_auto_when_key_exists(monkeypatch):
    captured = {}

    def fake_openai_labeler(model_id, *, timeout_seconds=None, max_retries=1):
        captured["label"] = (model_id, timeout_seconds, max_retries)
        return lambda keywords, exemplars: "openai-label"

    def fake_openai_causal(model_id, *, timeout_seconds=None, max_retries=1):
        captured["causal"] = (model_id, timeout_seconds, max_retries)
        return lambda text, context: "openai-cause"

    def fake_openai_synthesizer(model_id, *, timeout_seconds=None, max_retries=1):
        captured["synth"] = (model_id, timeout_seconds, max_retries)
        return lambda label, keywords, causes: "openai-synth"

    monkeypatch.setattr(llm, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(llm, "openai_labeler", fake_openai_labeler)
    monkeypatch.setattr(llm, "openai_causal", fake_openai_causal)
    monkeypatch.setattr(llm, "openai_synthesizer", fake_openai_synthesizer)

    label_fn, causal_fn, synth_fn = resolve_llm_helpers(
        "auto",
        model_id="gpt-test",
        timeout_seconds=12.5,
        max_retries=2,
    )

    assert label_fn([], []) == "openai-label"
    assert causal_fn("", {}) == "openai-cause"
    assert synth_fn("", [], []) == "openai-synth"
    assert captured == {
        "label": ("gpt-test", 12.5, 2),
        "causal": ("gpt-test", 12.5, 2),
        "synth": ("gpt-test", 12.5, 2),
    }


def test_resolve_llm_helpers_uses_luna_default_for_openai(monkeypatch):
    captured = {}

    def fake_openai_labeler(model_id, *, timeout_seconds=None, max_retries=1):
        captured["label_model"] = model_id
        return lambda keywords, exemplars: "openai-label"

    def fake_openai_causal(model_id, *, timeout_seconds=None, max_retries=1):
        captured["causal_model"] = model_id
        return lambda text, context: "openai-cause"

    def fake_openai_synthesizer(model_id, *, timeout_seconds=None, max_retries=1):
        captured["synth_model"] = model_id
        return lambda label, keywords, causes: "openai-synth"

    monkeypatch.setattr(llm, "openai_labeler", fake_openai_labeler)
    monkeypatch.setattr(llm, "openai_causal", fake_openai_causal)
    monkeypatch.setattr(llm, "openai_synthesizer", fake_openai_synthesizer)

    label_fn, causal_fn, synth_fn = resolve_llm_helpers("openai")

    assert label_fn([], []) == "openai-label"
    assert causal_fn("", {}) == "openai-cause"
    assert synth_fn("", [], []) == "openai-synth"
    assert captured == {
        "label_model": "gpt-5.6-luna",
        "causal_model": "gpt-5.6-luna",
        "synth_model": "gpt-5.6-luna",
    }


def test_resolve_llm_helpers_supports_explicit_bedrock(monkeypatch):
    captured = {}

    def fake_bedrock_labeler(model_id, region):
        captured["label"] = (model_id, region)
        return lambda keywords, exemplars: "bedrock-label"

    def fake_bedrock_causal(model_id, region):
        captured["causal"] = (model_id, region)
        return lambda text, context: "bedrock-cause"

    def fake_bedrock_synthesizer(model_id, region):
        captured["synth"] = (model_id, region)
        return lambda label, keywords, causes: "bedrock-synth"

    monkeypatch.setattr(llm, "bedrock_labeler", fake_bedrock_labeler)
    monkeypatch.setattr(llm, "bedrock_causal", fake_bedrock_causal)
    monkeypatch.setattr(llm, "bedrock_synthesizer", fake_bedrock_synthesizer)

    label_fn, causal_fn, synth_fn = resolve_llm_helpers(
        "bedrock",
        model_id="bedrock-model",
        region="us-west-2",
    )

    assert label_fn([], []) == "bedrock-label"
    assert causal_fn("", {}) == "bedrock-cause"
    assert synth_fn("", [], []) == "bedrock-synth"
    assert captured == {
        "label": ("bedrock-model", "us-west-2"),
        "causal": ("bedrock-model", "us-west-2"),
        "synth": ("bedrock-model", "us-west-2"),
    }
