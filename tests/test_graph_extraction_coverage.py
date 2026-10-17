from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest
from pydantic import BaseModel, ConfigDict

from biblicus.extraction import (
    ExtractionConfigurationManifest,
    ExtractionItemResult,
    ExtractionSnapshotManifest,
)
from biblicus.graph import extraction as graph_extraction
from biblicus.graph.extraction import (
    build_graph_snapshot,
    export_graph_snapshot,
    latest_graph_snapshot_reference,
    list_graph_snapshots,
    load_graph_snapshot_manifest,
    resolve_graph_snapshot_reference,
)
from biblicus.graph.models import (
    GraphEdge,
    GraphExtractionResult,
    GraphNode,
    GraphSnapshotReference,
)
from biblicus.models import ExtractionSnapshotReference


class StrictDummyGraphConfig(BaseModel):
    """Test double: strict dummy graph config."""

    model_config = ConfigDict(extra="forbid")

    label_prefix: str = "entity"


class GraphExtractionDummyCorpus:
    """Test double: graph extraction dummy corpus."""

    def __init__(self, root: Path, item_results: List[ExtractionItemResult]) -> None:
        self.root = root
        self.uri = "file://dummy-corpus"
        self.item_results = item_results
        self.graph_snapshots_dir = root / "graph"

    def load_catalog(self):
        """Return a fake catalog with a fixed timestamp."""
        return SimpleNamespace(generated_at="2026-01-01T00:00:00Z")

    def load_extraction_snapshot_manifest(self, *, extractor_id: str, snapshot_id: str):
        """Return an extraction manifest for the scripted items."""
        configuration_manifest = ExtractionConfigurationManifest(
            configuration_id="extraction-configuration",
            extractor_id=extractor_id,
            name="extraction",
            created_at="2026-01-01T00:00:00Z",
            configuration={},
        )
        return ExtractionSnapshotManifest(
            snapshot_id=snapshot_id,
            configuration=configuration_manifest,
            corpus_uri=self.uri,
            catalog_generated_at="2026-01-01T00:00:00Z",
            created_at="2026-01-01T00:00:00Z",
            items=list(self.item_results),
        )

    def get_item(self, item_id: str):
        """Return a fake catalog item."""
        return SimpleNamespace(id=item_id, title=None, relpath=f"{item_id}.txt")

    def extraction_snapshot_dir(self, *, extractor_id: str, snapshot_id: str) -> Path:
        """Return the extraction snapshot directory."""
        return self.root / "extracted" / extractor_id / snapshot_id

    def graph_snapshot_dir(self, *, extractor_id: str, snapshot_id: str) -> Path:
        """Return the graph snapshot directory."""
        return self.graph_snapshots_dir / extractor_id / snapshot_id


class RecordingNeo4jDriver:
    """Test double: recording neo4j driver."""

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        """Mark the fake driver as closed."""
        self.closed = True


class ScriptedGraphExtractor:
    """Test double: scripted graph extractor."""

    def __init__(self, behaviors: Dict[str, List[Any]]) -> None:
        self.behaviors = behaviors
        self.calls: List[str] = []

    def validate_config(self, config: Dict[str, object]) -> BaseModel:
        """Validate the configuration with the strict dummy model."""
        return StrictDummyGraphConfig.model_validate(config)

    def extract_graph(self, *, corpus, item, extracted_text, config, extraction_metadata):
        """Return the next scripted extraction behavior for the item."""
        self.calls.append(item.id)
        queue = self.behaviors.get(item.id) or []
        behavior = queue.pop(0) if queue else "complete"
        if isinstance(behavior, BaseException):
            raise behavior
        if callable(behavior):
            return behavior()
        return GraphExtractionResult(
            item_id=item.id,
            nodes=[
                GraphNode(node_id=f"{item.id}:a", node_type="entity", label="Alpha"),
                GraphNode(node_id=f"{item.id}:b", node_type="entity", label="Beta"),
            ],
            edges=[
                GraphEdge(
                    edge_id=f"{item.id}:edge",
                    src=f"{item.id}:a",
                    dst=f"{item.id}:b",
                    edge_type="related_to",
                )
            ],
        )


