"""Tests for ReinforcementMemoryStore (Virtuus persistence layer)."""

from __future__ import annotations

import pytest

from biblicus.analysis.reinforcement_memory._models import TimestampedText
from biblicus.analysis.reinforcement_memory._store import (
    ReinforcementMemoryStore,
    _build_range_condition,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path):
    """Fresh store backed by a temporary directory."""
    return ReinforcementMemoryStore(str(tmp_path))


def _text(id, group_id="g1", timestamp="2024-01-15T10:00:00Z", text="hello"):
    return TimestampedText(
        id=id,
        group_id=group_id,
        timestamp=timestamp,
        text=text,
        metadata={"source": "test"},
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_store_creates_data_dir(tmp_path):
    sub = tmp_path / "sub" / "deep"
    ReinforcementMemoryStore(str(sub))
    assert sub.exists()


def test_store_creates_table_directories(tmp_path):
    ReinforcementMemoryStore(str(tmp_path))
    # Virtuus creates subdirectories on first write; just verify no exception


# ---------------------------------------------------------------------------
# put_text / get_texts_for_group
# ---------------------------------------------------------------------------


def test_put_and_retrieve_text(store):
    t = _text("1", group_id="g1", timestamp="2024-01-15T10:00:00Z", text="hello world")
    store.put_text(t)
    records = store.get_texts_for_group("g1")
    assert len(records) == 1
    assert records[0]["id"] == "1"
    assert records[0]["text"] == "hello world"


def test_put_text_idempotent(store):
    t = _text("1")
    store.put_text(t)
    store.put_text(t)
    records = store.get_texts_for_group("g1")
    assert len(records) == 1


def test_put_texts_returns_count(store):
    texts = [_text(str(i)) for i in range(5)]
    count = store.put_texts(texts)
    assert count == 5


def test_get_texts_different_groups_isolated(store):
    store.put_text(_text("1", group_id="g1"))
    store.put_text(_text("2", group_id="g2"))
    g1 = store.get_texts_for_group("g1")
    g2 = store.get_texts_for_group("g2")
    assert len(g1) == 1
    assert len(g2) == 1
    assert g1[0]["id"] == "1"
    assert g2[0]["id"] == "2"


def test_get_texts_empty_group(store):
    records = store.get_texts_for_group("nonexistent")
    assert records == []


def test_get_texts_metadata_preserved(store):
    t = TimestampedText(
        id="1",
        group_id="g1",
        timestamp="2024-01-15T00:00:00Z",
        text="test",
        metadata={"score": "q1", "editor": "alice"},
    )
    store.put_text(t)
    records = store.get_texts_for_group("g1")
    assert records[0]["metadata"]["score"] == "q1"
    assert records[0]["metadata"]["editor"] == "alice"


def test_get_texts_since_filter(store):
    store.put_text(_text("old", timestamp="2024-01-01T00:00:00Z"))
    store.put_text(_text("new", timestamp="2024-02-01T00:00:00Z"))
    records = store.get_texts_for_group("g1", since="2024-01-15T00:00:00Z")
    ids = [r["id"] for r in records]
    assert "new" in ids
    assert "old" not in ids


def test_get_texts_until_filter(store):
    store.put_text(_text("old", timestamp="2024-01-01T00:00:00Z"))
    store.put_text(_text("new", timestamp="2024-02-01T00:00:00Z"))
    records = store.get_texts_for_group("g1", until="2024-01-15T00:00:00Z")
    ids = [r["id"] for r in records]
    assert "old" in ids
    assert "new" not in ids


def test_get_texts_since_until_range(store):
    store.put_text(_text("jan", timestamp="2024-01-10T00:00:00Z"))
    store.put_text(_text("feb", timestamp="2024-02-10T00:00:00Z"))
    store.put_text(_text("mar", timestamp="2024-03-10T00:00:00Z"))
    records = store.get_texts_for_group(
        "g1",
        since="2024-01-15T00:00:00Z",
        until="2024-02-28T00:00:00Z",
    )
    ids = [r["id"] for r in records]
    assert "feb" in ids
    assert "jan" not in ids
    assert "mar" not in ids


# ---------------------------------------------------------------------------
# put_topic / get_topics_for_group / delete_topics_for_group
# ---------------------------------------------------------------------------


def _topic(topic_id, group_id="g1", weight=0.5):
    return {
        "topic_id": topic_id,
        "group_id": group_id,
        "label": "test topic",
        "keywords": ["foo", "bar"],
        "member_count": 10,
        "memory_weight": weight,
        "memory_tier": "warm",
        "last_updated": "2024-01-15T00:00:00Z",
    }


def test_put_and_get_topic(store):
    store.put_topic(_topic("g1::0"))
    topics = store.get_topics_for_group("g1")
    assert len(topics) == 1
    assert topics[0]["topic_id"] == "g1::0"


def test_get_topics_empty(store):
    assert store.get_topics_for_group("g1") == []


def test_put_topic_idempotent(store):
    store.put_topic(_topic("g1::0"))
    store.put_topic(_topic("g1::0", weight=0.8))
    topics = store.get_topics_for_group("g1")
    assert len(topics) == 1
    assert topics[0]["memory_weight"] == 0.8


def test_get_topics_different_groups_isolated(store):
    store.put_topic(_topic("g1::0", group_id="g1"))
    store.put_topic(_topic("g2::0", group_id="g2"))
    assert len(store.get_topics_for_group("g1")) == 1
    assert len(store.get_topics_for_group("g2")) == 1


def test_delete_topics_for_group(store):
    store.put_topic(_topic("g1::0"))
    store.put_topic(_topic("g1::1"))
    deleted = store.delete_topics_for_group("g1")
    assert deleted == 2
    assert store.get_topics_for_group("g1") == []


def test_delete_topics_only_affects_target_group(store):
    store.put_topic(_topic("g1::0", group_id="g1"))
    store.put_topic(_topic("g2::0", group_id="g2"))
    store.delete_topics_for_group("g1")
    assert store.get_topics_for_group("g1") == []
    assert len(store.get_topics_for_group("g2")) == 1


# ---------------------------------------------------------------------------
# record_run / get_runs_for_group
# ---------------------------------------------------------------------------


def _run(run_id, group_id="g1"):
    return {
        "run_id": run_id,
        "group_id": group_id,
        "timestamp": "2024-01-15T12:00:00Z",
        "texts_analyzed": 10,
        "topics_found": 3,
    }


def test_record_and_get_run(store):
    store.record_run(_run("run-1"))
    runs = store.get_runs_for_group("g1")
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-1"


def test_get_runs_empty(store):
    assert store.get_runs_for_group("g1") == []


def test_multiple_runs_recorded(store):
    store.record_run(_run("run-1"))
    store.record_run(_run("run-2"))
    runs = store.get_runs_for_group("g1")
    assert len(runs) == 2


# ---------------------------------------------------------------------------
# _build_range_condition
# ---------------------------------------------------------------------------


def test_build_range_condition_none_none():
    assert _build_range_condition(None, None) is None


def test_build_range_condition_since_only():
    cond = _build_range_condition("2024-01-01", None)
    assert cond is not None
    assert cond("2024-02-01") is True
    assert cond("2023-12-01") is False


def test_build_range_condition_until_only():
    cond = _build_range_condition(None, "2024-01-31")
    assert cond is not None
    assert cond("2024-01-15") is True
    assert cond("2024-02-01") is False


def test_build_range_condition_between():
    cond = _build_range_condition("2024-01-01", "2024-01-31")
    assert cond is not None
    assert cond("2024-01-15") is True
    assert cond("2023-12-31") is False
    assert cond("2024-02-01") is False
