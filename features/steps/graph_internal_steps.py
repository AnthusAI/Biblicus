from __future__ import annotations

import builtins
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

from behave import given, when, then

from biblicus import Corpus
from biblicus.extraction import build_extraction_snapshot
from biblicus.graph import extraction as graph_extraction
from biblicus.graph.extraction import _load_extracted_text
from biblicus.graph.base import GraphExtractor
from biblicus.graph.models import (
    GraphConfigurationManifest,
    GraphSnapshotManifest,
    GraphSnapshotReference,
    parse_graph_snapshot_reference,
)
from biblicus.graph import neo4j as graph_neo4j
from biblicus.graph.neo4j import (
    Neo4jSettings,
    _resolve_int,
    _run_docker,
    _wait_for_neo4j,
    create_neo4j_driver,
    ensure_neo4j_running,
)
from biblicus.cli import cmd_graph_extract
from biblicus.graph.extractors.cooccurrence import CooccurrenceGraphExtractor, _windowed
from biblicus.graph.extractors.dependency_relations import DependencyRelationsGraphExtractor
from biblicus.graph.extractors.ner_entities import NerEntitiesGraphExtractor
from biblicus.graph.extractors.simple_entities import SimpleEntityGraphExtractor
from biblicus.models import CatalogItem, ExtractionSnapshotReference


def _sample_item() -> CatalogItem:
    return CatalogItem(
        id="item-1",
        relpath="raw/item.txt",
        sha256="",
        bytes=0,
        media_type="text/plain",
        tags=[],
        metadata={},
        created_at="2024-01-01T00:00:00Z",
        source_uri="file://item.txt",
    )


def _install_fake_spacy_relations(context) -> None:
    if getattr(context, "_fake_spacy_relations_installed", False):
        return
    context._fake_spacy_relations_original_module = sys.modules.get("spacy")

    class _FakeSpan:
        def __init__(self, text: str, label: str):
            self.text = text
            self.label_ = label

    class _FakeToken:
        def __init__(self, text: str, dep: str, *, with_lemma: bool = True):
            self.text = text
            self.dep_ = dep
            if with_lemma:
                self.lemma_ = text.lower()
            self.head = self
            self.children: List[_FakeToken] = []

    class _FakeDoc:
        def __init__(self, text: str):
            self.text = text
            self.ents = [_FakeSpan("Alice", "PERSON"), _FakeSpan("Bob", "PERSON")]
            subj = _FakeToken("Alice", "nsubj")
            verb = _FakeToken("writes", "ROOT")
            obj = _FakeToken("code", "dobj")
            subj.head = verb
            verb.children = [obj]
            self._tokens = [subj, verb, obj]

        def __iter__(self):
            return iter(self._tokens)

    class _FakeNlp:
        def __init__(self, name: str):
            self.name = name

        def __call__(self, text: str):
            return _FakeDoc(text)

    def load(_name: str):
        return _FakeNlp(_name)

    fake_module = types.ModuleType("spacy")
    fake_module.load = load
    sys.modules["spacy"] = fake_module
    context._fake_spacy_relations_installed = True


def _install_fake_spacy_short_entities(context) -> None:
    if getattr(context, "_fake_spacy_short_installed", False):
        return
    context._fake_spacy_short_original_module = sys.modules.get("spacy")

    class _FakeSpan:
        def __init__(self, text: str, label: str):
            self.text = text
            self.label_ = label

    class _FakeDoc:
        def __init__(self, text: str):
            self.text = text
            self.ents = [_FakeSpan("Al", "PERSON")]

        def __iter__(self):
            return iter([])

    class _FakeNlp:
        def __init__(self, name: str):
            self.name = name

        def __call__(self, text: str):
            return _FakeDoc(text)

    def load(_name: str):
        return _FakeNlp(_name)

    fake_module = types.ModuleType("spacy")
    fake_module.load = load
    sys.modules["spacy"] = fake_module
    context._fake_spacy_short_installed = True


