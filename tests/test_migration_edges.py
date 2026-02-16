import json
from pathlib import Path

import pytest

import biblicus.migration as migration
from biblicus.constants import SCHEMA_VERSION


def _write_valid_legacy(meta_dir: Path):
    meta_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": SCHEMA_VERSION,
        "created_at": "now",
        "corpus_uri": "file://",
        "raw_dir": "raw",
    }
    # Minimal catalog matching CorpusCatalog: needs schema_version, generated_at, corpus_uri, items dict
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "now",
        "corpus_uri": "file://",
        "items": {},
    }
    (meta_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
    (meta_dir / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    (meta_dir / "snapshots").mkdir(exist_ok=True)


def test_migrate_layout_missing_legacy(tmp_path):
    with pytest.raises(ValueError):
        migration.migrate_layout(corpus_root=tmp_path)


def test_migrate_layout_force_overwrites(tmp_path):
    old_meta = tmp_path / ".biblicus"
    _write_valid_legacy(old_meta)
    (tmp_path / "metadata").mkdir()
    stats = migration.migrate_layout(corpus_root=tmp_path, force=True)
    assert stats["moved_retrieval_snapshots"] == 0


def test_migrate_retrieval_snapshots_handles_missing(tmp_path):
    stats = migration._migrate_retrieval_snapshots(
        snapshots_root=tmp_path / "snapshots",
        dest_root=tmp_path / "retrieval",
        force=False,
        stats={"moved_retrieval_snapshots": 0},
    )
    assert stats == 0