def write_extracted_artifacts(
    corpus: GraphExtractionDummyCorpus,
    *,
    extraction_snapshot: ExtractionSnapshotReference,
    item_id: str,
    text: Optional[str],
    metadata_text: Optional[str],
) -> ExtractionItemResult:
    """Write extracted artifacts."""
    snapshot_dir = corpus.extraction_snapshot_dir(
        extractor_id=extraction_snapshot.extractor_id,
        snapshot_id=extraction_snapshot.snapshot_id,
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    text_relpath = None
    metadata_relpath = None
    if text is not None:
        text_relpath = f"text/{item_id}.txt"
        (snapshot_dir / "text").mkdir(parents=True, exist_ok=True)
        (snapshot_dir / text_relpath).write_text(text, encoding="utf-8")
    if metadata_text is not None:
        metadata_relpath = f"metadata/{item_id}.json"
        (snapshot_dir / "metadata").mkdir(parents=True, exist_ok=True)
        (snapshot_dir / metadata_relpath).write_text(metadata_text, encoding="utf-8")
    return ExtractionItemResult(
        item_id=item_id,
        status="extracted",
        final_text_relpath=text_relpath,
        final_metadata_relpath=metadata_relpath,
    )


@pytest.fixture
def extraction_snapshot_reference() -> ExtractionSnapshotReference:
    """Return the extraction snapshot reference used by tests."""
    return ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id="extraction-snap")


@pytest.fixture
def patched_neo4j(monkeypatch):
    """Return recorded Neo4j calls after patching graph storage helpers."""
    recorded: Dict[str, Any] = {"writes": [], "clears": [], "drivers": []}

    def create_recording_driver(settings):
        """Create recording driver."""
        driver = RecordingNeo4jDriver()
        recorded["drivers"].append(driver)
        return driver

    def record_write(**kwargs):
        """Record write."""
        if kwargs["item_id"] == "item-write-fails":
            raise RuntimeError("neo4j write exploded")
        recorded["writes"].append(kwargs)

    monkeypatch.setattr(
        graph_extraction, "resolve_neo4j_settings", lambda: SimpleNamespace(database=None)
    )
    monkeypatch.setattr(graph_extraction, "create_neo4j_driver", create_recording_driver)
    monkeypatch.setattr(graph_extraction, "write_graph_records", record_write)
    monkeypatch.setattr(
        graph_extraction, "clear_graph_records", lambda **kwargs: recorded["clears"].append(kwargs)
    )
    return recorded


def install_scripted_extractor(monkeypatch, extractor: ScriptedGraphExtractor) -> None:
    """Install scripted extractor."""
    monkeypatch.setattr(graph_extraction, "get_graph_extractor", lambda _identifier: extractor)


def test_build_graph_snapshot_records_every_item_outcome_and_progress_events(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot records every item outcome and progress events."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    item_results = [
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id="item-complete",
            text="Alpha and Beta",
            metadata_text=json.dumps({"method": "grobid"}),
        ),
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id="item-without-text",
            text=None,
            metadata_text=None,
        ),
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id="item-times-out",
            text="slow",
            metadata_text=json.dumps(["not", "a", "mapping"]),
        ),
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id="item-corrupt-metadata",
            text="text",
            metadata_text="{not json",
        ),
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id="item-write-fails",
            text="text",
            metadata_text=None,
        ),
        ExtractionItemResult(
            item_id="item-missing-files",
            status="extracted",
            final_text_relpath="text/absent.txt",
            final_metadata_relpath="metadata/absent.json",
        ),
    ]
    corpus.item_results = item_results
    extractor = ScriptedGraphExtractor(
        {"item-times-out": [graph_extraction._ItemExtractionTimeout("too slow")]}
    )
    install_scripted_extractor(monkeypatch, extractor)
    events: List[tuple[str, Dict[str, Any]]] = []

    manifest = build_graph_snapshot(
        corpus,
        extractor_id="scripted",
        configuration_name="coverage",
        configuration={"_execution": "ignored-non-mapping"},
        extraction_snapshot=extraction_snapshot_reference,
        item_timeout_seconds=None,
        heartbeat_interval_seconds=0.000001,
        progress_callback=lambda event, payload: events.append((event, payload)),
    )

    summaries = {summary["item_id"]: summary for summary in manifest.stats["item_summaries"]}
    assert summaries["item-complete"]["status"] == "complete"
    assert summaries["item-without-text"]["error_reason"] == "no_extracted_text"
    assert summaries["item-missing-files"]["error_reason"] == "no_extracted_text"
    assert summaries["item-times-out"]["error_reason"] == "timeout"
    assert "timed out after -s" in summaries["item-times-out"]["error_message"]
    assert summaries["item-corrupt-metadata"]["error_reason"] == "value_error"
    assert summaries["item-write-fails"]["error_reason"] == "exception"
    assert manifest.stats["items_skipped"] == 2
    assert manifest.stats["items_errored"] == 3
    assert manifest.stats["items_timed_out"] == 1
    assert manifest.stats["nodes"] == 2
    assert manifest.stats["item_timeout_seconds"] is None
    assert manifest.configuration.configuration == {}
    event_names = [event for event, _payload in events]
    assert event_names[0] == "starting"
    assert event_names[-1] == "completed"
    assert "heartbeat" in event_names
    assert patched_neo4j["drivers"][0].closed is True
    snapshot_dir = corpus.graph_snapshot_dir(
        extractor_id="scripted", snapshot_id=manifest.snapshot_id
    )
    assert (snapshot_dir / "manifest.json").is_file()
    latest_payload = json.loads((snapshot_dir.parent / "latest.json").read_text("utf-8"))
    assert latest_payload["snapshot_id"] == manifest.snapshot_id