def _install_fake_spacy_short_relations(context) -> None:
    if getattr(context, "_fake_spacy_short_relations_installed", False):
        return
    context._fake_spacy_short_relations_original_module = sys.modules.get("spacy")

    class _FakeToken:
        def __init__(self, text: str, dep: str, *, with_lemma: bool = True):
            self.text = text
            self.dep_ = dep
            if with_lemma:
                self.lemma_ = text.lower()
            self.head = self
            self.children: List[_FakeToken] = []

    class _FakeDoc:
        def __init__(self, text: str):
            self.text = text
            self.ents = [types.SimpleNamespace(text="Al", label_="PERSON")]
            with_lemma = not getattr(context, "_fake_spacy_short_relations_no_lemma", False)
            subj = _FakeToken("Al", "nsubj", with_lemma=with_lemma)
            verb = _FakeToken("writes", "ROOT", with_lemma=with_lemma)
            obj = _FakeToken("Bo", "dobj", with_lemma=with_lemma)
            subj.head = verb
            verb.children = [obj]
            self._tokens = [subj, verb, obj]

        def __iter__(self):
            return iter(self._tokens)

    class _FakeNlp:
        def __init__(self, name: str):
            self.name = name

        def __call__(self, text: str):
            return _FakeDoc(text)

    def load(_name: str):
        return _FakeNlp(_name)

    fake_module = types.ModuleType("spacy")
    fake_module.load = load
    sys.modules["spacy"] = fake_module
    context._fake_spacy_short_relations_installed = True
    context._fake_spacy_short_relations_no_lemma = False


def _install_fake_spacy_relations_without_lemma(context) -> None:
    if getattr(context, "_fake_spacy_short_relations_installed", False):
        context._fake_spacy_short_relations_no_lemma = True
        return
    _install_fake_spacy_short_relations(context)
    context._fake_spacy_short_relations_no_lemma = True


def _block_spacy_import(context) -> None:
    original_import = builtins.__import__
    context._spacy_original_import = original_import

    def _blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "spacy":
            raise ImportError("spacy blocked")
        return original_import(name, *args, **kwargs)

    if "spacy" in sys.modules:
        context._spacy_original_module = sys.modules.get("spacy")
        del sys.modules["spacy"]

    builtins.__import__ = _blocked_import
    context._spacy_import_blocked = True


def _install_fake_neo4j_driver(context) -> None:
    if getattr(context, "_fake_neo4j_internal_installed", False):
        return
    context._fake_neo4j_internal_original = sys.modules.get("neo4j")

    class _FakeSession:
        def __init__(self, database=None):
            self.database = database

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type
            _ = exc
            _ = tb
            return False

        def run(self, _query, **_params):
            return None

        def execute_write(self, func, *args):
            return func(self, *args)

    class _FakeDriver:
        def session(self, database=None):
            return _FakeSession(database=database)

        def close(self):
            return None

    class _FakeGraphDatabase:
        @staticmethod
        def driver(_uri, auth=None):
            _ = auth
            return _FakeDriver()

    fake_module = types.ModuleType("neo4j")
    fake_module.GraphDatabase = _FakeGraphDatabase
    sys.modules["neo4j"] = fake_module
    context._fake_neo4j_internal_installed = True


def _prepare_extraction_snapshot(context) -> ExtractionSnapshotReference:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    text_path = corpus.root / "note.txt"
    text_path.write_text("Alpha beta", encoding="utf-8")
    corpus.ingest_source(text_path)
    manifest = build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="default",
        configuration={
            "steps": [
                {"extractor_id": "pass-through-text", "config": {}},
                {"extractor_id": "select-text", "config": {}},
            ]
        },
    )
    return ExtractionSnapshotReference(
        extractor_id="pipeline",
        snapshot_id=manifest.snapshot_id,
    )


