import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from biblicus import cli


def test_normalize_extraction_configuration_invalid_max_workers():
    with pytest.raises(ValueError):
        cli._normalize_extraction_configuration({"extractor_id": "x", "configuration": {}, "max_workers": True})


def test_cmd_benchmark_download_unknown(monkeypatch, tmp_path, capsys):
    args = SimpleNamespace(corpus=str(tmp_path), corpus_dir=str(tmp_path), datasets="unknown", count=None, force=False)
    cli.cmd_benchmark_download(args)
    out = capsys.readouterr().out
    assert "Unknown dataset" in out


def test_cmd_benchmark_run_missing_config(tmp_path):
    args = argparse.Namespace(config=str(tmp_path / "missing.yaml"), pipelines=None, category=None, output=None)
    with pytest.raises(FileNotFoundError):
        cli.cmd_benchmark_run(args)
