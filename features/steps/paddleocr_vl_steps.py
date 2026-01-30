from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Dict, List, Optional

from behave import given


class _BlockPaddleImportHook:
    """Import hook that blocks paddle-related imports."""

    def find_module(self, fullname, path=None):  # type: ignore[no-untyped-def]
        if "paddle" in fullname.lower():
            return self
        return None

    def load_module(self, fullname):  # type: ignore[no-untyped-def]
        raise ImportError(f"Paddle module {fullname!r} is unavailable for testing")


@dataclass
class _FakePaddleOcrVlLine:
    text: str
    confidence: float


@dataclass
class _FakePaddleOcrVlBehavior:
    mode: str
    lines: Optional[List[_FakePaddleOcrVlLine]] = None


def _ensure_fake_paddleocr_vl_behaviors(context) -> Dict[str, _FakePaddleOcrVlBehavior]:
    behaviors = getattr(context, "fake_paddleocr_vl_behaviors", None)
    if behaviors is None:
        behaviors = {}
        context.fake_paddleocr_vl_behaviors = behaviors
    return behaviors


def _install_fake_paddleocr_module(context) -> None:
    already_installed = getattr(context, "_fake_paddleocr_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "paddleocr",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    class PaddleOCR:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            pass

        def ocr(self, path: str, cls: bool = True):  # type: ignore[no-untyped-def]
            # Look up behaviors from context dynamically to support per-scenario reset
            behaviors = _ensure_fake_paddleocr_vl_behaviors(context)
            base_name = path.rsplit("/", 1)[-1]
            normalized_name = base_name.split("--", 1)[-1] if "--" in base_name else base_name
            behavior = behaviors.get(normalized_name)
            if behavior is None:
                return None
            if behavior.mode == "empty":
                return None
            if behavior.mode == "text":
                page_result: list[list[object]] = []
                for line in behavior.lines or []:
                    page_result.append(
                        [
                            [[0, 0], [100, 0], [100, 20], [0, 20]],
                            [line.text, float(line.confidence)],
                        ]
                    )
                return [page_result]
            if behavior.mode == "malformed":
                # Return malformed data to test defensive code (with one valid line)
                # Return format: list of page_results, each page_result is a list of line_results
                # line_result format: [coordinates, text_info] where text_info is [text, confidence]
                return [
                    [[[[0, 0]], ["valid", 0.95]]],  # Valid page with valid line
                    None,  # None page - line 197 continue
                    [None],  # Page with None line_result - line 199 continue
                    [["bad"]],  # Page with line_result len < 2 - line 200 continue
                    [
                        [[[0, 0]], "not-a-list"]
                    ],  # Page with line where text_info not list - 202 fails
                    [[[[0, 0]], ["text", "not-number"]]],  # Page with non-numeric conf - 205 False
                    [[[[0, 0]], [123, 0.95]]],  # Page with non-string text - 208 False
                    [[[[0, 0]], ["", 0.95]]],  # Page with empty text - 208 False
                    [[[[0, 0]], ["   ", 0.95]]],  # Page with whitespace-only text - 208 False
                ]
            if behavior.mode == "malformed-empty":
                # Return malformed data with no valid lines (all defensive code paths hit, no extraction)
                return [
                    None,  # None page - line 197 continue
                    [None],  # Page with None line_result - line 199 continue
                    [["bad"]],  # Page with line_result len < 2 - line 200 continue
                    [
                        [[[0, 0]], "not-a-list"]
                    ],  # Page with line where text_info not list - 202 fails
                    [[[[0, 0]], ["text", "not-number"]]],  # Page with non-numeric conf - 205 False
                    [[[[0, 0]], [123, 0.95]]],  # Page with non-string text - 208 False
                    [[[[0, 0]], ["", 0.95]]],  # Page with empty text - 208 False
                    [[[[0, 0]], ["   ", 0.95]]],  # Page with whitespace-only text - 208 False
                ]
            return None

    paddleocr_module = types.ModuleType("paddleocr")
    paddleocr_module.PaddleOCR = PaddleOCR

    sys.modules["paddleocr"] = paddleocr_module

    context._fake_paddleocr_installed = True
    context._fake_paddleocr_original_modules = original_modules


def _install_paddleocr_unavailable_module(context) -> None:
    already_installed = getattr(context, "_fake_paddleocr_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}

    # Remove all paddle-related modules to prevent import
    paddle_module_names = [name for name in list(sys.modules.keys()) if "paddle" in name.lower()]
    for name in paddle_module_names:
        original_modules[name] = sys.modules[name]
        del sys.modules[name]

    # Install import hook to block future imports
    hook = _BlockPaddleImportHook()
    sys.meta_path.insert(0, hook)

    context._fake_paddleocr_unavailable_installed = True
    context._fake_paddleocr_unavailable_original_modules = original_modules
    context._fake_paddleocr_import_hook = hook


@given("a fake PaddleOCR library is available")
def step_fake_paddleocr_available(context) -> None:
    _install_fake_paddleocr_module(context)


@given('a fake PaddleOCR library is available that returns empty output for filename "{filename}"')
def step_fake_paddleocr_returns_empty(context, filename: str) -> None:
    _install_fake_paddleocr_module(context)
    behaviors = _ensure_fake_paddleocr_vl_behaviors(context)
    behaviors[filename] = _FakePaddleOcrVlBehavior(mode="empty", lines=None)


@given("a fake PaddleOCR library is available that returns lines:")
def step_fake_paddleocr_returns_lines(context) -> None:
    _install_fake_paddleocr_module(context)
    behaviors = _ensure_fake_paddleocr_vl_behaviors(context)
    for row in context.table:
        filename = (row["filename"] if "filename" in row.headings else row[0]).strip()
        text = (row["text"] if "text" in row.headings else row[1]).strip()
        raw_confidence = (
            row["confidence"]
            if "confidence" in row.headings
            else (row[2] if len(row) > 2 else "1.0")
        )
        confidence = float(str(raw_confidence))
        existing_behavior = behaviors.get(filename)
        if existing_behavior and existing_behavior.lines:
            existing_behavior.lines.append(_FakePaddleOcrVlLine(text=text, confidence=confidence))
        else:
            behaviors[filename] = _FakePaddleOcrVlBehavior(
                mode="text", lines=[_FakePaddleOcrVlLine(text=text, confidence=confidence)]
            )


@given("the PaddleOCR dependency is unavailable")
def step_paddleocr_dependency_unavailable(context) -> None:
    _install_paddleocr_unavailable_module(context)


@given('a fake PaddleOCR library returns malformed output for filename "{filename}"')
def step_fake_paddleocr_returns_malformed(context, filename: str) -> None:
    _install_fake_paddleocr_module(context)
    behaviors = _ensure_fake_paddleocr_vl_behaviors(context)
    behaviors[filename] = _FakePaddleOcrVlBehavior(mode="malformed", lines=None)


@given('a fake PaddleOCR library returns malformed empty output for filename "{filename}"')
def step_fake_paddleocr_returns_malformed_empty(context, filename: str) -> None:
    _install_fake_paddleocr_module(context)
    behaviors = _ensure_fake_paddleocr_vl_behaviors(context)
    behaviors[filename] = _FakePaddleOcrVlBehavior(mode="malformed-empty", lines=None)
