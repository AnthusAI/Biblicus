from __future__ import annotations

import builtins
import sys
import types
from pathlib import Path
from typing import Any, Dict

from behave import given, when, then

from biblicus import Corpus
from biblicus.extractors.heron_layout import HeronLayoutExtractor
from biblicus.extractors.mock_layout_detector import MockLayoutDetectorExtractor
from biblicus.extractors.paddleocr_layout import PaddleOCRLayoutExtractor
from biblicus.extractors.paddleocr_vl_text import PaddleOcrVlExtractor, PaddleOcrVlExtractorConfig
from biblicus.models import CatalogItem


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _install_fake_heron_dependencies(context) -> None:
    if getattr(context, "_fake_heron_installed", False):
        return
    original_modules: Dict[str, object] = {}
    module_names = ["transformers", "torch", "PIL", "PIL.Image"]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    class _FakeTensor:
        def __init__(self, value: float):
            self._value = value

        def item(self) -> float:
            return self._value

    class _FakeModel:
        def __init__(self) -> None:
            self.config = types.SimpleNamespace(id2label={0: "text", 1: "table"})

        def __call__(self, **_kwargs):
            return {"logits": []}

        @classmethod
        def from_pretrained(cls, _name: str):
            return cls()

    class _FakeImageProcessor:
        @classmethod
        def from_pretrained(cls, _name: str):
            return cls()

        def __call__(self, images=None, return_tensors: str = "pt"):
            _ = images
            _ = return_tensors
            return {}

        def post_process_object_detection(self, _outputs, target_sizes=None, threshold: float = 0.0):
            _ = target_sizes
            _ = threshold
            if getattr(context, "_fake_heron_empty_results", False):
                return []
            boxes = [
                [_FakeTensor(10), _FakeTensor(20), _FakeTensor(30), _FakeTensor(40)],
                [_FakeTensor(5), _FakeTensor(15), _FakeTensor(25), _FakeTensor(35)],
            ]
            scores = [_FakeTensor(0.9), _FakeTensor(0.8)]
            labels = [_FakeTensor(0), _FakeTensor(1)]
            return [{"boxes": boxes, "scores": scores, "labels": labels}]

    class _NoGrad:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type
            _ = exc
            _ = tb
            return False

    def _no_grad():
        return _NoGrad()

    def _tensor(value):
        return value

    class _FakeImage:
        def __init__(self):
            self.size = (1000, 800)

        def convert(self, _mode: str):
            if getattr(context, "_fake_heron_image_none", False):
                return None
            return self

    def _open(_path: str):
        return _FakeImage()

    transformers_module = types.ModuleType("transformers")
    transformers_module.RTDetrV2ForObjectDetection = _FakeModel
    transformers_module.RTDetrImageProcessor = _FakeImageProcessor

    torch_module = types.ModuleType("torch")
    torch_module.no_grad = _no_grad
    torch_module.tensor = _tensor

    pil_module = types.ModuleType("PIL")
    pil_image_module = types.ModuleType("PIL.Image")
    pil_image_module.open = _open
    pil_module.Image = pil_image_module

    sys.modules["transformers"] = transformers_module
    sys.modules["torch"] = torch_module
    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = pil_image_module

    context._fake_heron_installed = True
    context._fake_heron_original_modules = original_modules


def _block_heron_imports(context) -> None:
    if getattr(context, "_fake_heron_import_blocked", False):
        return
    original_import = builtins.__import__
    context._fake_heron_original_import = original_import

    def _blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in {"transformers", "torch"}:
            raise ImportError("blocked")
        return original_import(name, *args, **kwargs)

    if "transformers" in sys.modules:
        context._fake_heron_original_transformers = sys.modules.get("transformers")
        del sys.modules["transformers"]
    if "torch" in sys.modules:
        context._fake_heron_original_torch = sys.modules.get("torch")
        del sys.modules["torch"]

    builtins.__import__ = _blocked_import
    context._fake_heron_import_blocked = True


