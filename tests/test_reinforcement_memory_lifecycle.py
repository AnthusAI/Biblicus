"""Tests for reinforcement memory lifecycle tier derivation."""

from datetime import datetime, timezone, timedelta

import pytest

from biblicus.analysis.reinforcement_memory._lifecycle import (
    _parse_timestamp,
    derive_lifecycle,
)


def _iso(days_ago: int, now: datetime) -> str:
    dt = now - timedelta(days=days_ago)
    return dt.isoformat()


NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# _parse_timestamp
# ---------------------------------------------------------------------------


def test_parse_z_suffix():
    dt = _parse_timestamp("2024-01-15T10:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_offset_suffix():
    dt = _parse_timestamp("2024-01-15T10:00:00+00:00")
    assert dt is not None


def test_parse_no_timezone_assumes_utc():
    dt = _parse_timestamp("2024-01-15T10:00:00")
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_parse_invalid_returns_none():
    assert _parse_timestamp("not-a-date") is None


def test_parse_empty_returns_none():
    assert _parse_timestamp("") is None


def test_parse_none_like_returns_none():
    assert _parse_timestamp(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# derive_lifecycle — no timestamps
# ---------------------------------------------------------------------------


def test_empty_timestamps_established_no_inactive():
    tier, is_new, is_trending, days_inactive = derive_lifecycle([], now=NOW)
    assert tier == "established"
    assert is_new is False
    assert is_trending is False
    assert days_inactive is None


# ---------------------------------------------------------------------------
# derive_lifecycle — new (only short-term members)
# ---------------------------------------------------------------------------


def test_new_tier_only_short_term():
    ts = [_iso(5, NOW), _iso(10, NOW)]
    tier, is_new, is_trending, days_inactive = derive_lifecycle(ts, now=NOW)
    assert tier == "new"
    assert is_new is True
    assert is_trending is True
    assert days_inactive == 5


def test_new_tier_single_recent():
    ts = [_iso(1, NOW)]
    tier, is_new, _, _ = derive_lifecycle(ts, now=NOW)
    assert tier == "new"
    assert is_new is True


# ---------------------------------------------------------------------------
# derive_lifecycle — trending (short/medium but no long-term)
# ---------------------------------------------------------------------------


def test_trending_short_and_medium():
    ts = [_iso(5, NOW), _iso(20, NOW)]
    tier, is_new, is_trending, _ = derive_lifecycle(ts, now=NOW)
    assert tier == "trending"
    assert is_new is False
    assert is_trending is True


def test_trending_medium_only():
    ts = [_iso(16, NOW), _iso(28, NOW)]
    tier, is_new, is_trending, _ = derive_lifecycle(ts, now=NOW)
    assert tier == "trending"
    assert is_new is False
    assert is_trending is True


# ---------------------------------------------------------------------------
# derive_lifecycle — established (has long-term members)
# ---------------------------------------------------------------------------


def test_established_has_long_term():
    ts = [_iso(5, NOW), _iso(45, NOW)]
    tier, is_new, is_trending, _ = derive_lifecycle(ts, now=NOW)
    assert tier == "established"
    assert is_new is False
    assert is_trending is False


def test_established_only_long_term():
    ts = [_iso(60, NOW), _iso(90, NOW)]
    tier, _, is_trending, _ = derive_lifecycle(ts, now=NOW)
    assert tier == "established"
    assert is_trending is False


# ---------------------------------------------------------------------------
# derive_lifecycle — days_inactive
# ---------------------------------------------------------------------------


def test_days_inactive_most_recent():
    ts = [_iso(3, NOW), _iso(10, NOW)]
    _, _, _, days_inactive = derive_lifecycle(ts, now=NOW)
    assert days_inactive == 3


def test_days_inactive_single():
    ts = [_iso(7, NOW)]
    _, _, _, days_inactive = derive_lifecycle(ts, now=NOW)
    assert days_inactive == 7


# ---------------------------------------------------------------------------
# derive_lifecycle — boundary conditions on window thresholds
# ---------------------------------------------------------------------------


def test_boundary_short_term_edge():
    # exactly 14 days ago → short-term
    ts = [_iso(14, NOW)]
    tier, is_new, _, _ = derive_lifecycle(ts, now=NOW)
    assert tier == "new"
    assert is_new is True


def test_boundary_medium_term_edge():
    # exactly 15 days ago → medium-term (not short)
    ts = [_iso(15, NOW)]
    tier, is_new, is_trending, _ = derive_lifecycle(ts, now=NOW)
    assert is_new is False
    assert is_trending is True


def test_boundary_long_term_edge():
    # exactly 30 days ago → medium (boundary still trending)
    ts = [_iso(30, NOW)]
    tier, _, is_trending, _ = derive_lifecycle(ts, now=NOW)
    assert is_trending is True


def test_boundary_just_past_long_term():
    # 31 days ago → long-term → established
    ts = [_iso(31, NOW)]
    tier, _, _, _ = derive_lifecycle(ts, now=NOW)
    assert tier == "established"


# ---------------------------------------------------------------------------
# derive_lifecycle — invalid timestamps ignored
# ---------------------------------------------------------------------------


def test_invalid_timestamps_ignored():
    ts = ["not-a-date", _iso(5, NOW)]
    tier, is_new, _, days_inactive = derive_lifecycle(ts, now=NOW)
    assert tier == "new"
    assert is_new is True
    assert days_inactive == 5


def test_all_invalid_timestamps_fallback():
    tier, is_new, is_trending, days_inactive = derive_lifecycle(
        ["bad", "also-bad"], now=NOW
    )
    assert tier == "established"
    assert days_inactive is None


# ---------------------------------------------------------------------------
# derive_lifecycle — custom window sizes
# ---------------------------------------------------------------------------


def test_custom_short_term_window():
    ts = [_iso(7, NOW)]
    tier, is_new, _, _ = derive_lifecycle(ts, now=NOW, short_term_days=5)
    # 7 days > 5 day short-term window → not new
    assert is_new is False


def test_custom_medium_term_window():
    ts = [_iso(25, NOW)]
    _, _, is_trending, _ = derive_lifecycle(ts, now=NOW, medium_term_days=20)
    # 25 days > 20 day medium-term window → long-term → not trending
    assert is_trending is False
