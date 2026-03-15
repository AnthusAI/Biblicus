from __future__ import annotations

import builtins
import sys
import types
from types import SimpleNamespace
from typing import Any, Dict

from behave import given, when, then

from biblicus import Corpus
from biblicus.errors import ExtractionSnapshotFatalError
from biblicus.extractors.tesseract_text import TesseractExtractor, TesseractExtractorConfig
from biblicus.models import CatalogItem, ExtractionStageOutput


def _block_pytesseract_import(context) -> None:
    original_import = builtins.__import__
    context._tesseract_original_import = original_import

    def _blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "pytesseract":
            raise ImportError("pytesseract blocked")
        return original_import(name, *args, **kwargs)

    if "pytesseract" in sys.modules:
        context._tesseract_original_module = sys.modules.get("pytesseract")
        del sys.modules["pytesseract"]

    builtins.__import__ = _blocked_import
    context._tesseract_import_blocked = True


def _install_pytesseract_version_error(context) -> None:
    original_modules: Dict[str, object] = {}
    for name in ["pytesseract"]:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    fake_module = types.ModuleType("pytesseract")

    def _get_tesseract_version() -> str:
        raise RuntimeError("tesseract missing")

    fake_module.get_tesseract_version = _get_tesseract_version
    sys.modules["pytesseract"] = fake_module

    context._tesseract_original_modules = original_modules
    context._tesseract_fake_installed = True


def _install_fake_tesseract_ocr(context, data: Dict[str, Any]) -> None:
    original_modules: Dict[str, object] = {}
    for name in ["pytesseract", "PIL", "PIL.Image"]:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    class _FakeImage:
        def crop(self, _box):
            return self

    def _open(_path: str):
        return _FakeImage()

    fake_pil = types.ModuleType("PIL")
    fake_pil_image = types.ModuleType("PIL.Image")
    fake_pil_image.open = _open
    fake_pil.Image = fake_pil_image

    class _FakePytesseract:
        Output = SimpleNamespace(DICT="DICT")

        @staticmethod
        def image_to_data(_image, lang: str, config: str, output_type=None):
            _ = lang
            _ = config
            _ = output_type
            return data

        @staticmethod
        def get_tesseract_version():
            return "1.0"

    sys.modules["pytesseract"] = _FakePytesseract()
    sys.modules["PIL"] = fake_pil
    sys.modules["PIL.Image"] = fake_pil_image

    context._fake_tesseract_installed = True
    context._fake_tesseract_original_modules = original_modules


@given("pytesseract import is blocked")
def step_block_pytesseract_import(context) -> None:
    _block_pytesseract_import(context)


@given("a fake pytesseract module raises on version check")
def step_fake_pytesseract_version_error(context) -> None:
    _install_pytesseract_version_error(context)


@when("I validate the tesseract extractor configuration")
def step_validate_tesseract_config(context) -> None:
    extractor = TesseractExtractor()
    try:
        extractor.validate_config({})
        context._tesseract_error = None
    except ExtractionSnapshotFatalError as exc:
        context._tesseract_error = exc


@when("I extract tesseract text with layout metadata and invalid regions")
def step_extract_tesseract_layout_invalid(context) -> None:
    data = {"text": ["", "Word"], "conf": ["0", "10"]}
    _install_fake_tesseract_ocr(context, data)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = corpus.root / "image.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    item = CatalogItem(
        id="item-1",
        relpath="image.png",
        sha256="",
        bytes=0,
        media_type="image/png",
        tags=[],
        metadata={},
        created_at="2024-01-01T00:00:00Z",
        source_uri="file://image.png",
    )
    layout_metadata = {
        "regions": [
            {"bbox": [0, 1, 2]},
            {"bbox": [0, 0, 10, 10], "order": 1},
        ]
    }
    previous = [
        ExtractionStageOutput(
            stage_index=1,
            extractor_id="layout",
            status="extracted",
            metadata=layout_metadata,
        )
    ]
    extractor = TesseractExtractor()
    config = TesseractExtractorConfig(use_layout_metadata=True, min_confidence=0.5)
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=config,
        previous_extractions=previous,
    )
    context._tesseract_result = result


@when("I extract tesseract text without layout regions")
def step_extract_tesseract_without_layout_regions(context) -> None:
    data = {"text": ["Word"], "conf": ["10"]}
    _install_fake_tesseract_ocr(context, data)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = corpus.root / "image.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    item = CatalogItem(
        id="item-1",
        relpath="image.png",
        sha256="",
        bytes=0,
        media_type="image/png",
        tags=[],
        metadata={},
        created_at="2024-01-01T00:00:00Z",
        source_uri="file://image.png",
    )
    previous = [
        ExtractionStageOutput(
            stage_index=1,
            extractor_id="layout",
            status="extracted",
            metadata={},
        )
    ]
    extractor = TesseractExtractor()
    config = TesseractExtractorConfig(use_layout_metadata=True, min_confidence=0.5)
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=config,
        previous_extractions=previous,
    )
    context._tesseract_result = result


@when("I extract tesseract text from a full image with blank words")
def step_extract_tesseract_full_image_blank_words(context) -> None:
    data = {"text": ["", "Word", " "], "conf": ["0", "90", "0"]}
    _install_fake_tesseract_ocr(context, data)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = corpus.root / "image.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    item = CatalogItem(
        id="item-1",
        relpath="image.png",
        sha256="",
        bytes=0,
        media_type="image/png",
        tags=[],
        metadata={},
        created_at="2024-01-01T00:00:00Z",
        source_uri="file://image.png",
    )
    extractor = TesseractExtractor()
    config = TesseractExtractorConfig(use_layout_metadata=False, min_confidence=0.5)
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=config,
        previous_extractions=[],
    )
    context._tesseract_result = result


@then("the tesseract extractor validation fails")
def step_tesseract_validation_fails(context) -> None:
    assert context._tesseract_error is not None


@then("the tesseract layout extraction is empty")
def step_tesseract_layout_empty(context) -> None:
    result = context._tesseract_result
    assert result is not None
    assert result.text == ""
    assert result.metadata["regions_processed"] == 2


@then("the tesseract extraction is empty")
def step_tesseract_extraction_empty(context) -> None:
    result = context._tesseract_result
    assert result is not None
    assert result.text == ""


@then("the tesseract extraction excludes blank words")
def step_tesseract_extraction_excludes_blanks(context) -> None:
    result = context._tesseract_result
    assert result is not None
    assert result.text == "Word"
