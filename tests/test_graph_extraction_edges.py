from types import SimpleNamespace
import signal
import sys
import time

import pytest

from biblicus.extraction import (
    ExtractionConfigurationManifest,
    ExtractionItemResult,
    ExtractionSnapshotManifest,
)
from biblicus.graph.extraction import build_graph_snapshot, export_graph_snapshot
from biblicus.graph.extractors import ner_entities
from biblicus.graph.extractors.ner_entities import _build_relation_edges, _looks_like_entity_label
from biblicus.graph.models import GraphExtractionResult, GraphSnapshotReference


def test_graph_extraction_requires_result_type(monkeypatch, tmp_path):
    """Graph extraction rejects extractors that return the wrong result type."""

    class DummyCorpus:
        def __init__(self, root):
            self.uri = "file://corpus"
            self.root = root
            self.meta_dir = root

        def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return self.root / "graph" / snapshot_id

        def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):  # noqa: ARG002
            config_manifest = ExtractionConfigurationManifest(
                configuration_id="c1",
                extractor_id=extractor_id,
                name="cfg",
                created_at="now",
                configuration={},
            )
            return ExtractionSnapshotManifest(
                snapshot_id=snapshot_id,
                configuration=config_manifest,
                corpus_uri="file://corpus",
                catalog_generated_at="now",
                created_at="now",
                items=[ExtractionItemResult(item_id="item1", status="complete", stage_results=[])],
            )

        def get_item(self, item_id):  # noqa: ARG002
            return SimpleNamespace(id=item_id)

        def load_catalog(self):
            return SimpleNamespace(generated_at="now")

    corpus = DummyCorpus(tmp_path)

    snapshot_ref = SimpleNamespace(
        extractor_id="extractor",
        snapshot_id="snap",
        as_string=lambda: "extractor:snap",
    )

    class DummyExtractor:
        def validate_config(self, config):  # noqa: ARG002
            return {}

        def extract_graph(self, **kwargs):  # noqa: ARG002
            return "not-a-result"

    class DummyDriver:
        def session(self, database=None):  # noqa: ARG002
            return SimpleNamespace()

        def close(self):
            pass

    monkeypatch.setattr("biblicus.graph.extraction.get_graph_extractor", lambda _: DummyExtractor())
    monkeypatch.setattr(
        "biblicus.graph.extraction.resolve_neo4j_settings", lambda: SimpleNamespace(database="neo")
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.create_neo4j_driver", lambda settings: DummyDriver()
    )  # noqa: ARG002
    monkeypatch.setattr("biblicus.graph.extraction.clear_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction.write_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction._load_extracted_text", lambda *a, **k: "text")

    with pytest.raises(ValueError):
        build_graph_snapshot(
            corpus=corpus,
            extractor_id="dummy",
            configuration_name="cfg",
            configuration={},
            extraction_snapshot=snapshot_ref,
        )


