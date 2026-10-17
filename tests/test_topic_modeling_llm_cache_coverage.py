from __future__ import annotations

import json
import sys
import types
from collections import Counter
from pathlib import Path
from typing import Dict, List

import pytest

from biblicus.analysis import topic_modeling
from biblicus.analysis.models import (
    TopicModelingConfiguration,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
)
from biblicus.analysis.topic_modeling import (
    TopicModelingDocument,
    _apply_llm_extraction,
    _llm_extraction_cache_identity,
    _llm_extraction_document_cache_key,
    _read_llm_extraction_cache,
    _seed_llm_extraction_cache,
    run_topic_modeling_for_documents,
)


def build_llm_extraction_config(**overrides) -> TopicModelingLlmExtractionConfig:
    """Build llm extraction config."""
    values = dict(
        enabled=True,
        client={"provider": "mock", "model": "test-model", "api_key": "secret"},
        prompt_template="Summarize: {text}",
        method=TopicModelingLlmExtractionMethod.SINGLE,
    )
    values.update(overrides)
    return TopicModelingLlmExtractionConfig(**values)


def build_documents(count: int) -> List[TopicModelingDocument]:
    """Build documents."""
    return [
        TopicModelingDocument(
            document_id=f"doc-{index}", source_item_id=f"item-{index}", text=f"text {index}"
        )
        for index in range(count)
    ]


def install_echoing_completion(monkeypatch, failing_prompts=()) -> List[str]:
    """Install echoing completion."""
    prompts: List[str] = []

    def fake_generate_completion(*, client, system_prompt, user_prompt):
        """Return a scripted completion for the prompt."""
        prompts.append(user_prompt)
        if user_prompt in failing_prompts:
            raise RuntimeError(f"provider failure for {user_prompt}")
        return f"  summary of {user_prompt}  "

    monkeypatch.setattr(topic_modeling, "generate_completion", fake_generate_completion)
    return prompts


def install_fake_bertopic_module(monkeypatch) -> None:
    """Install fake bertopic module."""

    class FakeBERTopic:
        """Test double: fake BERTopic model."""

        def __init__(self, **kwargs):
            self.assignments: List[int] = []

        def fit_transform(self, documents):
            """Assign every document to topic zero."""
            self.assignments = [0 for _ in documents]
            return self.assignments, None

        def get_topic_info(self):
            """Return topic counts for the fake model."""
            counts = Counter(self.assignments)
            return [
                {"Topic": topic_id, "Count": count, "Name": f"Topic {topic_id}"}
                for topic_id, count in sorted(counts.items())
            ]

        def get_topic(self, topic_id):
            """Return fixed keywords for any topic."""
            return [("summary", 0.9)]

    fake_module = types.ModuleType("bertopic")
    fake_module.BERTopic = FakeBERTopic
    fake_module.__biblicus_fake__ = True
    monkeypatch.setitem(sys.modules, "bertopic", fake_module)


def test_run_topic_modeling_for_documents_writes_llm_extraction_artifact(monkeypatch, tmp_path):
    """Verify run topic modeling for documents writes llm extraction artifact."""
    install_fake_bertopic_module(monkeypatch)
    install_echoing_completion(monkeypatch)
    configuration = TopicModelingConfiguration.model_validate(
        {"llm_extraction": build_llm_extraction_config().model_dump()}
    )
    artifacts_dir = tmp_path / "artifacts" / "nested"

    report = run_topic_modeling_for_documents(
        documents=build_documents(2), config=configuration, artifacts_dir=artifacts_dir
    )

    artifact_lines = (artifacts_dir / "llm_extraction.jsonl").read_text("utf-8").splitlines()
    assert [json.loads(line)["text"] for line in artifact_lines] == [
        "summary of Summarize: text 0",
        "summary of Summarize: text 1",
    ]
    assert report.llm_extraction.output_documents == 2
    assert report.topics[0].label == "summary"


def test_llm_extraction_cache_identity_ignores_workers_and_api_key():
    """Verify llm extraction cache identity ignores workers and api key."""
    first = build_llm_extraction_config(max_workers=1)
    second = build_llm_extraction_config(
        max_workers=8, client={"provider": "mock", "model": "test-model", "api_key": "other"}
    )
    different_model = build_llm_extraction_config(
        client={"provider": "mock", "model": "another-model"}
    )
    without_client = TopicModelingLlmExtractionConfig(enabled=False)

    assert _llm_extraction_cache_identity(first) == _llm_extraction_cache_identity(second)
    assert _llm_extraction_cache_identity(first) != _llm_extraction_cache_identity(different_model)
    assert isinstance(_llm_extraction_cache_identity(without_client), str)


