from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, Optional

from behave import given


@dataclass
class _FakeRequestsResponse:
    status_code: int
    content: bytes
    text: str

    def json(self) -> Any:
        import json
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@dataclass
class _FakeRequestsBehavior:
    response_text: Optional[str]
    status_code: int = 200


def _ensure_fake_requests_behaviors(context) -> Dict[str, _FakeRequestsBehavior]:
    behaviors = getattr(context, "fake_requests_behaviors", None)
    if behaviors is None:
        behaviors = {}
        context.fake_requests_behaviors = behaviors
    return behaviors


def _install_fake_requests_module(context) -> None:
    already_installed = getattr(context, "_fake_requests_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "requests",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    # IMPORTANT: Remove requests from sys.modules if it was already imported
    # so that future imports will get our fake version
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]

    def post(url: str, **kwargs: Any) -> _FakeRequestsResponse:
        # Look up behaviors dynamically
        behaviors = _ensure_fake_requests_behaviors(context)
        behavior = behaviors.get(url)
        if behavior is None:
            # Default: return error for unmocked URLs
            return _FakeRequestsResponse(
                status_code=500,
                content=b"Unmocked URL",
                text="Unmocked URL"
            )
        return _FakeRequestsResponse(
            status_code=behavior.status_code,
            content=(behavior.response_text or "").encode("utf-8"),
            text=behavior.response_text or ""
        )

    requests_module = types.ModuleType("requests")
    requests_module.post = post

    sys.modules["requests"] = requests_module

    context._fake_requests_installed = True
    context._fake_requests_original_modules = original_modules


@given("a fake requests library is available")
def step_fake_requests_available(context) -> None:
    _install_fake_requests_module(context)


@given('a fake requests library returns "{response_text}" for URL "{url}"')
def step_fake_requests_returns_text(context, response_text: str, url: str) -> None:
    # Behave passes escaped backslashes literally, so if the Gherkin has "\"foo\"",
    # we receive '\"foo\"' and need to decode it to '"foo"'
    # But if there are no backslashes, don't decode (to avoid breaking normal strings)
    if '\\' in response_text:
        import codecs
        decoded_text = codecs.decode(response_text, 'unicode_escape')
    else:
        decoded_text = response_text
    _install_fake_requests_module(context)
    behaviors = _ensure_fake_requests_behaviors(context)
    behaviors[url] = _FakeRequestsBehavior(response_text=decoded_text)


@given('a fake requests library returns error {status_code:d} for URL "{url}"')
def step_fake_requests_returns_error(context, status_code: int, url: str) -> None:
    _install_fake_requests_module(context)
    behaviors = _ensure_fake_requests_behaviors(context)
    behaviors[url] = _FakeRequestsBehavior(response_text="Error", status_code=status_code)


@given('a fake requests library returns HuggingFace OCR response for model "{model_id}" with text "{text}"')
def step_fake_requests_returns_huggingface_ocr_response(context, model_id: str, text: str) -> None:
    import json
    _install_fake_requests_module(context)
    behaviors = _ensure_fake_requests_behaviors(context)
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    response_payload = {"generated_text": text, "confidence": 0.95}
    behaviors[api_url] = _FakeRequestsBehavior(response_text=json.dumps(response_payload))


@given('a fake requests library returns HuggingFace string response for model "{model_id}" with value "{text}"')
def step_fake_requests_returns_huggingface_string_response(context, model_id: str, text: str) -> None:
    import json
    _install_fake_requests_module(context)
    behaviors = _ensure_fake_requests_behaviors(context)
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    behaviors[api_url] = _FakeRequestsBehavior(response_text=json.dumps(text))


@given('a fake requests library returns HuggingFace list response for model "{model_id}" with text "{text}"')
def step_fake_requests_returns_huggingface_list_response(context, model_id: str, text: str) -> None:
    import json
    _install_fake_requests_module(context)
    behaviors = _ensure_fake_requests_behaviors(context)
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    response_payload = [{"generated_text": text, "confidence": 0.88}]
    behaviors[api_url] = _FakeRequestsBehavior(response_text=json.dumps(response_payload))


@given('a fake requests library returns HuggingFace OCR response without confidence for model "{model_id}" with text "{text}"')
def step_fake_requests_returns_huggingface_no_confidence(context, model_id: str, text: str) -> None:
    import json
    _install_fake_requests_module(context)
    behaviors = _ensure_fake_requests_behaviors(context)
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    response_payload = {"generated_text": text}  # No confidence field
    behaviors[api_url] = _FakeRequestsBehavior(response_text=json.dumps(response_payload))


@given('a fake requests library returns HuggingFace list OCR response without confidence for model "{model_id}" with text "{text}"')
def step_fake_requests_returns_huggingface_list_no_confidence(context, model_id: str, text: str) -> None:
    import json
    _install_fake_requests_module(context)
    behaviors = _ensure_fake_requests_behaviors(context)
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    response_payload = [{"generated_text": text}]  # No confidence field
    behaviors[api_url] = _FakeRequestsBehavior(response_text=json.dumps(response_payload))
