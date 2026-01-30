"""Step definitions for PaddleOCR-VL and smart override unit tests."""

from __future__ import annotations

import json

from behave import given, then, when

from biblicus.extractors.paddleocr_vl_text import (
    PaddleOcrVlExtractor,
    PaddleOcrVlExtractorConfig,
)
from biblicus.extractors.select_smart_override import (
    SelectSmartOverrideConfig,
    SelectSmartOverrideExtractor,
)
from biblicus.models import CatalogItem, ExtractionStepOutput


@given("I have a PaddleOCR-VL extractor")
def step_have_paddleocr_extractor(context) -> None:
    context._paddleocr_extractor = PaddleOcrVlExtractor()
    context._paddleocr_config = PaddleOcrVlExtractorConfig()


@when("I parse an API response with value {value}")
def step_parse_api_response(context, value: str) -> None:
    parsed_value = json.loads(value)
    context._paddleocr_parsed_result = context._paddleocr_extractor._parse_api_response(
        parsed_value, context._paddleocr_config
    )


@then("the parsed text is empty")
def step_parsed_text_is_empty(context) -> None:
    text, confidence = context._paddleocr_parsed_result
    assert text == "", f"Expected empty text, got: {text!r}"


@then("the parsed confidence is None")
def step_parsed_confidence_is_none(context) -> None:
    text, confidence = context._paddleocr_parsed_result
    assert confidence is None, f"Expected None confidence, got: {confidence!r}"


@given("I have a smart override selector")
def step_have_smart_override_selector(context) -> None:
    context._smart_override_extractor = SelectSmartOverrideExtractor()


@given("I have previous extractions:")
def step_have_previous_extractions(context) -> None:
    """Create a list of ExtractionStepOutput objects from the table."""
    context._extractions = []
    for idx, row in enumerate(context.table, start=1):
        text = row["text"]
        confidence = float(row["confidence"]) if row["confidence"] else None
        extraction = ExtractionStepOutput(
            step_index=idx,
            extractor_id="test-extractor",
            status="extracted",
            text=text,
            confidence=confidence,
        )
        context._extractions.append(extraction)


@when("I select the best extraction with threshold {threshold:f} and min length {min_length:d}")
def step_select_best_extraction(context, threshold: float, min_length: int) -> None:
    """Call extract_text with the mock extractions."""
    import tempfile
    from datetime import datetime
    from pathlib import Path

    from biblicus.corpus import Corpus

    # Create a minimal corpus and item
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus = Corpus(root=Path(tmpdir))
        item = CatalogItem(
            id="test-item",
            relpath="test.txt",
            sha256="0" * 64,
            bytes=0,
            media_type="image/png",
            created_at=datetime.now().isoformat(),
        )

        config = SelectSmartOverrideConfig(
            media_type_patterns=["image/*"],
            min_confidence_threshold=threshold,
            min_text_length=min_length,
        )

        result = context._smart_override_extractor.extract_text(
            corpus=corpus,
            item=item,
            config=config,
            previous_extractions=context._extractions,
        )

        context._selected_text = result.text if result else ""


@then('the selected text is "{expected_text}"')
def step_selected_text_is(context, expected_text: str) -> None:
    assert (
        context._selected_text == expected_text
    ), f"Expected text {expected_text!r}, got {context._selected_text!r}"