def test_apply_llm_extraction_records_cache_and_reuses_it_on_next_run(monkeypatch, tmp_path):
    """Verify apply llm extraction records cache and reuses it on next run."""
    prompts = install_echoing_completion(monkeypatch)
    cache_path = tmp_path / "cache" / "llm.jsonl"
    duplicated_documents = build_documents(1) + build_documents(1)

    first_report, first_documents = _apply_llm_extraction(
        documents=duplicated_documents,
        config=build_llm_extraction_config(),
        cache_path=cache_path,
    )

    assert len(first_documents) == 2
    assert first_report.warnings == []
    assert len(cache_path.read_text("utf-8").splitlines()) == 1
    assert len(prompts) == 2

    second_report, second_documents = _apply_llm_extraction(
        documents=build_documents(1),
        config=build_llm_extraction_config(),
        cache_path=cache_path,
    )

    assert len(prompts) == 2
    assert [document.text for document in second_documents] == ["summary of Summarize: text 0"]
    assert second_report.warnings == ["Reused cached LLM extraction documents for 1 inputs"]


def test_apply_llm_extraction_without_cache_path_skips_cache_recording(monkeypatch):
    """Verify apply llm extraction without cache path skips cache recording."""
    install_echoing_completion(monkeypatch)

    report, documents = _apply_llm_extraction(
        documents=build_documents(1), config=build_llm_extraction_config(), cache_path=None
    )

    assert report.output_documents == 1
    assert documents[0].document_id == "doc-0"


def test_apply_llm_extraction_parallel_workers_collect_failures_and_item_errors(
    monkeypatch, tmp_path
):
    """Verify apply llm extraction parallel workers collect failures and item errors."""
    responses: Dict[str, str] = {
        "Items: text 0": '["first idea", "second idea"]',
        "Items: text 1": "[]",
    }

    def fake_generate_completion(*, client, system_prompt, user_prompt):
        """Return a scripted completion for the prompt."""
        if user_prompt == "Items: text 2":
            raise RuntimeError("provider unavailable")
        return responses[user_prompt]

    monkeypatch.setattr(topic_modeling, "generate_completion", fake_generate_completion)
    cache_path = tmp_path / "cache.jsonl"

    report, documents = _apply_llm_extraction(
        documents=build_documents(3),
        config=build_llm_extraction_config(
            method=TopicModelingLlmExtractionMethod.ITEMIZE,
            prompt_template="Items: {text}",
            max_workers=3,
        ),
        cache_path=cache_path,
    )

    assert [document.document_id for document in documents] == ["doc-0:1", "doc-0:2"]
    assert "LLM extraction failed for doc-2: provider unavailable" in report.errors
    assert "LLM itemization returned no items for doc-1" in report.errors
    cached_entries = [json.loads(line) for line in cache_path.read_text("utf-8").splitlines()]
    assert len(cached_entries) == 1


def test_apply_llm_extraction_parallel_workers_raise_when_every_document_fails(
    monkeypatch,
):
    """Verify apply llm extraction parallel workers raise when every document fails."""
    install_echoing_completion(
        monkeypatch, failing_prompts={"Summarize: text 0", "Summarize: text 1"}
    )

    with pytest.raises(ValueError, match="LLM extraction failed for doc-"):
        _apply_llm_extraction(
            documents=build_documents(2),
            config=build_llm_extraction_config(max_workers=2),
        )


