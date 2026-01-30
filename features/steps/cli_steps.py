from __future__ import annotations

import hashlib
import json
import re
import runpy
import shlex
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

import yaml
from behave import given, then, when

from biblicus.models import RetrievalResult
from features.environment import RunResult, run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _parse_ingest_standard_output(standard_output: str) -> Dict[str, str]:
    """
    Parse the ingest output line.

    :param standard_output: Command-line interface standard output content.
    :type standard_output: str
    :return: Parsed ingest fields.
    :rtype: dict[str, str]
    """
    line = standard_output.strip().splitlines()[-1]
    parts = line.split("\t")
    if len(parts) != 3:
        raise AssertionError(f"Unexpected ingest output: {standard_output!r}")
    return {"id": parts[0], "relpath": parts[1], "sha256": parts[2]}


def _record_ingest(context, result) -> None:
    context.last_ingest = (
        _parse_ingest_standard_output(result.stdout) if result.returncode == 0 else None
    )
    if context.last_ingest:
        context.ingested_ids.append(context.last_ingest["id"])


def _parse_markdown_front_matter(text: str) -> Dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    raw_yaml = text[4:end]
    data = yaml.safe_load(raw_yaml) or {}
    if not isinstance(data, dict):
        raise AssertionError("Front matter must be a mapping/object")
    return dict(data)


@when('I run "context-pack build" joining with "{join_with}"')
def step_context_pack_build_from_standard_input(context, join_with: str) -> None:
    decoded_join_with = bytes(join_with, "utf-8").decode("unicode_escape")
    retrieval_result_json = context.retrieval_result.model_dump_json(indent=2)
    result = run_biblicus(
        context,
        ["context-pack", "build", "--join-with", decoded_join_with],
        input_text=retrieval_result_json,
    )
    context.last_result = result
    assert result.returncode == 0, result.stderr
    context.context_pack_build_output = json.loads(result.stdout)


@when('I run "context-pack build" joining with "{join_with}" and token budget {max_tokens:d}')
def step_context_pack_build_with_token_budget_from_standard_input(
    context, join_with: str, max_tokens: int
) -> None:
    decoded_join_with = bytes(join_with, "utf-8").decode("unicode_escape")
    retrieval_result_json = context.retrieval_result.model_dump_json(indent=2)
    result = run_biblicus(
        context,
        [
            "context-pack",
            "build",
            "--join-with",
            decoded_join_with,
            "--max-tokens",
            str(max_tokens),
        ],
        input_text=retrieval_result_json,
    )
    context.last_result = result
    assert result.returncode == 0, result.stderr
    context.context_pack_build_output = json.loads(result.stdout)


@when(
    'I run "context-pack build" joining with "{join_with}" ordering "{ordering}" and including metadata'
)
def step_context_pack_build_with_metadata_from_standard_input(
    context, join_with: str, ordering: str
) -> None:
    decoded_join_with = bytes(join_with, "utf-8").decode("unicode_escape")
    retrieval_result_json = context.retrieval_result.model_dump_json(indent=2)
    result = run_biblicus(
        context,
        [
            "context-pack",
            "build",
            "--join-with",
            decoded_join_with,
            "--ordering",
            ordering,
            "--include-metadata",
        ],
        input_text=retrieval_result_json,
    )
    context.last_result = result
    assert result.returncode == 0, result.stderr
    context.context_pack_build_output = json.loads(result.stdout)


@when(
    'I run "context-pack build" joining with "{join_with}" and character budget {max_characters:d}'
)
def step_context_pack_build_with_character_budget_from_standard_input(
    context, join_with: str, max_characters: int
) -> None:
    decoded_join_with = bytes(join_with, "utf-8").decode("unicode_escape")
    retrieval_result_json = context.retrieval_result.model_dump_json(indent=2)
    result = run_biblicus(
        context,
        [
            "context-pack",
            "build",
            "--join-with",
            decoded_join_with,
            "--max-characters",
            str(max_characters),
        ],
        input_text=retrieval_result_json,
    )
    context.last_result = result
    assert result.returncode == 0, result.stderr
    context.context_pack_build_output = json.loads(result.stdout)


@when('I run "context-pack build" with empty standard input')
def step_context_pack_build_with_empty_standard_input(context) -> None:
    result = run_biblicus(context, ["context-pack", "build", "--join-with", "\n\n"], input_text="")
    context.last_result = result


@then("the context pack build output text equals:")
def step_then_context_pack_build_output_text_equals(context) -> None:
    actual_text = context.context_pack_build_output["context_pack"]["text"]
    assert actual_text == context.text


