from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import types
from pathlib import Path

from behave import given, then, when
from pydantic import BaseModel, ConfigDict

from biblicus.graph import get_graph_extractor
from biblicus.graph.base import GraphExtractor
from biblicus.graph.models import GraphExtractionResult
from biblicus.models import CatalogItem
from biblicus.corpus import Corpus
from features.environment import run_biblicus


class _DummyGraphExtractor(GraphExtractor):
    extractor_id = "dummy"

    def validate_config(self, config: dict[str, object]) -> BaseModel:
        _ = config
        raise NotImplementedError

    def extract_graph(
        self,
        *,
        corpus: Corpus,
        item: CatalogItem,
        extracted_text: str,
        config: BaseModel,
    ) -> GraphExtractionResult:
        _ = corpus
        _ = item
        _ = extracted_text
        _ = config
        return super().extract_graph(
            corpus=corpus,
            item=item,
            extracted_text=extracted_text,
            config=config,
        )


class _DummyGraphConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _table_key_value(row) -> tuple[str, str]:
    if "key" in row.headings and "value" in row.headings:
        return row["key"].strip(), row["value"].strip()
    return row[0].strip(), row[1].strip()


def _parse_json_output(standard_output: str) -> dict[str, object]:
    return json.loads(standard_output)


def _snapshot_reference_from_context(context, name: str) -> str:
    snapshots = getattr(context, "graph_snapshot_refs", {})
    reference = snapshots.get(name)
    assert isinstance(reference, str)
    return reference


def _install_fake_neo4j_module(context) -> None:
    if getattr(context, "_fake_neo4j_installed", False):
        return
    context._fake_neo4j_original_module = sys.modules.get("neo4j")
    calls = []

    class _FakeSession:
        def __init__(self, database=None):
            self.database = database

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, **params):
            calls.append(("run", query, params))

        def execute_write(self, func, *args):
            tx = _FakeTx(calls)
            return func(tx, *args)

    class _FakeTx:
        def __init__(self, call_log):
            self._call_log = call_log

        def run(self, query, **params):
            self._call_log.append(("tx_run", query, params))

    class _FakeDriver:
        def __init__(self):
            self._closed = False

        def session(self, database=None):
            return _FakeSession(database=database)

        def close(self):
            self._closed = True

    class _FakeGraphDatabase:
        @staticmethod
        def driver(_uri, auth=None):
            calls.append(("driver", _uri, auth))
            return _FakeDriver()

    fake_module = types.ModuleType("neo4j")
    fake_module.GraphDatabase = _FakeGraphDatabase
    sys.modules["neo4j"] = fake_module
    context._fake_neo4j_installed = True
    context.fake_neo4j_calls = calls


def _install_fake_spacy_module(context) -> None:
    if getattr(context, "_fake_spacy_installed", False):
        return
    context._fake_spacy_original_module = sys.modules.get("spacy")

    class _FakeSpan:
        def __init__(self, text: str, label: str):
            self.text = text
            self.label_ = label

    class _FakeToken:
        def __init__(self, text: str):
            self.text = text
            self.lemma_ = text.lower()
            self.dep_ = "ROOT"
            self.head = self

    class _FakeDoc:
        def __init__(self, text: str):
            self.text = text
            self.ents = _extract_fake_ents(text)
            self._tokens = [_FakeToken(token) for token in text.split()]

        def __iter__(self):
            return iter(self._tokens)

    class _FakeNlp:
        def __init__(self, name: str):
            self.name = name

        def __call__(self, text: str):
            return _FakeDoc(text)

    def _extract_fake_ents(text: str):
        import re

        matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        return [_FakeSpan(match, "PERSON") for match in matches]

    def load(name: str):
        return _FakeNlp(name)

    fake_module = types.ModuleType("spacy")
    fake_module.load = load
    sys.modules["spacy"] = fake_module
    context._fake_spacy_installed = True


