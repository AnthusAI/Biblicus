from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import biblicus.topic_trends as topic_trends
from biblicus.corpus import Corpus
from biblicus.topic_trends import (
    TopicTrendEntry,
    TopicTrendOutput,
    TopicTrendWindowMetric,
    migrate_publication_dates,
    topic_trends_markdown,
)


def _write_sidecar(corpus: Corpus, name: str, payload: object) -> Path:
    path = corpus.root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def _window_metric(window: str = "all", momentum: float = 1.0) -> TopicTrendWindowMetric:
    return TopicTrendWindowMetric(
        window=window,
        document_count=1,
        corpus_document_count=2,
        share=0.5,
        baseline_share=0.5,
        momentum_score=momentum,
    )


def _entry(label: str, *, topic_id: int | None = 0, momentum: float = 1.0) -> TopicTrendEntry:
    return TopicTrendEntry(
        rank=1,
        topic_id=topic_id,
        label=label,
        keywords=["alpha", "beta"],
        document_count=1,
        trend_eligible_document_count=1,
        document_ids=["item-1"],
        window_metrics={"all": _window_metric(momentum=momentum)},
    )


def _output(**overrides: object) -> TopicTrendOutput:
    payload: dict[str, object] = {
        "snapshot_id": "snapshot",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "as_of": "2026-01-01",
        "windows": ["all"],
        "rank_window": "all",
        "summary": {"trend_eligible_items": 1, "undated_items": 0},
    }
    payload.update(overrides)
    return TopicTrendOutput.model_validate(payload)


def test_output_rejects_foreign_analysis_identifier() -> None:
    """The output model only accepts the topic governance analysis identifier."""
    with pytest.raises(ValueError, match="analysis_id must be topic-governance"):
        _output(analysis_id="something-else")


def test_build_topic_trends_requires_rank_window_in_windows(tmp_path: Path) -> None:
    """A rank window outside the requested windows is rejected before any loading."""
    corpus = Corpus.init(tmp_path / "corpus")
    with pytest.raises(ValueError, match="rank_window must be included in windows"):
        topic_trends.build_topic_trends(
            corpus=corpus,
            topic_modeling_snapshot_id="missing",
            classifier_id=None,
            windows=["30d"],
            as_of=None,
            rank_window="90d",
        )


def test_build_topic_trends_reports_missing_topic_modeling_output(tmp_path: Path) -> None:
    """A missing topic modeling snapshot raises a clear file error."""
    corpus = Corpus.init(tmp_path / "corpus")
    with pytest.raises(FileNotFoundError, match="Missing topic modeling output"):
        topic_trends.build_topic_trends(
            corpus=corpus,
            topic_modeling_snapshot_id="missing",
            classifier_id=None,
            windows=["all"],
            as_of=None,
            rank_window="all",
        )


def test_migrate_publication_dates_moves_legacy_fields(tmp_path: Path) -> None:
    """Legacy published and updated fields move into dates with provenance."""
    corpus = Corpus.init(tmp_path / "corpus")
    sidecar = _write_sidecar(
        corpus,
        "paper.pdf.biblicus.yml",
        {"published": "2024-01-02", "updated": "2024-02-03", "title": "Paper"},
    )
    _write_sidecar(corpus, "clean.pdf.biblicus.yml", {"title": "Clean"})
    result = migrate_publication_dates(corpus=corpus)
    migrated = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    assert result.scanned_sidecars >= 2
    assert result.migrated_sidecars == 1
    assert result.migrated_fields == {"published_at": 1, "updated_at": 1}
    assert migrated["dates"] == {"published_at": "2024-01-02", "updated_at": "2024-02-03"}
    assert migrated["date_provenance"]["published_at"] == "metadata-migration"
    assert "published" not in migrated


def test_migrate_publication_dates_accepts_matching_existing_values(tmp_path: Path) -> None:
    """A legacy value equal to the canonical value is migrated without conflict."""
    corpus = Corpus.init(tmp_path / "corpus")
    sidecar = _write_sidecar(
        corpus,
        "paper.pdf.biblicus.yml",
        {
            "published": "2024-01-02",
            "dates": {"published_at": "2024-01-02"},
            "date_provenance": {"published_at": "manual"},
        },
    )
    result = migrate_publication_dates(corpus=corpus)
    migrated = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    assert result.migrated_fields == {"published_at": 1}
    assert migrated["date_provenance"]["published_at"] == "manual"


