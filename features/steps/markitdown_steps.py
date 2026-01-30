from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Dict, Optional

from behave import given


@dataclass
class _FakeMarkItDownBehavior:
    mode: str
    text: Optional[str] = None


def _ensure_fake_markitdown_behaviors(context) -> Dict[str, _FakeMarkItDownBehavior]:
    behaviors = getattr(context, "fake_markitdown_behaviors", None)
    if behaviors is None:
        behaviors = {}
        context.fake_markitdown_behaviors = behaviors
    return behaviors


def _install_fake_markitdown_module(context) -> None:
    already_installed = getattr(context, "_fake_markitdown_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "markitdown",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    behaviors = _ensure_fake_markitdown_behaviors(context)

    class _ConversionResult:
        def __init__(self, text_content: object) -> None:
            self.text_content = text_content

    class MarkItDown:
        def __init__(self, *, enable_plugins: bool = False) -> None:
            self.enable_plugins = enable_plugins

        def convert(self, filename: str) -> object:
            base_name = filename.rsplit("/", 1)[-1]
            normalized_name = base_name.split("--", 1)[-1] if "--" in base_name else base_name
            behavior = behaviors.get(normalized_name)
            if behavior is None:
                return _ConversionResult("")
            if behavior.mode == "error":
                raise RuntimeError("fake markitdown error")
            if behavior.mode == "empty":
                return _ConversionResult("")
            if behavior.mode == "none":
                return None
            if behavior.mode == "string":
                return behavior.text or ""
            if behavior.mode == "nonstring":
                return _ConversionResult(123)
            if behavior.mode == "whitespace":
                return _ConversionResult("   ")
            if behavior.mode == "text":
                return _ConversionResult(behavior.text or "")
            return _ConversionResult("")

    markitdown_module = types.ModuleType("markitdown")
    markitdown_module.MarkItDown = MarkItDown
    markitdown_module.__biblicus_fake__ = True

    sys.modules["markitdown"] = markitdown_module

    context._fake_markitdown_installed = True
    context._fake_markitdown_original_modules = original_modules


def _install_markitdown_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_markitdown_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    if "markitdown" in sys.modules:
        original_modules["markitdown"] = sys.modules["markitdown"]

    markitdown_module = types.ModuleType("markitdown")
    sys.modules["markitdown"] = markitdown_module

    context._fake_markitdown_unavailable_installed = True
    context._fake_markitdown_unavailable_original_modules = original_modules


@given("a fake MarkItDown library is available")
def step_fake_markitdown_available(context) -> None:
    _install_fake_markitdown_module(context)


@given(
    'a fake MarkItDown library is available that returns text "{text}" for filename "{filename}"'
)
def step_fake_markitdown_returns_text(context, text: str, filename: str) -> None:
    _install_fake_markitdown_module(context)
    behaviors = _ensure_fake_markitdown_behaviors(context)
    behaviors[filename] = _FakeMarkItDownBehavior(mode="text", text=text)


@given('a fake MarkItDown library is available that returns empty output for filename "{filename}"')
def step_fake_markitdown_returns_empty(context, filename: str) -> None:
    _install_fake_markitdown_module(context)
    behaviors = _ensure_fake_markitdown_behaviors(context)
    behaviors[filename] = _FakeMarkItDownBehavior(mode="empty", text=None)


@given('a fake MarkItDown library is available that returns None for filename "{filename}"')
def step_fake_markitdown_returns_none(context, filename: str) -> None:
    _install_fake_markitdown_module(context)
    behaviors = _ensure_fake_markitdown_behaviors(context)
    behaviors[filename] = _FakeMarkItDownBehavior(mode="none", text=None)


@given('a fake MarkItDown library is available that returns a string for filename "{filename}"')
def step_fake_markitdown_returns_string(context, filename: str) -> None:
    _install_fake_markitdown_module(context)
    behaviors = _ensure_fake_markitdown_behaviors(context)
    behaviors[filename] = _FakeMarkItDownBehavior(mode="string", text="Extracted by MarkItDown")


@given(
    'a fake MarkItDown library is available that returns non-text output for filename "{filename}"'
)
def step_fake_markitdown_returns_nonstring(context, filename: str) -> None:
    _install_fake_markitdown_module(context)
    behaviors = _ensure_fake_markitdown_behaviors(context)
    behaviors[filename] = _FakeMarkItDownBehavior(mode="nonstring", text=None)


@given(
    'a fake MarkItDown library is available that raises a RuntimeError for filename "{filename}"'
)
def step_fake_markitdown_raises_error(context, filename: str) -> None:
    _install_fake_markitdown_module(context)
    behaviors = _ensure_fake_markitdown_behaviors(context)
    behaviors[filename] = _FakeMarkItDownBehavior(mode="error", text=None)


@given(
    'a fake MarkItDown library is available that returns whitespace output for filename "{filename}"'
)
def step_fake_markitdown_returns_whitespace(context, filename: str) -> None:
    _install_fake_markitdown_module(context)
    behaviors = _ensure_fake_markitdown_behaviors(context)
    behaviors[filename] = _FakeMarkItDownBehavior(mode="whitespace", text=None)


@given("the MarkItDown dependency is unavailable")
def step_markitdown_dependency_unavailable(context) -> None:
    _install_markitdown_unavailable_module(context)


@given("a fake MarkItDown library is available but marked as real")
def step_fake_markitdown_marked_real(context) -> None:
    _install_fake_markitdown_module(context)
    markitdown_module = sys.modules.get("markitdown")
    if markitdown_module is not None:
        markitdown_module.__biblicus_fake__ = False
    if not hasattr(context, "_original_sys_version_info"):
        context._original_sys_version_info = sys.version_info
    sys.version_info = (3, 9, 0, "final", 0)
