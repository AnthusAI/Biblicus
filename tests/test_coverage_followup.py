from types import SimpleNamespace
from pathlib import Path

import pytest

from biblicus import cli
from biblicus.analysis import markov
from biblicus.analysis.models import MarkovAnalysisTextSourceConfig
from biblicus.corpus import Corpus
from biblicus.models import CatalogItem, RemoteCorpusSourceConfig
from biblicus.pipelines import _normalize_extraction_configuration


def test_markov_collect_documents_truncates_and_warns(tmp_path, monkeypatch):
    class FakeItem:
        def __init__(self, item_id: str, relpath: str, status: str = "extracted"):
            self.item_id = item_id
            self.final_text_relpath = relpath
            self.status = status

    manifest_items = [
        FakeItem("item-1", "text/1.txt"),
        FakeItem("item-2", "text/2.txt"),
        FakeItem("item-3", "text/3.txt"),
    ]

    for index, content in enumerate(["first doc", "second doc", ""], start=1):
        text_path = tmp_path / "text" / f"{index}.txt"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(content, encoding="utf-8")

    manifest = SimpleNamespace(items=manifest_items)

    class FakeCorpus:
        def __init__(self, root: Path):
            self.root = root

        def load_extraction_snapshot_manifest(self, extractor_id: str, snapshot_id: str):
            return manifest

        def extraction_snapshot_dir(self, extractor_id: str, snapshot_id: str) -> Path:
            return self.root

    config = MarkovAnalysisTextSourceConfig(sample_size=1)
    documents, report = markov._collect_documents(  # type: ignore[arg-type]
        corpus=FakeCorpus(tmp_path),
        extraction_snapshot=SimpleNamespace(extractor_id="pipeline", snapshot_id="snap"),
        config=config,
    )

    assert len(documents) == 1
    assert "Text collection truncated to sample_size" in report.warnings
    assert report.empty_texts == 1


def test_cli_benchmark_download_handles_unknown_and_pending(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("subprocess.run", lambda *a, **k: SimpleNamespace(returncode=0))
    arguments = SimpleNamespace(
        datasets="scanned-arxiv,unknown", corpus_dir=str(tmp_path), count=None, force=False
    )
    cli.cmd_benchmark_download(arguments)
    output = capsys.readouterr().out
    assert "scanned-arxiv dataset is not yet available" in output
    assert "Unknown dataset" in output


def test_cli_benchmark_status_uses_legacy_metadata_dir(tmp_path, capsys):
    corpus_dir = tmp_path / "datasets"
    meta_dir = corpus_dir / "funsd_benchmark" / "metadata"
    meta_dir.mkdir(parents=True)
    (meta_dir / "config.json").write_text("{}", encoding="utf-8")
    gt_dir = meta_dir / "funsd_ground_truth"
    gt_dir.mkdir(parents=True)
    (gt_dir / "sample.txt").write_text("ok", encoding="utf-8")

    arguments = SimpleNamespace(corpus_dir=str(corpus_dir))
    cli.cmd_benchmark_status(arguments)
    output = capsys.readouterr().out
    assert "READY (1 docs)" in output


def test_pipeline_normalize_rejects_bool_max_workers():
    with pytest.raises(ValueError):
        _normalize_extraction_configuration({"extractor_id": "x", "max_workers": True})


def test_corpus_remote_helpers(tmp_path):
    corpus = Corpus(tmp_path)
    source_config = RemoteCorpusSourceConfig(
        kind="s3", bucket="MyBucket", profile="my-profile"
    )
    assert corpus._resolve_remote_source_name(source_config) == "MyBucket"

    source = SimpleNamespace(etag="abc", last_modified=None)
    existing = CatalogItem(
        id="i1",
        relpath="imports/remote/sample/file.txt",
        sha256="",
        bytes=0,
        media_type="text/plain",
        title=None,
        tags=[],
        metadata={"biblicus": {"source_etag": "abc"}},
        created_at="now",
        source_uri="s3://bucket/file.txt",
    )
    assert corpus._remote_item_unchanged(existing, source)
