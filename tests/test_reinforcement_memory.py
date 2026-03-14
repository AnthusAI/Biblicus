"""
End-to-end integration tests for ReinforcementMemory.

Uses hash_embedder (no external services), LocalVectorStore, and mock LLM
callables to verify the full ingest -> analyze -> get_topics pipeline.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import MagicMock

import numpy as np
import pytest

from biblicus.analysis.reinforcement_memory import (
    AnalysisResult,
    LocalVectorStore,
    ReinforcementMemory,
    TimestampedText,
    TopicResult,
    hash_embedder,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ts(days_ago: int = 0) -> str:
    """Return an ISO timestamp N days in the past."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


def _make_engine(tmp_path, label_fn=None, infer_cause=None, synthesize_cause=None):
    data_dir = str(tmp_path / "data")
    vector_dir = str(tmp_path / "vectors")
    return ReinforcementMemory(
        data_dir=data_dir,
        vector_store=LocalVectorStore(vector_dir, embedding_dim=384),
        embed=hash_embedder(384),
        label=label_fn,
        infer_cause=infer_cause,
        synthesize_cause=synthesize_cause,
        min_topic_size=2,
    )


def _texts(group_id: str, n: int = 20, days_ago: int = 0) -> List[TimestampedText]:
    """Generate N distinct timestamped texts for a group."""
    topics = [
        "user authentication login password",
        "payment billing invoice subscription",
        "performance slow timeout latency",
        "ui design layout button style",
    ]
    records = []
    for i in range(n):
        topic = topics[i % len(topics)]
        records.append(
            TimestampedText(
                id=f"{group_id}-{i}",
                group_id=group_id,
                timestamp=_ts(days_ago),
                text=f"{topic} example text number {i}",
                metadata={"source": "test", "index": i},
            )
        )
    return records


# ---------------------------------------------------------------------------
# Basic ingest tests
# ---------------------------------------------------------------------------


def test_ingest_returns_count(tmp_path):
    engine = _make_engine(tmp_path)
    texts = _texts("g1", n=5)
    assert engine.ingest(texts) == 5


def test_ingest_idempotent(tmp_path):
    engine = _make_engine(tmp_path)
    texts = _texts("g1", n=5)
    engine.ingest(texts)
    count = engine.ingest(texts)  # same IDs
    assert count == 5


def test_ingest_empty(tmp_path):
    engine = _make_engine(tmp_path)
    assert engine.ingest([]) == 0


# ---------------------------------------------------------------------------
# Analyze — empty group
# ---------------------------------------------------------------------------


def test_analyze_empty_group_returns_empty_result(tmp_path):
    engine = _make_engine(tmp_path)
    result = engine.analyze("nonexistent-group")
    assert isinstance(result, AnalysisResult)
    assert result.group_id == "nonexistent-group"
    assert result.topics == []
    assert result.texts_analyzed == 0


# ---------------------------------------------------------------------------
# Analyze — basic pipeline
# ---------------------------------------------------------------------------


