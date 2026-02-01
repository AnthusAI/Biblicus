from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from behave import given, then, when

from biblicus.text.link import (
    _attempt_missing_coverage_recovery,
    _autofill_ref_spans,
    _build_coverage_guidance,
    _is_ref_coverage_error,
    _promote_ref_spans_to_id,
    _render_span_markup,
    _validate_link_coverage,
    _validate_link_span_minimality,
    _validate_link_spans,
)
from biblicus.text.markup import TextAnnotatedSpan, strip_span_tags


@given("the text link errors are:")
def step_given_text_link_errors(context) -> None:
    raw = str(getattr(context, "text", "") or "")
    errors = [line.strip() for line in raw.splitlines() if line.strip()]
    context.text_link_internal_errors = errors


@when("I build text link coverage guidance")
def step_build_text_link_coverage_guidance(context) -> None:
    errors = getattr(context, "text_link_internal_errors", None)
    assert isinstance(errors, list)
    context.text_link_coverage_guidance = _build_coverage_guidance(errors)


@then('the text link coverage guidance includes "{expected}"')
def step_text_link_coverage_guidance_includes(context, expected: str) -> None:
    guidance = getattr(context, "text_link_coverage_guidance", None)
    assert isinstance(guidance, str)
    unescaped = expected.replace('\\"', '"')
    assert unescaped in guidance


@when('I attempt to render link span markup for text "{text}" with overlapping spans')
def step_attempt_render_overlap(context, text: str) -> None:
    spans = [
        TextAnnotatedSpan(
            index=1,
            start_char=0,
            end_char=4,
            text=text[0:4],
            attributes={"id": "link_1"},
        ),
        TextAnnotatedSpan(
            index=2,
            start_char=3,
            end_char=5,
            text=text[3:5],
            attributes={"ref": "link_1"},
        ),
    ]
    try:
        _ = _render_span_markup(text, spans)
        context.text_link_internal_error = None
    except Exception as exc:  # noqa: BLE001
        context.text_link_internal_error = str(exc)


@then('the text link internal error mentions "{expected}"')
def step_text_link_internal_error_mentions(context, expected: str) -> None:
    error = getattr(context, "text_link_internal_error", None)
    assert isinstance(error, str)
    assert expected in error


@when('I autofill ref spans for marked-up text "{marked_up_text}"')
def step_autofill_ref_spans(context, marked_up_text: str) -> None:
    plain_text = strip_span_tags(marked_up_text)
    spans = [
        TextAnnotatedSpan(
            index=1,
            start_char=0,
            end_char=len("Acme"),
            text="Acme",
            attributes={"id": "link_1"},
        )
    ]
    result = _autofill_ref_spans(marked_up_text, spans)
    assert result is not None
    context.autofill_marked_up_text, context.autofill_spans, context.autofill_warnings = result
    context.autofill_plain_text = plain_text


@then("the autofill result includes {count:d} new ref spans")
def step_autofill_includes_new_spans(context, count: int) -> None:
    spans = getattr(context, "autofill_spans", None)
    assert isinstance(spans, list)
    ref_spans = [span for span in spans if "ref" in (span.attributes or {})]
    assert len(ref_spans) == count


@then('the autofill warnings include "{expected}"')
def step_autofill_warnings_include(context, expected: str) -> None:
    warnings = getattr(context, "autofill_warnings", None)
    assert isinstance(warnings, list)
    assert any(expected in warning for warning in warnings)


@when('I promote ref spans to id for text spans with id prefix "{id_prefix}"')
def step_promote_ref_spans(context, id_prefix: str) -> None:
    spans = [
        TextAnnotatedSpan(
            index=1, start_char=0, end_char=4, text="Acme", attributes={"ref": "link_1"}
        )
    ]
    promoted, warnings = _promote_ref_spans_to_id(spans=spans, id_prefix=id_prefix)
    context.promoted_spans = promoted
    context.promotion_warnings = warnings


@when('I promote ref spans to id for multiple ref spans with id prefix "{id_prefix}"')
def step_promote_ref_spans_multiple(context, id_prefix: str) -> None:
    spans = [
        TextAnnotatedSpan(
            index=1, start_char=0, end_char=4, text="Acme", attributes={"ref": "link_1"}
        ),
        TextAnnotatedSpan(
            index=2, start_char=10, end_char=14, text="Acme", attributes={"ref": "link_1"}
        ),
    ]
    promoted, warnings = _promote_ref_spans_to_id(spans=spans, id_prefix=id_prefix)
    context.promoted_spans = promoted
    context.promotion_warnings = warnings


