from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

import biblicus.topic_trends as topic_trends
from biblicus.api import TopicTrendsRequest, validate_request
from biblicus.corpus import Corpus
from biblicus.topic_identity import (
    TopicIdentityCluster,
    TopicIdentityGoneCluster,
    TopicIdentityOutput,
    build_topic_identity,
    topic_identity_markdown,
)
from biblicus.topic_trends import TopicTrendOutput, TopicTrendWeeklyBins


def _trend_output(**overrides: object) -> TopicTrendOutput:
    payload: dict[str, object] = {
        "snapshot_id": "snapshot",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "as_of": "2026-01-01",
        "windows": ["all"],
        "rank_window": "all",
    }
    payload.update(overrides)
    return TopicTrendOutput.model_validate(payload)


def test_weekly_bins_are_omitted_from_serialized_output_when_unrequested() -> None:
    """Output without weekly bins serializes without the weekly_bins key."""
    assert "weekly_bins" not in _trend_output().model_dump(mode="json")
    assert "weekly_bins" not in _trend_output().model_dump_json()


def test_weekly_bins_are_serialized_when_present() -> None:
    """Output with weekly bins serializes the weekly_bins block."""
    bins = TopicTrendWeeklyBins(weeks=1, as_of="2026-01-01", undated_items=0)
    assert _trend_output(weekly_bins=bins).model_dump(mode="json")["weekly_bins"]["weeks"] == 1


def test_today_utc_returns_a_date() -> None:
    """The default weekly anchor is the current UTC date."""
    assert isinstance(topic_trends._today_utc(), date)


def test_resolve_weekly_request_defaults_to_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without an as-of date the weekly anchor is today in UTC."""
    monkeypatch.setattr(topic_trends, "_today_utc", lambda: date(2026, 5, 6))
    assert topic_trends._resolve_weekly_request(bin="weekly", weeks=8, as_of=None) == date(
        2026, 5, 6
    )


def test_resolve_weekly_request_rejects_invalid_options() -> None:
    """Weeks without a bin, unknown bins, and out-of-range weeks are rejected."""
    with pytest.raises(ValueError, match="weeks requires bin"):
        topic_trends._resolve_weekly_request(bin=None, weeks=8, as_of=None)
    with pytest.raises(ValueError, match="bin must be weekly"):
        topic_trends._resolve_weekly_request(bin="daily", weeks=None, as_of=None)
    with pytest.raises(ValueError, match="weeks must be between"):
        topic_trends._resolve_weekly_request(bin="weekly", weeks=0, as_of=None)
    assert topic_trends._resolve_weekly_request(bin=None, weeks=None, as_of=None) is None


def test_weekly_counts_ignore_items_outside_the_window() -> None:
    """Items before the first week or after the final week are not counted."""
    first_week = date(2026, 1, 5)
    item_dates = {
        "before": date(2026, 1, 4),
        "first": date(2026, 1, 5),
        "last": date(2026, 1, 18),
        "after": date(2026, 1, 19),
    }
    counts = topic_trends._weekly_counts(
        item_ids=list(item_dates), item_dates=item_dates, first_week=first_week, weeks=2
    )
    assert counts == [1, 1]


def test_week_labels_follow_iso_week_year_boundaries() -> None:
    """ISO week labels use the ISO year, so early January can belong to the previous year."""
    bins = topic_trends._weekly_bins(
        weeks=2,
        anchor=date(2026, 1, 1),
        item_dates={},
        undated_count=0,
        discovered_topics=[],
        canonical_topics=[],
    )
    assert bins.iso_weeks == ["2025-W52", "2026-W01"]
    assert bins.week_starts == ["2025-12-22", "2025-12-29"]


def test_topic_trends_request_rejects_weeks_without_bin() -> None:
    """The typed request names the weeks field when bin is missing."""
    with pytest.raises(Exception, match="weeks"):
        validate_request(
            TopicTrendsRequest,
            "analyze topic-trends",
            corpus_path="corpus",
            topic_modeling_snapshot_id="run",
            weeks=8,
        )


def test_identity_output_rejects_foreign_analysis_identifier() -> None:
    """The output model only accepts the topic identity analysis identifier."""
    with pytest.raises(ValueError, match="analysis_id must be topic-identity"):
        TopicIdentityOutput(
            analysis_id="other",
            run_id="run",
            generated_at="2026-01-01T00:00:00+00:00",
            threshold=0.5,
            document_count=0,
            outlier_document_count=0,
            cluster_count=0,
        )


def test_build_topic_identity_rejects_threshold_outside_range(tmp_path: Path) -> None:
    """A threshold of zero or above one is rejected before any loading."""
    corpus = Corpus.init(tmp_path / "corpus")
    for threshold in (0, 1.5):
        with pytest.raises(ValueError, match="threshold must be greater than 0"):
            build_topic_identity(
                corpus=corpus,
                current_run_id="run",
                previous_run_id=None,
                threshold=threshold,
                trends_snapshot_id=None,
            )


def test_identity_markdown_lists_gone_clusters() -> None:
    """The Markdown report lists clusters that disappeared."""
    output = TopicIdentityOutput(
        run_id="run-b",
        previous_run_id="run-a",
        generated_at="2026-01-01T00:00:00+00:00",
        threshold=0.5,
        document_count=2,
        outlier_document_count=0,
        cluster_count=1,
        event_counts={"new": 1, "gone": 1},
        clusters=[
            TopicIdentityCluster(
                uid="cl-1",
                topic_id=0,
                event="new",
                label="Topic 0",
                top_terms=["alpha"],
                member_item_count=2,
                member_item_ids=["1", "2"],
                first_seen="2026-01-01",
            )
        ],
        gone=[
            TopicIdentityGoneCluster(
                uid="cl-0",
                label="Old",
                member_item_count=1,
                first_seen="2025-12-01",
                last_seen_run_id="run-a",
            )
        ],
    )
    markdown = topic_identity_markdown(output)
    assert "## Gone" in markdown
    assert "`cl-0` Old" in markdown


def test_identity_markdown_omits_gone_section_when_nothing_disappeared() -> None:
    """The Markdown report has no Gone section when every previous cluster matched."""
    output = TopicIdentityOutput(
        run_id="run-b",
        generated_at="2026-01-01T00:00:00+00:00",
        threshold=0.5,
        document_count=0,
        outlier_document_count=0,
        cluster_count=0,
    )
    assert "## Gone" not in topic_identity_markdown(output)
