"""Tests for reinforcement memory weight functions."""

import pytest

from biblicus.analysis.reinforcement_memory._weights import (
    DEFAULT_PRUNE_THRESHOLD,
    decay,
    initial_weight,
    reinforce,
    should_prune,
    tier_from_weight,
    update_memory_weights,
)

# ---------------------------------------------------------------------------
# initial_weight
# ---------------------------------------------------------------------------


def test_initial_weight_is_neutral():
    assert initial_weight() == 0.5


# ---------------------------------------------------------------------------
# reinforce
# ---------------------------------------------------------------------------


def test_reinforce_increases_weight():
    w = reinforce(0.5, new_docs=10)
    assert w > 0.5


def test_reinforce_clamped_at_one():
    w = reinforce(1.0, new_docs=100)
    assert w == 1.0


def test_reinforce_zero_docs_no_change():
    w = reinforce(0.5, new_docs=0)
    assert w == 0.5


def test_reinforce_small_doc_count_proportional():
    w5 = reinforce(0.5, new_docs=5)
    w10 = reinforce(0.5, new_docs=10)
    assert w5 < w10


def test_reinforce_custom_rate():
    w = reinforce(0.5, new_docs=10, rate=0.2)
    assert w == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# decay
# ---------------------------------------------------------------------------


def test_decay_decreases_weight():
    w = decay(0.5, days=7)
    assert w < 0.5


def test_decay_clamped_at_zero():
    w = decay(0.0, days=100)
    assert w == 0.0


def test_decay_zero_days_no_change():
    w = decay(0.5, days=0)
    assert w == 0.5


def test_decay_proportional_to_days():
    # decay saturates at 7 days; use values within the 0-7 day range
    w2 = decay(0.5, days=2)
    w5 = decay(0.5, days=5)
    assert w2 > w5


def test_decay_saturates_beyond_seven_days():
    # decay is capped at rate * 1.0 per call regardless of days > 7
    w14 = decay(0.5, days=14)
    w100 = decay(0.5, days=100)
    assert w14 == pytest.approx(w100)


def test_decay_custom_rate():
    w = decay(0.5, days=7, rate=0.1)
    assert w == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# tier_from_weight
# ---------------------------------------------------------------------------


def test_tier_hot():
    assert tier_from_weight(0.7) == "hot"
    assert tier_from_weight(1.0) == "hot"


def test_tier_warm():
    assert tier_from_weight(0.3) == "warm"
    assert tier_from_weight(0.69) == "warm"


def test_tier_cold():
    assert tier_from_weight(0.0) == "cold"
    assert tier_from_weight(0.29) == "cold"


def test_tier_custom_thresholds():
    assert tier_from_weight(0.5, hot_threshold=0.8, warm_threshold=0.4) == "warm"
    assert tier_from_weight(0.9, hot_threshold=0.8, warm_threshold=0.4) == "hot"
    assert tier_from_weight(0.3, hot_threshold=0.8, warm_threshold=0.4) == "cold"


# ---------------------------------------------------------------------------
# should_prune
# ---------------------------------------------------------------------------


def test_should_prune_below_threshold():
    assert should_prune(0.05) is True


def test_should_not_prune_above_threshold():
    assert should_prune(0.15) is False


def test_should_prune_at_threshold():
    # boundary: weight == threshold should NOT prune (strictly less-than)
    assert should_prune(DEFAULT_PRUNE_THRESHOLD) is False


def test_should_prune_custom_threshold():
    assert should_prune(0.2, threshold=0.3) is True
    assert should_prune(0.4, threshold=0.3) is False


# ---------------------------------------------------------------------------
# update_memory_weights
# ---------------------------------------------------------------------------


def _cluster(cid, weight=0.5):
    return {"cluster_id": cid, "memory_weight": weight}


def test_update_reinforces_active_clusters():
    clusters = [_cluster(0), _cluster(1)]
    updated, pruned = update_memory_weights(clusters, active_cluster_ids=[0, 1])
    weights = {c["cluster_id"]: c["memory_weight"] for c in updated}
    assert weights[0] > 0.5
    assert weights[1] > 0.5
    assert pruned == []


def test_update_decays_inactive_clusters():
    clusters = [_cluster(0, weight=0.5)]
    updated, pruned = update_memory_weights(clusters, active_cluster_ids=[], days_inactive={0: 7})
    # weight should have decayed but cluster stays above prune threshold
    assert updated[0]["memory_weight"] < 0.5


def test_update_prunes_very_cold_clusters():
    clusters = [_cluster(0, weight=0.05)]
    updated, pruned = update_memory_weights(
        clusters, active_cluster_ids=[], days_inactive={0: 100}, prune=True
    )
    assert 0 in pruned
    assert updated == []


def test_update_no_prune_flag():
    clusters = [_cluster(0, weight=0.05)]
    updated, pruned = update_memory_weights(
        clusters, active_cluster_ids=[], days_inactive={0: 100}, prune=False
    )
    assert pruned == []
    assert len(updated) == 1


def test_update_sets_memory_tier():
    clusters = [_cluster(0, weight=0.5)]
    updated, _ = update_memory_weights(clusters, active_cluster_ids=[0], days_inactive={})
    assert "memory_tier" in updated[0]
    assert updated[0]["memory_tier"] in {"hot", "warm", "cold"}


def test_update_skips_clusters_without_id():
    clusters = [{"memory_weight": 0.5}]  # no cluster_id
    updated, pruned = update_memory_weights(clusters, active_cluster_ids=[])
    assert updated == []
    assert pruned == []


def test_update_string_cluster_id_coerced():
    clusters = [{"cluster_id": "3", "memory_weight": 0.5}]
    updated, _ = update_memory_weights(clusters, active_cluster_ids=[3])
    assert updated[0]["memory_weight"] > 0.5


def test_update_invalid_weight_defaults_to_initial():
    clusters = [{"cluster_id": 0, "memory_weight": "bad"}]
    updated, _ = update_memory_weights(clusters, active_cluster_ids=[0])
    # should use initial_weight() = 0.5 as base, then reinforce
    assert updated[0]["memory_weight"] > 0.5


def test_update_preserves_extra_fields():
    clusters = [{"cluster_id": 0, "memory_weight": 0.5, "label": "my topic"}]
    updated, _ = update_memory_weights(clusters, active_cluster_ids=[0])
    assert updated[0]["label"] == "my topic"


def test_update_empty_clusters():
    updated, pruned = update_memory_weights([], active_cluster_ids=[1, 2])
    assert updated == []
    assert pruned == []


def test_update_days_inactive_defaults_to_seven():
    # no days_inactive entry for cluster 0 → defaults to 7
    updated_explicit, _ = update_memory_weights(
        [_cluster(0, weight=0.5)], active_cluster_ids=[], days_inactive={0: 7}
    )
    updated_default, _ = update_memory_weights(
        [_cluster(0, weight=0.5)], active_cluster_ids=[], days_inactive={}
    )
    assert updated_explicit[0]["memory_weight"] == pytest.approx(
        updated_default[0]["memory_weight"]
    )
