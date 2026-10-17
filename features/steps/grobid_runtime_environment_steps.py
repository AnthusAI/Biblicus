"""
Step definitions for GROBID runtime environment resolution.
"""

from __future__ import annotations

import os

from behave import given, then

from biblicus import grobid_runtime


def _restore_environment_variable(name: str, previous_value: str | None) -> None:
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remember_environment_variable(context, name: str) -> None:
    context.add_cleanup(_restore_environment_variable, name, os.environ.get(name))


@given('the GROBID environment variable "{name}" is "{value}"')
def step_set_grobid_environment_variable(context, name: str, value: str) -> None:
    _remember_environment_variable(context, name)
    os.environ[name] = value


@given('the GROBID environment variable "{name}" is unset')
def step_unset_grobid_environment_variable(context, name: str) -> None:
    _remember_environment_variable(context, name)
    os.environ.pop(name, None)


@then('the resolved GROBID base URL is "{expected_url}"')
def step_resolved_grobid_base_url(context, expected_url: str) -> None:
    assert grobid_runtime.resolve_grobid_base_url() == expected_url


@then('the resolved GROBID container name is "{expected_name}"')
def step_resolved_grobid_container_name(context, expected_name: str) -> None:
    assert grobid_runtime._grobid_container_name() == expected_name


@then('the resolved GROBID Docker image is "{expected_image}"')
def step_resolved_grobid_docker_image(context, expected_image: str) -> None:
    assert grobid_runtime._grobid_docker_image() == expected_image
