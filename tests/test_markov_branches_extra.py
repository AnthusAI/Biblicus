from pathlib import Path
from types import SimpleNamespace
import json

from biblicus.analysis import markov
from biblicus.analysis.models import MarkovAnalysisConfiguration, MarkovAnalysisTextSourceConfig
from biblicus.models import ExtractionSnapshotReference


def test_markov_span_markup_falls_back_to_llm(monkeypatch):
    # Force span_markup to raise non-transient error so llm segmentation is used.
    monkeypatch.setattr(
        markov,
        "apply_text_extract",
        lambda request: (_ for _ in ()).throw(ValueError("hard fail")),
    )
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda client, system_prompt, user_prompt: '["seg1"]',
    )
    llm_config = SimpleNamespace(
        prompt_template="{text}",
        system_prompt=None,
        client=SimpleNamespace(response_format=None),
    )
    markup_config = SimpleNamespace(
        label_attribute=None,
        prepend_label=False,
        chunk_characters=None,
        chunk_overlap_characters=0,
        system_prompt=None,
        prompt_template="extract",
        max_rounds=1,
        max_edits_per_round=1,
        normalize_nested_spans=False,
        client={"provider": "openai", "model": "gpt-4o"},
    )
    config = SimpleNamespace(segmentation=SimpleNamespace(span_markup=markup_config, llm=llm_config))
    segments = markov._span_markup_segments(item_id="i", text="hello", config=config)
    assert len(segments) == 1


def test_markov_llm_observation_handles_start_end(monkeypatch):
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda client, system_prompt, user_prompt: '{"label": "x", "label_confidence": 0.5, "summary": "s"}',
    )
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
    observations = markov._build_observations(
        segments=[
            markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="START"),
            markov.MarkovAnalysisSegment(item_id="i", segment_index=2, text="END"),
            markov.MarkovAnalysisSegment(item_id="i", segment_index=3, text="body"),
        ],
        config=config,
        cache_context=None,
    )
    assert observations[0].llm_label == "START"
    assert observations[1].llm_label == "END"
    assert observations[2].llm_label in {"x", "unknown"}


def test_markov_llm_observation_cache_write(monkeypatch, tmp_path):
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda client, system_prompt, user_prompt: '{"label": "y", "label_confidence": 0.4, "summary": "s"}',
    )
    monkeypatch.setattr(markov, "_parse_json_object", lambda text, error_label: json.loads(text))
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_context = markov._LlmObservationCacheContext(cache_id="cid", cache_dir=cache_dir, enabled=True)
    config = SimpleNamespace(
        llm_observations=SimpleNamespace(
            enabled=True,
            client=SimpleNamespace(response_format=None),
            prompt_template="{segment}",
            system_prompt=None,
            cache=SimpleNamespace(enabled=True, cache_name="cache"),
            max_workers=1,
        ),
        embeddings=SimpleNamespace(enabled=False),
    )
    segments = [markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="body")]
    markov._build_observations(segments=segments, config=config, cache_context=cache_context)
    cache_file = cache_dir / "items" / "i.json"
    assert cache_file.is_file()


def test_markov_collect_documents_respects_sample_size(tmp_path):
    run_root = tmp_path / "snap"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "a.txt").write_text("alpha", encoding="utf-8")
    (run_root / "b.txt").write_text("beta", encoding="utf-8")

    manifest = SimpleNamespace(
        items=[
            SimpleNamespace(item_id="a", status="extracted", final_text_relpath="a.txt"),
            SimpleNamespace(item_id="b", status="extracted", final_text_relpath="b.txt"),
        ]
    )

    class DummyCorpus:
        def __init__(self, root: Path, manifest_obj):
            self.root = root
            self.manifest = manifest_obj
            self.meta_dir = root

        def load_extraction_snapshot_manifest(self, extractor_id: str, snapshot_id: str):
            return self.manifest

        def extraction_snapshot_dir(self, extractor_id: str, snapshot_id: str):
            return self.root

    corpus = DummyCorpus(run_root, manifest)
    documents, report = markov._collect_documents(
        corpus=corpus,
        extraction_snapshot=ExtractionSnapshotReference(extractor_id="ext", snapshot_id="snap"),
        config=MarkovAnalysisTextSourceConfig(sample_size=1),
    )
    assert len(documents) == 1
    assert "Text collection truncated to sample_size" in report.warnings


