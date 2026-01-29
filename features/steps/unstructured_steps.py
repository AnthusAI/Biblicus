from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Dict, Optional

from behave import given


@dataclass
class _FakeUnstructuredBehavior:
    mode: str
    text: Optional[str] = None


def _ensure_fake_unstructured_behaviors(context) -> Dict[str, _FakeUnstructuredBehavior]:
    behaviors = getattr(context, "fake_unstructured_behaviors", None)
    if behaviors is None:
        behaviors = {}
        context.fake_unstructured_behaviors = behaviors
    return behaviors


def _install_fake_unstructured_module(context) -> None:
    already_installed = getattr(context, "_fake_unstructured_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "unstructured",
        "unstructured.partition",
        "unstructured.partition.auto",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    behaviors = _ensure_fake_unstructured_behaviors(context)

    class _Element:
        def __init__(self, text: str) -> None:
            self.text = text

    def partition(*, filename: str, **kwargs):  # type: ignore[no-untyped-def]
        _ = kwargs
        base_name = filename.rsplit("/", 1)[-1]
        normalized_name = base_name.split("--", 1)[-1] if "--" in base_name else base_name
        behavior = behaviors.get(normalized_name)
        if behavior is None:
            return []
        if behavior.mode == "error":
            raise RuntimeError("fake unstructured error")
        if behavior.mode == "empty":
            return []
        if behavior.mode == "whitespace":
            return [_Element("   ")]
        if behavior.mode == "text":
            return [_Element(behavior.text or "")]
        return []

    unstructured_module = types.ModuleType("unstructured")
    partition_module = types.ModuleType("unstructured.partition")
    auto_module = types.ModuleType("unstructured.partition.auto")
    auto_module.partition = partition

    sys.modules["unstructured"] = unstructured_module
    sys.modules["unstructured.partition"] = partition_module
    sys.modules["unstructured.partition.auto"] = auto_module

    context._fake_unstructured_installed = True
    context._fake_unstructured_original_modules = original_modules


def _install_unstructured_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_unstructured_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "unstructured",
        "unstructured.partition",
        "unstructured.partition.auto",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    unstructured_module = types.ModuleType("unstructured")
    sys.modules["unstructured"] = unstructured_module
    sys.modules.pop("unstructured.partition", None)
    sys.modules.pop("unstructured.partition.auto", None)

    context._fake_unstructured_unavailable_installed = True
    context._fake_unstructured_unavailable_original_modules = original_modules


@given("a fake Unstructured library is available")
def step_fake_unstructured_available(context) -> None:
    _install_fake_unstructured_module(context)


@given(
    'a fake Unstructured library is available that returns text "{text}" for filename "{filename}"'
)
def step_fake_unstructured_returns_text(context, text: str, filename: str) -> None:
    _install_fake_unstructured_module(context)
    behaviors = _ensure_fake_unstructured_behaviors(context)
    behaviors[filename] = _FakeUnstructuredBehavior(mode="text", text=text)


@given(
    'a fake Unstructured library is available that returns empty output for filename "{filename}"'
)
def step_fake_unstructured_returns_empty(context, filename: str) -> None:
    _install_fake_unstructured_module(context)
    behaviors = _ensure_fake_unstructured_behaviors(context)
    behaviors[filename] = _FakeUnstructuredBehavior(mode="empty", text=None)


@given(
    'a fake Unstructured library is available that raises a RuntimeError for filename "{filename}"'
)
def step_fake_unstructured_raises_error(context, filename: str) -> None:
    _install_fake_unstructured_module(context)
    behaviors = _ensure_fake_unstructured_behaviors(context)
    behaviors[filename] = _FakeUnstructuredBehavior(mode="error", text=None)


@given(
    'a fake Unstructured library is available that returns whitespace output for filename "{filename}"'
)
def step_fake_unstructured_returns_whitespace(context, filename: str) -> None:
    _install_fake_unstructured_module(context)
    behaviors = _ensure_fake_unstructured_behaviors(context)
    behaviors[filename] = _FakeUnstructuredBehavior(mode="whitespace", text=None)


@given("the Unstructured dependency is unavailable")
def step_unstructured_dependency_unavailable(context) -> None:
    _install_unstructured_unavailable_module(context)
