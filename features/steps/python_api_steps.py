from __future__ import annotations

import json
from pathlib import Path

import yaml
from behave import given, then, when

from biblicus.corpus import Corpus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _data_for_media_type(media_type: str) -> bytes:
    """
    Provide deterministic fixture data for a media type.

    :param media_type: Internet Assigned Numbers Authority media type.
    :type media_type: str
    :return: Fixture bytes.
    :rtype: bytes
    """

    if media_type == "text/markdown":
        return b"hello\n"
    if media_type.startswith("text/"):
        return b"hello"
    return b"\x89PNG\r\n\x1a\n...binary..."


@given('I have an initialized corpus at "{name}"')
def step_have_initialized_corpus(context, name: str) -> None:
    corpus_path = _corpus_path(context, name)
    context.corpus = Corpus.init(corpus_path)
    context.opened_corpus = None


@when('I open the corpus via the Python application programming interface at "{name}"')
def step_open_corpus_python(context, name: str) -> None:
    corpus_path = _corpus_path(context, name)
    context.opened_corpus = Corpus.open(corpus_path)


@then('the corpus uniform resource identifier starts with "{prefix}"')
def step_corpus_uri_startswith(context, prefix: str) -> None:
    assert context.opened_corpus is not None
    assert context.opened_corpus.uri.startswith(prefix), context.opened_corpus.uri


@when(
    "I ingest an item via the Python application programming interface into corpus "
    '"{name}" with filename "{filename}" and media type "{media_type}"'
)
def step_ingest_item_python(context, name: str, filename: str, media_type: str) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    data = _data_for_media_type(media_type)
    res = corpus.ingest_item(
        data,
        filename=filename,
        media_type=media_type,
        tags=["application-programming-interface"],
        title=None,
        source_uri="python-application-programming-interface",
    )
    context.python_ingest = res
    shown = corpus.get_item(res.item_id)
    context.python_item = json.loads(shown.model_dump_json())


@when(
    "I ingest an item via the Python application programming interface into corpus "
    '"{name}" with no filename and media type "{media_type}"'
)
def step_ingest_item_python_no_filename(context, name: str, media_type: str) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    data = _data_for_media_type(media_type)
    res = corpus.ingest_item(
        data,
        filename=None,
        media_type=media_type,
        tags=["application-programming-interface"],
        title=None,
        source_uri="python-application-programming-interface",
    )
    context.python_ingest = res
    shown = corpus.get_item(res.item_id)
    context.python_item = json.loads(shown.model_dump_json())


@when(
    "I ingest an item via the Python application programming interface with metadata foo "
    '"{value}" into corpus "{name}" with filename "{filename}" and media type "{media_type}"'
)
def step_ingest_item_python_with_metadata(context, value: str, name: str, filename: str, media_type: str) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    data = _data_for_media_type(media_type)
    res = corpus.ingest_item(
        data,
        filename=filename,
        media_type=media_type,
        tags=["application-programming-interface"],
        title=None,
        metadata={"foo": value},
        source_uri="python-application-programming-interface",
    )
    context.python_ingest = res
    shown = corpus.get_item(res.item_id)
    context.python_item = json.loads(shown.model_dump_json())


@when(
    "I ingest a markdown item via the Python application programming interface into corpus "
    '"{name}" with front matter tags and extra tags'
)
def step_ingest_markdown_with_weird_tags(context, name: str) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    md = (
        "---\n"
        "tags:\n"
        "  - x\n"
        "  - \"\"\n"
        "  - 1\n"
        "---\n"
        "body\n"
    ).encode("utf-8")
    res = corpus.ingest_item(
        md,
        filename="note.md",
        media_type="text/markdown",
        tags=[" ", "y"],
        title=None,
        source_uri="python-application-programming-interface",
    )
    context.python_ingest = res
    shown = corpus.get_item(res.item_id)
    context.python_item = json.loads(shown.model_dump_json())


@then("the python ingest result succeeds")
def step_python_ingest_succeeds(context) -> None:
    assert context.python_ingest is not None
    assert context.python_ingest.item_id


@then('the python ingested item has media type "{media_type}"')
def step_python_item_media_type(context, media_type: str) -> None:
    assert context.python_item is not None
    assert context.python_item.get("media_type") == media_type


@then('the python ingested item relpath ends with "{suffix}"')
def step_python_item_relpath_endswith(context, suffix: str) -> None:
    assert context.python_item is not None
    relpath = context.python_item.get("relpath") or ""
    assert relpath.endswith(suffix), relpath


@then('the python ingested item sidecar includes media type "{media_type}"')
def step_python_item_sidecar_media_type(context, media_type: str) -> None:
    assert context.python_item is not None
    relpath = context.python_item.get("relpath")
    assert isinstance(relpath, str) and relpath
    corpus_root = context.corpus.root
    content_path = corpus_root / relpath
    sidecar_path = content_path.with_name(content_path.name + ".biblicus.yml")
    assert sidecar_path.is_file()
    data = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
    assert isinstance(data, dict)
    assert data.get("media_type") == media_type


@then('the python ingested item sidecar includes metadata foo "{value}"')
def step_python_item_sidecar_includes_foo(context, value: str) -> None:
    assert context.python_item is not None
    relpath = context.python_item.get("relpath")
    assert isinstance(relpath, str) and relpath
    corpus_root = context.corpus.root
    content_path = corpus_root / relpath
    sidecar_path = content_path.with_name(content_path.name + ".biblicus.yml")
    assert sidecar_path.is_file()
    data = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
    assert isinstance(data, dict)
    assert data.get("foo") == value


@then('the python ingested item tags equal "{csv}"')
def step_python_item_tags_equal(context, csv: str) -> None:
    assert context.python_item is not None
    expected = [t.strip() for t in csv.split(",") if t.strip()]
    assert (context.python_item.get("tags") or []) == expected