def test_write_graph_records_skips_empty_payload(monkeypatch):
    """Neo4j writes are skipped when an item has no nodes or edges."""
    calls = []

    class DummySession:
        def execute_write(self, *args, **kwargs):
            calls.append(("write", args, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: ARG002
            return False

    class DummyDriver:
        def session(self, database=None):  # noqa: ARG002
            return DummySession()

    monkeypatch.setattr("biblicus.graph.neo4j._write_nodes", lambda *a, **k: calls.append("nodes"))
    monkeypatch.setattr("biblicus.graph.neo4j._write_edges", lambda *a, **k: calls.append("edges"))

    from biblicus.graph.neo4j import write_graph_records

    write_graph_records(
        driver=DummyDriver(),
        settings=SimpleNamespace(database="neo"),
        corpus_id="c",
        graph_id="g",
        extraction_snapshot="snap",
        item_id="item",
        nodes=[],
        edges=[],
    )
    assert calls == []


def test_graph_extraction_closes_driver(monkeypatch, tmp_path):
    """Graph extraction closes the Neo4j driver after processing."""
    closed = {"called": False}

    class DummyDriver:
        def __init__(self):
            self.closed = False

        def session(self, database=None):  # noqa: ARG002
            return SimpleNamespace()

        def close(self):
            closed["called"] = True

    class DummyExtractor:
        def validate_config(self, config):  # noqa: ARG002
            return {}

        def extract_graph(self, **kwargs):  # noqa: ARG002
            return GraphExtractionResult(item_id="item1", nodes=[], edges=[])

    class DummyCorpus:
        def __init__(self, root):
            self.uri = "file://corpus"
            self.root = root
            self.meta_dir = root

        def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return self.root / "graph" / snapshot_id

        def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):  # noqa: ARG002
            config_manifest = ExtractionConfigurationManifest(
                configuration_id="c1",
                extractor_id=extractor_id,
                name="cfg",
                created_at="now",
                configuration={},
            )
            return ExtractionSnapshotManifest(
                snapshot_id=snapshot_id,
                configuration=config_manifest,
                corpus_uri="file://corpus",
                catalog_generated_at="now",
                created_at="now",
                items=[ExtractionItemResult(item_id="item1", status="complete", stage_results=[])],
            )

        def get_item(self, item_id):  # noqa: ARG002
            return SimpleNamespace(id=item_id)

        def load_catalog(self):
            return SimpleNamespace(generated_at="now")

    corpus = DummyCorpus(tmp_path)
    snapshot_ref = SimpleNamespace(
        extractor_id="extractor",
        snapshot_id="snap",
        as_string=lambda: "extractor:snap",
    )

    monkeypatch.setattr("biblicus.graph.extraction.get_graph_extractor", lambda _: DummyExtractor())
    monkeypatch.setattr(
        "biblicus.graph.extraction.resolve_neo4j_settings", lambda: SimpleNamespace(database="neo")
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.create_neo4j_driver", lambda settings: DummyDriver()
    )  # noqa: ARG002
    monkeypatch.setattr("biblicus.graph.extraction.clear_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction.write_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction._load_extracted_text", lambda *a, **k: "text")

    build_graph_snapshot(
        corpus=corpus,
        extractor_id="dummy",
        configuration_name="cfg",
        configuration={},
        extraction_snapshot=snapshot_ref,
    )
    assert closed["called"] is True


def test_graph_extraction_records_item_errors_and_progress(monkeypatch, tmp_path):
    """Graph extraction records per-item errors and emits progress events."""
    progress_events = []

    class DummyDriver:
        def session(self, database=None):  # noqa: ARG002
            return SimpleNamespace()

        def close(self):
            pass

    class DummyExtractor:
        def validate_config(self, config):  # noqa: ARG002
            return {}

        def extract_graph(self, *, item, **kwargs):  # noqa: ARG002
            if item.id == "item2":
                raise RuntimeError("item boom")
            return GraphExtractionResult(item_id=item.id, nodes=[], edges=[])

    class DummyCorpus:
        def __init__(self, root):
            self.uri = "file://corpus"
            self.root = root
            self.meta_dir = root

        def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return self.root / "graph" / snapshot_id

        def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):  # noqa: ARG002
            config_manifest = ExtractionConfigurationManifest(
                configuration_id="c1",
                extractor_id=extractor_id,
                name="cfg",
                created_at="now",
                configuration={},
            )
            return ExtractionSnapshotManifest(
                snapshot_id=snapshot_id,
                configuration=config_manifest,
                corpus_uri="file://corpus",
                catalog_generated_at="now",
                created_at="now",
                items=[
                    ExtractionItemResult(item_id="item1", status="complete", stage_results=[]),
                    ExtractionItemResult(item_id="item2", status="complete", stage_results=[]),
                ],
            )

        def get_item(self, item_id):
            return SimpleNamespace(id=item_id)

        def load_catalog(self):
            return SimpleNamespace(generated_at="now")

    corpus = DummyCorpus(tmp_path)
    snapshot_ref = SimpleNamespace(
        extractor_id="extractor",
        snapshot_id="snap",
        as_string=lambda: "extractor:snap",
    )

    monkeypatch.setattr("biblicus.graph.extraction.get_graph_extractor", lambda _: DummyExtractor())
    monkeypatch.setattr(
        "biblicus.graph.extraction.resolve_neo4j_settings",
        lambda: SimpleNamespace(database="neo"),
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.create_neo4j_driver",
        lambda _settings: DummyDriver(),
    )
    monkeypatch.setattr("biblicus.graph.extraction.clear_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction.write_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction._load_extracted_text", lambda *a, **k: "text")

    manifest = build_graph_snapshot(
        corpus=corpus,
        extractor_id="dummy",
        configuration_name="cfg",
        configuration={},
        extraction_snapshot=snapshot_ref,
        progress_callback=lambda event, payload: progress_events.append((event, payload)),
    )

    assert manifest.stats["items_processed"] == 2
    assert manifest.stats["items_errored"] == 1
    assert [event for event, _payload in progress_events].count("processed") == 2
    assert progress_events[-1][0] == "completed"


