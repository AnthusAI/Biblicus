from __future__ import annotations

import io
import json
from pathlib import Path
import yaml
from behave import given, then, when

from biblicus.corpus import Corpus
from biblicus.hook_manager import HookManager
from biblicus.hooks import HookContext, HookPoint, LifecycleHook
from biblicus.sources import load_source


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
def step_ingest_item_python_with_metadata(
    context, value: str, name: str, filename: str, media_type: str
) -> None:
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
    md = ("---\n" "tags:\n" "  - x\n" '  - ""\n' "  - 1\n" "---\n" "body\n").encode("utf-8")
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


@when(
    "I ingest an item via the Python application programming interface into corpus "
    '"{name}" with source uniform resource identifier "{source_uri}" and filename "{filename}"'
)
def step_ingest_item_python_with_source_uri(
    context, name: str, source_uri: str, filename: str
) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    res = corpus.ingest_item(
        b"payload",
        filename=filename,
        media_type="text/plain",
        tags=["application-programming-interface"],
        title=None,
        source_uri=source_uri,
    )
    context.python_ingest = res


@then('the corpus "{name}" hook logs do not include "{text}"')
def step_hook_logs_do_not_include(context, name: str, text: str) -> None:
    corpus_path = _corpus_path(context, name)
    log_dir = corpus_path / ".biblicus" / "hook_logs"
    combined = ""
    if log_dir.is_dir():
        for p in sorted(log_dir.glob("*.jsonl")):
            combined += p.read_text(encoding="utf-8")
    assert text not in combined


@then('the corpus "{name}" hook logs include "{text}"')
def step_hook_logs_include(context, name: str, text: str) -> None:
    corpus_path = _corpus_path(context, name)
    log_dir = corpus_path / ".biblicus" / "hook_logs"
    combined = ""
    if log_dir.is_dir():
        for p in sorted(log_dir.glob("*.jsonl")):
            combined += p.read_text(encoding="utf-8")
    assert text in combined


@given('I have a file "{filename}" with contents "{contents}"')
def step_have_file_with_contents(context, filename: str, contents: str) -> None:
    (context.workdir / filename).write_text(contents, encoding="utf-8")


@when('I load the source "{source}"')
def step_load_source(context, source: str) -> None:
    candidate_path = (context.workdir / source).resolve()
    context.loaded_source = load_source(str(candidate_path))


@then('the source payload filename is "{filename}"')
def step_source_payload_filename(context, filename: str) -> None:
    payload = getattr(context, "loaded_source", None)
    assert payload is not None
    assert payload.filename == filename


@then('the source payload source uniform resource identifier starts with "{prefix}"')
def step_source_payload_source_uri_prefix(context, prefix: str) -> None:
    payload = getattr(context, "loaded_source", None)
    assert payload is not None
    assert payload.source_uri.startswith(prefix), payload.source_uri


@when("I execute a hook manager with a non-Pydantic hook result")
def step_execute_hook_manager_with_bad_hook(context) -> None:
    class NonPydanticHook:
        hook_id = "non-pydantic"
        hook_points = [HookPoint.before_ingest]

        def run(self, hook_context):
            _ = hook_context
            return {"message": "not a model"}

    manager = HookManager(
        corpus_uri="file://example", log_dir=context.workdir / "logs", hooks=[NonPydanticHook()]
    )
    try:
        manager.run_ingest_hooks(
            hook_point=HookPoint.before_ingest,
            filename="x",
            media_type="text/plain",
            title=None,
            tags=[],
            metadata={},
            source_uri="example",
        )
        context.hook_error = None
    except Exception as exc:
        context.hook_error = exc


@then("a hook result error is raised")
def step_hook_result_error_raised(context) -> None:
    err = getattr(context, "hook_error", None)
    assert err is not None
    assert "non-Pydantic" in str(err) or "non-Pydantic result" in str(err)


@when('I attempt stream ingestion of a Markdown item into corpus "{name}"')
def step_attempt_stream_ingest_markdown(context, name: str) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    try:
        with (context.workdir / "tmp.md").open("wb") as handle:
            handle.write(b"---\n---\n")
        with (context.workdir / "tmp.md").open("rb") as handle:
            corpus.ingest_item_stream(
                handle,
                filename="tmp.md",
                media_type="text/markdown",
                source_uri="file://tmp.md",
            )
        context.stream_ingest_error = None
    except Exception as exc:
        context.stream_ingest_error = exc


@then("the python stream ingestion error is raised")
def step_python_stream_ingest_error(context) -> None:
    err = getattr(context, "stream_ingest_error", None)
    assert err is not None
    assert "Stream ingestion is not supported for Markdown" in str(err)


@when('I stream ingest bytes into corpus "{name}" with no filename and media type "{media_type}"')
def step_stream_ingest_no_filename(context, name: str, media_type: str) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    res = corpus.ingest_item_stream(
        io.BytesIO(b"streamed"),
        filename=None,
        media_type=media_type,
        tags=["application-programming-interface"],
        metadata=None,
        source_uri="python-stream",
    )
    context.python_ingest = res
    shown = corpus.get_item(res.item_id)
    context.python_item = json.loads(shown.model_dump_json())


@when(
    'I stream ingest bytes into corpus "{name}" with filename "{filename}" and media type "{media_type}" and metadata foo "{value}"'
)
def step_stream_ingest_with_metadata(
    context, name: str, filename: str, media_type: str, value: str
) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    res = corpus.ingest_item_stream(
        io.BytesIO(b"streamed"),
        filename=filename,
        media_type=media_type,
        tags=["application-programming-interface"],
        metadata={"foo": value},
        source_uri="python-stream",
    )
    context.python_ingest = res
    shown = corpus.get_item(res.item_id)
    context.python_item = json.loads(shown.model_dump_json())


@when("I call the base lifecycle hook run method")
def step_call_base_hook_run(context) -> None:
    try:
        hook_context = HookContext(
            hook_point=HookPoint.before_ingest,
            operation_id="operation",
            corpus_uri="file://corpus",
            created_at="2000-01-01T00:00:00Z",
        )
        LifecycleHook().run(hook_context)
        context.base_hook_error = None
    except Exception as exc:
        context.base_hook_error = exc


@then("a hook not implemented error is raised")
def step_hook_not_implemented_error(context) -> None:
    err = getattr(context, "base_hook_error", None)
    assert err is not None
    assert isinstance(err, NotImplementedError)


@when("I execute a hook manager with a hook that raises an exception")
def step_execute_hook_manager_with_raising_hook(context) -> None:
    class RaisingHook:
        hook_id = "raising"
        hook_points = [HookPoint.before_ingest]

        def run(self, hook_context):
            _ = hook_context
            raise RuntimeError("boom")

    manager = HookManager(
        corpus_uri="file://example", log_dir=context.workdir / "logs", hooks=[RaisingHook()]
    )
    try:
        manager.run_ingest_hooks(
            hook_point=HookPoint.before_ingest,
            filename="x",
            media_type="text/plain",
            title=None,
            tags=[],
            metadata={},
            source_uri="example",
        )
        context.raising_hook_error = None
    except Exception as exc:
        context.raising_hook_error = exc


@then("a hook execution error is raised")
def step_hook_execution_error_raised(context) -> None:
    err = getattr(context, "raising_hook_error", None)
    assert err is not None
    assert "failed" in str(err) and "boom" in str(err)
