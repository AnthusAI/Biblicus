from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

import biblicus.topic_context as topic_context
from biblicus.topic_context import (
    TopicContextExample,
    TopicContextOutput,
    TopicContextTopic,
    topic_context_markdown,
)


def _catalog_item(
    item_id: str,
    *,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    published_at: Optional[str] = None,
    source_uri: Optional[str] = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id,
        title=title,
        metadata=metadata or {},
        source_uri=source_uri,
        dates=SimpleNamespace(published_at=published_at) if published_at else None,
    )


def _topic(
    topic_id: int,
    label: str,
    document_ids: List[str],
    keywords: Optional[List[str]] = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        topic_id=topic_id,
        label=label,
        label_source=SimpleNamespace(value="bertopic"),
        document_count=len(document_ids),
        document_ids=document_ids,
        keywords=[SimpleNamespace(keyword=word) for word in (keywords or [])],
    )


class _FakeCorpus:
    def __init__(self, root: Path, items: Dict[str, Any], texts: Dict[str, str]) -> None:
        self.root = root
        self.analysis_dir = root / "analysis"
        self._items = items
        self._texts = texts

    def load_catalog(self) -> SimpleNamespace:
        return SimpleNamespace(items=self._items)

    def read_extracted_text(self, *, extractor_id: str, snapshot_id: str, item_id: str):
        return self._texts.get(item_id)

    def analysis_run_dir(self, *, analysis_id: str, snapshot_id: str) -> Path:
        return self.analysis_dir / analysis_id / snapshot_id


def _topic_modeling_output(topics: List[SimpleNamespace]) -> SimpleNamespace:
    reference = {"extractor_id": "pipeline", "snapshot_id": "extract-1"}
    return SimpleNamespace(
        snapshot=SimpleNamespace(
            input=SimpleNamespace(
                extraction_snapshot=SimpleNamespace(model_dump=lambda mode: reference)
            )
        ),
        report=SimpleNamespace(topics=topics),
    )


def _install_fake_openai(
    monkeypatch: pytest.MonkeyPatch, replies: List[Optional[str]]
) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []

    class _Completions:
        def create(self, *, model: str, messages: List[Dict[str, str]]) -> SimpleNamespace:
            calls.append({"model": model, "messages": messages})
            reply = replies.pop(0)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=reply))]
            )

    class _Client:
        def __init__(self, api_key: str) -> None:
            self.chat = SimpleNamespace(completions=_Completions())

    module = ModuleType("openai")
    module.OpenAI = _Client
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return calls


def _context_output(**overrides: Any) -> TopicContextOutput:
    payload: Dict[str, Any] = {
        "snapshot_id": "snap",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_topic_modeling_snapshot_id": "tm",
        "extraction_snapshot": "pipeline:extract-1",
        "max_topics": 3,
        "examples_per_topic": 2,
    }
    payload.update(overrides)
    return TopicContextOutput.model_validate(payload)


def test_output_rejects_foreign_analysis_identifier() -> None:
    """The output model only accepts the topic context analysis identifier."""
    with pytest.raises(ValueError, match="analysis_id must be topic-context"):
        _context_output(analysis_id="other")


def test_output_accepts_topic_context_analysis_identifier() -> None:
    """The default analysis identifier passes validation unchanged."""
    assert _context_output(analysis_id="topic-context").analysis_id == "topic-context"


@pytest.mark.parametrize(
    ("max_topics", "examples_per_topic", "message"),
    [
        (0, 1, "max_topics must be at least 1"),
        (1, 0, "examples_per_topic must be at least 1"),
    ],
)
def test_build_topic_context_validates_limits(
    tmp_path: Path, max_topics: int, examples_per_topic: int, message: str
) -> None:
    """Non-positive topic and example limits are rejected up front."""
    corpus = _FakeCorpus(tmp_path, {}, {})
    with pytest.raises(ValueError, match=message):
        topic_context.build_topic_context(
            corpus=corpus,
            topic_modeling_snapshot_id="tm",
            max_topics=max_topics,
            examples_per_topic=examples_per_topic,
            summary_model=None,
            include_outlier=False,
        )


def test_load_topic_modeling_output_reports_missing_file(tmp_path: Path) -> None:
    """A missing topic modeling snapshot raises a clear file error."""
    corpus = _FakeCorpus(tmp_path, {}, {})
    with pytest.raises(FileNotFoundError, match="Missing topic modeling output"):
        topic_context._load_topic_modeling_output(corpus=corpus, snapshot_id="absent")


