"""
Step definitions for Docling extractor BDD tests.

This module provides fake Docling library implementations for testing.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from typing import Dict, Optional

from behave import given


@dataclass
class _FakeDoclingBehavior:
    """
    Behavior specification for fake Docling conversions.

    :ivar mode: Behavior mode (text, empty, error).
    :vartype mode: str
    :ivar text: Text content to return.
    :vartype text: str or None
    :ivar output_formats: Output text per format.
    :vartype output_formats: dict[str, str]
    """

    mode: str
    text: Optional[str] = None
    output_formats: Dict[str, str] = field(default_factory=dict)


def _ensure_fake_docling_behaviors(context) -> Dict[str, _FakeDoclingBehavior]:
    """
    Ensure the fake Docling behaviors dictionary exists on the context.

    :param context: Behave context.
    :type context: behave.runner.Context
    :return: Behaviors dictionary.
    :rtype: dict[str, _FakeDoclingBehavior]
    """
    behaviors = getattr(context, "fake_docling_behaviors", None)
    if behaviors is None:
        behaviors = {}
        context.fake_docling_behaviors = behaviors
    return behaviors


def _install_fake_docling_module(context, *, with_mlx: bool = True) -> None:
    """
    Install a fake Docling module into sys.modules.

    :param context: Behave context.
    :type context: behave.runner.Context
    :param with_mlx: Whether to include MLX backend support.
    :type with_mlx: bool
    """
    already_installed = getattr(context, "_fake_docling_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "docling",
        "docling.document_converter",
        "docling.pipeline_options",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    behaviors = _ensure_fake_docling_behaviors(context)

    class _FakeDocument:
        """Fake Docling document with export methods."""

        def __init__(self, text: str, output_formats: Dict[str, str]) -> None:
            self._text = text
            self._output_formats = output_formats

        def export_to_markdown(self) -> str:
            if "markdown" in self._output_formats:
                return self._output_formats["markdown"]
            return self._text

        def export_to_html(self) -> str:
            if "html" in self._output_formats:
                return self._output_formats["html"]
            return self._text

        def export_to_text(self) -> str:
            if "text" in self._output_formats:
                return self._output_formats["text"]
            return self._text

    class _FakeConversionResult:
        """Fake Docling conversion result."""

        def __init__(self, text: str, output_formats: Dict[str, str]) -> None:
            self.document = _FakeDocument(text, output_formats)

    class DocumentConverterOptions:
        """Fake DocumentConverterOptions."""

        def __init__(self, *, pipeline_options=None) -> None:
            self.pipeline_options = pipeline_options

    class VlmPipelineOptions:
        """Fake VlmPipelineOptions."""

        def __init__(self, *, vlm_options=None) -> None:
            self.vlm_options = vlm_options

    class _VlmModelSpecs:
        """Fake vlm_model_specs with model constants."""

        def __init__(self, with_mlx: bool) -> None:
            self._with_mlx = with_mlx

        @property
        def SMOLDOCLING_MLX(self):
            if not self._with_mlx:
                raise AttributeError("MLX backend not available")
            return "smoldocling-mlx"

        @property
        def SMOLDOCLING_TRANSFORMERS(self):
            return "smoldocling-transformers"

        @property
        def GRANITE_DOCLING_MLX(self):
            if not self._with_mlx:
                raise AttributeError("MLX backend not available")
            return "granite-docling-mlx"

        @property
        def GRANITE_DOCLING_TRANSFORMERS(self):
            return "granite-docling-transformers"

    vlm_model_specs = _VlmModelSpecs(with_mlx)

    class InputFormat:
        PDF = "pdf"

    class PdfFormatOption:
        def __init__(self, *, pipeline_options=None) -> None:
            self.pipeline_options = pipeline_options

    class DocumentConverter:
        """Fake DocumentConverter."""

        def __init__(self, *, format_options=None) -> None:
            self.format_options = format_options

        def convert(self, filename: str) -> _FakeConversionResult:
            base_name = filename.rsplit("/", 1)[-1]
            normalized_name = base_name.split("--", 1)[-1] if "--" in base_name else base_name
            behavior = behaviors.get(normalized_name)
            if behavior is None:
                return _FakeConversionResult("", {})
            if behavior.mode == "error":
                raise RuntimeError("fake docling error")
            if behavior.mode == "empty":
                return _FakeConversionResult("", behavior.output_formats)
            if behavior.mode == "text":
                return _FakeConversionResult(behavior.text or "", behavior.output_formats)
            return _FakeConversionResult("", {})

    docling_module = types.ModuleType("docling")
    converter_module = types.ModuleType("docling.document_converter")
    format_module = types.ModuleType("docling.format_options")
    options_module = types.ModuleType("docling.pipeline_options")

    converter_module.DocumentConverter = DocumentConverter
    converter_module.DocumentConverterOptions = DocumentConverterOptions
    format_module.InputFormat = InputFormat
    format_module.PdfFormatOption = PdfFormatOption
    options_module.VlmPipelineOptions = VlmPipelineOptions
    options_module.vlm_model_specs = vlm_model_specs

    sys.modules["docling"] = docling_module
    sys.modules["docling.document_converter"] = converter_module
    sys.modules["docling.format_options"] = format_module
    sys.modules["docling.pipeline_options"] = options_module

    context._fake_docling_installed = True
    context._fake_docling_original_modules = original_modules
    context._fake_docling_with_mlx = with_mlx


def _install_docling_unavailable_module(context) -> None:
    """
    Install a fake Docling module that raises ImportError for key classes.

    :param context: Behave context.
    :type context: behave.runner.Context
    """
    already_installed = getattr(context, "_fake_docling_unavailable_installed", False)
    if already_installed:
        return

    original_modules: Dict[str, object] = {}
    module_names = [
        "docling",
        "docling.document_converter",
        "docling.format_options",
        "docling.pipeline_options",
    ]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]
            del sys.modules[name]

    context._fake_docling_unavailable_installed = True
    context._fake_docling_unavailable_original_modules = original_modules


@given("a fake Docling library is available")
def step_fake_docling_available(context) -> None:
    """
    Install a fake Docling library with default behavior.

    :param context: Behave context.
    :type context: behave.runner.Context
    """
    _install_fake_docling_module(context)


@given("a fake Docling library is available without MLX support")
def step_fake_docling_without_mlx(context) -> None:
    """
    Install a fake Docling library without MLX backend support.

    :param context: Behave context.
    :type context: behave.runner.Context
    """
    _install_fake_docling_module(context, with_mlx=False)


@given('a fake Docling library is available that returns text "{text}" for filename "{filename}"')
def step_fake_docling_returns_text(context, text: str, filename: str) -> None:
    """
    Configure fake Docling to return specific text for a filename.

    :param context: Behave context.
    :type context: behave.runner.Context
    :param text: Text to return.
    :type text: str
    :param filename: Filename to match.
    :type filename: str
    """
    _install_fake_docling_module(context)
    behaviors = _ensure_fake_docling_behaviors(context)
    behaviors[filename] = _FakeDoclingBehavior(mode="text", text=text)


@given(
    'a fake Docling library is available that returns empty output for filename "{filename}"'
)
def step_fake_docling_returns_empty(context, filename: str) -> None:
    """
    Configure fake Docling to return empty output for a filename.

    :param context: Behave context.
    :type context: behave.runner.Context
    :param filename: Filename to match.
    :type filename: str
    """
    _install_fake_docling_module(context)
    behaviors = _ensure_fake_docling_behaviors(context)
    behaviors[filename] = _FakeDoclingBehavior(mode="empty", text="")


@given(
    'a fake Docling library is available that raises a RuntimeError for filename "{filename}"'
)
def step_fake_docling_raises_error(context, filename: str) -> None:
    """
    Configure fake Docling to raise a RuntimeError for a filename.

    :param context: Behave context.
    :type context: behave.runner.Context
    :param filename: Filename to match.
    :type filename: str
    """
    _install_fake_docling_module(context)
    behaviors = _ensure_fake_docling_behaviors(context)
    behaviors[filename] = _FakeDoclingBehavior(mode="error", text=None)


@given('a fake Docling library is available that returns HTML "{html}" for filename "{filename}"')
def step_fake_docling_returns_html(context, html: str, filename: str) -> None:
    """
    Configure fake Docling to return HTML output for a filename.

    :param context: Behave context.
    :type context: behave.runner.Context
    :param html: HTML content to return.
    :type html: str
    :param filename: Filename to match.
    :type filename: str
    """
    _install_fake_docling_module(context)
    behaviors = _ensure_fake_docling_behaviors(context)
    behaviors[filename] = _FakeDoclingBehavior(
        mode="text", text=html, output_formats={"html": html}
    )


@given(
    'a fake Docling library is available that returns plain text "{text}" for filename "{filename}"'
)
def step_fake_docling_returns_plain_text(context, text: str, filename: str) -> None:
    """
    Configure fake Docling to return plain text output for a filename.

    :param context: Behave context.
    :type context: behave.runner.Context
    :param text: Plain text content to return.
    :type text: str
    :param filename: Filename to match.
    :type filename: str
    """
    _install_fake_docling_module(context)
    behaviors = _ensure_fake_docling_behaviors(context)
    behaviors[filename] = _FakeDoclingBehavior(
        mode="text", text=text, output_formats={"text": text}
    )


@given(
    'a fake Docling library is available with transformers backend that returns text "{text}" for filename "{filename}"'
)
def step_fake_docling_transformers_returns_text(context, text: str, filename: str) -> None:
    """
    Configure fake Docling with transformers backend to return text for a filename.

    :param context: Behave context.
    :type context: behave.runner.Context
    :param text: Text to return.
    :type text: str
    :param filename: Filename to match.
    :type filename: str
    """
    _install_fake_docling_module(context)
    behaviors = _ensure_fake_docling_behaviors(context)
    behaviors[filename] = _FakeDoclingBehavior(mode="text", text=text)


@given("the Docling dependency is unavailable")
def step_docling_dependency_unavailable(context) -> None:
    """
    Make the Docling dependency unavailable by removing it from sys.modules.

    :param context: Behave context.
    :type context: behave.runner.Context
    """
    _install_docling_unavailable_module(context)
