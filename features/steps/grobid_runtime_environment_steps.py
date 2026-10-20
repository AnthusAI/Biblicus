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


@then(
    'the GROBID consolidation fields are header "{expected_header}" and citations "{expected_citations}"'
)
def step_grobid_consolidation_fields(
    context, expected_header: str, expected_citations: str
) -> None:
    assert grobid_runtime.grobid_consolidation_fields() == {
        "consolidateHeader": expected_header,
        "consolidateCitations": expected_citations,
    }


@then("the GROBID Docker run arguments for port {port:d} are:")
def step_grobid_docker_run_arguments(context, port: int) -> None:
    expected_arguments = [row["argument"] for row in context.table]
    assert grobid_runtime.grobid_docker_run_arguments(port=port) == expected_arguments


@then('the GROBID Docker run arguments contain the pair "{flag}" "{value}"')
def step_grobid_docker_run_arguments_contain_pair(context, flag: str, value: str) -> None:
    arguments = grobid_runtime.grobid_docker_run_arguments(port=8070)
    assert (flag, value) in list(zip(arguments, arguments[1:]))


@then('the resolved GROBID Docker image is "{expected_image}"')
def step_resolved_grobid_docker_image(context, expected_image: str) -> None:
    assert grobid_runtime._grobid_docker_image() == expected_image