def _write_graph_manifest(
    context,
    *,
    extractor_id: str,
    snapshot_id: str,
) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    snapshots_dir = corpus.graph_snapshot_dir(
        extractor_id=extractor_id,
        snapshot_id=snapshot_id,
    )
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    configuration = GraphConfigurationManifest(
        configuration_id="config-1",
        extractor_id=extractor_id,
        name="default",
        created_at="2024-01-01T00:00:00Z",
        configuration={},
    )
    manifest = GraphSnapshotManifest(
        snapshot_id=snapshot_id,
        graph_id=f"graph-{snapshot_id}",
        configuration=configuration,
        corpus_uri=corpus.uri,
        catalog_generated_at="2024-01-01T00:00:00Z",
        extraction_snapshot="pipeline:snap-1",
        created_at="2024-01-01T00:00:00Z",
        stats={"nodes": 1, "edges": 0},
    )
    graph_extraction.write_graph_snapshot_manifest(snapshot_dir=snapshots_dir, manifest=manifest)


@when('I parse graph snapshot reference "{raw}"')
def step_parse_graph_snapshot_reference(context, raw: str) -> None:
    try:
        context._graph_snapshot_reference = parse_graph_snapshot_reference(raw)
        context._graph_reference_error = None
    except ValueError as exc:
        context._graph_reference_error = exc


@then("the graph snapshot reference error is present")
def step_graph_reference_error_present(context) -> None:
    assert context._graph_reference_error is not None


@when('I serialize graph snapshot reference "{raw}"')
def step_serialize_graph_snapshot_reference(context, raw: str) -> None:
    ref = parse_graph_snapshot_reference(raw)
    context._graph_snapshot_reference_string = ref.as_string()


@then('the graph snapshot reference equals "{expected}"')
def step_graph_reference_equals(context, expected: str) -> None:
    assert context._graph_snapshot_reference_string == expected