def test_build_graph_snapshot_uses_graph_execution_block_max_items(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot uses graph execution block max items."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    corpus.item_results = [
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id=f"item-{index}",
            text="Alpha",
            metadata_text=None,
        )
        for index in range(3)
    ]
    install_scripted_extractor(monkeypatch, ScriptedGraphExtractor({}))

    manifest = build_graph_snapshot(
        corpus,
        extractor_id="scripted",
        configuration_name="coverage",
        configuration={
            "label_prefix": "x",
            "graph": {"max_items": 2, "workers": 1},
            "_execution": {"note": "kept"},
        },
        extraction_snapshot=extraction_snapshot_reference,
        heartbeat_interval_seconds=3600.0,
        progress_callback=lambda event, payload: None,
    )

    assert manifest.stats["items_total"] == 2
    assert manifest.stats["items_available"] == 3
    assert manifest.configuration.configuration["_execution"] == {
        "max_items": 2,
        "workers": 1,
        "note": "kept",
    }


def test_build_graph_snapshot_explicit_max_items_overrides_graph_block(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot explicit max items overrides graph block."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    corpus.item_results = [
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id=f"item-{index}",
            text="Alpha",
            metadata_text=None,
        )
        for index in range(3)
    ]
    install_scripted_extractor(monkeypatch, ScriptedGraphExtractor({}))

    manifest = build_graph_snapshot(
        corpus,
        extractor_id="scripted",
        configuration_name="coverage",
        configuration={"graph": {"max_items": 3}},
        extraction_snapshot=extraction_snapshot_reference,
        max_items=1,
        item_timeout_seconds=0,
    )

    assert manifest.stats["items_total"] == 1
    assert manifest.stats["item_timeout_seconds"] is None
    assert manifest.configuration.configuration["_execution"]["max_items"] == 1


def test_build_graph_snapshot_graph_block_without_max_items_keeps_all_items(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot graph block without max items keeps all items."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    corpus.item_results = [
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id="item-only",
            text="Alpha",
            metadata_text=None,
        )
    ]
    install_scripted_extractor(monkeypatch, ScriptedGraphExtractor({}))

    manifest = build_graph_snapshot(
        corpus,
        extractor_id="scripted",
        configuration_name="coverage",
        configuration={"graph": {"workers": 2}},
        extraction_snapshot=extraction_snapshot_reference,
    )

    assert manifest.stats["items_total"] == 1
    assert manifest.configuration.configuration["_execution"] == {"workers": 2}


def test_build_graph_snapshot_reads_max_items_from_execution_block(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot reads max items from execution block."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    corpus.item_results = [
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id=f"item-{index}",
            text="Alpha",
            metadata_text=None,
        )
        for index in range(2)
    ]
    install_scripted_extractor(monkeypatch, ScriptedGraphExtractor({}))

    manifest = build_graph_snapshot(
        corpus,
        extractor_id="scripted",
        configuration_name="coverage",
        configuration={"_execution": {"max_items": 1}},
        extraction_snapshot=extraction_snapshot_reference,
    )

    assert manifest.stats["items_total"] == 1


