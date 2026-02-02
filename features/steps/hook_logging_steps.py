from behave import then, when

from biblicus.hook_logging import redact_source_uri


@when('I redact the source uri "{value}"')
def step_redact_source_uri(context, value: str) -> None:
    context.redacted_source_uri = redact_source_uri(value)


@then('the redacted source uri equals "{expected}"')
def step_redacted_source_uri_equals(context, expected: str) -> None:
    assert context.redacted_source_uri == expected
