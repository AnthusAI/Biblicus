import json
from pathlib import Path

import pytest

from biblicus.migration import (
    _migrate_retrieval_snapshots,
    _move_entry,
    migrate_layout,
)


def _write_manifest(path: Path, retriever_id: str, snapshot_id: str, artifacts: list[str]) -> None:
    snapshot = {
        "snapshot_id": snapshot_id,
        "created_at": "2024-01-01T00:00:00Z",
        "catalog_generated_at": "2024-01-01T00:00:00Z",
        "corpus_uri": path.parent.as_uri(),
        "configuration": {
            "configuration_id": "cfg-1",
            "retriever_id": retriever_id,
            "name": "config",
            "created_at": "2024-01-01T00:00:00Z",
            "configuration": {},
            "description": None,
        },
        "snapshot_artifacts": artifacts,
        "stats": {},
    }
    path.write_text(json.dumps(snapshot), encoding="utf-8")


def test_migrate_layout_metadata_exists_without_force(tmp_path: Path):
    legacy_meta = tmp_path / ".biblicus"
    legacy_meta.mkdir()
    (tmp_path / "metadata").mkdir()
    with pytest.raises(ValueError, match="metadata/ already exists"):
        migrate_layout(corpus_root=tmp_path, force=False)


def test_move_entry_overwrites_when_forced(tmp_path: Path):
    src_file = tmp_path / "src.txt"
    dest_file = tmp_path / "dest.txt"
    src_file.write_text("new")
    dest_file.write_text("old")
    _move_entry(src_file, dest_file, force=True)
    assert dest_file.read_text() == "new"

    # Overwrite a directory with a file to cover the directory removal branch.
    src_file2 = tmp_path / "src2.txt"
    dest_dir = tmp_path / "dest_dir"
    dest_dir.mkdir()
    src_file2.write_text("content")
    _move_entry(src_file2, dest_dir, force=True)
    assert dest_dir.is_file()


def test_move_entry_raises_without_force(tmp_path: Path):
    src = tmp_path / "src.txt"
    dest = tmp_path / "dest.txt"
    src.write_text("new")
    dest.write_text("existing")
    with pytest.raises(FileExistsError):
        _move_entry(src, dest, force=False)


def test_migrate_retrieval_snapshots_missing_artifact_force_false(tmp_path: Path):
    snapshots_root = tmp_path / "snapshots"
    snapshots_root.mkdir()
    manifest = snapshots_root / "run.json"
    _write_manifest(manifest, "retriever", "snap-1", [".biblicus/retrieval/artifact.json"])
    with pytest.raises(FileNotFoundError):
        _migrate_retrieval_snapshots(
            snapshots_root, tmp_path / "retrieval", force=False, stats={"updated_snapshot_artifacts": 0}
        )


def test_migrate_retrieval_snapshots_missing_artifact_force_true(tmp_path: Path):
    snapshots_root = tmp_path / "snapshots"
    snapshots_root.mkdir()
    manifest = snapshots_root / "run.json"
    _write_manifest(manifest, "retriever", "snap-1", [".biblicus/retrieval/artifact.json"])
    stats = {"updated_snapshot_artifacts": 0}
    moved = _migrate_retrieval_snapshots(
        snapshots_root, tmp_path / "retrieval", force=True, stats=stats
    )
    assert moved == 1
    latest = tmp_path / "retrieval" / "retriever" / "latest.json"
    assert latest.is_file()
    # Ensure non-file entries in snapshots are skipped (line 145 continue branch).
    (snapshots_root / "ignored_dir").mkdir()
    _migrate_retrieval_snapshots(snapshots_root, tmp_path / "retrieval2", force=True, stats=stats)


def test_migrate_snapshots_evaluation_branch(tmp_path: Path):
    legacy_meta = tmp_path / ".biblicus"
    snapshots_root = legacy_meta / "snapshots"
    evaluation_root = snapshots_root / "evaluation"
    evaluation_root.mkdir(parents=True)
    # Required legacy config and catalog so migrate_layout can validate.
    (legacy_meta / "config.json").write_text(
        json.dumps(
            {
                "raw_dir": "raw",
                "schema_version": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "corpus_uri": tmp_path.as_uri(),
            }
        ),
        encoding="utf-8",
    )
    (legacy_meta / "catalog.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "generated_at": "2024-01-01T00:00:00Z",
                "corpus_uri": tmp_path.as_uri(),
                "raw_dir": "raw",
                "items": {},
                "order": [],
            }
        ),
        encoding="utf-8",
    )

    stats = migrate_layout(corpus_root=tmp_path, force=True)
    expected_dest = tmp_path / "analysis" / "evaluation"
    assert expected_dest.is_dir()
    assert stats["moved_retrieval_snapshots"] == 0


def test_select_latest_manifest_invalid_and_valid(tmp_path: Path):
    extractor_dir = tmp_path / "extracted" / "text"
    invalid_snapshot = extractor_dir / "snap-invalid"
    invalid_snapshot.mkdir(parents=True)
    (invalid_snapshot / "manifest.json").write_text(json.dumps({"created_at": 1}))

    valid_snapshot = extractor_dir / "snap-valid"
    valid_snapshot.mkdir(parents=True)
    (valid_snapshot / "manifest.json").write_text(
        json.dumps({"created_at": "2024-01-02T00:00:00Z", "snapshot_id": "snap-valid"})
    )

    from biblicus.migration import _select_latest_manifest

    latest = _select_latest_manifest(extractor_dir)
    assert latest == {"snapshot_id": "snap-valid", "created_at": "2024-01-02T00:00:00Z"}