@when('I initialize a corpus at "{name}"')
def step_init_corpus(context, name: str) -> None:
    result = run_biblicus(context, ["init", str(_corpus_path(context, name))])
    assert result.returncode == 0, result.stderr


@when('I attempt to initialize a corpus at "{name}"')
def step_attempt_init_corpus(context, name: str) -> None:
    run_biblicus(context, ["init", str(_corpus_path(context, name))])


@given('the environment variable "{var_name}" is set to "{value}"')
def step_set_environment_variable(context, var_name: str, value: str) -> None:
    extra_env = getattr(context, "extra_env", None)
    if extra_env is None:
        extra_env = {}
        context.extra_env = extra_env
    extra_env[var_name] = value


@given('I initialized a corpus at "{name}"')
def step_given_init_corpus(context, name: str) -> None:
    step_init_corpus(context, name)


@then('the corpus directory "{name}" exists')
def step_corpus_dir_exists(context, name: str) -> None:
    assert _corpus_path(context, name).is_dir()


@then("the corpus has a config file")
def step_corpus_has_config(context) -> None:
    candidates = list(context.workdir.rglob(".biblicus/config.json"))
    assert len(candidates) == 1


@then("the corpus has a catalog file")
def step_corpus_has_catalog(context) -> None:
    candidates = list(context.workdir.rglob(".biblicus/catalog.json"))
    assert len(candidates) == 1


@when(
    'I ingest the text "{text}" with title "{title}" and tags "{tags}" into corpus "{corpus_name}"'
)
def step_ingest_text(context, text: str, title: str, tags: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    args = ["--corpus", str(corpus), "ingest", "--note", text, "--title", title]
    for tag in [t.strip() for t in tags.split(",") if t.strip()]:
        args.extend(["--tag", tag])
    result = run_biblicus(context, args)
    _record_ingest(context, result)


@when('I ingest the text "{text}" with no metadata into corpus "{corpus_name}"')
def step_ingest_text_minimal(context, text: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    result = run_biblicus(context, ["--corpus", str(corpus), "ingest", "--note", text])
    _record_ingest(context, result)


@given('I ingested note items into corpus "{corpus_name}":')
def step_ingest_note_items_table(context, corpus_name: str) -> None:
    for row in context.table:
        step_ingest_text_minimal(context, row["text"], corpus_name)


@given('I built a scan run for corpus "{corpus_name}"')
def step_build_scan_run(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        ["--corpus", str(corpus), "build", "--backend", "scan"],
    )
    assert result.returncode == 0, result.stderr


@when('I query corpus "{corpus_name}" with query "{query_text}" reranking with "{reranker_id}"')
def step_query_with_rerank(context, corpus_name: str, query_text: str, reranker_id: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        ["--corpus", str(corpus), "query", "--query", query_text, "--reranker-id", reranker_id],
    )
    assert result.returncode == 0, result.stderr
    context.last_query_result = RetrievalResult.model_validate_json(result.stdout)


@when(
    'I query corpus "{corpus_name}" with query "{query_text}" filtering with minimum score {minimum_score:f}'
)
def step_query_with_minimum_score_filter(
    context, corpus_name: str, query_text: str, minimum_score: float
) -> None:
    corpus = _corpus_path(context, corpus_name)
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(corpus),
            "query",
            "--query",
            query_text,
            "--minimum-score",
            str(minimum_score),
        ],
    )
    assert result.returncode == 0, result.stderr
    context.last_query_result = RetrievalResult.model_validate_json(result.stdout)


@then("the query result evidence text order is:")
def step_then_query_result_evidence_text_order_is(context) -> None:
    expected_text_values = [row["text"] for row in context.table]
    actual_text_values = [
        evidence_item.text for evidence_item in context.last_query_result.evidence
    ]
    assert actual_text_values == expected_text_values