def test_build_topic_context_writes_artifacts_with_summaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A full build ranks topics, summarizes examples with the model, and writes artifacts."""
    items = {
        "a": _catalog_item("a", title="Agent Memory", metadata={"abstract": "Memory for agents."}),
        "b": _catalog_item(
            "b",
            title="Agent Planning",
            published_at="2024-01-01",
            source_uri="https://example.com/b",
        ),
        "c": _catalog_item("c", title="Outlier Paper", metadata={"summary": "Odd."}),
    }
    texts = {"a": "agent memory systems", "b": "agent planning with memory systems"}
    corpus = _FakeCorpus(tmp_path, items, texts)
    topics = [
        _topic(0, "Agents", ["a", "b", "ghost"], ["agent", "memory"]),
        _topic(-1, "Outliers", ["c"], ["odd"]),
    ]
    monkeypatch.setattr(
        topic_context,
        "_load_topic_modeling_output",
        lambda **_: _topic_modeling_output(topics),
    )
    calls = _install_fake_openai(monkeypatch, ["Planning summary.", "Guidance one."])
    output = topic_context.build_topic_context(
        corpus=corpus,
        topic_modeling_snapshot_id="tm",
        max_topics=1,
        examples_per_topic=3,
        summary_model="test-model",
        include_outlier=False,
    )
    assert [topic.label for topic in output.topics] == ["Agents"]
    sources = {example.item_id: example.text_source for example in output.topics[0].examples}
    assert sources == {"a": "abstract", "b": "llm_summary"}
    assert output.topics[0].guidance == "Guidance one."
    assert any("missing catalog item ghost" in warning for warning in output.warnings)
    assert len(calls) == 2
    assert Path(output.artifact_paths["report"]).is_file()
    latest = json.loads((tmp_path / "analysis" / "topic-context" / "latest.json").read_text())
    assert latest["snapshot_id"] == output.snapshot_id


def test_rank_topic_candidates_orders_and_filters_outlier() -> None:
    """Candidates sort by size then label, and the outlier topic is optional."""
    topics = [
        _topic(-1, "Outliers", ["1", "2", "3"]),
        _topic(2, "beta", ["1"]),
        _topic(1, "Alpha", ["1"]),
        _topic(3, "Big", ["1", "2"]),
    ]
    without = topic_context._rank_topic_candidates(topics=topics, include_outlier=False)
    with_outlier = topic_context._rank_topic_candidates(topics=topics, include_outlier=True)
    assert [topic.topic_id for topic in without] == [3, 1, 2]
    assert [topic.topic_id for topic in with_outlier] == [-1, 3, 1, 2]


def test_representative_examples_skip_items_without_text(tmp_path: Path) -> None:
    """Examples without any usable text are dropped with a warning."""
    items = {"a": _catalog_item("a", title="Empty Item")}
    corpus = _FakeCorpus(tmp_path, items, {})
    warnings: List[str] = []
    examples = topic_context._representative_examples(
        corpus=corpus,
        catalog_items=items,
        extraction_snapshot=SimpleNamespace(extractor_id="pipeline", snapshot_id="extract-1"),
        topic=_topic(0, "Empty", ["a"]),
        examples_per_topic=2,
        summary_model=None,
        warnings=warnings,
    )
    assert examples == []
    assert warnings == ["Item a has no abstract, summary, or extracted text for context"]


def test_centrality_text_handles_missing_catalog_item() -> None:
    """Unknown catalog items fall back to their extracted text only."""
    assert topic_context._centrality_text("x", {}, {"x": "raw text"}) == "raw text"
    assert topic_context._centrality_text("y", {}, {}) == ""


def test_centrality_text_joins_metadata_and_extracted_text() -> None:
    """Catalog metadata fields and extracted text are joined for similarity scoring."""
    item = _catalog_item(
        "a",
        title="Title",
        metadata={"subtitle": "Sub", "description": "Desc"},
    )
    text = topic_context._centrality_text("a", {"a": item}, {"a": "Body"})
    assert text == "Title\nSub\nDesc\nBody"


def test_centrality_score_handles_single_empty_and_peer_vectors() -> None:
    """Scores are one for a lone item, zero for an empty vector, and mean cosine otherwise."""
    counts = topic_context._term_counts
    assert topic_context._centrality_score(item_id="a", vectors={"a": counts("agent")}) == 1.0
    assert (
        topic_context._centrality_score(
            item_id="a", vectors={"a": counts(""), "b": counts("agent")}
        )
        == 0.0
    )
    identical = topic_context._centrality_score(
        item_id="a", vectors={"a": counts("agent memory"), "b": counts("agent memory")}
    )
    assert identical == pytest.approx(1.0)


def test_cosine_similarity_handles_empty_vectors() -> None:
    """Empty vectors have zero similarity and disjoint vectors score zero."""
    counts = topic_context._term_counts
    assert topic_context._cosine_similarity(counts(""), counts("agent")) == 0.0
    assert topic_context._cosine_similarity(counts("agent"), counts("memory")) == 0.0
    assert topic_context._cosine_similarity(counts("agent"), counts("agent")) == pytest.approx(1.0)


def test_cosine_similarity_returns_zero_for_zero_norm_vectors() -> None:
    """Vectors whose values are all zero produce zero similarity."""
    zero_vector = topic_context.Counter({"agent": 0})
    assert topic_context._cosine_similarity(zero_vector, zero_vector) == 0.0


@pytest.mark.parametrize(
    ("metadata", "expected_source"),
    [
        ({"abstract": " Abstract text "}, "abstract"),
        ({"summary": "Summary text"}, "summary"),
        ({"description": "Description text"}, "description"),
    ],
)
def test_example_text_prefers_curated_metadata(
    metadata: Dict[str, Any], expected_source: str
) -> None:
    """Curated abstract, summary, and description fields are used before extracted text."""
    item = _catalog_item("a", metadata=metadata)
    source, text = topic_context._example_text(
        item=item, extracted_text="extracted", summary_model="model", warnings=[]
    )
    assert source == expected_source
    assert text == text.strip() and text


def test_example_text_uses_extracted_or_reports_missing() -> None:
    """Without a model the extracted text is used, and nothing yields a missing marker."""
    item = _catalog_item("a")
    assert topic_context._example_text(
        item=item, extracted_text=" body ", summary_model=None, warnings=[]
    ) == ("extracted_text", "body")
    assert topic_context._example_text(
        item=item, extracted_text="  ", summary_model="model", warnings=[]
    ) == ("missing", "")


def test_example_text_warns_when_model_returns_empty_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty model summary falls back to extracted text with a warning."""
    _install_fake_openai(monkeypatch, [None])
    warnings: List[str] = []
    source, text = topic_context._example_text(
        item=_catalog_item("a", title="T"),
        extracted_text="body text",
        summary_model="model",
        warnings=warnings,
    )
    assert (source, text) == ("extracted_text", "body text")
    assert warnings == ["OpenAI returned an empty example summary for item a"]