def test_markov_span_markup_normalizes_duplicates(monkeypatch):
    responses = [
        SimpleNamespace(spans=[SimpleNamespace(text="one")]),
        SimpleNamespace(spans=[SimpleNamespace(text="one")]),
        SimpleNamespace(spans=[SimpleNamespace(text="one and more")]),
    ]

    def fake_apply_text_extract(request):
        return responses.pop(0)

    monkeypatch.setattr(markov, "apply_text_extract", fake_apply_text_extract)
    markup_config = SimpleNamespace(
        label_attribute=None,
        prepend_label=False,
        chunk_characters=5,
        chunk_overlap_characters=0,
        system_prompt=None,
        prompt_template="extract",
        max_rounds=1,
        max_edits_per_round=1,
        normalize_nested_spans=False,
        client={"provider": "openai", "model": "gpt-4o"},
    )
    config = SimpleNamespace(segmentation=SimpleNamespace(span_markup=markup_config, llm=None))
    segments = markov._span_markup_segments(item_id="i", text="onetwothreefour", config=config)
    assert len(segments) == 1
    assert segments[0].text == "one and more"


def test_markov_llm_observation_uses_cache_and_handles_transient(monkeypatch, tmp_path):
    monkeypatch.setattr(markov.time, "sleep", lambda *_: None)
    monkeypatch.setattr(markov.time, "perf_counter", lambda: 0.0)
    monkeypatch.setattr(markov, "generate_completion", lambda *_, **__: (_ for _ in ()).throw(Exception("timeout")))

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    item_cache_dir = cache_dir / "items"
    item_cache_dir.mkdir(parents=True, exist_ok=True)
    cached_entry = {
        "item_id": "i",
        "segments": [
            {
                "segment_index": 1,
                "segment_text_hash": markov.hash_text("cached body"),
                "llm_label": "cached",
                "llm_label_confidence": 0.7,
                "llm_summary": "cached summary",
            }
        ],
    }
    (item_cache_dir / "i.json").write_text(json.dumps(cached_entry), encoding="utf-8")

    cache_context = markov._LlmObservationCacheContext(cache_id="cid", cache_dir=cache_dir, enabled=True)
    config = SimpleNamespace(
        llm_observations=SimpleNamespace(
            enabled=True,
            client=SimpleNamespace(response_format=None),
            prompt_template="{segment}",
            system_prompt=None,
            cache=SimpleNamespace(enabled=True, cache_name="cache"),
            max_workers=1,
        ),
        embeddings=SimpleNamespace(enabled=False),
    )
    segments = [
        markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="cached body"),
        markov.MarkovAnalysisSegment(item_id="i", segment_index=2, text="new body"),
    ]

    observations = markov._build_observations(
        segments=segments,
        config=config,
        cache_context=cache_context,
    )

    assert observations[0].llm_label == "cached"
    assert observations[0].llm_summary == "cached summary"
    assert observations[1].llm_label == "unknown"
    assert cache_context.cached_segments == 1


def test_markov_apply_start_end_labels_rejects(monkeypatch):
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda client, system_prompt, user_prompt: '{"is_end": false, "reason": "no end"}',
    )
    markup_config = SimpleNamespace(
        start_label_value="START",
        end_label_value="END",
        end_reject_label_value="REJECT",
        end_reject_reason_prefix="Because",
        end_label_verifier=SimpleNamespace(
            client=SimpleNamespace(response_format=None),
            system_prompt="{text}",
            prompt_template="prompt",
        ),
    )
    config = SimpleNamespace(segmentation=SimpleNamespace(span_markup=markup_config))
    payloads = [{"segment_index": 1, "text": "body"}]
    segments = markov._apply_start_end_labels(item_id="i", payloads=payloads, config=config)
    assert segments[0].text.startswith("START\n")
    assert "REJECT" in segments[-1].text
    assert "Because" in segments[-1].text


def test_markov_embeddings_use_llm_summary(monkeypatch):
    monkeypatch.setattr(
        markov,
        "generate_completion",
        lambda client, system_prompt, user_prompt: '{"label": "z", "label_confidence": 0.8, "summary": "sum"}',
    )
    monkeypatch.setattr(markov, "_parse_json_object", lambda text, error_label: json.loads(text))
    monkeypatch.setattr(
        markov,
        "generate_embeddings_batch",
        lambda client, texts: [[1.0, 0.0] for _ in texts],
    )
    config = SimpleNamespace(
        llm_observations=SimpleNamespace(
            enabled=True,
            client=SimpleNamespace(response_format=None),
            prompt_template="{segment}",
            system_prompt=None,
            cache=SimpleNamespace(enabled=False),
            max_workers=1,
        ),
        embeddings=SimpleNamespace(
            enabled=True,
            client=SimpleNamespace(response_format=None),
            text_source="llm_summary",
        ),
    )
    segments = [
        markov.MarkovAnalysisSegment(item_id="i", segment_index=1, text="START"),
        markov.MarkovAnalysisSegment(item_id="i", segment_index=2, text="body"),
        markov.MarkovAnalysisSegment(item_id="i", segment_index=3, text="END"),
    ]
    observations = markov._build_observations(segments=segments, config=config, cache_context=None)
    assert observations[1].embedding == [1.0, 0.0]
    assert observations[0].embedding == [0.0, 0.0]