def test_build_graph_snapshot_rejects_non_positive_max_items(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot rejects non positive max items."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    install_scripted_extractor(monkeypatch, ScriptedGraphExtractor({}))

    with pytest.raises(ValueError, match="max_items must be a positive integer"):
        build_graph_snapshot(
            corpus,
            extractor_id="scripted",
            configuration_name="coverage",
            configuration={},
            extraction_snapshot=extraction_snapshot_reference,
            max_items=0,
        )


def test_build_graph_snapshot_wraps_configuration_validation_errors(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot wraps configuration validation errors."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    install_scripted_extractor(monkeypatch, ScriptedGraphExtractor({}))

    with pytest.raises(ValueError, match="Invalid graph extraction configuration"):
        build_graph_snapshot(
            corpus,
            extractor_id="scripted",
            configuration_name="coverage",
            configuration={"unexpected_field": True},
            extraction_snapshot=extraction_snapshot_reference,
        )


def test_build_graph_snapshot_retries_failed_attempts_before_succeeding(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot retries failed attempts before succeeding."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    corpus.item_results = [
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id=item_id,
            text="Alpha",
            metadata_text=None,
        )
        for item_id in ["item-flaky", "item-slow-then-ok", "item-always-value-error"]
    ]
    extractor = ScriptedGraphExtractor(
        {
            "item-flaky": [RuntimeError("transient"), "complete"],
            "item-slow-then-ok": [graph_extraction._ItemExtractionTimeout("slow"), "complete"],
            "item-always-value-error": [ValueError("bad one"), ValueError("bad two")],
        }
    )
    install_scripted_extractor(monkeypatch, extractor)

    manifest = build_graph_snapshot(
        corpus,
        extractor_id="scripted",
        configuration_name="coverage",
        configuration={},
        extraction_snapshot=extraction_snapshot_reference,
        item_retry_attempts=1,
    )

    summaries = {summary["item_id"]: summary for summary in manifest.stats["item_summaries"]}
    assert summaries["item-flaky"]["status"] == "complete"
    assert summaries["item-flaky"]["attempts"] == 2
    assert summaries["item-slow-then-ok"]["attempts"] == 2
    assert summaries["item-always-value-error"]["error_reason"] == "value_error"
    assert summaries["item-always-value-error"]["error_message"] == "bad two"
    assert summaries["item-always-value-error"]["attempts"] == 2


def test_build_graph_snapshot_enforces_item_timeout_with_alarm_signal(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot enforces item timeout with alarm signal."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    corpus.item_results = [
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id="item-sleeps",
            text="Alpha",
            metadata_text=None,
        )
    ]

    def sleep_until_interrupted():
        """Sleep until interrupted."""
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            time.sleep(0.01)
        raise AssertionError("timeout alarm did not fire")

    install_scripted_extractor(
        monkeypatch, ScriptedGraphExtractor({"item-sleeps": [sleep_until_interrupted]})
    )

    manifest = build_graph_snapshot(
        corpus,
        extractor_id="scripted",
        configuration_name="coverage",
        configuration={},
        extraction_snapshot=extraction_snapshot_reference,
        item_timeout_seconds=0.05,
    )

    summary = manifest.stats["item_summaries"][0]
    assert summary["error_reason"] == "timeout"
    assert "timed out after 0.05s" in summary["error_message"]


