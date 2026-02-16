from types import SimpleNamespace
from pathlib import Path

import pytest

from biblicus.graph.extraction import build_graph_snapshot
from biblicus.graph.models import GraphExtractionResult
from biblicus.extraction import (
    ExtractionConfigurationManifest,
    ExtractionItemResult,
    ExtractionSnapshotManifest,
)


def test_graph_extraction_requires_result_type(monkeypatch, tmp_path):
    # Stub corpus with minimal interface
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

    # extraction snapshot reference
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

    # Patch extractor and supporting functions to avoid network/database work
    monkeypatch.setattr("biblicus.graph.extraction.get_graph_extractor", lambda _: DummyExtractor())
    monkeypatch.setattr("biblicus.graph.extraction.resolve_neo4j_settings", lambda: SimpleNamespace(database="neo"))
    monkeypatch.setattr("biblicus.graph.extraction.create_neo4j_driver", lambda settings: DummyDriver())  # noqa: ARG002
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
    # With no nodes or edges, nothing should be written
    assert calls == []


def test_graph_extraction_closes_driver(monkeypatch, tmp_path):
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
    monkeypatch.setattr("biblicus.graph.extraction.resolve_neo4j_settings", lambda: SimpleNamespace(database="neo"))
    monkeypatch.setattr("biblicus.graph.extraction.create_neo4j_driver", lambda settings: DummyDriver())  # noqa: ARG002
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