def test_graph_extraction_can_be_bounded_with_max_items(monkeypatch, tmp_path):
    """Graph extraction can process a deterministic prefix for validation runs."""

    processed = []

    class DummyDriver:
        def session(self, database=None):  # noqa: ARG002
            return SimpleNamespace()

        def close(self):
            pass

    class DummyExtractor:
        def validate_config(self, config):  # noqa: ARG002
            return {}

        def extract_graph(self, *, item, **kwargs):  # noqa: ARG002
            processed.append(item.id)
            return GraphExtractionResult(item_id=item.id, nodes=[], edges=[])

    class DummyCorpus:
        def __init__(self, root):
            self.uri = "file://corpus"
            self.root = root
            self.meta_dir = root

        def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return self.root / "graph" / snapshot_id

        def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):  # noqa: ARG002
            config_manifest = ExtractionConfigurationManifest(
                configuration_id="c1",
                extractor_id=extractor_id,
                name="cfg",
                created_at="now",
                configuration={},
            )
            return ExtractionSnapshotManifest(
                snapshot_id=snapshot_id,
                configuration=config_manifest,
                corpus_uri="file://corpus",
                catalog_generated_at="now",
                created_at="now",
                items=[
                    ExtractionItemResult(item_id="item1", status="complete", stage_results=[]),
                    ExtractionItemResult(item_id="item2", status="complete", stage_results=[]),
                    ExtractionItemResult(item_id="item3", status="complete", stage_results=[]),
                ],
            )

        def get_item(self, item_id):
            return SimpleNamespace(id=item_id)

        def load_catalog(self):
            return SimpleNamespace(generated_at="now")

    monkeypatch.setattr("biblicus.graph.extraction.get_graph_extractor", lambda _: DummyExtractor())
    monkeypatch.setattr(
        "biblicus.graph.extraction.resolve_neo4j_settings",
        lambda: SimpleNamespace(database="neo"),
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.create_neo4j_driver",
        lambda _settings: DummyDriver(),
    )
    monkeypatch.setattr("biblicus.graph.extraction.clear_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction.write_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction._load_extracted_text", lambda *a, **k: "text")

    manifest = build_graph_snapshot(
        corpus=DummyCorpus(tmp_path),
        extractor_id="dummy",
        configuration_name="cfg",
        configuration={},
        extraction_snapshot=SimpleNamespace(
            extractor_id="extractor",
            snapshot_id="snap",
            as_string=lambda: "extractor:snap",
        ),
        max_items=2,
    )

    assert processed == ["item1", "item2"]
    assert manifest.stats["items_total"] == 2
    assert manifest.stats["items_available"] == 3


def test_ner_entity_relation_edges_are_sentence_bounded():
    """NER relation edges are deterministic sentence-level co-occurrence signals."""

    edges = _build_relation_edges(
        [
            ("OpenAI", "ORG", 0),
            ("Microsoft", "ORG", 0),
            ("OpenAI", "ORG", 0),
            ("Papyrus", "ORG", 10),
            ("Biblicus", "ORG", 10),
            ("Tactus", "ORG", 10),
        ],
        max_entities_per_sentence=2,
        min_relation_weight=1,
    )

    assert [edge.edge_id for edge in edges] == [
        "entity:biblicus|related_to|entity:papyrus",
        "entity:microsoft|related_to|entity:openai",
    ]
    assert {edge.edge_type for edge in edges} == {"related_to"}
    assert all(edge.properties == {"source": "sentence_cooccurrence"} for edge in edges)


