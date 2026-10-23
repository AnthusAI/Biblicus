from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from behave import given, then, when

from biblicus.api import (
    API_COMMANDS,
    ContextPackBuildBlocksRequest,
    QueryRequest,
    ReindexRequest,
    WebMetadataRequest,
    context_pack_build_blocks,
    extract_web_metadata,
    query,
    reindex,
    validate_request,
)
from biblicus.api.schemas import find_stale_api_schemas, write_api_schemas
from biblicus.models import QueryBudget
from features.environment import run_biblicus
from features.steps.api_schema_support import (
    PUBLISHED_SCHEMA_DIRECTORY,
    assert_matches_published_schema,
)


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


@then('the standard output validates against the published "{command_name}" response schema')
def step_standard_output_validates(context, command_name: str) -> None:
    assert context.last_result is not None
    assert context.last_result.returncode == 0, context.last_result.stderr
    assert_matches_published_schema(
        command_name, "response", json.loads(context.last_result.stdout)
    )


@then(
    'the stored topic context output validates against the published "{command_name}" response schema'
)
def step_stored_topic_context_validates(context, command_name: str) -> None:
    assert_matches_published_schema(command_name, "response", context.last_topic_context_output)


@when("I run the command-line interface with arguments and standard input:")
def step_run_with_standard_input(context) -> None:
    arguments = json.loads(context.text.split("\n---\n")[0])
    standard_input = context.text.split("\n---\n")[1] if "\n---\n" in context.text else None
    resolved = [
        (
            str(_corpus_path(context, value[len("corpus:") :]))
            if isinstance(value, str) and value.startswith("corpus:")
            else value
        )
        for value in arguments
    ]
    context.last_result = run_biblicus(context, resolved, input_text=standard_input)


@then("the published application programming interface schemas are current")
def step_published_schemas_current(context) -> None:
    problems = find_stale_api_schemas(PUBLISHED_SCHEMA_DIRECTORY)
    assert problems == [], problems


@then("every Papyrus command has a published request schema and response schema")
def step_every_command_published(context) -> None:
    expected_commands = {
        "taxonomy-record",
        "taxonomy-discover",
        "steering-export",
        "steering-artifacts",
        "steering-graph-signals",
        "steering-render-seed-manifest",
        "topic-classifier-train",
        "topic-classifier-project",
        "analyze-topic-context",
        "analyze-topic-trends",
        "analyze-topic-identity",
        "context-pack-build-blocks",
        "summarize-map-reduce",
        "extract-url-text",
        "extract-article-text",
        "extract-typed-entities",
        "extract-web-metadata",
        "query",
        "reindex",
        "graph-extract",
    }
    assert set(API_COMMANDS) == expected_commands
    for command_name in expected_commands:
        for kind in ("request", "response"):
            path = PUBLISHED_SCHEMA_DIRECTORY / f"{command_name}.{kind}.schema.json"
            assert path.is_file(), path


@given("a scratch copy of the published application programming interface schemas")
def step_scratch_copy(context) -> None:
    context.scratch_schema_directory = Path(tempfile.mkdtemp(prefix="api-schemas-")) / "copy"
    shutil.copytree(PUBLISHED_SCHEMA_DIRECTORY, context.scratch_schema_directory)
    context.add_cleanup(shutil.rmtree, context.scratch_schema_directory.parent, True)


@when("I edit, delete and add published schema files in the scratch copy")
def step_damage_scratch_copy(context) -> None:
    directory = context.scratch_schema_directory
    (directory / "reindex.request.schema.json").write_text("{}\n", encoding="utf-8")
    (directory / "query.response.schema.json").unlink()
    (directory / "stray.schema.json").write_text("{}\n", encoding="utf-8")
    context.schema_problems = find_stale_api_schemas(directory)


@then("the schema check reports the changed, missing and unexpected files")
def step_schema_problems(context) -> None:
    assert context.schema_problems == [
        "missing: query.response.schema.json",
        "changed: reindex.request.schema.json",
        "unexpected: stray.schema.json",
    ]


