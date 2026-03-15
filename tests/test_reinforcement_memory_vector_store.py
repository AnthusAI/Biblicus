"""Tests for the vector store module (Protocol + LocalVectorStore + S3VectorStore)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call

import numpy as np
import pytest

from biblicus.analysis.reinforcement_memory._models import QueryResult, VectorRecord
from biblicus.analysis.reinforcement_memory._vector_store import (
    LocalVectorStore,
    S3VectorStore,
    VectorStore,
    _cosine_similarity,
)

# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------


def test_cosine_similarity_identical():
    a = np.array([1.0, 0.0, 0.0])
    assert _cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert _cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 0.0])
    assert _cosine_similarity(a, b) == 0.0


# ---------------------------------------------------------------------------
# LocalVectorStore — construction
# ---------------------------------------------------------------------------


def test_local_store_creates_directory(tmp_path):
    d = tmp_path / "vectors"
    LocalVectorStore(str(d))
    assert d.exists()


def test_local_store_satisfies_protocol(tmp_path):
    store = LocalVectorStore(str(tmp_path / "v"))
    assert isinstance(store, VectorStore)


# ---------------------------------------------------------------------------
# LocalVectorStore — health_check
# ---------------------------------------------------------------------------


def test_local_store_health_check_always_true(tmp_path):
    store = LocalVectorStore(str(tmp_path))
    assert store.health_check() is True


# ---------------------------------------------------------------------------
# LocalVectorStore — put_vectors / list_all
# ---------------------------------------------------------------------------


def _vec(key, dim=4, value=0.5, metadata=None):
    return VectorRecord(
        key=key,
        embedding=[value] * dim,
        metadata=metadata or {},
    )


def test_put_and_list_single(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    store.put_vectors([_vec("k1")])
    records = store.list_all()
    assert len(records) == 1
    assert records[0].key == "k1"


def test_put_multiple_vectors(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    store.put_vectors([_vec("a"), _vec("b"), _vec("c")])
    assert len(store.list_all()) == 3


def test_put_idempotent(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    store.put_vectors([_vec("k1", value=0.1)])
    store.put_vectors([_vec("k1", value=0.9)])
    records = store.list_all()
    assert len(records) == 1
    assert records[0].embedding[0] == pytest.approx(0.9)


def test_put_preserves_metadata(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    store.put_vectors([_vec("k1", metadata={"label": "pricing", "tier": "hot"})])
    rec = store.list_all()[0]
    assert rec.metadata["label"] == "pricing"
    assert rec.metadata["tier"] == "hot"


def test_list_all_empty(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    assert store.list_all() == []


def test_list_all_skips_malformed_files(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    bad = tmp_path / "bad.json"
    bad.write_text("not-json")
    store.put_vectors([_vec("k1")])
    records = store.list_all()
    assert len(records) == 1  # bad file skipped


def test_key_with_slashes_stored_safely(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    store.put_vectors([_vec("cluster:0/foo")])
    records = store.list_all()
    assert len(records) == 1
    assert records[0].key == "cluster:0/foo"


# ---------------------------------------------------------------------------
# LocalVectorStore — delete_all
# ---------------------------------------------------------------------------


def test_delete_all_removes_vectors(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    store.put_vectors([_vec("a"), _vec("b")])
    deleted = store.delete_all()
    assert deleted == 2
    assert store.list_all() == []


def test_delete_all_empty_store(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    assert store.delete_all() == 0


# ---------------------------------------------------------------------------
# LocalVectorStore — query_nearest
# ---------------------------------------------------------------------------


def _distinct_vectors(n, dim=4):
    """Return n orthogonal-ish vectors."""
    vecs = []
    for i in range(n):
        emb = [0.0] * dim
        emb[i % dim] += 1.0
        vecs.append(emb)
    return vecs


def test_query_nearest_returns_closest(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    # k1 is identical to query; k2 is orthogonal
    store.put_vectors(
        [
            VectorRecord("k1", [1.0, 0.0, 0.0, 0.0]),
            VectorRecord("k2", [0.0, 1.0, 0.0, 0.0]),
        ]
    )
    query = np.array([1.0, 0.0, 0.0, 0.0])
    results = store.query_nearest(query, k=1)
    assert len(results) == 1
    assert results[0].key == "k1"
    assert results[0].similarity == pytest.approx(1.0)


def test_query_nearest_respects_k(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    for i, emb in enumerate(_distinct_vectors(5)):
        store.put_vectors([VectorRecord(f"k{i}", emb)])
    query = np.array([1.0, 0.0, 0.0, 0.0])
    results = store.query_nearest(query, k=2)
    assert len(results) == 2


def test_query_nearest_ordered_by_similarity(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    store.put_vectors(
        [
            VectorRecord("best", [1.0, 0.0, 0.0, 0.0]),
            VectorRecord("ok", [0.8, 0.2, 0.0, 0.0]),
            VectorRecord("worst", [0.0, 1.0, 0.0, 0.0]),
        ]
    )
    query = np.array([1.0, 0.0, 0.0, 0.0])
    results = store.query_nearest(query, k=3)
    sims = [r.similarity for r in results]
    assert sims == sorted(sims, reverse=True)


def test_query_nearest_threshold_filters(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    store.put_vectors(
        [
            VectorRecord("close", [1.0, 0.0, 0.0, 0.0]),
            VectorRecord("far", [0.0, 1.0, 0.0, 0.0]),
        ]
    )
    query = np.array([1.0, 0.0, 0.0, 0.0])
    results = store.query_nearest(query, k=5, threshold=0.5)
    assert all(r.similarity >= 0.5 for r in results)


def test_query_nearest_empty_store(tmp_path):
    store = LocalVectorStore(str(tmp_path), embedding_dim=4)
    results = store.query_nearest(np.array([1.0, 0.0, 0.0, 0.0]), k=5)
    assert results == []


# ---------------------------------------------------------------------------
# S3VectorStore — mocked boto3 client
# ---------------------------------------------------------------------------


def _s3_store(dim=4, mock_client=None):
    client = mock_client or MagicMock()
    return S3VectorStore(
        bucket_name="test-bucket",
        index_name="test-index",
        region="us-east-1",
        embedding_dim=dim,
        client=client,
    )


def test_s3_store_satisfies_protocol():
    store = _s3_store()
    assert isinstance(store, VectorStore)


def test_s3_health_check_true_on_success():
    client = MagicMock()
    client.get_index.return_value = {}
    store = _s3_store(mock_client=client)
    assert store.health_check() is True


def test_s3_health_check_false_on_error():
    client = MagicMock()
    client.get_index.side_effect = Exception("unreachable")
    store = _s3_store(mock_client=client)
    assert store.health_check() is False


def test_s3_put_vectors_calls_put_vectors():
    client = MagicMock()
    store = _s3_store(dim=4, mock_client=client)
    store.put_vectors([VectorRecord("k1", [0.1, 0.2, 0.3, 0.4])])
    assert client.put_vectors.called
    args = client.put_vectors.call_args
    vectors_sent = args.kwargs.get("vectors") or args[1].get("vectors") or args[0][-1]
    assert vectors_sent[0]["key"] == "k1"


def test_s3_put_vectors_skips_wrong_dim():
    client = MagicMock()
    store = _s3_store(dim=4, mock_client=client)
    store.put_vectors([VectorRecord("k1", [0.1, 0.2])])  # 2 dims, not 4
    client.put_vectors.assert_not_called()


def test_s3_delete_all_returns_count():
    client = MagicMock()
    client.list_vectors.return_value = {
        "vectors": [{"key": "a"}, {"key": "b"}],
        "nextToken": None,
    }
    store = _s3_store(mock_client=client)
    deleted = store.delete_all()
    assert deleted == 2
    assert client.delete_vectors.called


def test_s3_delete_all_empty():
    client = MagicMock()
    client.list_vectors.return_value = {"vectors": [], "nextToken": None}
    store = _s3_store(mock_client=client)
    assert store.delete_all() == 0
    client.delete_vectors.assert_not_called()


def test_s3_query_nearest_returns_results():
    client = MagicMock()
    client.query_vectors.return_value = {
        "vectors": [
            {"key": "k1", "distance": 0.1, "metadata": {"label": "foo"}},
            {"key": "k2", "distance": 0.4, "metadata": {}},
        ]
    }
    store = _s3_store(dim=4, mock_client=client)
    results = store.query_nearest(np.array([0.1, 0.2, 0.3, 0.4]), k=2)
    assert len(results) == 2
    assert results[0].key == "k1"
    assert results[0].similarity == pytest.approx(0.9)


def test_s3_query_nearest_threshold_applied():
    client = MagicMock()
    client.query_vectors.return_value = {
        "vectors": [
            {"key": "close", "distance": 0.1, "metadata": {}},
            {"key": "far", "distance": 0.8, "metadata": {}},
        ]
    }
    store = _s3_store(dim=4, mock_client=client)
    results = store.query_nearest(np.array([0.1, 0.2, 0.3, 0.4]), k=5, threshold=0.5)
    assert len(results) == 1
    assert results[0].key == "close"


def test_s3_query_nearest_wrong_dim_returns_empty():
    client = MagicMock()
    store = _s3_store(dim=4, mock_client=client)
    results = store.query_nearest(np.array([0.1, 0.2]), k=5)
    assert results == []
    client.query_vectors.assert_not_called()


def test_s3_query_nearest_error_returns_empty():
    client = MagicMock()
    client.query_vectors.side_effect = Exception("timeout")
    store = _s3_store(dim=4, mock_client=client)
    results = store.query_nearest(np.array([0.1, 0.2, 0.3, 0.4]), k=5)
    assert results == []


def test_s3_uses_index_arn_when_provided():
    client = MagicMock()
    client.get_index.return_value = {}
    store = S3VectorStore(
        bucket_name="b",
        index_name="i",
        region="us-east-1",
        index_arn="arn:aws:s3vectors:us-east-1:123:bucket/b/index/i",
        client=client,
    )
    store.health_check()
    args = client.get_index.call_args
    assert "indexArn" in (args.kwargs or args[1])