@then('the promotion warnings include "{expected}"')
def step_promotion_warnings_include(context, expected: str) -> None:
    warnings = getattr(context, "promotion_warnings", None)
    assert isinstance(warnings, list)
    assert any(expected in warning for warning in warnings)


@then("the promoted spans include both id and ref spans")
def step_promoted_spans_include_id_and_ref(context) -> None:
    spans = getattr(context, "promoted_spans", None)
    assert isinstance(spans, list)
    has_id = any("id" in (span.attributes or {}) for span in spans)
    has_ref = any("ref" in (span.attributes or {}) for span in spans)
    assert has_id and has_ref


@when(
    'I attempt missing coverage recovery for marked-up text "{marked_up_text}" with id prefix "{id_prefix}"'
)
def step_attempt_missing_coverage_recovery(context, marked_up_text: str, id_prefix: str) -> None:
    warnings: List[str] = []
    context.missing_coverage_recovery = _attempt_missing_coverage_recovery(
        marked_up_text=marked_up_text,
        id_prefix=id_prefix,
        warnings=warnings,
    )
    context.missing_coverage_recovery_warnings = warnings


@then("the missing coverage recovery returned a result")
def step_missing_coverage_recovery_returned(context) -> None:
    result = getattr(context, "missing_coverage_recovery", None)
    assert result is not None


@then("the missing coverage recovery returned no result")
def step_missing_coverage_recovery_returned_none(context) -> None:
    result = getattr(context, "missing_coverage_recovery", None)
    assert result is None


@then('the missing coverage recovery warnings include "{expected}"')
def step_missing_coverage_recovery_warnings_include(context, expected: str) -> None:
    warnings = getattr(context, "missing_coverage_recovery_warnings", None)
    assert isinstance(warnings, list)
    assert any(expected in warning for warning in warnings)


@when('I validate link span minimality for span text "{text}"')
def step_validate_link_span_minimality(context, text: str) -> None:
    spans: Sequence[TextAnnotatedSpan] = [
        TextAnnotatedSpan(
            index=1, start_char=0, end_char=len(text), text=text, attributes={"id": "link_1"}
        )
    ]
    context.link_minimality_errors = _validate_link_span_minimality(spans)


@then('the link minimality errors include "{expected}"')
def step_link_minimality_errors_include(context, expected: str) -> None:
    errors: Optional[list[str]] = getattr(context, "link_minimality_errors", None)
    assert isinstance(errors, list)
    assert any(expected in error for error in errors)


@then("the link minimality errors are empty")
def step_link_minimality_errors_empty(context) -> None:
    errors: Optional[list[str]] = getattr(context, "link_minimality_errors", None)
    assert isinstance(errors, list)
    assert errors == []


@when(
    'I promote ref spans to id for text spans with ref value "{ref_value}" and id prefix "{id_prefix}"'
)
def step_promote_ref_spans_custom(context, ref_value: str, id_prefix: str) -> None:
    spans = [
        TextAnnotatedSpan(
            index=1, start_char=0, end_char=4, text="Acme", attributes={"ref": ref_value}
        )
    ]
    promoted, warnings = _promote_ref_spans_to_id(spans=spans, id_prefix=id_prefix)
    context.promoted_spans = promoted
    context.promotion_warnings = warnings


@then("the promotion warnings are empty")
def step_promotion_warnings_empty(context) -> None:
    warnings = getattr(context, "promotion_warnings", None)
    assert isinstance(warnings, list)
    assert warnings == []


@when("I validate link spans with mismatched id/ref texts")
def step_validate_link_spans_mismatched_texts(context) -> None:
    spans = [
        TextAnnotatedSpan(
            index=1, start_char=0, end_char=4, text="Acme", attributes={"id": "link_1"}
        ),
        TextAnnotatedSpan(
            index=2, start_char=10, end_char=14, text="Acme", attributes={"ref": "link_1"}
        ),
        TextAnnotatedSpan(
            index=3, start_char=20, end_char=24, text="ACME", attributes={"ref": "link_1"}
        ),
    ]
    context.link_span_errors = _validate_link_spans(spans, "link_")


@when("I validate link spans with repeated text requiring exactly one id")
def step_validate_link_spans_repeated_text_multiple_ids(context) -> None:
    spans = [
        TextAnnotatedSpan(
            index=1, start_char=0, end_char=4, text="Acme", attributes={"id": "link_1"}
        ),
        TextAnnotatedSpan(
            index=2, start_char=10, end_char=14, text="Acme", attributes={"id": "link_2"}
        ),
    ]
    context.link_span_errors = _validate_link_spans(spans, "link_")