def test_read_llm_extraction_cache_skips_malformed_entries(tmp_path):
    """Verify read llm extraction cache skips malformed entries."""
    cache_path = tmp_path / "cache.jsonl"
    cache_path.write_text(
        "\n".join(
            [
                "",
                json.dumps({"documents": []}),
                json.dumps({"cache_key": "not-a-list", "documents": "nope"}),
                json.dumps(
                    {
                        "cache_key": "valid",
                        "documents": [
                            {"document_id": "d1", "source_item_id": "s1", "text": "t1"},
                            "not-a-mapping",
                            {},
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    cached = _read_llm_extraction_cache(cache_path)

    assert list(cached.keys()) == ["valid"]
    assert [document.document_id for document in cached["valid"]] == ["d1", ""]
    assert _read_llm_extraction_cache(None) == {}
    assert _read_llm_extraction_cache(tmp_path / "absent.jsonl") == {}


def write_previous_analysis_run(
    analysis_root: Path,
    *,
    run_name: str,
    llm_extraction_config: TopicModelingLlmExtractionConfig,
    llm_documents: List[TopicModelingDocument] | None,
) -> None:
    """Write previous analysis run."""
    run_dir = analysis_root / run_name
    run_dir.mkdir(parents=True)
    configuration = TopicModelingConfiguration.model_validate(
        {"llm_extraction": llm_extraction_config.model_dump()}
    )
    payload = {"snapshot": {"configuration": {"config": configuration.model_dump(mode="json")}}}
    (run_dir / "output.json").write_text(json.dumps(payload), encoding="utf-8")
    if llm_documents is not None:
        topic_modeling._write_documents_jsonl(run_dir / "llm_extraction.jsonl", llm_documents)


def test_seed_llm_extraction_cache_imports_matching_previous_runs(tmp_path, capsys):
    """Verify seed llm extraction cache imports matching previous runs."""
    analysis_root = tmp_path / "analysis" / "topic-modeling"
    target_config = build_llm_extraction_config()
    documents = build_documents(3)
    write_previous_analysis_run(
        analysis_root,
        run_name="run-without-llm-artifact",
        llm_extraction_config=target_config,
        llm_documents=None,
    )
    corrupt_run_dir = analysis_root / "run-corrupt-output"
    corrupt_run_dir.mkdir(parents=True)
    (corrupt_run_dir / "output.json").write_text("{corrupt", encoding="utf-8")
    (corrupt_run_dir / "llm_extraction.jsonl").write_text("", encoding="utf-8")
    write_previous_analysis_run(
        analysis_root,
        run_name="run-different-configuration",
        llm_extraction_config=build_llm_extraction_config(prompt_template="Other: {text}"),
        llm_documents=[
            TopicModelingDocument(document_id="doc-2", source_item_id="item-2", text="other")
        ],
    )
    write_previous_analysis_run(
        analysis_root,
        run_name="run-matching-configuration",
        llm_extraction_config=target_config,
        llm_documents=[
            TopicModelingDocument(document_id="doc-0:1", source_item_id="item-0", text="a"),
            TopicModelingDocument(document_id="doc-0:2", source_item_id="item-0", text="b"),
            TopicModelingDocument(document_id="doc-1", source_item_id="item-1", text="c"),
            TopicModelingDocument(document_id="doc-2", source_item_id="item-2", text="d"),
            TopicModelingDocument(document_id="unknown", source_item_id="x", text="e"),
        ],
    )
    cache_path = tmp_path / "cache" / "llm.jsonl"
    topic_modeling._append_llm_extraction_cache_entry(
        path=cache_path,
        cache_key=_llm_extraction_document_cache_key(documents[1]),
        documents=[documents[1]],
    )

    _seed_llm_extraction_cache(
        analysis_root=analysis_root,
        cache_path=cache_path,
        config=target_config,
        documents=documents,
    )

    cached = _read_llm_extraction_cache(cache_path)
    assert [
        document.text for document in cached[_llm_extraction_document_cache_key(documents[0])]
    ] == [
        "a",
        "b",
    ]
    assert [
        document.text for document in cached[_llm_extraction_document_cache_key(documents[1])]
    ] == ["text 1"]
    assert [
        document.text for document in cached[_llm_extraction_document_cache_key(documents[2])]
    ] == ["d"]
    assert "seeded 2 LLM extraction cache entries" in capsys.readouterr().err


def test_seed_llm_extraction_cache_is_silent_when_nothing_matches(tmp_path, capsys):
    """Verify seed llm extraction cache is silent when nothing matches."""
    analysis_root = tmp_path / "analysis" / "topic-modeling"
    analysis_root.mkdir(parents=True)

    _seed_llm_extraction_cache(
        analysis_root=analysis_root,
        cache_path=tmp_path / "cache.jsonl",
        config=build_llm_extraction_config(),
        documents=build_documents(1),
    )

    assert "seeded" not in capsys.readouterr().err
    assert not (tmp_path / "cache.jsonl").exists()


def test_run_topic_modeling_for_documents_skips_llm_artifact_when_extraction_disabled(
    monkeypatch, tmp_path
):
    """Verify run topic modeling for documents skips llm artifact when extraction disabled."""
    install_fake_bertopic_module(monkeypatch)
    artifacts_dir = tmp_path / "artifacts"

    report = run_topic_modeling_for_documents(
        documents=build_documents(1),
        config=TopicModelingConfiguration(),
        artifacts_dir=artifacts_dir,
    )

    assert not (artifacts_dir / "llm_extraction.jsonl").exists()
    assert report.llm_extraction.status == "skipped"


def test_apply_llm_extraction_sequential_collects_failures_and_empty_outputs(monkeypatch):
    """Verify apply llm extraction sequential collects failures and empty outputs."""
    responses = {"Summarize: text 0": "useful summary", "Summarize: text 1": "   "}

    def fake_generate_completion(*, client, system_prompt, user_prompt):
        """Return a scripted completion for the prompt."""
        if user_prompt == "Summarize: text 2":
            raise RuntimeError("provider unavailable")
        return responses[user_prompt]

    monkeypatch.setattr(topic_modeling, "generate_completion", fake_generate_completion)

    report, documents = _apply_llm_extraction(
        documents=build_documents(3), config=build_llm_extraction_config()
    )

    assert [document.text for document in documents] == ["useful summary"]
    assert report.errors == [
        "LLM extraction failed for doc-2: provider unavailable",
        "LLM extraction returned empty output for doc-1",
    ]
