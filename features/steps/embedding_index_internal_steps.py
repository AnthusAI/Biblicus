from behave import then, when

from biblicus.retrievers.embedding_index_common import _build_snippet, _extract_span_text


@when("I extract span text from non-text with span {start:d} {end:d}")
def step_extract_span_non_text(context, start: int, end: int) -> None:
    context.snippet_result = _extract_span_text(None, (start, end))


@when('I extract span text from "{text}" with span {start:d} {end:d}')
def step_extract_span_text(context, text: str, start: int, end: int) -> None:
    context.snippet_result = _extract_span_text(text, (start, end))


@when("I build a snippet from non-text with span {start:d} {end:d} and max chars {max_chars:d}")
def step_build_snippet_non_text(context, start: int, end: int, max_chars: int) -> None:
    context.snippet_result = _build_snippet(None, (start, end), max_chars)


@when('I build a snippet from "{text}" with span {start:d} {end:d} and max chars {max_chars:d}')
def step_build_snippet_text(context, text: str, start: int, end: int, max_chars: int) -> None:
    context.snippet_result = _build_snippet(text, (start, end), max_chars)


@then("the snippet result is None")
def step_snippet_result_none(context) -> None:
    assert context.snippet_result is None


@then('the snippet result equals "{expected}"')
def step_snippet_result_equals(context, expected: str) -> None:
    normalized_expected = "" if expected == "<empty>" else expected
    assert context.snippet_result == normalized_expected
