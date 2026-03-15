import argparse
from pathlib import Path

import pytest

from biblicus import cli, migration


def test_cmd_download_unknown_dataset(capsys):
    args = argparse.Namespace(datasets="unknown", corpus_dir=Path("/tmp"), count=None, force=False)
    rc = cli.cmd_benchmark_download(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Unknown dataset" in out


def test_migration_missing_legacy(tmp_path):
    with pytest.raises(ValueError):
        migration.migrate_layout(corpus_root=tmp_path)