def test_migrate_publication_dates_rejects_conflicting_values(tmp_path: Path) -> None:
    """A legacy value that disagrees with the canonical value is an error."""
    corpus = Corpus.init(tmp_path / "corpus")
    _write_sidecar(
        corpus,
        "paper.pdf.biblicus.yml",
        {"published": "2024-01-02", "dates": {"published_at": "2023-01-01"}},
    )
    with pytest.raises(ValueError, match="Legacy published conflicts with dates.published_at"):
        migrate_publication_dates(corpus=corpus)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (["not", "a", "mapping"], "Sidecar metadata must be a mapping/object"),
        ({"dates": "text"}, "Sidecar dates must be a mapping/object"),
        ({"date_provenance": "text"}, "Sidecar date_provenance must be a mapping/object"),
    ],
)
def test_migrate_publication_dates_rejects_malformed_sidecars(
    tmp_path: Path, payload: object, message: str
) -> None:
    """Malformed sidecar structures raise descriptive errors."""
    corpus = Corpus.init(tmp_path / "corpus")
    _write_sidecar(corpus, "paper.pdf.biblicus.yml", payload)
    with pytest.raises(ValueError, match=message):
        migrate_publication_dates(corpus=corpus)


def test_migrate_publication_dates_tolerates_null_blocks(tmp_path: Path) -> None:
    """Null dates and provenance blocks are treated as empty mappings."""
    corpus = Corpus.init(tmp_path / "corpus")
    sidecar = _write_sidecar(
        corpus,
        "paper.pdf.biblicus.yml",
        {"updated": "2024-05-05", "dates": None, "date_provenance": None},
    )
    result = migrate_publication_dates(corpus=corpus)
    migrated = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    assert result.migrated_fields == {"updated_at": 1}
    assert migrated["dates"] == {"updated_at": "2024-05-05"}


def test_markdown_renders_empty_sections_and_warnings() -> None:
    """Empty topic lists and proposals render placeholders and warnings."""
    markdown = topic_trends_markdown(_output(warnings=["something odd"]))
    assert "No topics." in markdown
    assert "No proposals." in markdown
    assert "## Warnings" in markdown
    assert "- something odd" in markdown


def test_markdown_renders_topic_rows_and_proposals() -> None:
    """Topic rows and proposal rows appear in the rendered tables."""
    discovered = [_entry("Alpha | Beta")]
    proposals = topic_trends._governance_proposals(discovered_topics=discovered, rank_window="all")
    markdown = topic_trends_markdown(_output(discovered_topics=discovered, proposals=proposals))
    assert "Alpha \\| Beta" in markdown
    assert "new-topic:alpha-beta" in markdown
    assert "| 1 | 0 |" in markdown
    assert "No proposals." not in markdown


def test_parse_windows_splits_commas_and_validates() -> None:
    """Window parsing flattens comma lists and rejects empty or unknown units."""
    assert topic_trends._parse_windows(["30d, 1y", "all", " "]) == ["30d", "1y", "all"]
    with pytest.raises(ValueError, match="At least one trend window is required"):
        topic_trends._parse_windows([" , "])
    with pytest.raises(ValueError, match="Trend windows must use d, y, or all"):
        topic_trends._parse_windows(["5w"])


def test_window_days_converts_units() -> None:
    """Window units convert to day counts, with all meaning unbounded."""
    assert topic_trends._window_days("all") is None
    assert topic_trends._window_days("7d") == 7
    assert topic_trends._window_days("2y") == 730


def test_trend_item_dates_classifies_missing_and_invalid_dates() -> None:
    """Items with missing or unparsable publication dates are excluded with warnings."""
    items = {
        "good": SimpleNamespace(dates=SimpleNamespace(published_at="2024-03-01")),
        "no-block": SimpleNamespace(dates=None),
        "empty": SimpleNamespace(dates=SimpleNamespace(published_at="")),
        "bad": SimpleNamespace(dates=SimpleNamespace(published_at="not-a-date")),
        "blank": SimpleNamespace(dates=SimpleNamespace(published_at="   ")),
    }
    item_dates, excluded, warnings = topic_trends._trend_item_dates(items)
    assert item_dates == {"good": date(2024, 3, 1)}
    assert excluded == ["bad", "blank", "empty", "no-block"]
    assert any("missing dates.published_at" in warning for warning in warnings)
    assert any("invalid dates.published_at" in warning for warning in warnings)


def test_parse_publication_date_handles_timestamps() -> None:
    """Timestamps normalize to UTC dates and empty strings are rejected."""
    assert topic_trends._parse_publication_date("2024-03-01") == date(2024, 3, 1)
    assert topic_trends._parse_publication_date("2024-03-01T23:30:00-05:00") == date(2024, 3, 2)
    assert topic_trends._parse_publication_date("2024-03-01T10:00:00Z") == date(2024, 3, 1)
    assert topic_trends._parse_publication_date("2024-03-01T10:00:00") == date(2024, 3, 1)
    with pytest.raises(ValueError, match="must not be empty"):
        topic_trends._parse_publication_date("  ")


