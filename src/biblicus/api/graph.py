"""
Typed request and function for the ``graph extract`` command.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import Field

from ..configuration import (
    apply_dotted_overrides,
    load_configuration_view,
    parse_dotted_overrides,
)
from ..graph.models import GraphSnapshotManifest
from ..models import ExtractionSnapshotReference
from ._common import ApiRequestModel, open_request_corpus


class GraphExtractRequest(ApiRequestModel):
    """
    Request to build a graph extraction snapshot.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar extractor_id: Graph extractor identifier, for example ``cooccurrence``.
    :vartype extractor_id: str
    :ivar extraction_snapshot: Extraction snapshot supplying item text.
    :vartype extraction_snapshot: ExtractionSnapshotReference
    :ivar configuration_name: Human-readable configuration name that keys the snapshot identity.
    :vartype configuration_name: str
    :ivar configuration_paths: Configuration YAML paths; later files override earlier ones.
    :vartype configuration_paths: list[str]
    :ivar overrides: ``key=value`` overrides applied after composing configurations.
    :vartype overrides: list[str]
    :ivar max_items: Maximum extraction items to process, or None for all.
    :vartype max_items: int or None
    :ivar item_timeout_seconds: Per-item timeout in seconds; zero or less disables the timeout.
    :vartype item_timeout_seconds: float
    :ivar item_retry_attempts: Retries per item after a timeout or error.
    :vartype item_retry_attempts: int
    :ivar heartbeat_interval_seconds: Progress heartbeat interval; zero or less disables it.
    :vartype heartbeat_interval_seconds: float
    """

    corpus_path: str = Field(min_length=1)
    extractor_id: str = Field(min_length=1)
    extraction_snapshot: ExtractionSnapshotReference
    configuration_name: str = Field(default="default", min_length=1)
    configuration_paths: List[str] = Field(default_factory=list)
    overrides: List[str] = Field(default_factory=list)
    max_items: Optional[int] = None
    item_timeout_seconds: float = 60.0
    item_retry_attempts: int = Field(default=0, ge=0)
    heartbeat_interval_seconds: float = 10.0


def graph_extract(
    request: GraphExtractRequest,
    *,
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> GraphSnapshotManifest:
    """
    Build a graph extraction snapshot.

    :param request: Validated request.
    :type request: GraphExtractRequest
    :param progress_callback: Optional callback receiving progress event names and payloads.
    :type progress_callback: collections.abc.Callable or None
    :return: Graph snapshot manifest.
    :rtype: GraphSnapshotManifest
    """
    from ..graph import extraction as graph_extraction_module

    corpus = open_request_corpus(request.corpus_path)
    base_configuration: Dict[str, object] = {}
    if request.configuration_paths:
        base_configuration = load_configuration_view(
            request.configuration_paths,
            configuration_label="Graph extraction configuration",
            mapping_error_message="Graph extraction configuration must be a mapping/object",
        )
    configuration = apply_dotted_overrides(
        base_configuration, parse_dotted_overrides(request.overrides)
    )
    return graph_extraction_module.build_graph_snapshot(
        corpus,
        extractor_id=request.extractor_id,
        configuration_name=request.configuration_name,
        configuration=configuration,
        extraction_snapshot=request.extraction_snapshot,
        max_items=request.max_items,
        item_timeout_seconds=request.item_timeout_seconds,
        item_retry_attempts=request.item_retry_attempts,
        heartbeat_interval_seconds=request.heartbeat_interval_seconds,
        progress_callback=progress_callback,
    )