def test_ner_entity_label_shape_filter_rejects_math_fragments():
    """NER entity labels keep named entities and reject common paper/math fragments."""

    assert _looks_like_entity_label("OpenAI")
    assert _looks_like_entity_label("GPT-4")
    assert _looks_like_entity_label("Microsoft Research")
    assert not _looks_like_entity_label("0.232")
    assert not _looks_like_entity_label("+𝑡 𝑛𝑑(𝐴 𝑛 𝐵𝑛)+𝑦=")
    assert not _looks_like_entity_label("Classic LM Search\n LM")
    assert not _looks_like_entity_label("Cambridge,3Georgia Institute")


def test_ner_spacy_pipeline_cache_reused(monkeypatch):
    ner_entities._SPACY_PIPELINE_CACHE.clear()
    load_calls: list[str] = []

    class FakeDoc:
        ents = []

    class FakePipeline:
        def __call__(self, _text):
            return FakeDoc()

    class FakeSpacy:
        @staticmethod
        def load(model_name):
            load_calls.append(model_name)
            return FakePipeline()

    monkeypatch.setitem(sys.modules, "spacy", FakeSpacy())
    ner_entities._extract_entities(
        extracted_text="OpenAI and Microsoft",
        model_name="fake-model",
        min_length=1,
        max_length=100,
        entity_labels=None,
    )
    ner_entities._extract_entities(
        extracted_text="OpenAI and Microsoft",
        model_name="fake-model",
        min_length=1,
        max_length=100,
        entity_labels=None,
    )
    assert load_calls == ["fake-model"]


def test_graph_extraction_timeout_records_error_reason(monkeypatch, tmp_path):
    if not hasattr(signal, "setitimer"):
        pytest.skip("signal.setitimer is unavailable on this platform")

    class DummyDriver:
        def session(self, database=None):  # noqa: ARG002
            return SimpleNamespace()

        def close(self):
            pass

    class DummyExtractor:
        def validate_config(self, config):  # noqa: ARG002
            return {}

        def extract_graph(self, **kwargs):  # noqa: ARG002
            time.sleep(0.05)
            return GraphExtractionResult(item_id="item1", nodes=[], edges=[])

    class DummyCorpus:
        def __init__(self, root):
            self.uri = "file://corpus"
            self.root = root
            self.meta_dir = root

        def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return self.root / "graph" / snapshot_id

        def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):  # noqa: ARG002
            config_manifest = ExtractionConfigurationManifest(
                configuration_id="c1",
                extractor_id=extractor_id,
                name="cfg",
                created_at="now",
                configuration={},
            )
            return ExtractionSnapshotManifest(
                snapshot_id=snapshot_id,
                configuration=config_manifest,
                corpus_uri="file://corpus",
                catalog_generated_at="now",
                created_at="now",
                items=[ExtractionItemResult(item_id="item1", status="complete", stage_results=[])],
            )

        def get_item(self, item_id):
            return SimpleNamespace(id=item_id)

        def load_catalog(self):
            return SimpleNamespace(generated_at="now")

    monkeypatch.setattr("biblicus.graph.extraction.get_graph_extractor", lambda _: DummyExtractor())
    monkeypatch.setattr("biblicus.graph.extraction.resolve_neo4j_settings", lambda: SimpleNamespace(database="neo"))
    monkeypatch.setattr("biblicus.graph.extraction.create_neo4j_driver", lambda _settings: DummyDriver())
    monkeypatch.setattr("biblicus.graph.extraction.clear_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction.write_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction._load_extracted_text", lambda *a, **k: "text")

    manifest = build_graph_snapshot(
        corpus=DummyCorpus(tmp_path),
        extractor_id="dummy",
        configuration_name="cfg",
        configuration={},
        extraction_snapshot=SimpleNamespace(
            extractor_id="extractor",
            snapshot_id="snap",
            as_string=lambda: "extractor:snap",
        ),
        item_timeout_seconds=0.01,
        item_retry_attempts=0,
    )

    assert manifest.stats["items_errored"] == 1
    assert manifest.stats["items_timed_out"] == 1
    summary = manifest.stats["item_summaries"][0]
    assert summary["status"] == "error"
    assert summary["error_reason"] == "timeout"
    assert summary["attempts"] == 1