def test_update_config_and_catalog(tmp_path: Path):
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir()
    config_path = meta_dir / "config.json"
    catalog_path = meta_dir / "catalog.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "corpus_uri": tmp_path.as_uri(),
                "raw_dir": "raw",
            }
        ),
        encoding="utf-8",
    )
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "generated_at": "2024-01-01T00:00:00Z",
                "corpus_uri": tmp_path.as_uri(),
                "raw_dir": "raw",
                "items": {
                    "item1": {
                        "id": "item1",
                        "relpath": "raw/file.txt",
                        "sha256": "0" * 64,
                        "bytes": 1,
                        "media_type": "text/plain",
                        "title": None,
                        "tags": [],
                        "metadata": {},
                        "created_at": "2024-01-01T00:00:00Z",
                        "source_uri": None,
                    }
                },
                "order": ["item1"],
            }
        ),
        encoding="utf-8",
    )

    stats = {"updated_catalog_items": 0}
    from biblicus.migration import _update_config_and_catalog

    _update_config_and_catalog(meta_dir=meta_dir, stats=stats)
    assert stats["updated_catalog_items"] == 1
    updated_config = json.loads(config_path.read_text())
    updated_catalog = json.loads(catalog_path.read_text())
    assert updated_config["raw_dir"] == "."
    assert updated_catalog["items"]["item1"]["relpath"] == "file.txt"


def test_migrate_raw_items_and_snapshot_edges(tmp_path: Path):
    # Cover _migrate_raw_items removing the old folder.
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "a.txt").write_text("a")
    stats = {"moved_raw_items": 0}
    from biblicus.migration import _migrate_raw_items

    _migrate_raw_items(root=tmp_path, force=True, stats=stats)
    assert stats["moved_raw_items"] == 1
    assert not raw_dir.exists()

    # Cover _move_snapshot_tree skip branches.
    source_root = tmp_path / "snapshots" / "extraction"
    source_root.mkdir(parents=True)
    (source_root / "notadir.txt").write_text("x")  # skipped at extractor level
    extractor_dir = source_root / "extractor"
    extractor_dir.mkdir()
    (extractor_dir / "file.txt").write_text("y")  # skipped at snapshot level
    from biblicus.migration import _move_snapshot_tree

    moved = _move_snapshot_tree(source_root, tmp_path / "dest", force=True)
    assert moved == 0

    # Cover _write_latest_pointers skipping non-dir entries.
    from biblicus.migration import _write_latest_pointers

    dest_root = tmp_path / "dest"
    dest_root.mkdir(parents=True, exist_ok=True)
    (dest_root / "junk.txt").write_text("z")
    _write_latest_pointers(dest_root)

    # Create a manifest with missing snapshot_id to exercise continue in _select_latest_manifest.
    extractor_root = dest_root / "extractor"
    extractor_root.mkdir()
    snap_dir = extractor_root / "snap1"
    snap_dir.mkdir()
    (snap_dir / "manifest.json").write_text(json.dumps({"created_at": "2024-01-01"}))
    _write_latest_pointers(dest_root)

    # Cover _migrate_snapshots cleanup branches.
    meta_dir = tmp_path / "metadata"
    snapshots_root = meta_dir / "snapshots"
    retrieval_dir = snapshots_root / "retrieval"
    retrieval_dir.mkdir(parents=True)
    stats_full = {
        "moved_raw_items": 0,
        "moved_extraction_snapshots": 0,
        "moved_graph_snapshots": 0,
        "moved_analysis_runs": 0,
        "moved_retrieval_snapshots": 0,
        "updated_catalog_items": 0,
        "updated_snapshot_artifacts": 0,
    }
    from biblicus.migration import _migrate_snapshots

    _migrate_snapshots(root=tmp_path, meta_dir=meta_dir, force=True, stats=stats_full)


def test_migration_branch_coverage_additional(tmp_path: Path):
    # _migrate_raw_items early return when directory is missing.
    stats = {"moved_raw_items": 0}
    from biblicus.migration import _migrate_raw_items, _migrate_retrieval_snapshots, _update_config_and_catalog, _select_latest_manifest

    _migrate_raw_items(root=tmp_path, force=True, stats=stats)
    assert stats["moved_raw_items"] == 0

    # _migrate_retrieval_snapshots skip non-file manifest entries (line 145).
    snapshots_root = tmp_path / "snapshots"
    snapshots_root.mkdir()
    (snapshots_root / "dir.json").mkdir()
    stats2 = {"updated_snapshot_artifacts": 0}
    moved = _migrate_retrieval_snapshots(snapshots_root, tmp_path / "retrieval", force=True, stats=stats2)
    assert moved == 0

    # _update_config_and_catalog branches when files are absent.
    stats3 = {"updated_catalog_items": 0}
    _update_config_and_catalog(meta_dir=tmp_path, stats=stats3)
    assert stats3["updated_catalog_items"] == 0

    # _select_latest_manifest returns None on empty directory (line 266 path).
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert _select_latest_manifest(empty_dir) is None