def test_resolve_as_of_prefers_explicit_then_latest_item() -> None:
    """The anchor is the explicit date, else the newest item date, else an error."""
    item_dates = {"a": date(2024, 1, 1), "b": date(2024, 6, 1)}
    assert topic_trends._resolve_as_of(as_of="2024-02-02", item_dates=item_dates) == date(
        2024, 2, 2
    )
    assert topic_trends._resolve_as_of(as_of=None, item_dates=item_dates) == date(2024, 6, 1)
    with pytest.raises(ValueError, match="at least one item with dates.published_at"):
        topic_trends._resolve_as_of(as_of=None, item_dates={})


def test_window_items_filters_by_window_and_anchor() -> None:
    """Window filtering excludes items after the anchor and before the window start."""
    item_dates = {"old": date(2020, 1, 1), "recent": date(2024, 5, 20), "future": date(2025, 1, 1)}
    anchor = date(2024, 6, 1)
    ids = ["old", "recent", "future"]
    assert topic_trends._window_items(
        item_ids=ids, item_dates=item_dates, window="30d", as_of=anchor
    ) == ["recent"]
    assert topic_trends._window_items(
        item_ids=ids, item_dates=item_dates, window="all", as_of=anchor
    ) == ["old", "recent"]


def test_topic_label_prefers_meaningful_keywords() -> None:
    """Topic labels use up to two meaningful keywords and fall back to the identifier."""
    assert topic_trends._topic_label(["agent", "memory", "x"], topic_id=3) == "agent memory"
    assert topic_trends._topic_label(["et", "agent"], topic_id=3) == "agent"
    assert topic_trends._topic_label([], topic_id=3) == "Topic 3"


def test_meaningful_keywords_falls_back_when_all_are_stopwords() -> None:
    """When every keyword is a stopword the original list is kept."""
    assert topic_trends._meaningful_keywords(["et", "al"]) == ["et", "al"]
    assert topic_trends._meaningful_keywords(["et", "agent"]) == ["agent"]


def test_slug_from_keywords_uses_fallback_and_default() -> None:
    """Slugs use two keywords, then the fallback label, then a default name."""
    assert topic_trends._slug_from_keywords(["Agent", "Memory!"], fallback="x") == "agent-memory"
    assert topic_trends._slug_from_keywords(["Solo"], fallback="Fallback Label") == "fallback-label"
    assert topic_trends._slug_from_keywords([], fallback="!!!") == "discovered-topic"


def test_display_name_capitalizes_slug_parts() -> None:
    """Display names title-case each hyphenated slug part."""
    assert topic_trends._display_name("agent-memory") == "Agent Memory"


def test_governance_proposals_skip_outliers_and_undated_topics() -> None:
    """The outlier topic and topics without dated documents produce no proposal."""
    undated = _entry("Undated", topic_id=2).model_copy(update={"trend_eligible_document_count": 0})
    topics = [_entry("Outlier", topic_id=-1), undated, _entry("Real", topic_id=1)]
    proposals = topic_trends._governance_proposals(discovered_topics=topics, rank_window="all")
    assert [proposal.proposal_id for proposal in proposals] == ["new-topic:alpha-beta"]


def test_rank_rows_orders_by_momentum_then_count_then_label() -> None:
    """Ranking sorts by descending momentum and breaks ties by label."""
    rows = [_entry("b", momentum=1.0), _entry("a", momentum=1.0), _entry("c", momentum=3.0)]
    ranked = topic_trends._rank_rows(rows=rows, rank_window="all")
    assert [(row.rank, row.label) for row in ranked] == [(1, "c"), (2, "a"), (3, "b")]


def test_metrics_for_items_handles_empty_corpus_windows() -> None:
    """Empty corpus windows yield zero shares and momentum."""
    metrics = topic_trends._metrics_for_items(
        item_ids=["a"],
        item_dates={"a": date(2024, 1, 1)},
        corpus_windows={"all": 0, "30d": 0},
        windows=["30d"],
        as_of=date(2024, 1, 2),
    )
    assert metrics["30d"].share == 0.0
    assert metrics["30d"].momentum_score == 0.0


def test_canonical_trends_without_classifier_warns() -> None:
    """Without a classifier the canonical list is empty and a warning is returned."""
    rows, warnings = topic_trends._canonical_topic_trends(
        corpus=None,
        classifier_id=None,
        topic_modeling_output=None,
        item_ids=[],
        item_dates={},
        corpus_windows={},
        windows=["all"],
        as_of=date(2024, 1, 1),
        rank_window="all",
    )
    assert rows == []
    assert "No classifier was provided" in warnings[0]