@when("I list graph snapshots with invalid manifests")
def step_list_graph_snapshots_invalid(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    snapshots_dir = corpus.graph_snapshots_dir / "cooccurrence"
    invalid_dir = snapshots_dir / "invalid"
    missing_dir = snapshots_dir / "missing"
    invalid_dir.mkdir(parents=True, exist_ok=True)
    missing_dir.mkdir(parents=True, exist_ok=True)
    (invalid_dir / "manifest.json").write_text("{not-json}", encoding="utf-8")
    entries = graph_extraction.list_graph_snapshots(corpus)
    context._graph_snapshot_entries = entries


@when("I load a missing graph snapshot manifest")
def step_load_missing_graph_manifest(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    try:
        graph_extraction.load_graph_snapshot_manifest(
            corpus,
            extractor_id="missing",
            snapshot_id="missing",
        )
        context._graph_error = None
    except Exception as exc:
        context._graph_error = exc


@when('I create a graph snapshot manifest for extractor "{extractor_id}" snapshot "{snapshot_id}"')
def step_create_graph_snapshot_manifest(context, extractor_id: str, snapshot_id: str) -> None:
    _write_graph_manifest(context, extractor_id=extractor_id, snapshot_id=snapshot_id)


@when('I list graph snapshots for extractor "{extractor_id}"')
def step_list_graph_snapshots_filtered(context, extractor_id: str) -> None:
    corpus_root = context.workdir / "corpus"
    if not corpus_root.exists():
        corpus = Corpus.init(corpus_root, force=True)
    else:
        corpus = Corpus.open(corpus_root)
    entries = graph_extraction.list_graph_snapshots(corpus, extractor_id=extractor_id)
    context._graph_snapshot_entries = entries


@when("I list graph snapshots with a non-directory entry")
def step_list_graph_snapshots_non_dir(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    snapshots_dir = corpus.graph_snapshots_dir / "cooccurrence"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    (snapshots_dir / "not-a-dir").write_text("data", encoding="utf-8")
    entries = graph_extraction.list_graph_snapshots(corpus)
    context._graph_snapshot_entries = entries


@then('the graph snapshot list includes extractor "{extractor_id}"')
def step_graph_snapshot_list_includes_extractor(context, extractor_id: str) -> None:
    entries = context._graph_snapshot_entries
    assert any(entry.extractor_id == extractor_id for entry in entries)


@when("I resolve the latest graph snapshot reference")
def step_resolve_latest_graph_snapshot_reference(context) -> None:
    corpus = Corpus.open(context.workdir / "corpus")
    context._latest_graph_snapshot_reference = graph_extraction.latest_graph_snapshot_reference(
        corpus
    )


@when("I resolve the latest graph snapshot reference with no snapshots")
def step_resolve_latest_graph_snapshot_reference_none(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    context._latest_graph_snapshot_reference = graph_extraction.latest_graph_snapshot_reference(
        corpus
    )


@then("the latest graph snapshot reference is present")
def step_latest_graph_snapshot_reference_present(context) -> None:
    assert context._latest_graph_snapshot_reference is not None


@then("the latest graph snapshot reference is absent")
def step_latest_graph_snapshot_reference_absent(context) -> None:
    assert context._latest_graph_snapshot_reference is None


@when('I resolve the graph snapshot reference "{raw}"')
def step_resolve_graph_snapshot_reference(context, raw: str) -> None:
    corpus = Corpus.open(context.workdir / "corpus")
    context._graph_snapshot_reference = graph_extraction.resolve_graph_snapshot_reference(
        corpus, raw=raw
    )


@then("the graph snapshot reference is present")
def step_graph_snapshot_reference_present(context) -> None:
    assert context._graph_snapshot_reference is not None


@when("I run the graph extract command with a configuration file")
def step_run_graph_extract_command_with_config(context) -> None:
    ref = _prepare_extraction_snapshot(context)
    corpus = Corpus.open(context.workdir / "corpus")
    config_path = context.workdir / "graph-config.yml"
    config_path.write_text("window_size: 2\nmin_cooccurrence: 1\n", encoding="utf-8")
    _install_fake_neo4j_driver(context)
    arguments = SimpleNamespace(
        corpus=str(corpus.root),
        extractor="cooccurrence",
        configuration=[str(config_path)],
        configuration_name="default",
        extraction_snapshot=ref.as_string(),
        override=[],
    )
    result = cmd_graph_extract(arguments)
    context._graph_cli_result = result
    context._graph_error = None


@when("I run the graph extract command without snapshots")
def step_run_graph_extract_command_without_snapshots(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus-empty", force=True)
    arguments = SimpleNamespace(
        corpus=str(corpus.root),
        extractor="cooccurrence",
        configuration=None,
        configuration_name="default",
        extraction_snapshot=None,
        override=[],
    )
    try:
        cmd_graph_extract(arguments)
        context._graph_error = None
    except Exception as exc:
        context._graph_error = exc


@then("the graph snapshot list is empty")
def step_graph_snapshot_list_empty(context) -> None:
    assert context._graph_snapshot_entries == []


@when("I load graph extracted text with missing relpath")
def step_load_graph_text_missing_relpath(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    ref = ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id="snap")
    item_result = SimpleNamespace(final_text_relpath=None)
    context._graph_loaded_text = _load_extracted_text(corpus, extraction_snapshot=ref, item_result=item_result)


@when("I load graph extracted text with missing file")
def step_load_graph_text_missing_file(context) -> None:
    corpus = Corpus.init(context.workdir / "corpus", force=True)
    ref = ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id="snap")
    item_result = SimpleNamespace(final_text_relpath="text/missing.txt")
    context._graph_loaded_text = _load_extracted_text(corpus, extraction_snapshot=ref, item_result=item_result)


@when("I build a graph snapshot with missing extracted text")
def step_build_graph_missing_text(context) -> None:
    ref = _prepare_extraction_snapshot(context)
    corpus = Corpus.open(context.workdir / "corpus")
    text_dir = corpus.extraction_snapshot_dir(
        extractor_id=ref.extractor_id, snapshot_id=ref.snapshot_id
    ) / "text"
    for path in text_dir.glob("*.txt"):
        path.unlink()
    _install_fake_neo4j_driver(context)
    manifest = graph_extraction.build_graph_snapshot(
        corpus,
        extractor_id="cooccurrence",
        configuration_name="default",
        configuration={"window_size": 2, "min_cooccurrence": 1},
        extraction_snapshot=ref,
    )
    context._graph_snapshot_manifest = manifest


@then("graph snapshot build succeeds")
def step_graph_snapshot_build_succeeds(context) -> None:
    manifest = getattr(context, "_graph_snapshot_manifest", None)
    assert manifest is not None


@then("the graph extracted text is None")
def step_graph_loaded_text_none(context) -> None:
    assert context._graph_loaded_text is None


@given("a fake NLP model is installed for relations")
def step_fake_spacy_relations(context) -> None:
    _install_fake_spacy_relations(context)
    context._graph_results = []


@given("a fake NLP model is installed with short entities")
def step_fake_spacy_short_entities(context) -> None:
    _install_fake_spacy_short_entities(context)
    context._graph_results = []


@given("a fake NLP model is installed with short relations")
def step_fake_spacy_short_relations(context) -> None:
    _install_fake_spacy_short_relations(context)
    context._graph_results = []


@when('I extract cooccurrence graph edges from "{text}"')
def step_extract_cooccurrence(context, text: str) -> None:
    extractor = CooccurrenceGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text=text, config={"window_size": 2, "min_cooccurrence": 1})
    context._graph_results.append(result)


@when("I extract cooccurrence graph edges with empty text")
def step_extract_cooccurrence_empty(context) -> None:
    extractor = CooccurrenceGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text="", config={"window_size": 2, "min_cooccurrence": 1})
    context._graph_results.append(result)


@when("I extract cooccurrence graph edges with invalid window size")
def step_extract_cooccurrence_invalid_window(context) -> None:
    windows = _windowed(["alpha", "beta"], 0)
    context._graph_results.append(windows)


@when("I extract cooccurrence graph edges with high min count")
def step_extract_cooccurrence_high_min(context) -> None:
    extractor = CooccurrenceGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text="Alpha beta", config={"window_size": 2, "min_cooccurrence": 10})
    context._graph_results.append(result)


@when('I extract simple entity graph edges from "{text}"')
def step_extract_simple_entities(context, text: str) -> None:
    extractor = SimpleEntityGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text=text, config={"min_entity_length": 3, "max_entity_words": 2, "include_item_node": True})
    context._graph_results.append(result)