def _install_fake_paddleocr_layout_dependencies(context) -> None:
    if getattr(context, "_fake_paddleocr_layout_installed", False):
        return
    original_modules: Dict[str, object] = {}
    module_names = ["paddleocr", "cv2"]
    for name in module_names:
        if name in sys.modules:
            original_modules[name] = sys.modules[name]

    class PPStructureV3:
        def __init__(self, lang: str = "en"):
            self.lang = lang

        def predict(self, _path: str):
            if getattr(context, "_fake_paddleocr_layout_empty", False):
                return []
            if getattr(context, "_fake_paddleocr_layout_non_dict", False):
                return [object()]
            return [
                {
                    "layout_det_res": {
                        "boxes": [
                            (
                                {"label": "text", "score": 0.9}
                                if getattr(context, "_fake_paddleocr_layout_missing_coordinates", False)
                                else {"coordinate": [0, 0, 50, 50], "label": "text", "score": 0.9}
                            ),
                            {"coordinate": [60, 0, 100, 50], "label": "table", "score": 0.8},
                        ]
                    }
                }
            ]

    def _imread(_path: str):
        if getattr(context, "_fake_paddleocr_layout_no_image", False):
            return None
        return object()

    paddle_module = types.ModuleType("paddleocr")
    paddle_module.PPStructureV3 = PPStructureV3

    cv2_module = types.ModuleType("cv2")
    cv2_module.imread = _imread

    sys.modules["paddleocr"] = paddle_module
    sys.modules["cv2"] = cv2_module

    context._fake_paddleocr_layout_installed = True
    context._fake_paddleocr_layout_original_modules = original_modules


def _block_paddleocr_layout_imports(context) -> None:
    if getattr(context, "_fake_paddleocr_layout_import_blocked", False):
        return
    original_import = builtins.__import__
    context._fake_paddleocr_layout_original_import = original_import

    def _blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "paddleocr":
            raise ImportError("blocked")
        return original_import(name, *args, **kwargs)

    if "paddleocr" in sys.modules:
        context._fake_paddleocr_layout_original_module = sys.modules.get("paddleocr")
        del sys.modules["paddleocr"]

    builtins.__import__ = _blocked_import
    context._fake_paddleocr_layout_import_blocked = True


def _sample_image_path(context) -> Path:
    image_path = context.workdir / "image.png"
    _write_bytes(image_path, b"\x89PNG\r\n\x1a\n")
    return image_path


def _sample_item(context, relpath: str, media_type: str) -> CatalogItem:
    return CatalogItem(
        id="item-1",
        relpath=relpath,
        sha256="",
        bytes=0,
        media_type=media_type,
        tags=[],
        metadata={},
        created_at="2024-01-01T00:00:00Z",
        source_uri="file://example.png",
    )


@when('I validate mock layout detector config with layout_type "{layout_type}"')
def step_validate_mock_layout_config(context, layout_type: str) -> None:
    extractor = MockLayoutDetectorExtractor()
    try:
        extractor.validate_config({"layout_type": layout_type})
        context._mock_layout_error = None
    except ValueError as exc:
        context._mock_layout_error = exc


@then("the mock layout detector config validation fails")
def step_mock_layout_validation_fails(context) -> None:
    assert context._mock_layout_error is not None


