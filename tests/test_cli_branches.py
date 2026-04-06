import argparse

from biblicus import cli
from biblicus.models import ExtractionSnapshotReference
from biblicus.corpus import Corpus


def test_get_or_build_extraction_snapshot_reuses_latest(monkeypatch, tmp_path):
    corpus = Corpus(tmp_path)
    corpus.meta_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir = corpus.extraction_snapshot_dir(extractor_id="pipeline", snapshot_id="snap")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        Corpus, "latest_extraction_snapshot_reference", lambda self, extractor_id=None: ExtractionSnapshotReference(extractor_id="pipeline", snapshot_id="snap")
    )
    ref = cli._get_or_build_extraction_snapshot(
        corpus=corpus,
        recipe_path=tmp_path / "recipe.yml",
        analysis_label="analysis",
    )
    assert ref.snapshot_id == "snap"


def test_cmd_benchmark_download_handles_unknown(tmp_path, capsys):
    arguments = argparse.Namespace(datasets=["unknown"], corpus_dir=tmp_path, count=None, force=False)
    result = cli.cmd_benchmark_download(arguments)
    out = capsys.readouterr().out
    assert "Unknown dataset" in out
    assert result == 0