@when('I extract simple entity graph edges with minimum length {min_length:d} from "{text}"')
def step_extract_simple_entities_min_length(context, min_length: int, text: str) -> None:
    extractor = SimpleEntityGraphExtractor()
    result = extractor.extract_graph(
        corpus=Corpus.init(context.workdir / "corpus", force=True),
        item=_sample_item(),
        extracted_text=text,
        config={"min_entity_length": min_length, "max_entity_words": 2, "include_item_node": True},
    )
    context._graph_results.append(result)


@when("I extract simple entity graph edges without item node")
def step_extract_simple_entities_no_item(context) -> None:
    extractor = SimpleEntityGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text="Alice and BOB", config={"min_entity_length": 3, "max_entity_words": 2, "include_item_node": False})
    context._graph_results.append(result)


@when('I extract NER graph edges from "{text}"')
def step_extract_ner_entities(context, text: str) -> None:
    extractor = NerEntitiesGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text=text, config={"model": "fake", "min_entity_length": 3, "include_item_node": True})
    context._graph_results.append(result)


@when('I extract NER graph edges with minimum length {min_length:d} from "{text}"')
def step_extract_ner_entities_min_length(context, min_length: int, text: str) -> None:
    extractor = NerEntitiesGraphExtractor()
    result = extractor.extract_graph(
        corpus=Corpus.init(context.workdir / "corpus", force=True),
        item=_sample_item(),
        extracted_text=text,
        config={"model": "fake", "min_entity_length": min_length, "include_item_node": True},
    )
    context._graph_results.append(result)


