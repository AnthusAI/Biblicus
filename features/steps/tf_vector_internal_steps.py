from behave import then, when

from biblicus.backends.tf_vector import _build_snippet


@when('I build a TF vector snippet for "{text}" with no span and max chars {max_chars:d}')
def step_build_tf_vector_snippet(context, text: str, max_chars: int) -> None:
    context.tf_vector_snippet = _build_snippet(text, None, max_chars=max_chars)


@then('the TF vector snippet equals "{expected}"')
def step_tf_vector_snippet_equals(context, expected: str) -> None:
    normalized = "" if expected == "<empty>" else expected
    assert context.tf_vector_snippet == normalized
