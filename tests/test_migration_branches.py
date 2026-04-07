
from biblicus import migration


def test_migrate_layout_moves_legacy(tmp_path):
    root = tmp_path
    legacy = root / ".biblicus"
    legacy.mkdir()
    (legacy / "snapshots" / "extraction").mkdir(parents=True)
    (legacy / "snapshots" / "graph").mkdir(parents=True)
    (legacy / "snapshots" / "analysis").mkdir(parents=True)
    (legacy / "snapshots" / "evaluation").mkdir(parents=True)
    (legacy / "snapshots" / "retrieval").mkdir(parents=True)
    (legacy / "raw").mkdir()
    (legacy / "raw" / "a.txt").write_text("x")

    stats = migration.migrate_layout(corpus_root=root, force=True)
    assert stats["moved_raw_items"] == 1
    assert (root / "metadata" / "snapshots").exists() is False
    assert (root / "metadata" / "config.json").exists()