def test_graph_extraction_retry_recovers_from_first_failure(monkeypatch, tmp_path):
    attempts_by_item: dict[str, int] = {}

    class DummyDriver:
        def session(self, database=None):  # noqa: ARG002
            return SimpleNamespace()

        def close(self):
            pass

    class DummyExtractor:
        def validate_config(self, config):  # noqa: ARG002
            return {}

        def extract_graph(self, *, item, **kwargs):  # noqa: ARG002
            attempts_by_item[item.id] = attempts_by_item.get(item.id, 0) + 1
            if attempts_by_item[item.id] == 1:
                raise RuntimeError("first attempt fails")
            return GraphExtractionResult(item_id=item.id, nodes=[], edges=[])

    class DummyCorpus:
        def __init__(self, root):
            self.uri = "file://corpus"
            self.root = root
            self.meta_dir = root

        def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return self.root / "graph" / snapshot_id

        def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):  # noqa: ARG002
            config_manifest = ExtractionConfigurationManifest(
                configuration_id="c1",
                extractor_id=extractor_id,
                name="cfg",
                created_at="now",
                configuration={},
            )
            return ExtractionSnapshotManifest(
                snapshot_id=snapshot_id,
                configuration=config_manifest,
                corpus_uri="file://corpus",
                catalog_generated_at="now",
                created_at="now",
                items=[ExtractionItemResult(item_id="item1", status="complete", stage_results=[])],
            )

        def get_item(self, item_id):
            return SimpleNamespace(id=item_id)

        def load_catalog(self):
            return SimpleNamespace(generated_at="now")

    monkeypatch.setattr("biblicus.graph.extraction.get_graph_extractor", lambda _: DummyExtractor())
    monkeypatch.setattr("biblicus.graph.extraction.resolve_neo4j_settings", lambda: SimpleNamespace(database="neo"))
    monkeypatch.setattr("biblicus.graph.extraction.create_neo4j_driver", lambda _settings: DummyDriver())
    monkeypatch.setattr("biblicus.graph.extraction.clear_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction.write_graph_records", lambda **kwargs: None)
    monkeypatch.setattr("biblicus.graph.extraction._load_extracted_text", lambda *a, **k: "text")

    manifest = build_graph_snapshot(
        corpus=DummyCorpus(tmp_path),
        extractor_id="dummy",
        configuration_name="cfg",
        configuration={},
        extraction_snapshot=SimpleNamespace(
            extractor_id="extractor",
            snapshot_id="snap",
            as_string=lambda: "extractor:snap",
        ),
        item_timeout_seconds=None,
        item_retry_attempts=1,
    )

    assert manifest.stats["items_errored"] == 0
    summary = manifest.stats["item_summaries"][0]
    assert summary["status"] == "complete"
    assert summary["attempts"] == 2
    assert not _looks_like_entity_label("D. Kapur")