@when("I extract NER graph edges without item node")
def step_extract_ner_entities_no_item(context) -> None:
    extractor = NerEntitiesGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text="Alice", config={"model": "fake", "min_entity_length": 3, "include_item_node": False})
    context._graph_results.append(result)


@when('I extract dependency graph edges from "{text}"')
def step_extract_dependency(context, text: str) -> None:
    extractor = DependencyRelationsGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text=text, config={"model": "fake", "min_entity_length": 3, "include_item_node": True})
    context._graph_results.append(result)


@when('I extract dependency graph edges with minimum length {min_length:d} from "{text}"')
def step_extract_dependency_min_length(context, min_length: int, text: str) -> None:
    extractor = DependencyRelationsGraphExtractor()
    result = extractor.extract_graph(
        corpus=Corpus.init(context.workdir / "corpus", force=True),
        item=_sample_item(),
        extracted_text=text,
        config={"model": "fake", "min_entity_length": min_length, "include_item_node": True},
    )
    context._graph_results.append(result)


@when('I extract dependency relations predicate without lemma from "{text}"')
def step_extract_dependency_without_lemma(context, text: str) -> None:
    _install_fake_spacy_relations_without_lemma(context)
    extractor = DependencyRelationsGraphExtractor()
    result = extractor.extract_graph(
        corpus=Corpus.init(context.workdir / "corpus", force=True),
        item=_sample_item(),
        extracted_text=text,
        config={"model": "fake", "min_entity_length": 1, "include_item_node": True},
    )
    context._graph_results.append(result)


@when("I extract dependency relations with short labels")
def step_extract_dependency_short_labels(context) -> None:
    _install_fake_spacy_short_relations(context)
    from biblicus.graph.extractors.dependency_relations import _extract_relations

    relations = _extract_relations(
        extracted_text="Al writes Bo",
        model_name="fake",
        min_length=3,
    )
    context._graph_relations = relations


@when("I extract dependency graph edges without item node")
def step_extract_dependency_no_item(context) -> None:
    extractor = DependencyRelationsGraphExtractor()
    result = extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text="Alice writes code", config={"model": "fake", "min_entity_length": 3, "include_item_node": False})
    context._graph_results.append(result)


@then("graph extractor results are available")
def step_graph_results_available(context) -> None:
    assert context._graph_results


@then("dependency relations are empty")
def step_dependency_relations_empty(context) -> None:
    relations = getattr(context, "_graph_relations", None)
    assert relations == []


@given("the NLP dependency is unavailable")
def step_nlp_dependency_unavailable(context) -> None:
    _block_spacy_import(context)


@when('I attempt to extract NER entities from "{text}"')
def step_attempt_ner_entities(context, text: str) -> None:
    extractor = NerEntitiesGraphExtractor()
    try:
        extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text=text, config={"model": "fake", "min_entity_length": 3, "include_item_node": True})
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc


@when('I attempt to extract dependency relations from "{text}"')
def step_attempt_dependency(context, text: str) -> None:
    extractor = DependencyRelationsGraphExtractor()
    try:
        extractor.extract_graph(corpus=Corpus.init(context.workdir / "corpus", force=True), item=_sample_item(), extracted_text=text, config={"model": "fake", "min_entity_length": 3, "include_item_node": True})
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc


@then("the graph NLP error is present")
def step_graph_nlp_error_present(context) -> None:
    assert context._graph_error is not None


@given("a fake Neo4j driver is installed for internal checks")
def step_fake_neo4j_driver(context) -> None:
    _install_fake_neo4j_driver(context)