def test_build_graph_snapshot_reraises_wrong_result_type_error(
    monkeypatch, tmp_path, extraction_snapshot_reference, patched_neo4j
):
    """Verify build graph snapshot reraises wrong result type error."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    corpus.item_results = [
        write_extracted_artifacts(
            corpus,
            extraction_snapshot=extraction_snapshot_reference,
            item_id="item-wrong-type",
            text="Alpha",
            metadata_text=None,
        )
    ]
    install_scripted_extractor(
        monkeypatch,
        ScriptedGraphExtractor({"item-wrong-type": [lambda: {"not": "a result"}]}),
    )

    with pytest.raises(ValueError, match="must return GraphExtractionResult"):
        build_graph_snapshot(
            corpus,
            extractor_id="scripted",
            configuration_name="coverage",
            configuration={},
            extraction_snapshot=extraction_snapshot_reference,
        )
    assert patched_neo4j["drivers"][0].closed is True


def test_item_timeout_guard_is_noop_outside_main_thread():
    """Verify item timeout guard is noop outside main thread."""
    observed: Dict[str, Any] = {}

    def enter_guard_in_worker_thread():
        """Enter guard in worker thread."""
        with graph_extraction._item_timeout_guard(0.01):
            observed["entered"] = True

    worker = threading.Thread(target=enter_guard_in_worker_thread)
    worker.start()
    worker.join()

    assert observed == {"entered": True}


def test_item_timeout_guard_is_noop_without_setitimer_support(monkeypatch):
    """Verify item timeout guard is noop without setitimer support."""
    monkeypatch.delattr(graph_extraction.signal, "setitimer")
    entered = []

    with graph_extraction._item_timeout_guard(0.01):
        entered.append(True)

    assert entered == [True]


def test_emit_graph_progress_ignores_missing_callback():
    """Verify emit graph progress ignores missing callback."""
    assert graph_extraction._emit_graph_progress(None, "starting", snapshot_id="s") is None


def test_maybe_emit_graph_heartbeat_returns_previous_timestamp_when_disabled():
    """Verify maybe emit graph heartbeat returns previous timestamp when disabled."""
    common_arguments = dict(
        snapshot_id="s",
        extractor_id="e",
        items_total=1,
        items_available=1,
        item_index=0,
        node_total=0,
        edge_total=0,
        skipped_total=0,
        errored_total=0,
        timed_out_total=0,
        started_monotonic=0.0,
        last_heartbeat_monotonic=12.5,
    )
    assert (
        graph_extraction._maybe_emit_graph_heartbeat(
            progress_callback=None, heartbeat_interval_seconds=1.0, **common_arguments
        )
        == 12.5
    )
    assert (
        graph_extraction._maybe_emit_graph_heartbeat(
            progress_callback=lambda event, payload: None,
            heartbeat_interval_seconds=0.0,
            **common_arguments,
        )
        == 12.5
    )


def write_graph_snapshot_manifest_file(
    corpus: GraphExtractionDummyCorpus,
    *,
    extractor_id: str,
    snapshot_id: str,
    created_at: str,
    stats: Optional[Dict[str, Any]] = None,
) -> None:
    """Write graph snapshot manifest file."""
    snapshot_dir = corpus.graph_snapshot_dir(extractor_id=extractor_id, snapshot_id=snapshot_id)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_id": snapshot_id,
        "graph_id": f"{extractor_id}:graph",
        "configuration": {
            "configuration_id": f"{snapshot_id}-configuration",
            "extractor_id": extractor_id,
            "name": "coverage",
            "created_at": created_at,
            "configuration": {},
        },
        "corpus_uri": corpus.uri,
        "catalog_generated_at": "2026-01-01T00:00:00Z",
        "extraction_snapshot": "pipeline:extraction-snap",
        "created_at": created_at,
        "stats": stats or {},
    }
    (snapshot_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def test_load_graph_snapshot_manifest_requires_manifest_file(tmp_path):
    """Verify load graph snapshot manifest requires manifest file."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])

    with pytest.raises(FileNotFoundError, match="Missing graph snapshot manifest"):
        load_graph_snapshot_manifest(corpus, extractor_id="scripted", snapshot_id="absent")