def test_canonical_trends_group_predictions_and_collect_errors(monkeypatch) -> None:
    """Predictions group by topic, unassigned items are skipped, and errors become warnings."""
    predictions = {
        "one": SimpleNamespace(topic_uid="agents", display_name="Agents"),
        "two": SimpleNamespace(topic_uid="agents", display_name=None),
        "three": SimpleNamespace(topic_uid=None, display_name=None),
        "four": ValueError("no extracted text for four"),
    }

    def fake_classify(*, item_id: str, **_: object) -> object:
        prediction = predictions[item_id]
        if isinstance(prediction, Exception):
            raise prediction
        return prediction

    monkeypatch.setattr(topic_trends, "_load_model_bundle", lambda **_: {"run_dir": Path("unused")})
    monkeypatch.setattr(topic_trends, "_load_bertopic_model", lambda _path: object())
    monkeypatch.setattr(topic_trends, "_classify_item_with_bundle", fake_classify)
    reference = {"extractor_id": "pipeline", "snapshot_id": "snap"}
    topic_modeling_output = SimpleNamespace(
        snapshot=SimpleNamespace(
            input=SimpleNamespace(
                extraction_snapshot=SimpleNamespace(model_dump=lambda mode: reference)
            )
        )
    )
    item_dates = {name: date(2024, 1, 1) for name in predictions}
    rows, warnings = topic_trends._canonical_topic_trends(
        corpus=None,
        classifier_id="classifier",
        topic_modeling_output=topic_modeling_output,
        item_ids=list(predictions),
        item_dates=item_dates,
        corpus_windows={"all": 4},
        windows=["all"],
        as_of=date(2024, 1, 2),
        rank_window="all",
    )
    assert warnings == ["no extracted text for four"]
    assert len(rows) == 1
    assert rows[0].topic_uid == "agents"
    assert rows[0].label == "Agents"
    assert rows[0].document_ids == ["one", "two"]


def test_output_accepts_topic_governance_analysis_identifier() -> None:
    """The default analysis identifier passes validation unchanged."""
    assert _output(analysis_id="topic-governance").analysis_id == "topic-governance"


class _FakeTrendCorpus:
    def __init__(self, root: Path, items: dict) -> None:
        self.root = root
        self.analysis_dir = root / "analysis"
        self._items = items

    def load_catalog(self) -> SimpleNamespace:
        return SimpleNamespace(items=self._items, generated_at="2026-01-01T00:00:00+00:00")

    def analysis_run_dir(self, *, analysis_id: str, snapshot_id: str) -> Path:
        return self.analysis_dir / analysis_id / snapshot_id


def test_build_topic_trends_ranks_topics_and_writes_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A full build ranks discovered topics, proposes governance, and writes artifacts."""
    items = {
        "recent-a": SimpleNamespace(dates=SimpleNamespace(published_at="2024-06-01")),
        "recent-b": SimpleNamespace(dates=SimpleNamespace(published_at="2024-05-25")),
        "old": SimpleNamespace(dates=SimpleNamespace(published_at="2020-01-01")),
        "undated": SimpleNamespace(dates=None),
    }
    topics = [
        SimpleNamespace(
            topic_id=0,
            label="",
            keywords=[SimpleNamespace(keyword="agent"), SimpleNamespace(keyword="memory")],
            document_ids=["recent-a", "recent-b", "undated"],
        ),
        SimpleNamespace(
            topic_id=1,
            label="Legacy Systems",
            keywords=[SimpleNamespace(keyword="legacy")],
            document_ids=["old"],
        ),
        SimpleNamespace(topic_id=-1, label="Outliers", keywords=[], document_ids=["old"]),
    ]
    monkeypatch.setattr(
        topic_trends,
        "_load_topic_modeling_output",
        lambda **_: SimpleNamespace(report=SimpleNamespace(topics=topics)),
    )
    corpus = _FakeTrendCorpus(tmp_path, items)
    output = topic_trends.build_topic_trends(
        corpus=corpus,
        topic_modeling_snapshot_id="tm",
        classifier_id=None,
        windows=["30d,all"],
        as_of=None,
        rank_window="30d",
    )
    assert output.as_of == "2024-06-01"
    assert output.discovered_topics[0].label == "agent memory"
    assert output.discovered_topics[0].rank == 1
    assert output.summary["undated_items"] == 1
    assert [proposal.proposal_id for proposal in output.proposals][0] == "new-topic:agent-memory"
    assert any("No classifier was provided" in warning for warning in output.warnings)
    assert Path(output.artifact_paths["report"]).is_file()
    assert (tmp_path / "analysis" / "topic-governance" / "latest.json").is_file()
