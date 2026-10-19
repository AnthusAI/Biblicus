"""
Graph extraction snapshots for Biblicus.
"""

from __future__ import annotations

import json
import signal
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from ..corpus import Corpus
from ..models import ExtractionSnapshotReference
from ..retrieval import hash_text
from ..time import utc_now_iso
from .extractors import get_graph_extractor
from .models import (
    GraphConfigurationManifest,
    GraphExportEdge,
    GraphExportNode,
    GraphExtractionItemSummary,
    GraphExtractionResult,
    GraphSnapshotExport,
    GraphSnapshotListEntry,
    GraphSnapshotManifest,
    GraphSnapshotReference,
    parse_graph_snapshot_reference,
)
from .neo4j import (
    clear_graph_records,
    create_neo4j_driver,
    read_graph_records,
    resolve_neo4j_settings,
    write_graph_records,
)


def create_graph_configuration_manifest(
    *, extractor_id: str, name: str, configuration: Dict[str, Any]
) -> GraphConfigurationManifest:
    """
    Create a deterministic graph extraction configuration manifest.

    :param extractor_id: Graph extractor identifier.
    :type extractor_id: str
    :param name: Human configuration name.
    :type name: str
    :param configuration: Extractor configuration.
    :type configuration: dict[str, Any]
    :return: Configuration manifest.
    :rtype: GraphConfigurationManifest
    """
    configuration_payload = json.dumps(
        {"extractor_id": extractor_id, "name": name, "configuration": configuration},
        sort_keys=True,
    )
    configuration_id = hash_text(configuration_payload)
    return GraphConfigurationManifest(
        configuration_id=configuration_id,
        extractor_id=extractor_id,
        name=name,
        created_at=utc_now_iso(),
        configuration=configuration,
    )


def create_graph_id(*, extractor_id: str, configuration: Dict[str, Any]) -> str:
    """
    Create a deterministic graph identifier from extractor and configuration.

    :param extractor_id: Graph extractor identifier.
    :type extractor_id: str
    :param configuration: Extractor configuration.
    :type configuration: dict[str, Any]
    :return: Graph identifier.
    :rtype: str
    """
    config_payload = json.dumps(configuration, sort_keys=True)
    config_hash = hash_text(config_payload)
    return f"{extractor_id}:{config_hash}"


def create_graph_snapshot_manifest(
    corpus: Corpus,
    *,
    configuration: GraphConfigurationManifest,
    extraction_snapshot: ExtractionSnapshotReference,
    graph_id: str,
) -> GraphSnapshotManifest:
    """
    Create a new graph snapshot manifest for a corpus.

    :param corpus: Corpus associated with the snapshot.
    :type corpus: Corpus
    :param configuration: Configuration manifest.
    :type configuration: GraphConfigurationManifest
    :param extraction_snapshot: Extraction snapshot reference.
    :type extraction_snapshot: ExtractionSnapshotReference
    :param graph_id: Graph identifier.
    :type graph_id: str
    :return: Graph snapshot manifest.
    :rtype: GraphSnapshotManifest
    """
    catalog = corpus.load_catalog()
    snapshot_id = hash_text(
        f"{configuration.configuration_id}:{extraction_snapshot.as_string()}:{catalog.generated_at}"
    )
    return GraphSnapshotManifest(
        snapshot_id=snapshot_id,
        graph_id=graph_id,
        configuration=configuration,
        corpus_uri=corpus.uri,
        catalog_generated_at=catalog.generated_at,
        extraction_snapshot=extraction_snapshot.as_string(),
        created_at=utc_now_iso(),
        stats={},
    )


def write_graph_snapshot_manifest(*, snapshot_dir: Path, manifest: GraphSnapshotManifest) -> None:
    """
    Persist a graph snapshot manifest to a snapshot directory.

    :param snapshot_dir: Graph snapshot directory.
    :type snapshot_dir: Path
    :param manifest: Snapshot manifest to write.
    :type manifest: GraphSnapshotManifest
    :return: None.
    :rtype: None
    """
    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")


