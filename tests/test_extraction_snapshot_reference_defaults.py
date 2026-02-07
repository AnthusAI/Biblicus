"""
Unit tests for default extraction snapshot resolution in retrievers.
"""

from __future__ import annotations

import json

import pytest

from biblicus.corpus import Corpus
from biblicus.models import ExtractionSnapshotReference
from biblicus.retrievers.scan import (
    ScanConfiguration,
)
from biblicus.retrievers.scan import (
    _resolve_extraction_reference as resolve_scan,
)
from biblicus.retrievers.sqlite_full_text_search import (
    SqliteFullTextSearchConfiguration,
)
from biblicus.retrievers.sqlite_full_text_search import (
    _resolve_extraction_reference as resolve_sqlite,
)
from biblicus.retrievers.tf_vector import (
    TfVectorConfiguration,
)
from biblicus.retrievers.tf_vector import (
    _resolve_extraction_reference as resolve_tf_vector,
)


def _write_extraction_snapshot(
    corpus_root,
    *,
    extractor_id: str,
    snapshot_id: str,
    created_at: str,
) -> None:
    """
    Write a minimal extraction snapshot manifest into a corpus directory.

    :param corpus_root: Root path for the corpus.
    :type corpus_root: pathlib.Path
    :param extractor_id: Extractor identifier to place under the extraction snapshots directory.
    :type extractor_id: str
    :param snapshot_id: Snapshot identifier directory name.
    :type snapshot_id: str
    :param created_at: International Organization for Standardization 8601 timestamp.
    :type created_at: str
    :return: None.
    :rtype: None
    """
    snapshot_dir = corpus_root / "extracted" / extractor_id / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "snapshot_id": snapshot_id,
        "configuration": {
            "configuration_id": f"config-{extractor_id}",
            "extractor_id": extractor_id,
            "name": "test",
            "created_at": created_at,
            "configuration": {},
        },
        "corpus_uri": corpus_root.as_uri(),
        "catalog_generated_at": created_at,
        "created_at": created_at,
        "items": [],
        "stats": {},
    }
    (snapshot_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_default_extraction_snapshot_reference_is_latest(tmp_path):
    """
    When not configured, retrievers should default to the latest extraction snapshot.
    """
    corpus = Corpus(tmp_path)
    _write_extraction_snapshot(
        tmp_path, extractor_id="extractor", snapshot_id="old", created_at="2026-02-01T00:00:00Z"
    )
    _write_extraction_snapshot(
        tmp_path,
        extractor_id="extractor",
        snapshot_id="new",
        created_at="2026-02-02T00:00:00Z",
    )

    expected = ExtractionSnapshotReference(extractor_id="extractor", snapshot_id="new")

    assert resolve_tf_vector(corpus, TfVectorConfiguration.model_validate({})) == expected
    assert resolve_scan(corpus, ScanConfiguration.model_validate({})) == expected
    assert resolve_sqlite(corpus, SqliteFullTextSearchConfiguration.model_validate({})) == expected


def test_explicit_extraction_snapshot_reference_requires_directory(tmp_path):
    """
    Explicit extraction snapshot references must exist on disk.
    """
    corpus = Corpus(tmp_path)
    configuration = TfVectorConfiguration.model_validate(
        {"extraction_snapshot": "extractor:missing"}
    )
    with pytest.raises(FileNotFoundError, match="Missing extraction snapshot"):
        resolve_tf_vector(corpus, configuration)
