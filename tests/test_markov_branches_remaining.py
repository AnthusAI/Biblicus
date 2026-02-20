from types import SimpleNamespace

from biblicus.analysis import markov


def test_markov_llm_observation_transient_after_retries(monkeypatch):
    attempts = {"count": 0}

    def fake_generate(client, system_prompt, user_prompt):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise Exception("timeout")
        return '{"label": "ok", "label_confidence": 0.6, "summary": "done"}'

    monkeypatch.setattr(markov, "generate_completion", fake_generate)
    monkeypatch.setattr(markov, "_parse_json_object", lambda text, error_label: {"label": "ok", "label_confidence": 0.6, "summary": "done"})
    monkeypatch.setattr(markov.time, "sleep", lambda *_: None)
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
    segments = [markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="body")]
    observations = markov._build_observations(segments=segments, config=config, cache_context=None)
    assert attempts["count"] == 3
    assert observations[0].llm_label == "ok"


def test_markov_collect_documents_warns_sample(monkeypatch, tmp_path):
    run_root = tmp_path / "snap"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "a.txt").write_text("", encoding="utf-8")
    manifest = SimpleNamespace(
        items=[SimpleNamespace(item_id="a", status="extracted", final_text_relpath="a.txt")]
    )

    class DummyCorpus:
        def __init__(self, root, manifest):
            self.root = root
            self.manifest = manifest
            self.meta_dir = root

        def load_extraction_snapshot_manifest(self, extractor_id, snapshot_id):
            return self.manifest

        def extraction_snapshot_dir(self, extractor_id, snapshot_id):
            return self.root

    corpus = DummyCorpus(run_root, manifest)
    docs, report = markov._collect_documents(
        corpus=corpus,
        extraction_snapshot=SimpleNamespace(extractor_id="e", snapshot_id="s"),
        config=SimpleNamespace(sample_size=1, min_text_characters=None),
    )
    assert report.empty_texts == 1
