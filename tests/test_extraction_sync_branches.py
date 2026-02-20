import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from biblicus.extraction import build_extraction_snapshot
from biblicus.models import CorpusCatalog
from biblicus.corpus import Corpus


def test_extraction_auto_sync_warns(monkeypatch, tmp_path: Path, capsys):
    corpus = Corpus(tmp_path)
    corpus.meta_dir.mkdir(parents=True, exist_ok=True)
    catalog = CorpusCatalog(
        schema_version=2,
        generated_at="2024-01-01T00:00:00Z",
        corpus_uri=tmp_path.as_uri(),
        raw_dir="raw",
        items={},
        order=[],
    )
    corpus._write_catalog(catalog)
    (corpus.root / "catalog.json").write_text("{}", encoding="utf-8")

    manifest = SimpleNamespace(snapshot_id="snap", configuration_id="cfg", items=[], stats={}, schema_version=1)
    monkeypatch.setattr("biblicus.extraction.load_or_build_extraction_snapshot", lambda *a, **k: manifest)
    monkeypatch.setattr("biblicus.extraction.utc_now_iso", lambda: "now")

    class FakePublisher:
        def __init__(self, name):
            self.name = name

        def sync_catalog(self, path, force=False):
            return SimpleNamespace(skipped=False, created=1, updated=0, deleted=0)

    monkeypatch.setitem(
        sys.modules, "biblicus.sync.amplify_publisher", SimpleNamespace(AmplifyPublisher=FakePublisher)
    )
    monkeypatch.setenv("AMPLIFY_AUTO_SYNC_CATALOG", "true")

    build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="cfg",
        configuration={"stages": [{"extractor_id": "pass-through-text", "config": {}}]},
    )
    err = capsys.readouterr().err
    assert "Synced catalog" in err


def test_extraction_auto_sync_handles_failure(monkeypatch, tmp_path: Path, capsys):
    corpus = Corpus(tmp_path)
    corpus.meta_dir.mkdir(parents=True, exist_ok=True)
    catalog = CorpusCatalog(
        schema_version=2,
        generated_at="2024-01-01T00:00:00Z",
        corpus_uri=tmp_path.as_uri(),
        raw_dir="raw",
        items={},
        order=[],
    )
    corpus._write_catalog(catalog)
    (corpus.root / "catalog.json").write_text("{}", encoding="utf-8")

    manifest = SimpleNamespace(snapshot_id="snap", configuration_id="cfg", items=[], stats={}, schema_version=1)
    monkeypatch.setattr("biblicus.extraction.load_or_build_extraction_snapshot", lambda *a, **k: manifest)
    monkeypatch.setattr("biblicus.extraction.utc_now_iso", lambda: "now")

    class FakePublisher:
        def __init__(self, name):
            self.name = name

        def sync_catalog(self, path, force=False):
            raise RuntimeError("sync boom")

    monkeypatch.setitem(
        sys.modules, "biblicus.sync.amplify_publisher", SimpleNamespace(AmplifyPublisher=FakePublisher)
    )
    monkeypatch.setenv("AMPLIFY_AUTO_SYNC_CATALOG", "true")

    build_extraction_snapshot(
        corpus,
        extractor_id="pipeline",
        configuration_name="cfg",
        configuration={"stages": [{"extractor_id": "pass-through-text", "config": {}}]},
    )
    err = capsys.readouterr().err
    assert "Catalog sync failed" in err