@when("I run mock layout detector on a non-image item")
def step_mock_layout_non_image(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    item = _sample_item(context, "raw/file.txt", "text/plain")
    extractor = MockLayoutDetectorExtractor()
    parsed = extractor.validate_config({"layout_type": "single-column"})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._mock_layout_result = result


@then("the mock layout detector returns no extraction")
def step_mock_layout_returns_none(context) -> None:
    assert context._mock_layout_result is None


@given("fake Heron layout dependencies are installed")
def step_fake_heron_dependencies(context) -> None:
    _install_fake_heron_dependencies(context)


@given("Heron layout dependencies are unavailable")
def step_heron_dependencies_unavailable(context) -> None:
    _block_heron_imports(context)


@when("I run the Heron layout extractor on a sample image")
def step_run_heron_layout(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = HeronLayoutExtractor()
    parsed = extractor.validate_config({})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._heron_layout_result = result


@when("I run the Heron layout extractor on a non-image item")
def step_run_heron_layout_non_image(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    item = _sample_item(context, "raw/file.txt", "text/plain")
    extractor = HeronLayoutExtractor()
    parsed = extractor.validate_config({})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._heron_layout_result = result


@when("I run the Heron layout extractor with the base model")
def step_run_heron_layout_base(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = HeronLayoutExtractor()
    parsed = extractor.validate_config({"model_variant": "base"})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._heron_layout_result = result


@when("I run the Heron layout extractor with empty results")
def step_run_heron_layout_empty(context) -> None:
    context._fake_heron_empty_results = True
    _install_fake_heron_dependencies(context)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = HeronLayoutExtractor()
    parsed = extractor.validate_config({})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._heron_layout_result = result


@when("I run the Heron layout extractor with a missing image")
def step_run_heron_layout_missing_image(context) -> None:
    context._fake_heron_image_none = True
    _install_fake_heron_dependencies(context)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = HeronLayoutExtractor()
    parsed = extractor.validate_config({})
    try:
        extractor.extract_text(
            corpus=corpus,
            item=item,
            config=parsed,
            previous_extractions=[],
        )
        context._heron_layout_error = None
    except Exception as exc:
        context._heron_layout_error = exc


@then("Heron layout metadata includes regions")
def step_heron_layout_has_regions(context) -> None:
    result = context._heron_layout_result
    assert result is not None
    metadata = result.metadata
    assert metadata is not None
    assert metadata.get("regions")


@then("Heron layout metadata is present")
def step_heron_layout_metadata_present(context) -> None:
    result = context._heron_layout_result
    assert result is not None
    metadata = result.metadata
    assert metadata is not None
    assert "regions" in metadata


@then("Heron layout extraction returns no result")
def step_heron_layout_none(context) -> None:
    assert context._heron_layout_result is None


@then("Heron layout extraction fails")
def step_heron_layout_error(context) -> None:
    assert getattr(context, "_heron_layout_error", None) is not None


@given("fake PaddleOCR layout dependencies are installed")
def step_fake_paddleocr_layout_dependencies(context) -> None:
    _install_fake_paddleocr_layout_dependencies(context)


@given("PaddleOCR layout dependencies are unavailable")
def step_paddleocr_layout_dependencies_unavailable(context) -> None:
    _block_paddleocr_layout_imports(context)


@when("I run the PaddleOCR layout extractor on a sample image")
def step_run_paddleocr_layout(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = PaddleOCRLayoutExtractor()
    parsed = extractor.validate_config({})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._paddleocr_layout_result = result


@when("I run the PaddleOCR layout extractor on a non-image item")
def step_run_paddleocr_layout_non_image(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    item = _sample_item(context, "raw/file.txt", "text/plain")
    extractor = PaddleOCRLayoutExtractor()
    parsed = extractor.validate_config({})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._paddleocr_layout_result = result


@when("I run the PaddleOCR layout extractor with empty results")
def step_run_paddleocr_layout_empty(context) -> None:
    context._fake_paddleocr_layout_empty = True
    _install_fake_paddleocr_layout_dependencies(context)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = PaddleOCRLayoutExtractor()
    parsed = extractor.validate_config({})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._paddleocr_layout_result = result


@when("I run the PaddleOCR layout extractor with missing coordinates")
def step_run_paddleocr_layout_missing_coordinates(context) -> None:
    context._fake_paddleocr_layout_missing_coordinates = True
    _install_fake_paddleocr_layout_dependencies(context)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = PaddleOCRLayoutExtractor()
    parsed = extractor.validate_config({})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._paddleocr_layout_result = result


@when("I run the PaddleOCR layout extractor with a non-dict page result")
def step_run_paddleocr_layout_non_dict(context) -> None:
    context._fake_paddleocr_layout_non_dict = True
    _install_fake_paddleocr_layout_dependencies(context)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = PaddleOCRLayoutExtractor()
    parsed = extractor.validate_config({})
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._paddleocr_layout_result = result


@when("I run the PaddleOCR layout extractor with a missing image")
def step_run_paddleocr_layout_missing_image(context) -> None:
    context._fake_paddleocr_layout_no_image = True
    _install_fake_paddleocr_layout_dependencies(context)
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = _sample_image_path(context)
    relpath = "raw/image.png"
    _write_bytes(corpus.root / relpath, image_path.read_bytes())
    item = _sample_item(context, relpath, "image/png")
    extractor = PaddleOCRLayoutExtractor()
    parsed = extractor.validate_config({})
    try:
        extractor.extract_text(
            corpus=corpus,
            item=item,
            config=parsed,
            previous_extractions=[],
        )
        context._paddleocr_layout_error = None
    except Exception as exc:
        context._paddleocr_layout_error = exc


@when("I parse a PaddleOCR layout region")
def step_parse_paddleocr_layout_region(context) -> None:
    extractor = PaddleOCRLayoutExtractor()
    region = extractor._parse_region({"label": "text", "bbox": [0, 1, 2, 3]}, order=1)
    context._paddleocr_parsed_region = region


@then("PaddleOCR layout metadata includes regions")
def step_paddleocr_layout_has_regions(context) -> None:
    result = context._paddleocr_layout_result
    assert result is not None
    metadata = result.metadata
    assert metadata is not None
    assert metadata.get("regions")
    assert context._paddleocr_parsed_region["type"] == "text"


@then("PaddleOCR layout metadata is present")
def step_paddleocr_layout_metadata_present(context) -> None:
    result = context._paddleocr_layout_result
    assert result is not None
    metadata = result.metadata
    assert metadata is not None
    assert "regions" in metadata


@then("PaddleOCR layout includes an empty bbox region")
def step_paddleocr_layout_empty_bbox(context) -> None:
    result = context._paddleocr_layout_result
    assert result is not None
    regions = result.metadata.get("regions", [])
    assert any(region.get("bbox") == [] for region in regions)


@then("PaddleOCR layout has no regions")
def step_paddleocr_layout_no_regions(context) -> None:
    result = context._paddleocr_layout_result
    assert result is not None
    regions = result.metadata.get("regions", [])
    assert regions == []


@then("PaddleOCR layout extraction returns no result")
def step_paddleocr_layout_none(context) -> None:
    assert context._paddleocr_layout_result is None


@then("PaddleOCR layout extraction fails")
def step_paddleocr_layout_error(context) -> None:
    assert getattr(context, "_paddleocr_layout_error", None) is not None


@when("I validate the Heron layout extractor configuration")
def step_validate_heron_layout_config(context) -> None:
    extractor = HeronLayoutExtractor()
    try:
        extractor.validate_config({})
        context._heron_layout_error = None
    except Exception as exc:
        context._heron_layout_error = exc


@when("I validate the PaddleOCR layout extractor configuration")
def step_validate_paddleocr_layout_config(context) -> None:
    extractor = PaddleOCRLayoutExtractor()
    try:
        extractor.validate_config({})
        context._paddleocr_layout_error = None
    except Exception as exc:
        context._paddleocr_layout_error = exc


@when('I run PaddleOCR-VL extraction on "{filename}"')
def step_run_paddleocr_vl(context, filename: str) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    image_path = corpus.root / filename
    _write_bytes(image_path, b"\x89PNG\r\n\x1a\n")
    item = _sample_item(context, filename, "image/png")
    extractor = PaddleOcrVlExtractor()
    parsed = PaddleOcrVlExtractorConfig()
    result = extractor.extract_text(
        corpus=corpus,
        item=item,
        config=parsed,
        previous_extractions=[],
    )
    context._paddleocr_vl_result = result


@then('PaddleOCR-VL extraction returns text "{expected}"')
def step_paddleocr_vl_text(context, expected: str) -> None:
    result = context._paddleocr_vl_result
    assert result is not None
    if expected == "<empty>":
        normalized_expected = ""
    else:
        normalized_expected = expected.replace("\\n", "\n")
    assert result.text == normalized_expected, (
        f"Expected {normalized_expected!r}, got {result.text!r}"
    )