def _install_fake_docker(context) -> None:
    if getattr(context, "_fake_docker_installed", False):
        return
    bin_dir = context.workdir / "fake-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    state_path = bin_dir / "docker-state.json"
    log_path = bin_dir / "docker-log.txt"
    state_path.write_text(json.dumps({"exists": False, "running": False}) + "\n")
    log_path.write_text("")

    script_path = bin_dir / "docker"
    python_path = "/opt/anaconda3/bin/python"
    script = f"""#!/bin/sh
set -e
STATE={state_path}
LOG={log_path}
echo "$@" >> "$LOG"
cmd="$1"
shift
if [ "$cmd" = "ps" ]; then
  exists=$({python_path} - <<'PY'
import json
import os
state=json.load(open(os.environ['STATE']))
print('1' if state.get('exists') else '0')
PY
)
  running=$({python_path} - <<'PY'
import json
import os
state=json.load(open(os.environ['STATE']))
print('1' if state.get('running') else '0')
PY
)
  if echo "$@" | grep -q "status=running"; then
    if [ "$running" = "1" ]; then
      echo "biblicus-neo4j"
    fi
    exit 0
  fi
  if [ "$exists" = "1" ]; then
    echo "biblicus-neo4j"
  fi
  exit 0
fi
if [ "$cmd" = "start" ]; then
  {python_path} - <<'PY'
import json
import os
path=os.environ['STATE']
state=json.load(open(path))
state['exists']=True
state['running']=True
json.dump(state, open(path, 'w'))
PY
  exit 0
fi
if [ "$cmd" = "run" ]; then
  {python_path} - <<'PY'
import json
import os
path=os.environ['STATE']
state=json.load(open(path))
state['exists']=True
state['running']=True
json.dump(state, open(path, 'w'))
PY
  exit 0
fi
echo "unsupported docker command" >&2
exit 1
"""
    script_path.write_text(script)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    context._fake_docker_installed = True
    context.fake_docker_state = state_path
    context.fake_docker_log = log_path
    extra_env = getattr(context, "extra_env", {})
    extra_env["PATH"] = f"{bin_dir}:{os.environ.get('PATH','')}"
    extra_env["STATE"] = str(state_path)
    context.extra_env = extra_env


def _docker_log_contains(context, text: str) -> bool:
    log_path = getattr(context, "fake_docker_log", None)
    if log_path is None:
        return False
    return text in log_path.read_text()


@when('I attempt to resolve graph extractor "{extractor_id}"')
def step_attempt_resolve_graph_extractor(context, extractor_id: str) -> None:
    try:
        get_graph_extractor(extractor_id)
        context.graph_error = None
    except KeyError as exc:
        context.graph_error = exc


@then('the graph extractor error mentions "{text}"')
def step_graph_extractor_error_mentions(context, text: str) -> None:
    error = getattr(context, "graph_error", None)
    assert error is not None
    assert text in str(error)


@when("I invoke the graph extractor base class")
def step_invoke_graph_extractor_base(context) -> None:
    extractor = _DummyGraphExtractor()
    try:
        extractor.extract_graph(
            corpus=Corpus.init(context.workdir / "corpus", force=True),
            item=CatalogItem(
                id="item",
                relpath="item.txt",
                sha256="",
                bytes=0,
                media_type="text/plain",
                tags=[],
                metadata={},
                created_at="2024-01-01T00:00:00Z",
                source_uri="file://item.txt",
            ),
            extracted_text="",
            config=_DummyGraphConfig(),
        )
        context.graph_error = None
    except NotImplementedError as exc:
        context.graph_error = exc
        context.analysis_error = exc


@when(
    'I attempt to build a "{extractor_id}" graph extraction snapshot in corpus "{corpus_name}" with extraction snapshot "{snapshot_ref}"'
)
def step_attempt_build_graph_snapshot_missing_extraction(
    context, extractor_id: str, corpus_name: str, snapshot_ref: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = [
        "--corpus",
        str(corpus),
        "graph",
        "extract",
        "--extractor",
        extractor_id,
        "--extraction-snapshot",
        snapshot_ref,
    ]
    context.last_result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))


@given("a fake Neo4j driver is installed")
@when("a fake Neo4j driver is installed")
def step_install_fake_neo4j(context) -> None:
    _install_fake_neo4j_module(context)


@given("a fake Docker daemon is installed for Neo4j")
@when("a fake Docker daemon is installed for Neo4j")
def step_install_fake_docker(context) -> None:
    _install_fake_docker(context)


@given("a fake NLP model is installed")
@when("a fake NLP model is installed")
def step_install_fake_spacy(context) -> None:
    _install_fake_spacy_module(context)