def test_topic_guidance_is_skipped_without_model() -> None:
    """Guidance is only generated when a summary model is configured."""
    assert (
        topic_context._topic_guidance(
            topic=_topic(0, "T", []), examples=[], summary_model=None, warnings=[]
        )
        is None
    )


def test_topic_guidance_warns_on_empty_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty guidance completion yields no guidance and a warning."""
    calls = _install_fake_openai(monkeypatch, [""])
    example = TopicContextExample(
        item_id="a",
        title="Title",
        text_source="abstract",
        text="Some text",
        centrality_score=1.0,
    )
    warnings: List[str] = []
    guidance = topic_context._topic_guidance(
        topic=_topic(4, "T", ["a"], ["k"]),
        examples=[example],
        summary_model="model",
        warnings=warnings,
    )
    assert guidance is None
    assert warnings == ["OpenAI returned empty topic guidance for topic 4"]
    assert "Title: Some text" in calls[0]["messages"][1]["content"]


def test_openai_completion_requires_openai_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing openai package raises an installation hint."""
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(ValueError, match="require the openai package"):
        topic_context._openai_completion(model="m", messages=[])


def test_openai_completion_requires_openai_client_class(monkeypatch: pytest.MonkeyPatch) -> None:
    """An openai module without a client class raises an installation hint."""
    monkeypatch.setitem(sys.modules, "openai", ModuleType("openai"))
    with pytest.raises(ValueError, match="require the openai package"):
        topic_context._openai_completion(model="m", messages=[])


def test_metadata_title_and_sort_helpers() -> None:
    """Title helpers prefer catalog titles, then metadata titles, then identifiers."""
    assert topic_context._item_title(_catalog_item("a", title="Given")) == "Given"
    assert topic_context._item_title(_catalog_item("a", metadata={"title": "Meta"})) == "Meta"
    assert topic_context._item_title(_catalog_item("a")) == "a"
    assert topic_context._title_for_sort(None) == ""
    assert topic_context._title_for_sort(_catalog_item("a", title="MiXed")) == "mixed"
    assert topic_context._metadata_text(_catalog_item("a", metadata={"k": 3}), "k") is None


def test_truncate_text_collapses_whitespace_and_adds_ellipsis() -> None:
    """Long text is truncated with an ellipsis and whitespace is collapsed."""
    assert topic_context._truncate_text("a   b\n c", 50) == "a b c"
    assert topic_context._truncate_text("abcdefghij", 8) == "abcde..."


def test_markdown_renders_guidance_examples_and_warnings() -> None:
    """The report includes guidance, example detail lines, empty notes, and warnings."""
    example = TopicContextExample(
        item_id="a",
        title="Title",
        subtitle="Sub",
        source_uri="https://example.com",
        published_at="2024-01-01",
        text_source="abstract",
        text="Body",
        centrality_score=0.5,
    )
    topics = [
        TopicContextTopic(
            rank=1,
            topic_id=0,
            label="Agents",
            label_source="bertopic",
            document_count=2,
            keywords=["agent"],
            guidance="Use for agents.",
            examples=[example],
        ),
        TopicContextTopic(
            rank=2,
            topic_id=1,
            label="Bare",
            label_source="bertopic",
            document_count=1,
        ),
    ]
    markdown = topic_context_markdown(_context_output(topics=topics, warnings=["careful"]))
    assert "- Guidance: Use for agents." in markdown
    assert "- Subtitle: Sub" in markdown
    assert "- Source: https://example.com" in markdown
    assert "- Published: 2024-01-01" in markdown
    assert "- Keywords: none" in markdown
    assert "No representative examples available." in markdown
    assert "## Warnings" in markdown
    assert "- careful" in markdown