def test_graph_snapshot_export_reads_neo4j_records(monkeypatch, tmp_path):
    """Graph export returns deterministic snapshot nodes and edges."""

    closed = {"called": False}

    class DummyDriver:
        def close(self):
            closed["called"] = True

    class DummyCorpus:
        uri = "file://corpus"

        def __init__(self, root):
            self.root = root

        def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return self.root / "graph" / extractor_id / snapshot_id

    corpus = DummyCorpus(tmp_path)
    snapshot_dir = corpus.graph_snapshot_dir("ner-entities", "snap1")
    snapshot_dir.mkdir(parents=True)
    snapshot_dir.joinpath("manifest.json").write_text(
        """
{
  "snapshot_id": "snap1",
  "graph_id": "graph-1",
  "configuration": {
    "configuration_id": "cfg-1",
    "extractor_id": "ner-entities",
    "name": "reference-entity-graph",
    "created_at": "2026-05-19T00:00:00Z",
    "configuration": {"model": "en_core_web_sm"}
  },
  "corpus_uri": "file://corpus",
  "catalog_generated_at": "2026-05-19T00:00:00Z",
  "extraction_snapshot": "text:snap",
  "created_at": "2026-05-19T00:00:00Z",
  "stats": {"nodes": 2, "edges": 1}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.resolve_neo4j_settings",
        lambda: SimpleNamespace(database="neo"),
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.create_neo4j_driver",
        lambda _settings: DummyDriver(),
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.read_graph_records",
        lambda **_kwargs: {
            "nodes": [
                {
                    "item_id": "item-b",
                    "node_id": "entity:b",
                    "node_type": "entity",
                    "label": "Beta",
                    "properties": {"kind": "ORG"},
                },
                {
                    "item_id": "item-a",
                    "node_id": "entity:a",
                    "node_type": "entity",
                    "label": "Alpha",
                    "properties": {"kind": "PERSON"},
                },
            ],
            "edges": [
                {
                    "item_id": "item-a",
                    "edge_id": "edge-1",
                    "src": "item:item-a",
                    "dst": "entity:a",
                    "edge_type": "mentions",
                    "weight": 2,
                    "properties": {"count": 2},
                }
            ],
        },
    )

    exported = export_graph_snapshot(
        corpus,
        snapshot=GraphSnapshotReference(extractor_id="ner-entities", snapshot_id="snap1"),
    )

    assert closed["called"] is True
    assert exported.snapshot.as_string() == "ner-entities:snap1"
    assert [node.item_id for node in exported.nodes] == ["item-a", "item-b"]
    assert exported.nodes[0].properties == {"kind": "PERSON"}
    assert exported.edges[0].edge_type == "mentions"
    assert exported.stats["exported_nodes"] == 2
    assert exported.stats["exported_edges"] == 1


def test_graph_snapshot_export_allows_empty_graph(monkeypatch, tmp_path):
    """Graph export preserves the manifest even when Neo4j has no rows."""

    class DummyDriver:
        def close(self):
            pass

    class DummyCorpus:
        uri = "file://corpus"

        def __init__(self, root):
            self.root = root

        def graph_snapshot_dir(self, extractor_id, snapshot_id):  # noqa: ARG002
            return self.root / "graph" / extractor_id / snapshot_id

    corpus = DummyCorpus(tmp_path)
    snapshot_dir = corpus.graph_snapshot_dir("ner-entities", "empty")
    snapshot_dir.mkdir(parents=True)
    snapshot_dir.joinpath("manifest.json").write_text(
        """
{
  "snapshot_id": "empty",
  "graph_id": "graph-empty",
  "configuration": {
    "configuration_id": "cfg-empty",
    "extractor_id": "ner-entities",
    "name": "reference-entity-graph",
    "created_at": "2026-05-19T00:00:00Z",
    "configuration": {}
  },
  "corpus_uri": "file://corpus",
  "catalog_generated_at": "2026-05-19T00:00:00Z",
  "extraction_snapshot": "text:snap",
  "created_at": "2026-05-19T00:00:00Z",
  "stats": {"nodes": 0, "edges": 0}
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.resolve_neo4j_settings",
        lambda: SimpleNamespace(database="neo"),
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.create_neo4j_driver",
        lambda _settings: DummyDriver(),
    )
    monkeypatch.setattr(
        "biblicus.graph.extraction.read_graph_records",
        lambda **_kwargs: {"nodes": [], "edges": []},
    )

    exported = export_graph_snapshot(
        corpus,
        snapshot=GraphSnapshotReference(extractor_id="ner-entities", snapshot_id="empty"),
    )

    assert exported.nodes == []
    assert exported.edges == []
    assert exported.stats["exported_nodes"] == 0