@when("I invoke the graph extractor base validate_config")
def step_invoke_graph_base_validate(context) -> None:
    class _Base(GraphExtractor):
        extractor_id = "base"

        def validate_config(self, config: Dict[str, object]):
            return super().validate_config(config)

        def extract_graph(self, **_kwargs):
            raise NotImplementedError

    extractor = _Base()
    try:
        extractor.validate_config({})
        context._graph_error = None
    except NotImplementedError as exc:
        context._graph_error = exc

@when("I attempt to build a graph snapshot with invalid config")
def step_build_graph_invalid_config(context) -> None:
    ref = _prepare_extraction_snapshot(context)
    context._graph_snapshot_ref = ref
    corpus = Corpus.open(context.workdir / "corpus")
    try:
        graph_extraction.build_graph_snapshot(
            corpus,
            extractor_id="cooccurrence",
            configuration_name="default",
            configuration={"window_size": 1, "min_cooccurrence": 1},
            extraction_snapshot=ref,
        )
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc


@when("I attempt to build a graph snapshot with invalid result type")
def step_build_graph_invalid_result(context) -> None:
    ref = getattr(context, "_graph_snapshot_ref", None)
    if ref is None:
        ref = _prepare_extraction_snapshot(context)
    corpus = Corpus.open(context.workdir / "corpus")
    _install_fake_neo4j_driver(context)

    class _BadExtractor:
        def validate_config(self, config: Dict[str, object]):
            return config

        def extract_graph(self, **_kwargs):
            return {"bad": "result"}

    original_get = graph_extraction.get_graph_extractor
    graph_extraction.get_graph_extractor = lambda _id: _BadExtractor()
    try:
        graph_extraction.build_graph_snapshot(
            corpus,
            extractor_id="cooccurrence",
            configuration_name="default",
            configuration={"window_size": 2, "min_cooccurrence": 1},
            extraction_snapshot=ref,
        )
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
    finally:
        graph_extraction.get_graph_extractor = original_get


@then("the graph extraction error is present")
def step_graph_error_present(context) -> None:
    assert context._graph_error is not None


@then("the graph extraction error is absent")
def step_graph_error_absent(context) -> None:
    assert context._graph_error is None


@then("the Neo4j timeout error includes details")
def step_neo4j_timeout_error_details(context) -> None:
    assert "not ready" in context._graph_error_message


@then("the Neo4j timeout error omits details")
def step_neo4j_timeout_error_no_details(context) -> None:
    assert "not ready" not in context._graph_error_message


@when("I resolve Neo4j port with invalid value")
def step_resolve_neo4j_port_invalid(context) -> None:
    os.environ["NEO4J_HTTP_PORT"] = "not-int"
    try:
        _resolve_int("NEO4J_HTTP_PORT", 7474)
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
    finally:
        os.environ.pop("NEO4J_HTTP_PORT", None)


@when("I ensure Neo4j running without Docker")
def step_ensure_neo4j_no_docker(context) -> None:
    settings = Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test",
        database="neo4j",
        auto_start=True,
        container_name="biblicus-neo4j",
        docker_image="neo4j:5",
        http_port=7474,
        bolt_port=7687,
    )
    original_which = graph_neo4j.shutil.which
    graph_neo4j.shutil.which = lambda _name: None
    try:
        ensure_neo4j_running(settings)
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
    finally:
        graph_neo4j.shutil.which = original_which


