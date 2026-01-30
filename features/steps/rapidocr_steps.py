from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Dict, List, Optional

from behave import given


@dataclass
class _FakeRapidOcrLine:
    text: str
    confidence: float


@dataclass
class _FakeRapidOcrBehavior:
    mode: str
    lines: Optional[List[_FakeRapidOcrLine]] = None


def _ensure_fake_rapidocr_behaviors(context) -> Dict[str, _FakeRapidOcrBehavior]:
    behaviors = getattr(context, "fake_rapidocr_behaviors", None)
    if behaviors is None:
        behaviors = {}
        context.fake_rapidocr_behaviors = behaviors
    return behaviors


def _install_fake_rapidocr_module(context) -> None:
    already_installed = getattr(context, "_fake_rapidocr_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "rapidocr_onnxruntime",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    class RapidOCR:
        def __call__(self, path: str):  # type: ignore[no-untyped-def]
            # Look up behaviors from context dynamically to support per-scenario reset
            behaviors = _ensure_fake_rapidocr_behaviors(context)
            base_name = path.rsplit("/", 1)[-1]
            normalized_name = base_name.split("--", 1)[-1] if "--" in base_name else base_name
            behavior = behaviors.get(normalized_name)
            if behavior is None:
                return (None, 0.0)
            if behavior.mode == "empty":
                return (None, 0.0)
            if behavior.mode == "mixed":
                return (
                    [
                        "not-a-list",
                        [1, 2],
                        [[[0, 0], [1, 0], [1, 1], [0, 1]], 123, 0.99],
                        [[[0, 0], [1, 0], [1, 1], [0, 1]], "bad-confidence", "not-a-number"],
                        [[[0, 0], [1, 0], [1, 1], [0, 1]], "too-low", 0.0],
                        [[[0, 0], [1, 0], [1, 1], [0, 1]], "   ", 1.0],
                        [[[0, 0], [1, 0], [1, 1], [0, 1]], "ok", 1.0],
                    ],
                    0.0,
                )
            if behavior.mode == "text":
                entries: list[list[object]] = []
                for line in behavior.lines or []:
                    entries.append(
                        [[[0, 0], [1, 0], [1, 1], [0, 1]], line.text, float(line.confidence)]
                    )
                return (entries, 0.0)
            return (None, 0.0)

    rapidocr_module = types.ModuleType("rapidocr_onnxruntime")
    rapidocr_module.RapidOCR = RapidOCR

    sys.modules["rapidocr_onnxruntime"] = rapidocr_module

    context._fake_rapidocr_installed = True
    context._fake_rapidocr_original_modules = original_modules


def _install_rapidocr_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_rapidocr_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "rapidocr_onnxruntime",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    rapidocr_module = types.ModuleType("rapidocr_onnxruntime")
    sys.modules["rapidocr_onnxruntime"] = rapidocr_module

    context._fake_rapidocr_unavailable_installed = True
    context._fake_rapidocr_unavailable_original_modules = original_modules


@given("a fake RapidOCR library is available")
def step_fake_rapidocr_available(context) -> None:
    _install_fake_rapidocr_module(context)


@given('a fake RapidOCR library is available that returns empty output for filename "{filename}"')
def step_fake_rapidocr_returns_empty(context, filename: str) -> None:
    _install_fake_rapidocr_module(context)
    behaviors = _ensure_fake_rapidocr_behaviors(context)
    behaviors[filename] = _FakeRapidOcrBehavior(mode="empty", lines=None)


@given("a fake RapidOCR library is available that returns lines:")
def step_fake_rapidocr_returns_lines(context) -> None:
    _install_fake_rapidocr_module(context)
    behaviors = _ensure_fake_rapidocr_behaviors(context)
    for row in context.table:
        filename = (row["filename"] if "filename" in row.headings else row[0]).strip()
        text = (row["text"] if "text" in row.headings else row[1]).strip()
        raw_confidence = (
            row["confidence"]
            if "confidence" in row.headings
            else (row[2] if len(row) > 2 else "1.0")
        )
        confidence = float(str(raw_confidence))
        behaviors[filename] = _FakeRapidOcrBehavior(
            mode="text", lines=[_FakeRapidOcrLine(text=text, confidence=confidence)]
        )


@given("the RapidOCR dependency is unavailable")
def step_rapidocr_dependency_unavailable(context) -> None:
    _install_rapidocr_unavailable_module(context)


@given('a fake RapidOCR library is available that returns a mixed result for filename "{filename}"')
def step_fake_rapidocr_returns_mixed(context, filename: str) -> None:
    _install_fake_rapidocr_module(context)
    behaviors = _ensure_fake_rapidocr_behaviors(context)
    behaviors[filename] = _FakeRapidOcrBehavior(mode="mixed", lines=None)
