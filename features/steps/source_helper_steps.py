from behave import then, when

from biblicus.sources import _namespaced_filename, _sanitize_filename_component


def _normalize_value(value: str) -> str:
    return "" if value == "<empty>" else value


@when('I sanitize the filename "{name}"')
def step_sanitize_filename(context, name: str) -> None:
    context.sanitized_filename = _sanitize_filename_component(_normalize_value(name))


@when(
    'I build a namespaced filename from source uri "{source_uri}" and fallback "{fallback}" with media type "{media_type}"'
)
def step_namespaced_filename(context, source_uri: str, fallback: str, media_type: str) -> None:
    source = _normalize_value(source_uri) or None
    fallback_name = _normalize_value(fallback) or None
    context.namespaced_filename = _namespaced_filename(
        source_uri=source,
        fallback_name=fallback_name,
        media_type=media_type,
    )


@then('the sanitized filename equals "{expected}"')
def step_sanitized_filename_equals(context, expected: str) -> None:
    assert context.sanitized_filename == expected


@then('the namespaced filename equals "{expected}"')
def step_namespaced_filename_equals(context, expected: str) -> None:
    assert context.namespaced_filename == expected