@when("I regenerate the schemas into the scratch copy")
def step_regenerate_scratch_copy(context) -> None:
    context.written_schema_files = write_api_schemas(context.scratch_schema_directory)
    (context.scratch_schema_directory / "stray.schema.json").unlink()
    context.schema_problems = find_stale_api_schemas(context.scratch_schema_directory)


@then("the scratch copy is current again with {count:d} schema files")
def step_scratch_current(context, count: int) -> None:
    assert len(context.written_schema_files) == count
    assert context.schema_problems == []


@when('I call the Python reindex function for corpus "{corpus_name}"')
def step_python_reindex(context, corpus_name: str) -> None:
    request = validate_request(
        ReindexRequest, "reindex", corpus_path=str(_corpus_path(context, corpus_name))
    )
    context.python_response = reindex(request)


@then("the Python reindex response reports {inserted:d} inserted items")
def step_python_reindex_inserted(context, inserted: int) -> None:
    assert context.python_response.inserted == inserted
    assert_matches_published_schema(
        "reindex", "response", json.loads(context.python_response.model_dump_json())
    )


@when('I call the Python query function for "{query_text}" against corpus "{corpus_name}"')
def step_python_query(context, query_text: str, corpus_name: str) -> None:
    request = validate_request(
        QueryRequest,
        "query",
        corpus_path=str(_corpus_path(context, corpus_name)),
        query_text=query_text,
        budget=QueryBudget(max_total_items=3),
    )
    context.python_error = None
    try:
        context.python_response = query(request)
    except ValueError as error:
        context.python_error = str(error)


@then("the Python query response has evidence")
def step_python_query_evidence(context) -> None:
    assert context.python_error is None
    assert len(context.python_response.evidence) >= 1
    assert_matches_published_schema(
        "query", "response", json.loads(context.python_response.model_dump_json())
    )


@then('the Python query fails with "{message}"')
def step_python_query_fails(context, message: str) -> None:
    assert context.python_error is not None
    assert message in context.python_error, context.python_error


@when("I call the Python context block function with two blocks")
def step_python_context_blocks(context) -> None:
    request = ContextPackBuildBlocksRequest.model_validate(
        {
            "blocks": [
                {"block_id": "a", "section": "doctrine", "text": "First block."},
                {"block_id": "b", "section": "evidence", "text": "Second block."},
            ]
        }
    )
    context.python_response = context_pack_build_blocks(request)


@then("the Python context block response text is {text}")
def step_python_context_block_text(context, text: str) -> None:
    expected = json.loads(text)
    assert context.python_response.text == expected
    assert_matches_published_schema(
        "context-pack-build-blocks",
        "response",
        json.loads(context.python_response.model_dump_json()),
    )


@when("I call the Python web metadata function with supplied HTML")
def step_python_web_metadata(context) -> None:
    request = validate_request(
        WebMetadataRequest,
        "extract web-metadata",
        html_content="<html><head><title>Typed Contract</title></head><body><p>Body</p></body></html>",
    )
    context.python_response = extract_web_metadata(request)


@then('the Python web metadata response has status "{status}" and title "{title}"')
def step_python_web_metadata_response(context, status: str, title: str) -> None:
    assert context.python_response.status == status
    assert context.python_response.title == title
    assert_matches_published_schema(
        "extract-web-metadata",
        "response",
        json.loads(context.python_response.model_dump_json()),
    )


@when('I build a "{label}" request with a blank classifier identifier')
def step_invalid_request(context, label: str) -> None:
    from biblicus.api import TaxonomyDiscoverRequest

    context.python_error = None
    try:
        validate_request(
            TaxonomyDiscoverRequest,
            label,
            corpus_path="corpus",
            classifier_id="",
            extraction_snapshot={"extractor_id": "pipeline", "snapshot_id": "one"},
            unknown_field=True,
        )
    except ValueError as error:
        context.python_error = str(error)


@then('the request error says "{message}"')
def step_request_error(context, message: str) -> None:
    assert context.python_error is not None
    assert message in context.python_error, context.python_error


@when("I build a web metadata request with neither a page address nor HTML")
def step_invalid_web_metadata_request(context) -> None:
    context.python_error = None
    try:
        validate_request(WebMetadataRequest, "extract web-metadata")
    except ValueError as error:
        context.python_error = str(error)
