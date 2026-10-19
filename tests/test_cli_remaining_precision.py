import argparse
from types import SimpleNamespace

import pytest

from biblicus.cli import benchmark as cli_benchmark
from biblicus.cli import common as cli_common


def test_normalize_extraction_configuration_bad_type():
    with pytest.raises(ValueError):
        cli_common._normalize_extraction_configuration({"extractor_id": 123, "configuration": {}})


def test_cmd_benchmark_download_unknown_dataset(capsys, tmp_path):
    args = SimpleNamespace(corpus=str(tmp_path), corpus_dir=str(tmp_path), datasets="weird", count=None, force=False)
    cli_benchmark.cmd_benchmark_download(args)
    out = capsys.readouterr().out
    assert "Unknown dataset" in out


def test_cmd_benchmark_run_unknown_category(tmp_path):
    # create dummy config file
    config_path = tmp_path / "bench.yaml"
    config_path.write_text(
        "benchmark_name: demo\ncategories: {}\npipelines: []\naggregate_weights: {}\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(config=str(config_path), pipelines=None, category="missing", output=None)
    with pytest.raises(ValueError):
        cli_benchmark.cmd_benchmark_run(args)