@when(
    'I build a "{extractor_id}" graph extraction snapshot in corpus "{corpus_name}" using the latest extraction snapshot and config:'
)
def step_build_graph_snapshot_latest_extraction(context, extractor_id: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    _install_fake_neo4j_module(context)
    if not getattr(context, "_fake_docker_installed", False):
        extra_env = getattr(context, "extra_env", {})
        extra_env["BIBLICUS_NEO4J_AUTO_START"] = "false"
        context.extra_env = extra_env
    args = ["--corpus", str(corpus), "graph", "extract", "--extractor", extractor_id]
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend(["--override", f"{key}={value}"])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_graph_snapshot = _parse_json_output(result.stdout)
    context.last_graph_snapshot_id = context.last_graph_snapshot.get("snapshot_id")
    context.last_graph_extractor_id = extractor_id


@when(
    'I build a "{extractor_id}" graph extraction snapshot in corpus "{corpus_name}" using the latest extraction snapshot with real Neo4j and config:'
)
def step_build_graph_snapshot_latest_extraction_real(
    context, extractor_id: str, corpus_name: str
) -> None:
    corpus = _corpus_path(context, corpus_name)
    if shutil.which("docker") is None:
        scenario = getattr(context, "scenario", None)
        if scenario is not None:
            scenario.skip("Docker is required for Neo4j integration scenarios.")
        return
    docker_info = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    if docker_info.returncode != 0:
        scenario = getattr(context, "scenario", None)
        if scenario is not None:
            scenario.skip("Docker daemon is required for Neo4j integration scenarios.")
        return
    extra_env = getattr(context, "extra_env", {})
    extra_env["BIBLICUS_NEO4J_AUTO_START"] = "true"
    context.extra_env = extra_env
    args = ["--corpus", str(corpus), "graph", "extract", "--extractor", extractor_id]
    for row in context.table:
        key, value = _table_key_value(row)
        args.extend(["--override", f"{key}={value}"])
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_graph_snapshot = _parse_json_output(result.stdout)
    context.last_graph_snapshot_id = context.last_graph_snapshot.get("snapshot_id")
    context.last_graph_extractor_id = extractor_id


@when('I remember the last graph extraction snapshot reference as "{name}"')
def step_remember_graph_snapshot_reference(context, name: str) -> None:
    extractor_id = context.last_graph_extractor_id
    snapshot_id = context.last_graph_snapshot_id
    assert isinstance(extractor_id, str) and extractor_id
    assert isinstance(snapshot_id, str) and snapshot_id
    reference = f"{extractor_id}:{snapshot_id}"
    snapshots = getattr(context, "graph_snapshot_refs", {})
    snapshots[name] = reference
    context.graph_snapshot_refs = snapshots


@then('the last graph extraction snapshot reference equals "{name}"')
def step_last_graph_snapshot_reference_equals(context, name: str) -> None:
    reference = _snapshot_reference_from_context(context, name)
    extractor_id = context.last_graph_extractor_id
    snapshot_id = context.last_graph_snapshot_id
    combined = f"{extractor_id}:{snapshot_id}"
    assert combined == reference


@then('the last graph extraction snapshot reference does not equal "{name}"')
def step_last_graph_snapshot_reference_not_equals(context, name: str) -> None:
    reference = _snapshot_reference_from_context(context, name)
    extractor_id = context.last_graph_extractor_id
    snapshot_id = context.last_graph_snapshot_id
    combined = f"{extractor_id}:{snapshot_id}"
    assert combined != reference


@when('I list graph extraction snapshots in corpus "{corpus_name}"')
def step_list_graph_snapshots(context, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    args = ["--corpus", str(corpus), "graph", "list"]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.graph_snapshot_list = _parse_json_output(result.stdout)


@then('the graph extraction snapshot list includes "{name}"')
def step_graph_snapshot_list_includes(context, name: str) -> None:
    reference = _snapshot_reference_from_context(context, name)
    entries = getattr(context, "graph_snapshot_list", None)
    assert entries is not None
    references = {f"{entry['extractor_id']}:{entry['snapshot_id']}" for entry in entries}
    assert reference in references


@then("the graph extraction snapshot list is empty")
def step_graph_snapshot_list_empty(context) -> None:
    entries = getattr(context, "graph_snapshot_list", None)
    assert entries == []


@when('I show graph extraction snapshot "{name}" in corpus "{corpus_name}"')
def step_show_graph_snapshot(context, name: str, corpus_name: str) -> None:
    corpus = _corpus_path(context, corpus_name)
    reference = _snapshot_reference_from_context(context, name)
    args = ["--corpus", str(corpus), "graph", "show", "--snapshot", reference]
    result = run_biblicus(context, args, extra_env=getattr(context, "extra_env", None))
    assert result.returncode == 0, result.stderr
    context.last_graph_snapshot = _parse_json_output(result.stdout)


@then('the shown graph extraction snapshot reference equals "{name}"')
def step_graph_snapshot_reference_equals(context, name: str) -> None:
    reference = _snapshot_reference_from_context(context, name)
    snapshot = getattr(context, "last_graph_snapshot", None)
    assert snapshot is not None
    combined = f"{snapshot['configuration']['extractor_id']}:{snapshot['snapshot_id']}"
    assert combined == reference


@then('the graph extraction snapshot graph identifier starts with "{prefix}"')
def step_graph_snapshot_graph_id_prefix(context, prefix: str) -> None:
    snapshot = getattr(context, "last_graph_snapshot", None)
    assert snapshot is not None
    graph_id = snapshot.get("graph_id")
    assert isinstance(graph_id, str)
    assert graph_id.startswith(prefix)


@then("the Docker run command is invoked for Neo4j")
def step_docker_run_invoked(context) -> None:
    assert _docker_log_contains(context, "run")
