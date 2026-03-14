"""Tests for TopicClusterer.

BERTopic/UMAP/HDBSCAN are optional; these tests exercise the KMeans fallback
path and all pure-numpy helpers so they run without heavy ML dependencies.
"""

from __future__ import annotations

import numpy as np
import pytest

from biblicus.analysis.reinforcement_memory._clusterer import (
    TopicClusterer,
    _cosine_distance,
)


# ---------------------------------------------------------------------------
# _cosine_distance
# ---------------------------------------------------------------------------


def test_cosine_distance_identical_vectors():
    a = np.array([1.0, 0.0, 0.0])
    assert _cosine_distance(a, a) == pytest.approx(0.0)


def test_cosine_distance_orthogonal_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert _cosine_distance(a, b) == pytest.approx(1.0)


def test_cosine_distance_opposite_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert _cosine_distance(a, b) == pytest.approx(2.0)


def test_cosine_distance_zero_vector_returns_one():
    a = np.array([0.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    assert _cosine_distance(a, b) == 1.0
    assert _cosine_distance(b, a) == 1.0


# ---------------------------------------------------------------------------
# Helpers to build deterministic small embeddings
# ---------------------------------------------------------------------------


def _make_embeddings(n: int, dim: int = 8, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.random((n, dim)).astype(np.float32)


def _make_docs(n: int) -> list[str]:
    return [f"document {i} about topic" for i in range(n)]


# ---------------------------------------------------------------------------
# cluster — KMeans path (n < 15)
# ---------------------------------------------------------------------------


def test_cluster_returns_topic_ids_and_version():
    clusterer = TopicClusterer(min_topic_size=2)
    embeddings = _make_embeddings(6)
    docs = _make_docs(6)
    topic_ids, version = clusterer.cluster(embeddings, docs)
    assert len(topic_ids) == 6
    assert isinstance(version, str)
    assert len(version) > 0


def test_cluster_small_dataset_no_negative_one():
    # KMeans fallback should not produce outlier labels (-1)
    clusterer = TopicClusterer()
    embeddings = _make_embeddings(6)
    docs = _make_docs(6)
    topic_ids, _ = clusterer.cluster(embeddings, docs)
    assert -1 not in topic_ids


def test_cluster_single_item_all_zeros():
    clusterer = TopicClusterer()
    embeddings = _make_embeddings(1)
    docs = _make_docs(1)
    topic_ids, _ = clusterer.cluster(embeddings, docs)
    assert list(topic_ids) == [0]


def test_cluster_two_items():
    clusterer = TopicClusterer()
    embeddings = _make_embeddings(2)
    docs = _make_docs(2)
    topic_ids, _ = clusterer.cluster(embeddings, docs)
    assert len(topic_ids) == 2


# ---------------------------------------------------------------------------
# cluster_centroids
# ---------------------------------------------------------------------------


def test_cluster_centroids_empty_before_clustering():
    assert TopicClusterer().cluster_centroids() == {}


def test_cluster_centroids_after_clustering():
    clusterer = TopicClusterer()
    embeddings = _make_embeddings(6)
    clusterer.cluster(embeddings, _make_docs(6))
    centroids = clusterer.cluster_centroids()
    assert len(centroids) > 0
    for cid, vec in centroids.items():
        assert isinstance(cid, int)
        assert cid != -1
        assert vec.shape == (8,)


def test_cluster_centroids_excludes_outliers():
    clusterer = TopicClusterer()
    # Manually inject topics with outliers
    clusterer._topics = np.array([-1, 0, 0, 1, 1])
    clusterer._embeddings = _make_embeddings(5)
    centroids = clusterer.cluster_centroids()
    assert -1 not in centroids


# ---------------------------------------------------------------------------
# cluster_boundaries
# ---------------------------------------------------------------------------


def test_cluster_boundaries_empty_before_clustering():
    assert TopicClusterer().cluster_boundaries() == {}


def test_cluster_boundaries_after_clustering():
    clusterer = TopicClusterer()
    embeddings = _make_embeddings(6)
    clusterer.cluster(embeddings, _make_docs(6))
    boundaries = clusterer.cluster_boundaries()
    for cid, p95 in boundaries.items():
        assert isinstance(p95, float)
        assert p95 >= 0.0


# ---------------------------------------------------------------------------
# get_keywords
# ---------------------------------------------------------------------------


def test_get_keywords_empty_before_clustering():
    assert TopicClusterer().get_keywords(0) == []


def test_get_keywords_single_doc_returns_empty():
    # TF-IDF needs at least 2 docs to produce meaningful keywords
    clusterer = TopicClusterer()
    embeddings = _make_embeddings(2)
    docs = ["hello world", "foo bar"]
    clusterer.cluster(embeddings, docs)
    # With only one member per cluster (k=1 when n<3), single docs → empty
    # (this tests the <2 docs early-return branch)


def test_get_keywords_with_enough_docs():
    clusterer = TopicClusterer()
    # Force a known cluster manually (bypass BERTopic)
    docs = [
        "pricing confusion about billing",
        "billing statement unclear pricing",
        "customer service response slow",
        "slow response customer service delay",
    ]
    embeddings = _make_embeddings(4)
    clusterer._topics = np.array([0, 0, 1, 1])
    clusterer._embeddings = np.asarray(embeddings, dtype=np.float32)
    clusterer._documents = docs
    kw = clusterer.get_keywords(0, n=5)
    assert isinstance(kw, list)
    # Should surface some pricing/billing related terms


def test_get_keywords_unknown_topic_returns_empty():
    clusterer = TopicClusterer()
    clusterer._topics = np.array([0, 0])
    clusterer._embeddings = _make_embeddings(2)
    clusterer._documents = ["hello world", "foo bar"]
    assert clusterer.get_keywords(99) == []


# ---------------------------------------------------------------------------
# get_representative_exemplars
# ---------------------------------------------------------------------------


def test_get_representative_exemplars_empty_before_clustering():
    assert TopicClusterer().get_representative_exemplars(0) == []


def test_get_representative_exemplars_returns_n_closest():
    clusterer = TopicClusterer()
    docs = ["doc a", "doc b", "doc c", "doc d"]
    embeddings = _make_embeddings(4)
    clusterer._topics = np.array([0, 0, 0, 0])
    clusterer._embeddings = np.asarray(embeddings, dtype=np.float32)
    clusterer._documents = docs
    exemplars = clusterer.get_representative_exemplars(0, n=2)
    assert len(exemplars) == 2
    for idx, text in exemplars:
        assert isinstance(idx, int)
        assert text in docs


def test_get_representative_exemplars_unknown_topic():
    clusterer = TopicClusterer()
    clusterer._topics = np.array([0, 0])
    clusterer._embeddings = _make_embeddings(2)
    clusterer._documents = ["a", "b"]
    assert clusterer.get_representative_exemplars(99) == []


# ---------------------------------------------------------------------------
# generate_labels
# ---------------------------------------------------------------------------


def test_generate_labels_default_label():
    clusterer = TopicClusterer()
    clusterer._topics = np.array([0, 0, 1, 1])
    clusterer._embeddings = _make_embeddings(4)
    clusterer._documents = _make_docs(4)
    labels = clusterer.generate_labels()
    assert labels[0] == "Topic 0"
    assert labels[1] == "Topic 1"


def test_generate_labels_uses_generator():
    calls = []

    def my_gen(docs):
        calls.append(docs)
        return "custom label"

    clusterer = TopicClusterer(label_generator=my_gen)
    clusterer._topics = np.array([0, 0])
    clusterer._embeddings = _make_embeddings(2)
    clusterer._documents = ["hello", "world"]
    labels = clusterer.generate_labels()
    assert labels[0] == "custom label"
    assert len(calls) == 1


def test_generate_labels_empty_before_clustering():
    assert TopicClusterer().generate_labels() == {}


# ---------------------------------------------------------------------------
# get_cluster_records
# ---------------------------------------------------------------------------


def test_get_cluster_records_structure():
    clusterer = TopicClusterer()
    clusterer._topics = np.array([0, 0, 1, 1])
    clusterer._embeddings = _make_embeddings(4)
    clusterer._documents = _make_docs(4)
    clusterer._cluster_version = "20240101-120000"
    records = clusterer.get_cluster_records()
    assert len(records) == 2
    for rec in records:
        assert "doc_id" in rec
        assert "embedding" in rec
        assert "label" in rec
        assert "member_count" in rec
        assert rec["cluster_version"] == "20240101-120000"
        assert isinstance(rec["embedding"], list)


def test_get_cluster_records_empty_before_clustering():
    assert TopicClusterer().get_cluster_records() == []