@when("I validate link spans with repeated text missing ref spans")
def step_validate_link_spans_repeated_text_missing_refs(context) -> None:
    spans = [
        TextAnnotatedSpan(
            index=1, start_char=0, end_char=4, text="Acme", attributes={"id": "link_1"}
        ),
        TextAnnotatedSpan(
            index=2, start_char=10, end_char=14, text="Acme", attributes={"label": "x"}
        ),
    ]
    context.link_span_errors = _validate_link_spans(spans, "link_")


@when("I validate link spans with repeated refs that do not match ids")
def step_validate_link_spans_repeated_text_mismatched_refs(context) -> None:
    spans = [
        TextAnnotatedSpan(
            index=1, start_char=0, end_char=4, text="Acme", attributes={"id": "link_1"}
        ),
        TextAnnotatedSpan(
            index=2, start_char=10, end_char=14, text="Acme", attributes={"ref": "link_2"}
        ),
    ]
    context.link_span_errors = _validate_link_spans(spans, "link_")


@then('the link span errors include "{expected}"')
def step_link_span_errors_include(context, expected: str) -> None:
    errors: Optional[list[str]] = getattr(context, "link_span_errors", None)
    assert isinstance(errors, list)
    assert any(expected in error for error in errors)


@when("I validate link coverage for empty span text")
def step_validate_link_coverage_empty_span_text(context) -> None:
    spans = [
        TextAnnotatedSpan(index=1, start_char=0, end_char=0, text="", attributes={"id": "link_1"}),
    ]
    context.link_coverage_errors = _validate_link_coverage("Hello", spans)


@then("the link coverage errors are empty")
def step_link_coverage_errors_empty(context) -> None:
    errors: Optional[list[str]] = getattr(context, "link_coverage_errors", None)
    assert isinstance(errors, list)
    assert errors == []


@when("I attempt to autofill ref spans for empty id span text")
def step_attempt_autofill_ref_spans_empty_text(context) -> None:
    spans = [
        TextAnnotatedSpan(index=1, start_char=0, end_char=0, text="", attributes={"id": "link_1"}),
    ]
    context.autofill_result = _autofill_ref_spans("Hello", spans)


@then("the autofill returned no result")
def step_autofill_returned_none(context) -> None:
    result = getattr(context, "autofill_result", None)
    assert result is None


@when('I render span markup for text "{text}" with an attribute-less span')
def step_render_attrless_span_markup(context, text: str) -> None:
    spans = [
        TextAnnotatedSpan(index=1, start_char=0, end_char=len(text), text=text, attributes={}),
    ]
    context.rendered_markup = _render_span_markup(text, spans)


@then('the rendered markup equals "{expected}"')
def step_rendered_markup_equals(context, expected: str) -> None:
    rendered = getattr(context, "rendered_markup", None)
    assert isinstance(rendered, str)
    assert rendered == expected


@when("I classify repeated-text errors as coverage-only")
def step_classify_repeated_text_errors(context) -> None:
    context.repeated_text_coverage_only = _is_ref_coverage_error(
        "Repeated text 'Acme' must include ref spans for repeats"
    )


@then("the repeated-text error is treated as coverage-only")
def step_repeated_text_coverage_only_true(context) -> None:
    coverage_only = getattr(context, "repeated_text_coverage_only", None)
    assert coverage_only is True


@when("I attempt missing coverage recovery where autofill produces invalid spans")
def step_attempt_missing_coverage_recovery_invalid_autofill(context) -> None:
    import biblicus.text.link as link_module

    original_autofill = link_module._autofill_ref_spans

    def fake_autofill(marked_up_text: str, spans: Iterable[TextAnnotatedSpan]):  # type: ignore[no-untyped-def]
        _ = marked_up_text
        _ = spans
        result_spans = [
            TextAnnotatedSpan(
                index=1, start_char=0, end_char=4, text="Acme", attributes={"id": "link_1"}
            ),
            TextAnnotatedSpan(
                index=2, start_char=13, end_char=17, text="ACME", attributes={"ref": "link_1"}
            ),
        ]
        result_text = (
            '<span id="link_1">Acme</span> launched. <span ref="link_1">ACME</span> updated.'
        )
        return result_text, result_spans, ["Autofilled 1 ref spans for repeated text."]

    link_module._autofill_ref_spans = fake_autofill  # type: ignore[assignment]
    try:
        warnings: List[str] = []
        context.missing_coverage_recovery = _attempt_missing_coverage_recovery(
            marked_up_text='<span id="link_1">Acme</span> launched. Acme updated.',
            id_prefix="link_",
            warnings=warnings,
        )
        context.missing_coverage_recovery_warnings = warnings
    finally:
        link_module._autofill_ref_spans = original_autofill  # type: ignore[assignment]