def test_list_graph_snapshots_returns_empty_without_graph_directory(tmp_path):
    """Verify list graph snapshots returns empty without graph directory."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])

    assert list_graph_snapshots(corpus) == []
    assert latest_graph_snapshot_reference(corpus) is None


def test_list_graph_snapshots_skips_unusable_entries_and_sorts_newest_first(tmp_path):
    """Verify list graph snapshots skips unusable entries and sorts newest first."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    write_graph_snapshot_manifest_file(
        corpus,
        extractor_id="alpha-extractor",
        snapshot_id="older",
        created_at="2026-01-01T00:00:00Z",
        stats={"nodes": 1},
    )
    write_graph_snapshot_manifest_file(
        corpus,
        extractor_id="beta-extractor",
        snapshot_id="newer",
        created_at="2026-02-01T00:00:00Z",
    )
    alpha_dir = corpus.graph_snapshots_dir / "alpha-extractor"
    (alpha_dir / "latest.json").write_text("{}", encoding="utf-8")
    (alpha_dir / "without-manifest").mkdir()
    invalid_dir = alpha_dir / "invalid-manifest"
    invalid_dir.mkdir()
    (invalid_dir / "manifest.json").write_text(json.dumps({"snapshot_id": 1}), encoding="utf-8")
    (corpus.graph_snapshots_dir / "stray-file.txt").write_text("x", encoding="utf-8")

    entries = list_graph_snapshots(corpus)

    assert [entry.snapshot_id for entry in entries] == ["newer", "older"]
    assert entries[1].stats == {"nodes": 1}
    filtered = list_graph_snapshots(corpus, extractor_id="alpha-extractor")
    assert [entry.snapshot_id for entry in filtered] == ["older"]
    assert list_graph_snapshots(corpus, extractor_id="missing-extractor") == []
    latest = latest_graph_snapshot_reference(corpus)
    assert latest == GraphSnapshotReference(extractor_id="beta-extractor", snapshot_id="newer")


def test_resolve_graph_snapshot_reference_parses_raw_reference(tmp_path):
    """Verify resolve graph snapshot reference parses raw reference."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])

    reference = resolve_graph_snapshot_reference(corpus, raw="alpha-extractor:snap")

    assert reference.extractor_id == "alpha-extractor"
    assert reference.snapshot_id == "snap"


def test_export_graph_snapshot_sorts_records_and_applies_defaults(monkeypatch, tmp_path):
    """Verify export graph snapshot sorts records and applies defaults."""
    corpus = GraphExtractionDummyCorpus(tmp_path, [])
    write_graph_snapshot_manifest_file(
        corpus,
        extractor_id="alpha-extractor",
        snapshot_id="snap",
        created_at="2026-01-01T00:00:00Z",
        stats={"nodes": 2},
    )
    drivers: List[RecordingNeo4jDriver] = []
    captured_read_arguments: Dict[str, Any] = {}

    def create_recording_driver(settings):
        """Create recording driver."""
        driver = RecordingNeo4jDriver()
        drivers.append(driver)
        return driver

    def read_records(**kwargs):
        """Read records."""
        captured_read_arguments.update(kwargs)
        return {
            "nodes": [
                {
                    "item_id": "item-b",
                    "node_id": "n2",
                    "node_type": "entity",
                    "label": "Beta",
                    "properties": None,
                },
                {
                    "item_id": "item-a",
                    "node_id": "n1",
                    "node_type": "entity",
                    "label": "Alpha",
                    "properties": {"canonical": "alpha"},
                },
            ],
            "edges": [
                {
                    "item_id": "item-a",
                    "edge_id": "e2",
                    "src": "n1",
                    "dst": "n2",
                    "edge_type": "related_to",
                },
                {
                    "item_id": "item-a",
                    "edge_id": "e1",
                    "src": "n1",
                    "dst": "n2",
                    "edge_type": "mentions",
                    "weight": 3,
                    "properties": {"source": "test"},
                },
            ],
        }

    monkeypatch.setattr(
        graph_extraction, "resolve_neo4j_settings", lambda: SimpleNamespace(database=None)
    )
    monkeypatch.setattr(graph_extraction, "create_neo4j_driver", create_recording_driver)
    monkeypatch.setattr(graph_extraction, "read_graph_records", read_records)

    export = export_graph_snapshot(
        corpus,
        snapshot=GraphSnapshotReference(extractor_id="alpha-extractor", snapshot_id="snap"),
    )

    assert [node.node_id for node in export.nodes] == ["n1", "n2"]
    assert export.nodes[1].properties == {}
    assert [edge.edge_id for edge in export.edges] == ["e1", "e2"]
    assert export.edges[0].weight == 3.0
    assert export.edges[1].weight == 1.0
    assert export.edges[1].properties == {}
    assert export.stats == {"nodes": 2, "exported_nodes": 2, "exported_edges": 2}
    assert captured_read_arguments["graph_id"] == "alpha-extractor:graph"
    assert captured_read_arguments["extraction_snapshot"] == "pipeline:extraction-snap"
    assert drivers[0].closed is True
