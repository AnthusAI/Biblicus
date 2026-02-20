from pathlib import Path
from types import SimpleNamespace

import pytest

from biblicus import pipelines
from biblicus.models import CorpusCatalog
from biblicus.corpus import Corpus


def test_normalize_extraction_configuration_validates_max_workers():
    with pytest.raises(ValueError):
        pipelines._normalize_extraction_configuration({"max_workers": 0})
    with pytest.raises(ValueError):
        pipelines._normalize_extraction_configuration({"max_workers": True})
    extractor_id, config, workers = pipelines._normalize_extraction_configuration(
        {"extractor_id": "pass-through-text", "configuration": {"foo": "bar"}}
    )
    assert extractor_id == "pipeline"
    assert config["stages"][0]["extractor_id"] == "pass-through-text"
    assert workers is None


def test_run_retrieval_executes_plan(monkeypatch, tmp_path):
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

    called = {"execute": False, "snapshot": False}

    class DummyPlan:
        status = "pending"
        root = SimpleNamespace(reason=None)

        def execute(self, mode, handler_registry):
            called["execute"] = True

    class DummyRetriever:
        def build_snapshot(self, corpus, configuration_name, configuration):
            called["snapshot"] = True
            return SimpleNamespace(snapshot_id="sid")

    monkeypatch.setattr(pipelines, "load_configuration_view", lambda *a, **k: {})
    monkeypatch.setattr(pipelines, "get_retriever", lambda rid: DummyRetriever())
    monkeypatch.setattr(pipelines, "build_plan_for_index", lambda *a, **k: DummyPlan())
    monkeypatch.setattr(pipelines, "build_default_handler_registry", lambda corpus: {})

    config = SimpleNamespace(retriever="scan", configuration=tmp_path / "retrieval.yml")
    snapshot = pipelines._run_retrieval(corpus, config)
    assert called["execute"] and called["snapshot"]
    assert snapshot.snapshot_id == "sid"


def test_run_analysis_loads_configuration(monkeypatch, tmp_path):
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

    loaded = {}

    monkeypatch.setattr(
        pipelines,
        "load_configuration_view",
        lambda *args, **kwargs: loaded.setdefault("config", {"k": "v"}),
    )

    class DummyBackend:
        def run_analysis(self, corpus, configuration_name, configuration):
            loaded["ran"] = (configuration_name, configuration)

    monkeypatch.setattr(pipelines, "get_analysis_backend", lambda kind: DummyBackend())

    analysis_config = SimpleNamespace(kind="markov", configuration=tmp_path / "analysis.yml")
    pipelines._run_analysis(
        corpus,
        analysis_configs=[analysis_config],
        extraction_snapshot=SimpleNamespace(extractor_id="ext", snapshot_id="snap"),
    )
    assert loaded["ran"][0] == "analysis"
    assert loaded["ran"][1] == {"k": "v"}
