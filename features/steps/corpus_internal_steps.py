from __future__ import annotations

import io

from behave import then, when

from biblicus import corpus as corpus_module
from biblicus.corpus import (
    _preferred_extension_for_media_type,
    _storage_filename_for_ingest,
)
from biblicus.errors import IngestCollisionError


@when("I build a storage filename for a long source uri")
def step_storage_filename_long(context) -> None:
    source_uri = "http://example.com/" + ("a" * 500)
    context.storage_filename = _storage_filename_for_ingest(
        filename=None,
        media_type="text/plain",
        source_uri=source_uri,
    )


@when("I build a storage filename without hints")
def step_storage_filename_empty(context) -> None:
    context.storage_filename = _storage_filename_for_ingest(
        filename=None,
        media_type="text/plain",
        source_uri=None,
    )


@when('I build a storage filename with filename "{filename}" and no source uri')
def step_storage_filename_filename_only(context, filename: str) -> None:
    context.storage_filename = _storage_filename_for_ingest(
        filename=filename,
        media_type="application/pdf",
        source_uri=None,
    )


@when('I build a storage filename with filename "{filename}" and source uri "{source_uri}"')
def step_storage_filename_with_source_uri(context, filename: str, source_uri: str) -> None:
    context.storage_filename = _storage_filename_for_ingest(
        filename=filename,
        media_type="text/plain",
        source_uri=source_uri,
    )


@when('I build a storage filename with an empty sanitized filename and source uri "{source_uri}"')
def step_storage_filename_empty_sanitized(context, source_uri: str) -> None:
    original_sanitize = corpus_module._sanitize_filename
    try:
        corpus_module._sanitize_filename = lambda _name: ""
        context.storage_filename = _storage_filename_for_ingest(
            filename="bad",
            media_type="text/plain",
            source_uri=source_uri,
        )
    finally:
        corpus_module._sanitize_filename = original_sanitize


@when('I lookup an item by source uri "{value}"')
def step_lookup_source_uri(context, value: str) -> None:
    normalized = "" if value == "<empty>" else value
    context.lookup_item = context.corpus._find_item_by_source_uri(normalized)


@when('I ingest bytes with no filename and no source uri and media type "{media_type}"')
def step_ingest_bytes_no_filename(context, media_type: str) -> None:
    result = context.corpus.ingest_item(
        b"data",
        filename=None,
        media_type=media_type,
        title=None,
        tags=(),
        metadata=None,
        source_uri=None,
    )
    item = context.corpus.get_item(result.item_id)
    context.ingested_relpath = item.relpath
    context.ingested_item_id = result.item_id


@when("I stream-ingest the same source uri twice")
def step_stream_ingest_collision(context) -> None:
    stream = io.BytesIO(b"data")
    context.stream_error = None
    context.corpus.ingest_item_stream(
        stream,
        filename=None,
        media_type="application/octet-stream",
        tags=(),
        metadata=None,
        source_uri="stream:dup",
    )
    try:
        context.corpus.ingest_item_stream(
            io.BytesIO(b"data"),
            filename=None,
            media_type="application/octet-stream",
            tags=(),
            metadata=None,
            source_uri="stream:dup",
        )
    except IngestCollisionError as exc:
        context.stream_error = exc


@when('I stream-ingest bytes with no filename and empty source uri and media type "{media_type}"')
def step_stream_ingest_no_source_uri(context, media_type: str) -> None:
    context.stream_ingest_extension = _preferred_extension_for_media_type(media_type) or ""
    result = context.corpus.ingest_item_stream(
        io.BytesIO(b"data"),
        filename=None,
        media_type=media_type,
        tags=(),
        metadata=None,
        source_uri="",
    )
    item = context.corpus.get_item(result.item_id)
    context.stream_ingested_relpath = item.relpath


@when("I ingest a note without a source uri")
def step_ingest_note_no_source_uri(context) -> None:
    result = context.corpus.ingest_note("Hello", title="Note", source_uri=None)
    item = context.corpus.get_item(result.item_id)
    context.note_source_uri = item.source_uri


@when('I ingest a note with source uri "{source_uri}"')
def step_ingest_note_with_source_uri(context, source_uri: str) -> None:
    result = context.corpus.ingest_note("Hello", title="Note", source_uri=source_uri)
    item = context.corpus.get_item(result.item_id)
    context.note_source_uri = item.source_uri


@then('the storage filename starts with "{prefix}"')
def step_storage_filename_starts_with(context, prefix: str) -> None:
    assert context.storage_filename.startswith(prefix)


@then('the storage filename equals "{expected}"')
def step_storage_filename_equals(context, expected: str) -> None:
    normalized = "" if expected == "<empty>" else expected
    assert context.storage_filename == normalized


@then('the storage filename contains "{expected}"')
def step_storage_filename_contains(context, expected: str) -> None:
    assert expected in context.storage_filename


@then("the lookup result is empty")
def step_lookup_empty(context) -> None:
    assert context.lookup_item is None


@then("the stored relpath contains the item id")
def step_relpath_contains_item_id(context) -> None:
    assert context.ingested_item_id in context.ingested_relpath


@then('the stream ingestion error mentions "{message}"')
def step_stream_error_mentions(context, message: str) -> None:
    assert context.stream_error is not None
    assert message in str(context.stream_error)


@then('the stream-ingested relpath ends with the preferred extension for "{media_type}"')
def step_stream_ingested_relpath_extension(context, media_type: str) -> None:
    expected_extension = _preferred_extension_for_media_type(media_type) or ""
    if expected_extension:
        assert context.stream_ingested_relpath.endswith(expected_extension)
    else:
        assert context.stream_ingested_relpath


@then('the note source uri starts with "{prefix}"')
def step_note_source_uri_prefix(context, prefix: str) -> None:
    assert context.note_source_uri.startswith(prefix)


@then('the note source uri equals "{expected}"')
def step_note_source_uri_equals(context, expected: str) -> None:
    assert context.note_source_uri == expected
