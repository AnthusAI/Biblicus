from types import SimpleNamespace
import json
from pathlib import Path

import pytest

from biblicus import cli
from biblicus.analysis import markov
from biblicus.analysis.models import (
    MarkovAnalysisObservation,
    MarkovAnalysisTextSourceConfig,
)
from biblicus.corpus import Corpus, _update_biblicus_block
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


def test_corpus_update_biblicus_block_handles_non_mapping():
    data = {"biblicus": "not-a-dict"}
    updated = _update_biblicus_block(data, {"source_etag": "x"})
    assert isinstance(updated["biblicus"], dict)
    assert updated["biblicus"]["source_etag"] == "x"


def test_corpus_raw_prefix_respects_custom_and_dot(tmp_path):
    meta = tmp_path / ".biblicus"
    meta.mkdir()
    base_config = {
        "schema_version": 2,
        "created_at": "2024-01-01T00:00:00Z",
        "corpus_uri": tmp_path.as_uri(),
    }
    (meta / "config.json").write_text(
        json.dumps({**base_config, "raw_dir": "custom"}), encoding="utf-8"
    )
    corpus = Corpus(tmp_path)
    assert corpus._raw_prefix_for_storage("remote") == Path("custom") / "remote"

    (meta / "config.json").write_text(
        json.dumps({**base_config, "raw_dir": "."}), encoding="utf-8"
    )
    corpus = Corpus(tmp_path)
    assert corpus._raw_prefix_for_storage("remote").as_posix() == "remote"


def test_cli_benchmark_download_force_and_error(monkeypatch, capsys, tmp_path):
    called = {}

    def fake_run(cmd, capture_output):
        called["cmd"] = cmd
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr("subprocess.run", fake_run)
    arguments = SimpleNamespace(
        datasets="funsd", corpus_dir=str(tmp_path), count=2, force=True
    )
    cli.cmd_benchmark_download(arguments)
    out = capsys.readouterr().out
    assert "ERROR: Failed to download funsd" in out
    assert "--count" in " ".join(called["cmd"])
    assert "--force" in " ".join(called["cmd"])


def test_cli_benchmark_status_downloaded_but_not_ready(tmp_path, capsys):
    corpus_dir = tmp_path / "datasets"
    meta_dir = corpus_dir / "sroie_benchmark" / ".biblicus"
    meta_dir.mkdir(parents=True)
    (meta_dir / "config.json").write_text("{}", encoding="utf-8")

    arguments = SimpleNamespace(corpus_dir=str(corpus_dir))
    cli.cmd_benchmark_status(arguments)
    out = capsys.readouterr().out
    assert "sroie" in out and "DOWNLOADED" in out


def test_markov_span_markup_chunks_multiple_iterations(monkeypatch):
    spans = [SimpleNamespace(text="first"), SimpleNamespace(text="second")]
    monkeypatch.setattr(
        markov,
        "apply_text_extract",
        lambda request: SimpleNamespace(spans=spans),
    )
    markup_config = SimpleNamespace(
        label_attribute=None,
        prepend_label=False,
        chunk_characters=5,
        chunk_overlap_characters=2,
        system_prompt=None,
        prompt_template="extract",
        max_rounds=1,
        max_edits_per_round=1,
        normalize_nested_spans=False,
        client={"provider": "openai", "model": "gpt-4o"},
    )
    segmentation = SimpleNamespace(span_markup=markup_config, llm=SimpleNamespace())
    config = SimpleNamespace(segmentation=segmentation)
    segments = markov._span_markup_segments(
        item_id="item-1", text="abcdefghij", config=config  # len>chunk size to iterate
    )
    assert len(segments) >= 2


def test_markov_llm_observation_retries_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_generate_completion(client, system_prompt, user_prompt):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ValueError("Rate limit temporary")
        return json.dumps({"label": "x", "label_confidence": 0.5, "summary": "ok"})

    monkeypatch.setattr(markov, "generate_completion", fake_generate_completion)
    monkeypatch.setattr(markov, "_parse_json_object", lambda text, error_label: json.loads(text))
    config = SimpleNamespace(
        llm_observations=SimpleNamespace(
            enabled=True,
            client=SimpleNamespace(response_format=None),
            prompt_template="{segment}",
            system_prompt=None,
            cache=SimpleNamespace(enabled=False),
            max_workers=1,
        ),
        embeddings=SimpleNamespace(enabled=False),
    )
    segments = [SimpleNamespace(item_id="i", segment_index=1, text="hello")]
    observations = markov._build_observations(
        segments=segments,
        config=config,
        cache_context=None,
    )
    assert observations[0].llm_label == "x"
    assert calls["count"] == 2
