from __future__ import annotations

import json
from unittest.mock import patch

from behave import given, then, when

from biblicus.api import API_COMMANDS
from biblicus.cli import build_parser
from biblicus.url_text import UrlTextExtractionError
from features.environment import run_biblicus

EMPTY_STANDARD_INPUT_MARKER = "(empty)"


def _resolve_corpus_references(context, arguments: list) -> list:
    return [
        (
            str((context.workdir / value[len("corpus:") :]).resolve())
            if isinstance(value, str) and value.startswith("corpus:")
            else value
        )
        for value in arguments
    ]


def _failed_url_text_payload() -> dict:
    return {
        "status": "failed",
        "source_kind": "web",
        "strategy": "markdown-then-html-then-direct",
        "text": "",
        "markdown": "",
        "title": None,
        "content_type": None,
        "prompt_version": "test",
        "attempts": [{"strategy": "markdown", "outcome": "failed"}],
        "error": {
            "code": "direct_conversion_failed",
            "message": "Conversion failed",
            "details": {"http_status": 503},
        },
    }


def _start_patch(context, patcher) -> None:
    patcher.start()
    context.add_cleanup(patcher.stop)


@given('the typed operation behind "{operation}" fails')
def step_typed_operation_fails(context, operation: str) -> None:
    if operation == "url text failed result":
        _start_patch(
            context,
            patch("biblicus.url_text.extract_url_text", return_value=_failed_url_text_payload()),
        )
    elif operation == "url text raised error":
        _start_patch(
            context,
            patch(
                "biblicus.url_text.extract_url_text",
                side_effect=UrlTextExtractionError(
                    code="grobid_unreachable", message="Service unreachable"
                ),
            ),
        )
    elif operation == "web metadata rejection":
        _start_patch(
            context,
            patch(
                "biblicus.web_reference_metadata.extract_web_reference_metadata_from_html",
                side_effect=ValueError("Page rejected"),
            ),
        )
    else:
        assert operation == "missing corpus", operation


@when("I run the typed command with arguments '{arguments}' and standard input '{standard_input}'")
def step_run_typed_command(context, arguments: str, standard_input: str) -> None:
    resolved = _resolve_corpus_references(context, json.loads(arguments))
    text = "" if standard_input == EMPTY_STANDARD_INPUT_MARKER else standard_input
    run_biblicus(context, resolved, input_text=text)


def _failure_envelope(context) -> dict:
    stdout = context.last_result.stdout
    envelope = json.loads(stdout)
    assert set(envelope) == {"status", "error"}, envelope
    assert envelope["status"] == "failed", envelope
    assert set(envelope["error"]) == {"code", "message", "details"}, envelope
    assert isinstance(envelope["error"]["details"], dict), envelope
    return envelope


@then('standard output is one failure envelope with code "{code}"')
def step_standard_output_is_failure_envelope(context, code: str) -> None:
    envelope = _failure_envelope(context)
    assert envelope["error"]["code"] == code, envelope


@then('the failure envelope message includes "{text}"')
def step_failure_envelope_message_includes(context, text: str) -> None:
    message = _failure_envelope(context)["error"]["message"]
    assert text in message, message


@then('the failure envelope details include "{key}" with JSON {value}')
def step_failure_envelope_details_include(context, key: str, value: str) -> None:
    assert _failure_envelope(context)["error"]["details"][key] == json.loads(value)


@then('the failure envelope details have exactly the keys "{keys}"')
def step_failure_envelope_details_keys(context, keys: str) -> None:
    expected = {key.strip() for key in keys.split(",")}
    assert set(_failure_envelope(context)["error"]["details"]) == expected


@then("standard error is empty")
def step_standard_error_is_empty(context) -> None:
    assert context.last_result.stderr == "", context.last_result.stderr


@then("standard output is empty")
def step_standard_output_is_empty(context) -> None:
    assert context.last_result.stdout == "", context.last_result.stdout


@then("standard error is plain text rather than JSON")
def step_standard_error_is_plain_text(context) -> None:
    stderr = context.last_result.stderr
    assert stderr.strip()
    try:
        json.loads(stderr)
    except json.JSONDecodeError:
        return
    raise AssertionError(f"Standard error parsed as JSON: {stderr}")


@then('the typed command succeeds with status "{status}" on standard output')
def step_typed_command_succeeds(context, status: str) -> None:
    assert context.last_result.returncode == 0, context.last_result.stderr
    assert json.loads(context.last_result.stdout)["status"] == status


def _declared_typed_commands() -> set[str]:
    import argparse

    declared: set[str] = set()

    def walk(parser: argparse.ArgumentParser, path: tuple[str, ...]) -> None:
        subparser_actions = [
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ]
        if not subparser_actions:
            label = parser.get_default("typed_command")
            if label is not None:
                assert label == " ".join(path), (label, path)
                declared.add("-".join(path))
            return
        for action in subparser_actions:
            for name, child in action.choices.items():
                walk(child, path + (name,))

    walk(build_parser(), ())
    return declared


@then("every typed command declares the failure envelope")
def step_every_typed_command_declares_envelope(context) -> None:
    assert _declared_typed_commands() == set(API_COMMANDS), _declared_typed_commands() ^ set(
        API_COMMANDS
    )
