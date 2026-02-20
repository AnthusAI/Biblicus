from pathlib import Path

import pytest

from biblicus import migration


def test_migrate_layout_requires_legacy(tmp_path: Path):
    with pytest.raises(ValueError):
        migration.migrate_layout(corpus_root=tmp_path, force=False)


def test_migrate_layout_force_overwrites(tmp_path: Path):
    old = tmp_path / ".biblicus"
    new = tmp_path / "metadata"
    old.mkdir()
    (old / "raw").mkdir()
    (old / "raw" / "f.txt").write_text("x")
    new.mkdir()
    (new / "config.json").write_text("{}", encoding="utf-8")
    stats = migration.migrate_layout(corpus_root=tmp_path, force=True)
    assert stats["moved_raw_items"] == 1
    assert (tmp_path / "metadata" / "config.json").exists()
