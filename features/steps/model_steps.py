from __future__ import annotations

from behave import then, when
from pydantic import ValidationError

from biblicus.models import Evidence


@when("I attempt to create evidence without text or content reference")
def step_create_invalid_evidence(context) -> None:
    try:
        Evidence(
            item_id="item-1",
            source_uri=None,
            media_type="text/markdown",
            score=1.0,
            rank=1,
            text=None,
            content_ref=None,
            span_start=None,
            span_end=None,
            stage="scan",
            recipe_id="recipe",
            run_id="run",
            hash=None,
        )
        context.validation_error = None
    except ValidationError as exc:
        context.validation_error = exc


@then("a model validation error is raised")
def step_model_validation_error(context) -> None:
    assert context.validation_error is not None