@when("I ensure Neo4j running with container start")
def step_ensure_neo4j_start(context) -> None:
    settings = Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test",
        database="neo4j",
        auto_start=True,
        container_name="biblicus-neo4j",
        docker_image="neo4j:5",
        http_port=7474,
        bolt_port=7687,
    )
    state = context.workdir / "docker-state.json"
    state.write_text('{"exists": true, "running": false}', encoding="utf-8")
    log_path = context.workdir / "docker-log.txt"
    log_path.write_text("", encoding="utf-8")
    bin_dir = context.workdir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "docker"
    script.write_text(
        f"""#!/bin/sh
set -e
if [ \"$1\" = \"ps\" ]; then
  if echo \"$@\" | grep -q \"status=running\"; then
    exit 0
  fi
  echo \"biblicus-neo4j\"
  exit 0
fi
if [ \"$1\" = \"start\" ]; then
  exit 0
fi
exit 1
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    original_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}:{original_path}"
    try:
        ensure_neo4j_running(settings)
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
    finally:
        os.environ["PATH"] = original_path


@when("I ensure Neo4j running with container run")
def step_ensure_neo4j_run(context) -> None:
    settings = Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test",
        database="neo4j",
        auto_start=True,
        container_name="biblicus-neo4j",
        docker_image="neo4j:5",
        http_port=7474,
        bolt_port=7687,
    )
    bin_dir = context.workdir / "bin-run"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "docker"
    script.write_text(
        """#!/bin/sh
set -e
if [ \"$1\" = \"ps\" ]; then
  exit 0
fi
if [ \"$1\" = \"run\" ]; then
  exit 0
fi
exit 1
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    original_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}:{original_path}"
    try:
        ensure_neo4j_running(settings)
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
    finally:
        os.environ["PATH"] = original_path


@when("I run a docker command that fails")
def step_run_docker_fails(context) -> None:
    bin_dir = context.workdir / "bin-fail"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "docker"
    script.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    script.chmod(0o755)
    original_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}:{original_path}"
    try:
        _run_docker(["ps"])
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
    finally:
        os.environ["PATH"] = original_path


@when("I wait for Neo4j availability and it times out")
def step_wait_neo4j_timeout(context) -> None:
    class _FailingDriver:
        def session(self, database=None):
            _ = database
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type
            _ = exc
            _ = tb
            return False

        def run(self, _query):
            raise RuntimeError("not ready")

    settings = Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test",
        database="neo4j",
        auto_start=False,
        container_name="biblicus-neo4j",
        docker_image="neo4j:5",
        http_port=7474,
        bolt_port=7687,
    )
    original_time = graph_neo4j.time.time
    times = [0.0, 0.0, 31.0]
    graph_neo4j.time.time = lambda: times.pop(0)
    try:
        _wait_for_neo4j(_FailingDriver(), settings)
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
        context._graph_error_message = str(exc)
    finally:
        graph_neo4j.time.time = original_time


@when("I wait for Neo4j availability and it times out without details")
def step_wait_neo4j_timeout_no_details(context) -> None:
    class _OkDriver:
        def session(self, database=None):
            _ = database
            return self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type
            _ = exc
            _ = tb
            return False

        def run(self, _query):
            return None

    settings = Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test",
        database="neo4j",
        auto_start=False,
        container_name="biblicus-neo4j",
        docker_image="neo4j:5",
        http_port=7474,
        bolt_port=7687,
    )
    original_time = graph_neo4j.time.time
    times = [100.0, 200.0]
    graph_neo4j.time.time = lambda: times.pop(0)
    try:
        _wait_for_neo4j(_OkDriver(), settings)
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
        context._graph_error_message = str(exc)
    finally:
        graph_neo4j.time.time = original_time


@when("I create a Neo4j driver without dependency")
def step_create_neo4j_driver_missing(context) -> None:
    settings = Neo4jSettings(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test",
        database="neo4j",
        auto_start=False,
        container_name="biblicus-neo4j",
        docker_image="neo4j:5",
        http_port=7474,
        bolt_port=7687,
    )
    original_module = sys.modules.get("neo4j")
    if "neo4j" in sys.modules:
        del sys.modules["neo4j"]
    original_import = builtins.__import__

    def _blocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "neo4j":
            raise ImportError("neo4j blocked")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = _blocked_import
    try:
        create_neo4j_driver(settings)
        context._graph_error = None
    except ValueError as exc:
        context._graph_error = exc
    finally:
        builtins.__import__ = original_import
        if original_module is not None:
            sys.modules["neo4j"] = original_module