def write_graph_latest_pointer(*, extractor_dir: Path, manifest: GraphSnapshotManifest) -> None:
    """
    Persist the latest pointer for a graph extractor.

    :param extractor_dir: Extractor directory containing snapshots.
    :type extractor_dir: Path
    :param manifest: Snapshot manifest used for the pointer.
    :type manifest: GraphSnapshotManifest
    :return: None.
    :rtype: None
    """
    latest_path = extractor_dir / "latest.json"
    latest_path.write_text(
        json.dumps(
            {"snapshot_id": manifest.snapshot_id, "created_at": manifest.created_at},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_graph_snapshot(
    corpus: Corpus,
    *,
    extractor_id: str,
    configuration_name: str,
    configuration: Dict[str, Any],
    extraction_snapshot: ExtractionSnapshotReference,
    max_items: Optional[int] = None,
    item_timeout_seconds: Optional[float] = 60.0,
    item_retry_attempts: int = 0,
    heartbeat_interval_seconds: float = 10.0,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> GraphSnapshotManifest:
    """
    Build a graph extraction snapshot for a corpus.

    :param corpus: Corpus to process.
    :type corpus: Corpus
    :param extractor_id: Graph extractor identifier.
    :type extractor_id: str
    :param configuration_name: Human configuration name.
    :type configuration_name: str
    :param configuration: Extractor configuration values.
    :type configuration: dict[str, Any]
    :param extraction_snapshot: Extraction snapshot reference.
    :type extraction_snapshot: ExtractionSnapshotReference
    :param max_items: Optional maximum number of extraction items to process.
    :type max_items: int or None
    :param item_timeout_seconds: Optional per-item extraction timeout in seconds.
        Non-positive values disable timeout enforcement.
    :type item_timeout_seconds: float or None
    :param item_retry_attempts: Number of retries after a failed extraction attempt.
    :type item_retry_attempts: int
    :param heartbeat_interval_seconds: Progress heartbeat cadence in seconds.
    :type heartbeat_interval_seconds: float
    :param progress_callback: Optional callback for progress events.
    :type progress_callback: collections.abc.Callable or None
    :return: Graph snapshot manifest.
    :rtype: GraphSnapshotManifest
    """
    snapshot_configuration = dict(configuration)
    execution_block = snapshot_configuration.pop("_execution", None)
    if not isinstance(execution_block, dict):
        execution_block = {}
    graph_execution = snapshot_configuration.pop("graph", None)
    if isinstance(graph_execution, dict):
        if "max_items" in graph_execution and max_items is None:
            max_items = int(graph_execution["max_items"])
        execution_block = {**graph_execution, **execution_block}
    if max_items is not None:
        execution_block["max_items"] = max_items

    extractor = get_graph_extractor(extractor_id)
    try:
        parsed_config = extractor.validate_config(snapshot_configuration)
    except ValidationError as exc:
        raise ValueError(f"Invalid graph extraction configuration: {exc}") from exc

    if max_items is None:
        execution_max_items = execution_block.get("max_items") if execution_block else None
        if execution_max_items is not None:
            max_items = int(execution_max_items)

    manifest_configuration = dict(snapshot_configuration)
    if execution_block:
        manifest_configuration["_execution"] = execution_block
    graph_id = create_graph_id(extractor_id=extractor_id, configuration=manifest_configuration)
    configuration_manifest = create_graph_configuration_manifest(
        extractor_id=extractor_id,
        name=configuration_name,
        configuration=manifest_configuration,
    )
    manifest = create_graph_snapshot_manifest(
        corpus,
        configuration=configuration_manifest,
        extraction_snapshot=extraction_snapshot,
        graph_id=graph_id,
    )
    extraction_manifest = corpus.load_extraction_snapshot_manifest(
        extractor_id=extraction_snapshot.extractor_id,
        snapshot_id=extraction_snapshot.snapshot_id,
    )
    extraction_items = list(extraction_manifest.items)
    if max_items is not None:
        if max_items <= 0:
            raise ValueError("max_items must be a positive integer")
        extraction_items = extraction_items[:max_items]
    timeout_seconds = float(item_timeout_seconds) if item_timeout_seconds is not None else None
    if timeout_seconds is not None and timeout_seconds <= 0:
        timeout_seconds = None
    retry_attempts = max(0, int(item_retry_attempts))
    heartbeat_seconds = max(0.0, float(heartbeat_interval_seconds))

    snapshot_dir = corpus.graph_snapshot_dir(
        extractor_id=extractor_id,
        snapshot_id=manifest.snapshot_id,
    )
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    settings = resolve_neo4j_settings()
    _emit_graph_progress(
        progress_callback,
        "starting",
        snapshot_id=manifest.snapshot_id,
        extractor_id=extractor_id,
        items_total=len(extraction_items),
        items_available=len(extraction_manifest.items),
    )
    driver = create_neo4j_driver(settings)

    node_total = 0
    edge_total = 0
    errored_total = 0
    timed_out_total = 0
    skipped_total = 0
    item_summaries: List[GraphExtractionItemSummary] = []
    started_monotonic = time.monotonic()
    last_heartbeat_monotonic = started_monotonic

    try:
        clear_graph_records(
            driver=driver,
            settings=settings,
            corpus_id=corpus.uri,
            graph_id=graph_id,
            extraction_snapshot=extraction_snapshot.as_string(),
        )
        for index, item_result in enumerate(extraction_items, start=1):
            last_heartbeat_monotonic = _maybe_emit_graph_heartbeat(
                progress_callback=progress_callback,
                snapshot_id=manifest.snapshot_id,
                extractor_id=extractor_id,
                items_total=len(extraction_items),
                items_available=len(extraction_manifest.items),
                item_index=index - 1,
                node_total=node_total,
                edge_total=edge_total,
                skipped_total=skipped_total,
                errored_total=errored_total,
                timed_out_total=timed_out_total,
                started_monotonic=started_monotonic,
                heartbeat_interval_seconds=heartbeat_seconds,
                last_heartbeat_monotonic=last_heartbeat_monotonic,
            )
            item = corpus.get_item(item_result.item_id)
            item_started_monotonic = time.monotonic()
            _emit_graph_progress(
                progress_callback,
                "processing",
                snapshot_id=manifest.snapshot_id,
                item_id=item.id,
                item_index=index,
                items_total=len(extraction_items),
                elapsed_ms=int((time.monotonic() - started_monotonic) * 1000),
            )
            try:
                extracted_text = _load_extracted_text(
                    corpus,
                    extraction_snapshot=extraction_snapshot,
                    item_result=item_result,
                )
                extraction_metadata = _load_extracted_metadata(
                    corpus,
                    extraction_snapshot=extraction_snapshot,
                    item_result=item_result,
                )
                if extracted_text is None:
                    skipped_total += 1
                    item_summaries.append(
                        GraphExtractionItemSummary(
                            item_id=item.id,
                            status="skipped",
                            node_count=0,
                            edge_count=0,
                            error_message="No extracted text",
                            error_reason="no_extracted_text",
                            duration_ms=int((time.monotonic() - item_started_monotonic) * 1000),
                            attempts=1,
                        )
                    )
                    _emit_graph_progress(
                        progress_callback,
                        "processed",
                        snapshot_id=manifest.snapshot_id,
                        item_id=item.id,
                        item_index=index,
                        items_total=len(extraction_items),
                        status="skipped",
                        nodes=node_total,
                        edges=edge_total,
                        attempts=1,
                        duration_ms=int((time.monotonic() - item_started_monotonic) * 1000),
                        error_reason="no_extracted_text",
                        elapsed_ms=int((time.monotonic() - started_monotonic) * 1000),
                    )
                    continue
                result, attempts = _run_extractor_with_retry(
                    extractor=extractor,
                    corpus=corpus,
                    item=item,
                    extracted_text=extracted_text,
                    extraction_metadata=extraction_metadata,
                    config=parsed_config,
                    timeout_seconds=timeout_seconds,
                    retry_attempts=retry_attempts,
                )
                if not isinstance(result, GraphExtractionResult):
                    raise ValueError("Graph extractor must return GraphExtractionResult")
                write_graph_records(
                    driver=driver,
                    settings=settings,
                    corpus_id=corpus.uri,
                    graph_id=graph_id,
                    extraction_snapshot=extraction_snapshot.as_string(),
                    item_id=item.id,
                    nodes=result.nodes,
                    edges=result.edges,
                )
                node_total += len(result.nodes)
                edge_total += len(result.edges)
                item_summaries.append(
                    GraphExtractionItemSummary(
                        item_id=item.id,
                        status="complete",
                        node_count=len(result.nodes),
                        edge_count=len(result.edges),
                        duration_ms=int((time.monotonic() - item_started_monotonic) * 1000),
                        attempts=attempts,
                    )
                )
                _emit_graph_progress(
                    progress_callback,
                    "processed",
                    snapshot_id=manifest.snapshot_id,
                    item_id=item.id,
                    item_index=index,
                    items_total=len(extraction_items),
                    status="complete",
                    nodes=node_total,
                    edges=edge_total,
                    attempts=attempts,
                    duration_ms=int((time.monotonic() - item_started_monotonic) * 1000),
                    elapsed_ms=int((time.monotonic() - started_monotonic) * 1000),
                )
            except _ExtractorExecutionError as exc:
                errored_total += 1
                if exc.reason == "timeout":
                    timed_out_total += 1
                duration_ms = int((time.monotonic() - item_started_monotonic) * 1000)
                item_summaries.append(
                    GraphExtractionItemSummary(
                        item_id=item.id,
                        status="error",
                        node_count=0,
                        edge_count=0,
                        error_message=str(exc),
                        error_reason=exc.reason,
                        duration_ms=duration_ms,
                        attempts=exc.attempts,
                    )
                )
                _emit_graph_progress(
                    progress_callback,
                    "processed",
                    snapshot_id=manifest.snapshot_id,
                    item_id=item.id,
                    item_index=index,
                    items_total=len(extraction_items),
                    status="error",
                    error_message=str(exc),
                    error_reason=exc.reason,
                    attempts=exc.attempts,
                    duration_ms=duration_ms,
                    nodes=node_total,
                    edges=edge_total,
                    elapsed_ms=int((time.monotonic() - started_monotonic) * 1000),
                )
            except ValueError as exc:
                if "Graph extractor must return GraphExtractionResult" in str(exc):
                    raise
                errored_total += 1
                duration_ms = int((time.monotonic() - item_started_monotonic) * 1000)
                item_summaries.append(
                    GraphExtractionItemSummary(
                        item_id=item.id,
                        status="error",
                        node_count=0,
                        edge_count=0,
                        error_message=str(exc),
                        error_reason="value_error",
                        duration_ms=duration_ms,
                        attempts=1,
                    )
                )
                _emit_graph_progress(
                    progress_callback,
                    "processed",
                    snapshot_id=manifest.snapshot_id,
                    item_id=item.id,
                    item_index=index,
                    items_total=len(extraction_items),
                    status="error",
                    error_message=str(exc),
                    error_reason="value_error",
                    attempts=1,
                    duration_ms=duration_ms,
                    nodes=node_total,
                    edges=edge_total,
                    elapsed_ms=int((time.monotonic() - started_monotonic) * 1000),
                )
            except Exception as exc:
                errored_total += 1
                duration_ms = int((time.monotonic() - item_started_monotonic) * 1000)
                item_summaries.append(
                    GraphExtractionItemSummary(
                        item_id=item.id,
                        status="error",
                        node_count=0,
                        edge_count=0,
                        error_message=str(exc),
                        error_reason="exception",
                        duration_ms=duration_ms,
                        attempts=1,
                    )
                )
                _emit_graph_progress(
                    progress_callback,
                    "processed",
                    snapshot_id=manifest.snapshot_id,
                    item_id=item.id,
                    item_index=index,
                    items_total=len(extraction_items),
                    status="error",
                    error_message=str(exc),
                    error_reason="exception",
                    attempts=1,
                    duration_ms=duration_ms,
                    nodes=node_total,
                    edges=edge_total,
                    elapsed_ms=int((time.monotonic() - started_monotonic) * 1000),
                )
    finally:
        driver.close()

    manifest.stats = {
        "items_total": len(extraction_items),
        "items_available": len(extraction_manifest.items),
        "items_processed": len(item_summaries),
        "items_skipped": skipped_total,
        "items_errored": errored_total,
        "items_timed_out": timed_out_total,
        "nodes": node_total,
        "edges": edge_total,
        "item_timeout_seconds": timeout_seconds,
        "item_retry_attempts": retry_attempts,
        "item_summaries": [summary.model_dump(mode="json") for summary in item_summaries],
    }
    _emit_graph_progress(
        progress_callback,
        "completed",
        snapshot_id=manifest.snapshot_id,
        extractor_id=extractor_id,
        items_total=len(extraction_items),
        items_available=len(extraction_manifest.items),
        items_processed=len(item_summaries),
        items_skipped=skipped_total,
        items_errored=errored_total,
        items_timed_out=timed_out_total,
        nodes=node_total,
        edges=edge_total,
        elapsed_ms=int((time.monotonic() - started_monotonic) * 1000),
    )
    write_graph_snapshot_manifest(snapshot_dir=snapshot_dir, manifest=manifest)
    write_graph_latest_pointer(extractor_dir=snapshot_dir.parent, manifest=manifest)
    return manifest


def _emit_graph_progress(
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    event: str,
    **payload: Any,
) -> None:
    if progress_callback is None:
        return
    progress_callback(event, payload)


class _ExtractorExecutionError(RuntimeError):
    def __init__(self, *, reason: str, message: str, attempts: int) -> None:
        super().__init__(message)
        self.reason = reason
        self.attempts = attempts


class _ItemExtractionTimeout(RuntimeError):
    pass


def _run_extractor_with_retry(
    *,
    extractor,
    corpus: Corpus,
    item,
    extracted_text: str,
    extraction_metadata: dict[str, Any] | None,
    config,
    timeout_seconds: float | None,
    retry_attempts: int,
) -> tuple[Any, int]:
    attempts = 0
    while True:
        attempts += 1
        try:
            with _item_timeout_guard(timeout_seconds):
                result = extractor.extract_graph(
                    corpus=corpus,
                    item=item,
                    extracted_text=extracted_text,
                    config=config,
                    extraction_metadata=extraction_metadata,
                )
            return result, attempts
        except _ItemExtractionTimeout as exc:
            if attempts <= retry_attempts:
                continue
            timeout_label = timeout_seconds if timeout_seconds is not None else "-"
            raise _ExtractorExecutionError(
                reason="timeout",
                message=f"item extraction timed out after {timeout_label}s (attempts={attempts})",
                attempts=attempts,
            ) from exc
        except Exception as exc:
            if attempts <= retry_attempts:
                continue
            reason = "value_error" if isinstance(exc, ValueError) else "exception"
            raise _ExtractorExecutionError(reason=reason, message=str(exc), attempts=attempts) from exc


@contextmanager
def _item_timeout_guard(timeout_seconds: float | None):
    if timeout_seconds is None or timeout_seconds <= 0:
        yield
        return
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    if not hasattr(signal, "setitimer"):
        yield
        return

    def _raise_timeout(_signum, _frame):
        raise _ItemExtractionTimeout(f"item extraction exceeded {timeout_seconds}s")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _maybe_emit_graph_heartbeat(
    *,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]],
    snapshot_id: str,
    extractor_id: str,
    items_total: int,
    items_available: int,
    item_index: int,
    node_total: int,
    edge_total: int,
    skipped_total: int,
    errored_total: int,
    timed_out_total: int,
    started_monotonic: float,
    heartbeat_interval_seconds: float,
    last_heartbeat_monotonic: float,
) -> float:
    if progress_callback is None or heartbeat_interval_seconds <= 0:
        return last_heartbeat_monotonic
    now = time.monotonic()
    if (now - last_heartbeat_monotonic) < heartbeat_interval_seconds:
        return last_heartbeat_monotonic
    _emit_graph_progress(
        progress_callback,
        "heartbeat",
        snapshot_id=snapshot_id,
        extractor_id=extractor_id,
        items_total=items_total,
        items_available=items_available,
        item_index=item_index,
        nodes=node_total,
        edges=edge_total,
        items_skipped=skipped_total,
        items_errored=errored_total,
        items_timed_out=timed_out_total,
        elapsed_ms=int((now - started_monotonic) * 1000),
    )
    return now


def _load_extracted_text(
    corpus: Corpus,
    *,
    extraction_snapshot: ExtractionSnapshotReference,
    item_result,
) -> Optional[str]:
    if not item_result.final_text_relpath:
        return None
    snapshot_dir = corpus.extraction_snapshot_dir(
        extractor_id=extraction_snapshot.extractor_id,
        snapshot_id=extraction_snapshot.snapshot_id,
    )
    text_path = snapshot_dir / item_result.final_text_relpath
    if not text_path.is_file():
        return None
    return text_path.read_text(encoding="utf-8")


def _load_extracted_metadata(
    corpus: Corpus,
    *,
    extraction_snapshot: ExtractionSnapshotReference,
    item_result,
) -> Optional[dict[str, Any]]:
    if not item_result.final_metadata_relpath:
        return None
    snapshot_dir = corpus.extraction_snapshot_dir(
        extractor_id=extraction_snapshot.extractor_id,
        snapshot_id=extraction_snapshot.snapshot_id,
    )
    metadata_path = snapshot_dir / item_result.final_metadata_relpath
    if not metadata_path.is_file():
        return None
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def load_graph_snapshot_manifest(
    corpus: Corpus, *, extractor_id: str, snapshot_id: str
) -> GraphSnapshotManifest:
    """
    Load a graph snapshot manifest from the corpus.

    :param corpus: Corpus containing the snapshot.
    :type corpus: Corpus
    :param extractor_id: Graph extractor identifier.
    :type extractor_id: str
    :param snapshot_id: Graph snapshot identifier.
    :type snapshot_id: str
    :return: Parsed snapshot manifest.
    :rtype: GraphSnapshotManifest
    :raises FileNotFoundError: If the manifest file does not exist.
    :raises ValueError: If the manifest data is invalid.
    """
    manifest_path = (
        corpus.graph_snapshot_dir(extractor_id=extractor_id, snapshot_id=snapshot_id)
        / "manifest.json"
    )
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing graph snapshot manifest: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return GraphSnapshotManifest.model_validate(data)


def export_graph_snapshot(
    corpus: Corpus, *, snapshot: GraphSnapshotReference
) -> GraphSnapshotExport:
    """
    Export graph snapshot contents from Neo4j as portable JSON records.

    :param corpus: Corpus containing the snapshot manifest.
    :type corpus: Corpus
    :param snapshot: Graph snapshot reference.
    :type snapshot: GraphSnapshotReference
    :return: Portable graph snapshot export.
    :rtype: GraphSnapshotExport
    """
    manifest = load_graph_snapshot_manifest(
        corpus,
        extractor_id=snapshot.extractor_id,
        snapshot_id=snapshot.snapshot_id,
    )
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        records = read_graph_records(
            driver=driver,
            settings=settings,
            corpus_id=corpus.uri,
            graph_id=manifest.graph_id,
            extraction_snapshot=manifest.extraction_snapshot,
        )
    finally:
        driver.close()

    nodes = [
        GraphExportNode(
            extractor_id=snapshot.extractor_id,
            snapshot_id=snapshot.snapshot_id,
            graph_id=manifest.graph_id,
            extraction_snapshot=manifest.extraction_snapshot,
            item_id=str(entry["item_id"]),
            node_id=str(entry["node_id"]),
            node_type=str(entry["node_type"]),
            label=str(entry["label"]),
            properties=dict(entry.get("properties") or {}),
        )
        for entry in sorted(
            records["nodes"],
            key=lambda item: (str(item.get("item_id", "")), str(item.get("node_id", ""))),
        )
    ]
    edges = [
        GraphExportEdge(
            extractor_id=snapshot.extractor_id,
            snapshot_id=snapshot.snapshot_id,
            graph_id=manifest.graph_id,
            extraction_snapshot=manifest.extraction_snapshot,
            item_id=str(entry["item_id"]),
            edge_id=str(entry["edge_id"]),
            src=str(entry["src"]),
            dst=str(entry["dst"]),
            edge_type=str(entry["edge_type"]),
            weight=float(entry.get("weight", 1.0)),
            properties=dict(entry.get("properties") or {}),
        )
        for entry in sorted(
            records["edges"],
            key=lambda item: (str(item.get("item_id", "")), str(item.get("edge_id", ""))),
        )
    ]
    return GraphSnapshotExport(
        snapshot=snapshot,
        manifest=manifest,
        nodes=nodes,
        edges=edges,
        stats={
            **manifest.stats,
            "exported_nodes": len(nodes),
            "exported_edges": len(edges),
        },
    )


def list_graph_snapshots(
    corpus: Corpus, *, extractor_id: Optional[str] = None
) -> List[GraphSnapshotListEntry]:
    """
    List graph snapshots stored under the corpus.

    :param corpus: Corpus containing the snapshots.
    :type corpus: Corpus
    :param extractor_id: Optional extractor identifier filter.
    :type extractor_id: str or None
    :return: Summary list entries for each snapshot.
    :rtype: list[GraphSnapshotListEntry]
    """
    snapshots_root = corpus.graph_snapshots_dir
    if not snapshots_root.is_dir():
        return []

    extractor_dirs: List[Path]
    if extractor_id is None:
        extractor_dirs = [path for path in sorted(snapshots_root.iterdir()) if path.is_dir()]
    else:
        extractor_path = snapshots_root / extractor_id
        extractor_dirs = [extractor_path] if extractor_path.is_dir() else []

    entries: List[GraphSnapshotListEntry] = []
    for extractor_dir in extractor_dirs:
        for snapshot_dir in sorted(extractor_dir.iterdir()):
            if not snapshot_dir.is_dir():
                continue
            manifest_path = snapshot_dir / "manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = load_graph_snapshot_manifest(
                    corpus,
                    extractor_id=extractor_dir.name,
                    snapshot_id=snapshot_dir.name,
                )
            except (FileNotFoundError, ValueError):
                continue
            entries.append(
                GraphSnapshotListEntry(
                    extractor_id=extractor_dir.name,
                    snapshot_id=snapshot_dir.name,
                    graph_id=manifest.graph_id,
                    configuration_id=manifest.configuration.configuration_id,
                    configuration_name=manifest.configuration.name,
                    catalog_generated_at=manifest.catalog_generated_at,
                    created_at=manifest.created_at,
                    stats=dict(manifest.stats),
                )
            )

    entries.sort(
        key=lambda entry: (entry.created_at, entry.extractor_id, entry.snapshot_id),
        reverse=True,
    )
    return entries


def latest_graph_snapshot_reference(
    corpus: Corpus, *, extractor_id: Optional[str] = None
) -> Optional[GraphSnapshotReference]:
    """
    Return the most recent graph snapshot reference.

    :param corpus: Corpus containing the snapshots.
    :type corpus: Corpus
    :param extractor_id: Optional extractor identifier filter.
    :type extractor_id: str or None
    :return: Latest graph snapshot reference or None when no snapshots exist.
    :rtype: GraphSnapshotReference or None
    """
    entries = list_graph_snapshots(corpus, extractor_id=extractor_id)
    if not entries:
        return None
    latest = entries[0]
    return GraphSnapshotReference(extractor_id=latest.extractor_id, snapshot_id=latest.snapshot_id)


def resolve_graph_snapshot_reference(corpus: Corpus, *, raw: str) -> GraphSnapshotReference:
    """
    Resolve a graph snapshot reference from a raw string.

    :param corpus: Corpus containing the snapshots.
    :type corpus: Corpus
    :param raw: Raw snapshot reference.
    :type raw: str
    :return: Parsed graph snapshot reference.
    :rtype: GraphSnapshotReference
    """
    return parse_graph_snapshot_reference(raw)
