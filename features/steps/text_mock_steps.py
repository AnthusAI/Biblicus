from __future__ import annotations

from behave import then, when

from biblicus.ai.models import AiProvider, LlmClientConfig
from biblicus.text.annotate import TextAnnotateRequest, apply_text_annotate
from biblicus.text.extract import TextExtractRequest, apply_text_extract
from biblicus.text.link import TextLinkRequest, apply_text_link
from biblicus.text.redact import TextRedactRequest, apply_text_redact
from biblicus.text.slice import TextSliceRequest, apply_text_slice


def _build_client() -> LlmClientConfig:
    return LlmClientConfig(
        provider=AiProvider.OPENAI,
        model="gpt-4o-mini",
        api_key="test-openai-key",
        response_format="json_object",
    )


def _build_system_prompt() -> str:
    return "Insert the required markup into the text below:\n\n{text}"


def _build_prompt_template() -> str:
    return "Return only the updated markup."


def _record_failure(context, exc: Exception) -> None:
    context.text_utility_error_message = str(exc)


@when('I apply mock text extract to text "{text}" with markup "{markup}"')
def step_apply_mock_text_extract(context, text: str, markup: str) -> None:
    request = TextExtractRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        system_prompt=_build_system_prompt(),
        mock_marked_up_text=markup,
    )
    context.text_extract_result = apply_text_extract(request)


@when('I attempt to apply mock text extract to text "{text}" with markup "{markup}"')
def step_attempt_mock_text_extract(context, text: str, markup: str) -> None:
    try:
        step_apply_mock_text_extract(context, text, markup)
    except Exception as exc:
        _record_failure(context, exc)


@when('I apply mock text extract to text "{text}" with markup "{markup}" using default system prompt')
def step_apply_mock_text_extract_default_prompt(context, text: str, markup: str) -> None:
    request = TextExtractRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        mock_marked_up_text=markup,
    )
    context.text_extract_result = apply_text_extract(request)


@when('I apply mock text annotate to text "{text}" with markup "{markup}"')
def step_apply_mock_text_annotate(context, text: str, markup: str) -> None:
    request = TextAnnotateRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        system_prompt=_build_system_prompt(),
        mock_marked_up_text=markup,
    )
    context.text_annotate_result = apply_text_annotate(request)


@when('I attempt to apply mock text annotate to text "{text}" with markup "{markup}"')
def step_attempt_mock_text_annotate(context, text: str, markup: str) -> None:
    try:
        step_apply_mock_text_annotate(context, text, markup)
    except Exception as exc:
        _record_failure(context, exc)


@when('I apply mock text annotate to text "{text}" with markup "{markup}" using default system prompt')
def step_apply_mock_text_annotate_default_prompt(context, text: str, markup: str) -> None:
    request = TextAnnotateRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        mock_marked_up_text=markup,
    )
    context.text_annotate_result = apply_text_annotate(request)


@when('I apply mock text link to text "{text}" with markup "{markup}"')
def step_apply_mock_text_link(context, text: str, markup: str) -> None:
    request = TextLinkRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        system_prompt=_build_system_prompt(),
        mock_marked_up_text=markup,
    )
    context.text_link_result = apply_text_link(request)


@when('I attempt to apply mock text link to text "{text}" with markup "{markup}"')
def step_attempt_mock_text_link(context, text: str, markup: str) -> None:
    try:
        step_apply_mock_text_link(context, text, markup)
    except Exception as exc:
        _record_failure(context, exc)


@when('I apply mock text link to text "{text}" with markup "{markup}" using default system prompt')
def step_apply_mock_text_link_default_prompt(context, text: str, markup: str) -> None:
    request = TextLinkRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        mock_marked_up_text=markup,
    )
    context.text_link_result = apply_text_link(request)


@when('I apply mock text redact to text "{text}" with markup "{markup}"')
def step_apply_mock_text_redact(context, text: str, markup: str) -> None:
    request = TextRedactRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        system_prompt=_build_system_prompt(),
        mock_marked_up_text=markup,
    )
    context.text_redact_result = apply_text_redact(request)


@when('I attempt to apply mock text redact to text "{text}" with markup "{markup}"')
def step_attempt_mock_text_redact(context, text: str, markup: str) -> None:
    try:
        step_apply_mock_text_redact(context, text, markup)
    except Exception as exc:
        _record_failure(context, exc)


@when('I apply mock text redact to text "{text}" with markup "{markup}" using default system prompt')
def step_apply_mock_text_redact_default_prompt(context, text: str, markup: str) -> None:
    request = TextRedactRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        mock_marked_up_text=markup,
    )
    context.text_redact_result = apply_text_redact(request)


@when('I apply mock text slice to text "{text}" with markup "{markup}"')
def step_apply_mock_text_slice(context, text: str, markup: str) -> None:
    request = TextSliceRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        system_prompt=_build_system_prompt(),
        mock_marked_up_text=markup,
    )
    context.text_slice_result = apply_text_slice(request)


@when('I attempt to apply mock text slice to text "{text}" with markup "{markup}"')
def step_attempt_mock_text_slice(context, text: str, markup: str) -> None:
    try:
        step_apply_mock_text_slice(context, text, markup)
    except Exception as exc:
        _record_failure(context, exc)


@then('the text utility fails with message "{message}"')
def step_text_utility_fails_with_message(context, message: str) -> None:
    error_message = getattr(context, "text_utility_error_message", None)
    assert isinstance(error_message, str), "Expected a text utility error message"
    assert message in error_message

@when('I apply mock text slice to text "{text}" with markup "{markup}" using default system prompt')
def step_apply_mock_text_slice_default_prompt(context, text: str, markup: str) -> None:
    request = TextSliceRequest(
        text=text,
        client=_build_client(),
        prompt_template=_build_prompt_template(),
        mock_marked_up_text=markup,
    )
    context.text_slice_result = apply_text_slice(request)