@when(
    'I ingest the text "{text}" with title "{title}" and comma-tags "{tags}" into corpus "{corpus_name}"'
)
def step_ingest_text_with_tags_csv(
    context, text: str, title: str, tags: str, corpus_name: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    args = ["--corpus", str(corpus), "ingest", "--note", text, "--title", title, "--tags", tags]
    result = run_biblicus(context, args)
    _record_ingest(context, result)


@when('I ingest the file "{filename}" with tags "{tags}" into corpus "{corpus_name}"')
def step_ingest_file(context, filename: str, tags: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    path = (context.workdir / filename).resolve()
    args = ["--corpus", str(corpus), "ingest", str(path)]
    for tag in [t.strip() for t in tags.split(",") if t.strip()]:
        args.extend(["--tag", tag])
    result = run_biblicus(context, args)
    _record_ingest(context, result)


@when('I ingest the file "{filename}" into corpus "{corpus_name}"')
def step_ingest_file_no_tags(context, filename: str, corpus_name: str) -> None:
    step_ingest_file(context, filename, "", corpus_name)


@when('I ingest the uniform resource locator "{url}" into corpus "{corpus_name}"')
def step_ingest_url(context, url: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    result = run_biblicus(context, ["--corpus", str(corpus), "ingest", url])
    _record_ingest(context, result)


@then("the last ingest succeeds")
def step_last_ingest_succeeds(context) -> None:
    assert context.last_result is not None
    assert context.last_result.returncode == 0, context.last_result.stderr
    assert context.last_ingest is not None


@then("the last ingested item is stored in the corpus raw folder")
def step_last_item_stored_in_raw(context) -> None:
    assert context.last_ingest is not None
    relpath = Path(context.last_ingest["relpath"])
    assert relpath.parts[0] == "raw"


@then('the last ingested item is a markdown note with title "{title}" and tags:')
def step_last_item_markdown_note(context, title: str) -> None:
    assert context.last_ingest is not None
    relpath = context.last_ingest["relpath"]
    content = (context.last_corpus_root / relpath).read_text(encoding="utf-8")
    meta = _parse_markdown_front_matter(content)
    assert meta.get("title") == title
    assert isinstance(meta.get("tags"), list)
    expected = [row[0] for row in context.table]
    assert meta["tags"] == expected


@then('the last ingested item has biblicus provenance with source "{source}"')
def step_last_item_has_provenance_source(context, source: str) -> None:
    assert context.last_ingest is not None
    relpath = context.last_ingest["relpath"]
    content = (context.last_corpus_root / relpath).read_text(encoding="utf-8")
    meta = _parse_markdown_front_matter(content)
    bib = meta.get("biblicus")
    assert isinstance(bib, dict)
    assert bib.get("id") == context.last_ingest["id"]
    assert bib.get("source") == source


@given('a file "{filename}" exists with markdown front matter:')
def step_file_with_front_matter(context, filename: str) -> None:
    path = context.workdir / filename
    meta: Dict[str, Any] = {}
    for row in context.table:
        key, value = row[0], row[1]
        if key == "tags":
            meta[key] = [v.strip() for v in str(value).split(",") if v.strip()]
        else:
            meta[key] = value
    yaml_text = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    path.write_text(f"---\n{yaml_text}\n---\n", encoding="utf-8")


@given('the file "{filename}" has body:')
def step_file_body(context, filename: str) -> None:
    path = context.workdir / filename
    path.write_text(path.read_text(encoding="utf-8") + context.text, encoding="utf-8")


@given('a file "{filename}" exists with contents:')
def step_file_exists_with_contents(context, filename: str) -> None:
    path = context.workdir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(context.text, encoding="utf-8")


@given('a file "{filename}" exists with bytes:')
def step_file_exists_with_bytes(context, filename: str) -> None:
    raw = context.text.strip()
    data = raw.encode("utf-8").decode("unicode_escape").encode("latin1")
    (context.workdir / filename).write_bytes(data)


@then('the last ingested item is markdown with title "{title}" and tags:')
def step_last_item_markdown_with_title_tags(context, title: str) -> None:
    assert context.last_ingest is not None
    relpath = context.last_ingest["relpath"]
    raw = (context.last_corpus_root / relpath).read_text(encoding="utf-8")
    meta = _parse_markdown_front_matter(raw)
    assert meta.get("title") == title
    expected = [row[0] for row in context.table]
    assert meta.get("tags") == expected
    bib = meta.get("biblicus")
    assert isinstance(bib, dict)
    assert bib.get("id") == context.last_ingest["id"]


@given('a binary file "{filename}" exists')
def step_binary_file_exists(context, filename: str) -> None:
    (context.workdir / filename).write_bytes(b"%PDF-1.4\n%...\n")


@given('a binary file "{filename}" exists with Portable Document Format bytes')
def step_binary_file_exists_pdf_bytes(context, filename: str) -> None:
    (context.workdir / filename).write_bytes(b"%PDF-1.7\n%...\n")


@given('a binary file "{filename}" exists with invalid Unicode Transformation Format 8 bytes')
def step_binary_file_exists_invalid_utf8(context, filename: str) -> None:
    (context.workdir / filename).write_bytes(b"\xff\xfe\xfa")


@given('a binary file "{filename}" exists with size {size:d} bytes')
def step_binary_file_exists_with_size(context, filename: str, size: int) -> None:
    path = context.workdir / filename
    path.write_bytes(b"a" * size)


@given('a text file "{filename}" exists with contents "{contents}"')
def step_text_file_exists(context, filename: str, contents: str) -> None:
    (context.workdir / filename).write_text(contents, encoding="utf-8")


@given('a file "{filename}" exists with invalid Yet Another Markup Language front matter list')
def step_invalid_front_matter_list(context, filename: str) -> None:
    (context.workdir / filename).write_text("---\n- a\n---\nbody\n", encoding="utf-8")


@given(
    'a raw file with universally unique identifier "{item_id}" exists in corpus "{corpus_name}" named "{name}" with '
    'contents "{contents}"'
)
def step_raw_file_with_uuid_exists(
    context, item_id: str, corpus_name: str, name: str, contents: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    (corpus / "raw").mkdir(parents=True, exist_ok=True)
    (corpus / "raw" / f"{item_id}--{name}").write_text(contents, encoding="utf-8")


@given(
    'a raw file with universally unique identifier "{item_id}" exists in corpus "{corpus_name}" named "{name}" with '
    "contents:"
)
def step_raw_file_with_uuid_exists_doc(context, item_id: str, corpus_name: str, name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    (corpus / "raw").mkdir(parents=True, exist_ok=True)
    (corpus / "raw" / f"{item_id}--{name}").write_text(context.text, encoding="utf-8")


@given(
    "a raw file with universally unique identifier "
    '"{item_id}" exists in corpus "{corpus_name}" named "{name}" with invalid Unicode Transformation Format 8 bytes'
)
def step_raw_file_with_uuid_exists_invalid_utf8(
    context, item_id: str, corpus_name: str, name: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    (corpus / "raw").mkdir(parents=True, exist_ok=True)
    (corpus / "raw" / f"{item_id}--{name}").write_bytes(b"\xff\xfe\xfa")


@given('a raw file named "{filename}" exists in corpus "{corpus_name}" with contents "{contents}"')
def step_raw_file_named_exists(context, filename: str, corpus_name: str, contents: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    (corpus / "raw").mkdir(parents=True, exist_ok=True)
    (corpus / "raw" / filename).write_text(contents, encoding="utf-8")


@given(
    'a sidecar for raw file "{raw_filename}" exists in corpus "{corpus_name}" with Yet Another Markup Language:'
)
def step_sidecar_for_raw_file(context, raw_filename: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    content_path = corpus / "raw" / raw_filename
    sidecar_path = content_path.with_name(content_path.name + ".biblicus.yml")
    sidecar_path.write_text(context.text.strip() + "\n", encoding="utf-8")


@then("the last ingested item has a sidecar metadata file")
def step_has_sidecar(context) -> None:
    assert context.last_ingest is not None
    relpath = Path(context.last_ingest["relpath"])
    sidecar = (context.last_corpus_root / relpath).with_name(relpath.name + ".biblicus.yml")
    assert sidecar.is_file()
    data = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
    assert isinstance(data, dict)


@then('the last ingested item\'s sidecar includes media type "{media_type}"')
def step_sidecar_includes_media_type(context, media_type: str) -> None:
    assert context.last_ingest is not None
    relpath = Path(context.last_ingest["relpath"])
    sidecar = (context.last_corpus_root / relpath).with_name(relpath.name + ".biblicus.yml")
    assert sidecar.is_file()
    data = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
    assert isinstance(data, dict)
    assert data.get("media_type") == media_type


@then('the last ingested item relpath ends with "{suffix}"')
def step_last_ingested_relpath_endswith(context, suffix: str) -> None:
    assert context.last_ingest is not None
    relpath = context.last_ingest["relpath"]
    assert relpath.endswith(suffix), relpath


@given("a hypertext transfer protocol server is serving the workdir")
def step_http_server_serving(context) -> None:
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, message_format, *args):
            return

    handler = partial(QuietHandler, directory=str(context.workdir))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    context.httpd = httpd
    host, port = httpd.server_address
    context.http_base_url = f"http://{host}:{port}/"


@given("a hypertext transfer protocol server is serving the workdir without content type headers")
def step_http_server_serving_without_content_type(context) -> None:
    class NoContentTypeHandler(SimpleHTTPRequestHandler):
        def log_message(self, message_format, *args):
            return

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def guess_type(self, path: str) -> str:
            return "application/octet-stream"

    handler = partial(NoContentTypeHandler, directory=str(context.workdir))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    context.httpd = httpd
    host, port = httpd.server_address
    context.http_base_url = f"http://{host}:{port}/"


@given(
    'a hypertext transfer protocol server is serving the workdir with content type "{media_type}"'
)
def step_http_server_serving_with_content_type(context, media_type: str) -> None:
    class ForcedContentTypeHandler(SimpleHTTPRequestHandler):
        def log_message(self, message_format, *args):
            return

        def guess_type(self, path: str) -> str:
            _ = path
            return media_type

    handler = partial(ForcedContentTypeHandler, directory=str(context.workdir))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    context.httpd = httpd
    host, port = httpd.server_address
    context.http_base_url = f"http://{host}:{port}/"


@when('I ingest the file uniform resource locator for "{filename}" into corpus "{corpus_name}"')
def step_ingest_file_url(context, filename: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    url = (context.workdir / filename).resolve().as_uri()
    result = run_biblicus(context, ["--corpus", str(corpus), "ingest", url])
    context.last_ingest = (
        _parse_ingest_standard_output(result.stdout) if result.returncode == 0 else None
    )


@when(
    'I ingest the hypertext transfer protocol uniform resource locator for "{filename}" into corpus "{corpus_name}"'
)
def step_ingest_http_url(context, filename: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    context.last_corpus_root = corpus
    base = getattr(context, "http_base_url", None)
    assert isinstance(base, str) and base
    url = base + quote(filename)
    result = run_biblicus(context, ["--corpus", str(corpus), "ingest", url])
    context.last_ingest = (
        _parse_ingest_standard_output(result.stdout) if result.returncode == 0 else None
    )


@then(
    "the last ingested item has biblicus provenance with a file source uniform resource identifier"
)
def step_has_file_source_uri(context) -> None:
    assert context.last_ingest is not None
    corpus_root = context.last_corpus_root
    res = run_biblicus(context, ["--corpus", str(corpus_root), "show", context.last_ingest["id"]])
    assert res.returncode == 0, res.stderr
    shown = json.loads(res.stdout)
    source = shown.get("source_uri") or ""
    assert re.match(r"^file://", source), source


@when('I list items in corpus "{corpus_name}"')
def step_list_items(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    run_biblicus(context, ["--corpus", str(corpus), "list"])


@then("the list output includes the last ingested item identifier")
def step_list_includes_last_id(context) -> None:
    assert context.last_ingest is not None
    assert context.last_ingest["id"] in (context.last_result.stdout or "")


@when('I show the last ingested item in corpus "{corpus_name}"')
def step_show_last_item(context, corpus_name: str) -> None:
    assert context.last_ingest is not None
    corpus = _corpus_path(context, corpus_name)
    res = run_biblicus(context, ["--corpus", str(corpus), "show", context.last_ingest["id"]])
    assert res.returncode == 0, res.stderr
    context.last_shown = json.loads(res.stdout)


@when('I show item "{item_id}" in corpus "{corpus_name}"')
def step_show_item(context, item_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    res = run_biblicus(context, ["--corpus", str(corpus), "show", item_id])
    assert res.returncode == 0, res.stderr
    context.last_shown = json.loads(res.stdout)


@when('I clear the corpus catalog order list in corpus "{corpus_name}"')
def step_clear_catalog_order(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    catalog_path = corpus / ".biblicus" / "catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    data["order"] = []
    catalog_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


@when('I prepend an unknown identifier to the corpus catalog order list in corpus "{corpus_name}"')
def step_prepend_unknown_id_catalog_order(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    catalog_path = corpus / ".biblicus" / "catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    order = data.get("order") or []
    assert isinstance(order, list)
    unknown_id = "00000000-0000-0000-0000-000000000999"
    if unknown_id in order:
        order = [i for i in order if i != unknown_id]
    order.insert(0, unknown_id)
    data["order"] = order
    catalog_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


@then('the shown JavaScript Object Notation includes title "{title}"')
def step_shown_includes_title(context, title: str) -> None:
    assert context.last_shown is not None
    assert context.last_shown.get("title") == title


@then('the shown JavaScript Object Notation includes tag "{tag}"')
def step_shown_includes_tag(context, tag: str) -> None:
    assert context.last_shown is not None
    tags: List[str] = context.last_shown.get("tags") or []
    assert tag in tags


@then('the shown JavaScript Object Notation tags equal "{csv}"')
def step_shown_tags_equal(context, csv: str) -> None:
    assert context.last_shown is not None
    expected = [t.strip() for t in csv.split(",") if t.strip()]
    assert (context.last_shown.get("tags") or []) == expected


@then('the shown JavaScript Object Notation includes media type "{media_type}"')
def step_shown_includes_media_type(context, media_type: str) -> None:
    assert context.last_shown is not None
    assert context.last_shown.get("media_type") == media_type


@then(
    'the shown JavaScript Object Notation includes source uniform resource identifier "{source_uri}"'
)
def step_shown_includes_source_uri(context, source_uri: str) -> None:
    assert context.last_shown is not None
    assert context.last_shown.get("source_uri") == source_uri


@then("the shown JavaScript Object Notation has no tags")
def step_shown_has_no_tags(context) -> None:
    assert context.last_shown is not None
    assert (context.last_shown.get("tags") or []) == []


@then("the shown JavaScript Object Notation has no title")
def step_shown_has_no_title(context) -> None:
    assert context.last_shown is not None
    assert context.last_shown.get("title") in (None, "")


@when('I add tag "{tag}" to the last ingested item\'s sidecar metadata')
def step_add_tag_to_sidecar(context, tag: str) -> None:
    assert context.last_ingest is not None
    relpath = Path(context.last_ingest["relpath"])
    content_path = context.last_corpus_root / relpath
    sidecar_path = content_path.with_name(content_path.name + ".biblicus.yml")
    data = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
    tags = data.get("tags") or []
    if tag not in tags:
        tags.append(tag)
    data["tags"] = tags
    sidecar_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip() + "\n", encoding="utf-8"
    )


@when('I set the last ingested item\'s sidecar media type to "{media_type}"')
def step_set_sidecar_media_type(context, media_type: str) -> None:
    assert context.last_ingest is not None
    relpath = Path(context.last_ingest["relpath"])
    content_path = context.last_corpus_root / relpath
    sidecar_path = content_path.with_name(content_path.name + ".biblicus.yml")
    data = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
    assert isinstance(data, dict)
    data["media_type"] = media_type
    sidecar_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip() + "\n", encoding="utf-8"
    )


@when("I write a sidecar for the last ingested item with Yet Another Markup Language:")
def step_write_sidecar_for_last_item(context) -> None:
    assert context.last_ingest is not None
    relpath = Path(context.last_ingest["relpath"])
    content_path = context.last_corpus_root / relpath
    sidecar_path = content_path.with_name(content_path.name + ".biblicus.yml")
    sidecar_path.write_text(context.text.strip() + "\n", encoding="utf-8")


@given('I create an extra derived folder in corpus "{corpus_name}"')
def step_create_extra_derived_folder(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    meta_dir = corpus / ".biblicus"
    extra_dir = meta_dir / "tmpdir"
    extra_dir.mkdir(parents=True, exist_ok=True)
    (extra_dir / "tmp.txt").write_text("x", encoding="utf-8")
    (meta_dir / "tmpfile").write_text("y", encoding="utf-8")


@given('I delete the corpus "{corpus_name}" raw folder')
def step_delete_corpus_raw_folder(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    raw_dir = corpus / "raw"
    if raw_dir.exists():
        for p in sorted(raw_dir.rglob("*"), reverse=True):
            if p.is_file() or p.is_symlink():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
        raw_dir.rmdir()


@when("I overwrite the last ingested item's sidecar with a Yet Another Markup Language list")
def step_overwrite_sidecar_with_list(context) -> None:
    assert context.last_ingest is not None
    relpath = Path(context.last_ingest["relpath"])
    content_path = context.last_corpus_root / relpath
    sidecar_path = content_path.with_name(content_path.name + ".biblicus.yml")
    sidecar_path.write_text("- a\n- b\n", encoding="utf-8")


@when('I reindex corpus "{corpus_name}"')
def step_reindex(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    res = run_biblicus(context, ["--corpus", str(corpus), "reindex"])
    assert res.returncode == 0, res.stderr
    try:
        context.last_reindex_stats = json.loads(res.stdout)
    except json.JSONDecodeError:
        context.last_reindex_stats = None


@then("the command succeeds")
def step_command_succeeds(context) -> None:
    assert context.last_result is not None
    assert context.last_result.returncode == 0, context.last_result.stderr


@when('I list items in the corpus by file uniform resource identifier for "{corpus_name}"')
def step_list_items_corpus_uri(context, corpus_name: str) -> None:
    uri = _corpus_path(context, corpus_name).as_uri()
    run_biblicus(context, ["--corpus", uri, "list"])


@given('I create the directory "{path}"')
def step_create_dir(context, path: str) -> None:
    (context.workdir / path).mkdir(parents=True, exist_ok=True)


@when('I list items from within "{path}"')
def step_list_from_within(context, path: str) -> None:
    cwd = (context.workdir / path).resolve()
    run_biblicus(context, ["list"], cwd=cwd)


@when('I run "{cmdline}" without specifying a corpus')
def step_run_cmdline_without_corpus(context, cmdline: str) -> None:
    run_biblicus(context, shlex.split(cmdline))


@when('I run "{cmdline}" in corpus "{corpus_name}"')
def step_run_cmdline_in_corpus(context, cmdline: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), *shlex.split(cmdline)]
    run_biblicus(context, args)


@when('I run "{cmdline}" with corpus uniform resource identifier "{corpus_uri}"')
def step_run_cmdline_with_corpus_uri(context, cmdline: str, corpus_uri: str) -> None:
    args = ["--corpus", corpus_uri, *shlex.split(cmdline)]
    run_biblicus(context, args)


@when('I run the biblicus module with "{arg}"')
def step_run_module_entry_point(context, arg: str) -> None:
    import contextlib
    import io
    import sys

    out = io.StringIO()
    err = io.StringIO()
    prev_argv = sys.argv
    try:
        sys.argv = ["biblicus", arg]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                runpy.run_module("biblicus", run_name="__main__")
                code = 0
            except SystemExit as exc:
                code = int(exc.code) if isinstance(exc.code, int) else 1
    finally:
        sys.argv = prev_argv
    context.last_result = RunResult(returncode=code, stdout=out.getvalue(), stderr=err.getvalue())


@then("the command fails with exit code {code:d}")
def step_command_fails_with_code(context, code: int) -> None:
    assert context.last_result is not None
    assert context.last_result.returncode == code, context.last_result.stderr


@then('standard error includes "{text}"')
def step_standard_error_includes(context, text: str) -> None:
    assert context.last_result is not None
    stderr = context.last_result.stderr or ""
    assert text in stderr, f"Expected '{text}' in stderr but got: {stderr}"


@then('the corpus "{corpus_name}" raw folder is empty')
def step_corpus_raw_folder_empty(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    raw_dir = corpus / "raw"
    assert raw_dir.is_dir()
    files = [p for p in raw_dir.rglob("*") if p.is_file()]
    assert files == [], [str(p.relative_to(corpus)) for p in files]


@then('the corpus "{corpus_name}" catalog has {count:d} items')
def step_corpus_catalog_has_n_items(context, corpus_name: str, count: int) -> None:
    corpus = _corpus_path(context, corpus_name)
    catalog_path = corpus / ".biblicus" / "catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = data.get("items")
    assert isinstance(items, dict)
    assert len(items) == count, len(items)


@given('I delete the corpus catalog file in corpus "{corpus_name}"')
def step_delete_corpus_catalog_file(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    catalog_path = corpus / ".biblicus" / "catalog.json"
    if catalog_path.exists():
        catalog_path.unlink()


@given('I corrupt the corpus config schema version in corpus "{corpus_name}"')
def step_corrupt_config_schema_version(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    config_path = corpus / ".biblicus" / "config.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    data["schema_version"] = 999
    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


@given('I corrupt the corpus catalog schema version in corpus "{corpus_name}"')
def step_corrupt_catalog_schema_version(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    catalog_path = corpus / ".biblicus" / "catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    data["schema_version"] = 999
    catalog_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


@then("reindex stats include inserted {count:d}")
def step_reindex_stats_inserted(context, count: int) -> None:
    assert context.last_reindex_stats is not None
    assert context.last_reindex_stats.get("inserted") == count


@then("reindex stats include skipped {count:d}")
def step_reindex_stats_skipped(context, count: int) -> None:
    assert context.last_reindex_stats is not None
    assert context.last_reindex_stats.get("skipped") == count


@then('the last ingested item filename includes "{part}"')
def step_last_ingested_item_filename_includes(context, part: str) -> None:
    assert context.last_ingest is not None
    name = Path(context.last_ingest["relpath"]).name
    assert part in name


@then('the last ingest sha256 matches the file "{filename}"')
def step_last_ingest_sha256_matches_file(context, filename: str) -> None:
    assert context.last_ingest is not None
    expected = hashlib.sha256((context.workdir / filename).read_bytes()).hexdigest()
    assert context.last_ingest["sha256"] == expected


@given('the corpus "{corpus_name}" ignore file includes:')
def step_corpus_ignore_file_includes(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    (corpus / ".biblicusignore").write_text(context.text.strip() + "\n", encoding="utf-8")


@given(
    'the corpus "{corpus_name}" has a configured hook "{hook_id}" for hook point "{hook_point}" with tags "{tags}"'
)
def step_corpus_configured_hook_with_tags(
    context, corpus_name: str, hook_id: str, hook_point: str, tags: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    config_path = corpus / ".biblicus" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    hooks = list(config.get("hooks") or [])
    hook_config: Dict[str, Any] = {"hook_id": hook_id, "hook_points": [hook_point], "config": {}}
    if tags.strip():
        hook_config["config"]["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    hooks.append(hook_config)
    config["hooks"] = hooks
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


@given(
    'the corpus "{corpus_name}" has a configured hook "{hook_id}" for hook point "{hook_point}" with no tags'
)
def step_corpus_configured_hook_no_tags(
    context, corpus_name: str, hook_id: str, hook_point: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    config_path = corpus / ".biblicus" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    hooks = list(config.get("hooks") or [])
    hooks.append({"hook_id": hook_id, "hook_points": [hook_point], "config": {}})
    config["hooks"] = hooks
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


@given('the corpus "{corpus_name}" config includes hooks JavaScript Object Notation:')
def step_corpus_config_includes_hooks_json(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    config_path = corpus / ".biblicus" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    hooks = json.loads(context.text)
    config["hooks"] = hooks
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


@then(
    'the corpus "{corpus_name}" hook logs include a record for hook point "{hook_point}" and hook "{hook_id}"'
)
def step_hook_logs_include_record(context, corpus_name: str, hook_point: str, hook_id: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    log_dir = corpus / ".biblicus" / "hook_logs"
    assert log_dir.is_dir()
    entries: List[Dict[str, Any]] = []
    for path in sorted(log_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
    matched = [
        entry
        for entry in entries
        if entry.get("hook_point") == hook_point and entry.get("hook_id") == hook_id
    ]
    assert matched, entries


@given('the directory "{dir_name}" contains files:')
def step_directory_contains_files(context, dir_name: str) -> None:
    root = (context.workdir / dir_name).resolve()
    for row in context.table:
        relpath = row["relpath"]
        raw_contents = row["contents"]
        contents = raw_contents.encode("utf-8").decode("unicode_escape")
        file_path = root / relpath
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(contents, encoding="utf-8")


@given(
    'the directory "{dir_name}" contains a markdown file "{relpath}" with invalid Unicode Transformation Format 8 bytes'
)
def step_directory_contains_invalid_markdown_bytes(context, dir_name: str, relpath: str) -> None:
    root = (context.workdir / dir_name).resolve()
    file_path = root / relpath
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"\xff\xfe\xfa")


@when('I import the folder tree "{dir_name}" into corpus "{corpus_name}" with tags "{tags}"')
def step_import_tree(context, dir_name: str, corpus_name: str, tags: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    source_root = (context.workdir / dir_name).resolve()
    args = ["--corpus", str(corpus), "import-tree", str(source_root), "--tags", tags]
    run_biblicus(context, args)


@then('the corpus "{corpus_name}" has at least {count:d} items')
def step_corpus_has_at_least_n_items(context, corpus_name: str, count: int) -> None:
    corpus = _corpus_path(context, corpus_name)
    catalog_path = corpus / ".biblicus" / "catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = data.get("items")
    assert isinstance(items, dict)
    assert len(items) >= count, len(items)


@then('the corpus "{corpus_name}" has an item with source suffix "{suffix}"')
def step_corpus_has_item_with_source_suffix(context, corpus_name: str, suffix: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    catalog_path = corpus / ".biblicus" / "catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = data.get("items")
    assert isinstance(items, dict)
    any_matches = False
    for item in items.values():
        source_uri = (item.get("source_uri") or "").replace("%2F", "/")
        if source_uri.endswith(suffix):
            any_matches = True
            break
    assert any_matches


@then('the corpus "{corpus_name}" has no item with source suffix "{suffix}"')
def step_corpus_has_no_item_with_source_suffix(context, corpus_name: str, suffix: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    catalog_path = corpus / ".biblicus" / "catalog.json"
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = data.get("items")
    assert isinstance(items, dict)
    any_matches = False
    for item in items.values():
        source_uri = (item.get("source_uri") or "").replace("%2F", "/")
        if source_uri.endswith(suffix):
            any_matches = True
            break
    assert not any_matches