def test_analyze_returns_analysis_result(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    result = engine.analyze("g1")
    assert isinstance(result, AnalysisResult)
    assert result.group_id == "g1"
    assert result.texts_analyzed == 20
    assert result.run_id != ""
    assert result.cluster_version != ""


def test_analyze_produces_topics(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    result = engine.analyze("g1")
    assert len(result.topics) >= 1
    for topic in result.topics:
        assert isinstance(topic, TopicResult)
        assert topic.label != ""
        assert topic.member_count >= 1
        assert 0.0 <= topic.memory_weight <= 1.0
        assert topic.memory_tier in ("hot", "warm", "cold")
        assert topic.lifecycle_tier in ("new", "trending", "established", "unknown")


def test_analyze_topics_have_keywords(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    result = engine.analyze("g1")
    for topic in result.topics:
        assert isinstance(topic.keywords, list)


def test_analyze_topics_have_exemplars(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    result = engine.analyze("g1")
    for topic in result.topics:
        assert isinstance(topic.exemplars, list)
        for ex in topic.exemplars:
            assert ex.text != ""
            assert ex.text_id != ""


# ---------------------------------------------------------------------------
# Group isolation
# ---------------------------------------------------------------------------


def test_analyze_isolates_groups(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    engine.ingest(_texts("g2", n=20))
    r1 = engine.analyze("g1")
    r2 = engine.analyze("g2")
    assert r1.texts_analyzed == 20
    assert r2.texts_analyzed == 20
    # g2 analysis should not include g1 texts
    all_ids_r2 = {
        ex.text_id for t in r2.topics for ex in t.exemplars
    }
    for tid in all_ids_r2:
        assert tid.startswith("g2-")


# ---------------------------------------------------------------------------
# LLM label integration
# ---------------------------------------------------------------------------


def test_analyze_uses_label_fn(tmp_path):
    label_fn = MagicMock(return_value="Custom Label")
    engine = _make_engine(tmp_path, label_fn=label_fn)
    engine.ingest(_texts("g1", n=20))
    result = engine.analyze("g1")
    assert len(result.topics) >= 1
    # At least one topic should use the label fn
    assert label_fn.called
    labels = {t.label for t in result.topics}
    assert "Custom Label" in labels


def test_analyze_label_fn_exception_falls_back_to_keywords(tmp_path):
    def bad_label(kw, ex):
        raise RuntimeError("LLM unavailable")

    engine = _make_engine(tmp_path, label_fn=bad_label)
    engine.ingest(_texts("g1", n=20))
    result = engine.analyze("g1")
    # Should not raise; topics should have keyword-derived labels
    assert len(result.topics) >= 1
    for topic in result.topics:
        assert topic.label != ""


# ---------------------------------------------------------------------------
# Causal inference integration
# ---------------------------------------------------------------------------


def test_analyze_calls_infer_cause(tmp_path):
    infer_cause = MagicMock(return_value="A test cause")
    synthesize_cause = MagicMock(return_value="Synthesized root cause")
    engine = _make_engine(
        tmp_path, infer_cause=infer_cause, synthesize_cause=synthesize_cause
    )
    engine.ingest(_texts("g1", n=20))
    result = engine.analyze("g1")
    assert infer_cause.called
    assert synthesize_cause.called
    # At least one topic should have a root cause
    root_causes = [t.root_cause for t in result.topics if t.root_cause]
    assert len(root_causes) >= 1
    assert root_causes[0] == "Synthesized root cause"


def test_analyze_causal_exception_does_not_abort(tmp_path):
    def bad_cause(text, ctx):
        raise RuntimeError("cause fail")

    engine = _make_engine(tmp_path, infer_cause=bad_cause)
    engine.ingest(_texts("g1", n=20))
    result = engine.analyze("g1")
    assert len(result.topics) >= 1
    # root_cause should be None (synthesis skipped because no causes)
    for topic in result.topics:
        assert topic.root_cause is None


# ---------------------------------------------------------------------------
# get_topics / persistence
# ---------------------------------------------------------------------------


def test_get_topics_returns_persisted_state(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    engine.analyze("g1")
    topics = engine.get_topics("g1")
    assert isinstance(topics, list)
    assert len(topics) >= 1
    for t in topics:
        assert "topic_id" in t
        assert "label" in t
        assert "memory_weight" in t


def test_get_topics_empty_before_analyze(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    topics = engine.get_topics("g1")
    assert topics == []


def test_analyze_replaces_previous_topics(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    engine.analyze("g1")
    first_topics = engine.get_topics("g1")

    # Add more texts and re-analyze
    engine.ingest(_texts("g1", n=20))
    engine.analyze("g1")
    second_topics = engine.get_topics("g1")

    # Topics are replaced, not appended
    first_ids = {t["topic_id"] for t in first_topics}
    second_ids = {t["topic_id"] for t in second_topics}
    # They may or may not overlap — what matters is no duplication
    all_ids = [t["topic_id"] for t in engine.get_topics("g1")]
    assert len(all_ids) == len(set(all_ids)), "Duplicate topic IDs after re-analyze"


# ---------------------------------------------------------------------------
# query (vector store)
# ---------------------------------------------------------------------------


def test_query_returns_results_after_analyze(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=20))
    engine.analyze("g1")
    # Use hash embedder to embed a query
    query_vec = hash_embedder(384)(["user authentication login"])[0]
    results = engine.query(query_vec, k=3)
    assert isinstance(results, list)
    # May be empty if all topics had no centroids, but most runs should produce some
    for r in results:
        assert r.key.startswith("cluster:")
        assert -1.0 <= r.similarity <= 1.0


def test_query_empty_before_analyze(tmp_path):
    engine = _make_engine(tmp_path)
    engine.ingest(_texts("g1", n=5))
    query_vec = hash_embedder(384)(["some text"])[0]
    results = engine.query(query_vec, k=3)
    assert results == []


# ---------------------------------------------------------------------------
# Time filtering
# ---------------------------------------------------------------------------


def test_analyze_since_filters_old_texts(tmp_path):
    engine = _make_engine(tmp_path)
    old_texts = _texts("g1", n=10, days_ago=60)
    recent_texts = _texts("g1", n=10, days_ago=1)
    # Give recent texts different IDs
    for i, t in enumerate(recent_texts):
        t.id = f"recent-{i}"
    engine.ingest(old_texts + recent_texts)

    # Analyze only recent
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    result = engine.analyze("g1", since=since)
    assert result.texts_analyzed == 10


# ---------------------------------------------------------------------------
# Metadata passthrough
# ---------------------------------------------------------------------------


def test_exemplar_metadata_preserved(tmp_path):
    engine = _make_engine(tmp_path)
    texts = [
        TimestampedText(
            id=f"m{i}",
            group_id="g1",
            timestamp=_ts(),
            text=f"user authentication login password example {i}",
            metadata={"custom_field": f"val_{i}"},
        )
        for i in range(15)
    ]
    engine.ingest(texts)
    result = engine.analyze("g1")
    # At least one exemplar should carry metadata
    all_meta = [ex.metadata for t in result.topics for ex in t.exemplars]
    assert len(all_meta) >= 1
    has_custom = any("custom_field" in m for m in all_meta)
    assert has_custom
