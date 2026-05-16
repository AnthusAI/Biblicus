"""
Temporal topic intelligence workflows.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

import yaml
from pydantic import Field, field_validator

from .analysis.models import TopicModelingOutput
from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .models import ExtractionSnapshotReference
from .retrieval import hash_text
from .steering_proposals import SteeringProposal, topic_governance_proposal
from .topic_classifier import (
    _classify_item_with_bundle,
    _load_bertopic_model,
    _load_model_bundle,
)

TOPIC_GOVERNANCE_ANALYSIS_ID = "topic-governance"
PROPOSAL_KEYWORD_STOPWORDS = {"al", "et", "paper", "eq"}


class TopicTrendWindowMetric(AnalysisSchemaModel):
    """
    Publication-window metric for a topic.

    :ivar window: Window identifier.
    :vartype window: str
    :ivar document_count: Topic documents inside the window.
    :vartype document_count: int
    :ivar corpus_document_count: Corpus documents inside the window.
    :vartype corpus_document_count: int
    :ivar share: Topic share inside the window.
    :vartype share: float
    :ivar baseline_share: Topic all-time share.
    :vartype baseline_share: float
    :ivar momentum_score: Window share divided by baseline share.
    :vartype momentum_score: float
    """

    window: str = Field(min_length=1)
    document_count: int = Field(ge=0)
    corpus_document_count: int = Field(ge=0)
    share: float = Field(ge=0)
    baseline_share: float = Field(ge=0)
    momentum_score: float = Field(ge=0)


class TopicTrendEntry(AnalysisSchemaModel):
    """
    Ranked topic trend row.

    :ivar rank: Rank within its topic list.
    :vartype rank: int
    :ivar topic_id: BERTopic topic identifier for discovered topics.
    :vartype topic_id: int or None
    :ivar topic_uid: Canonical topic identity for classifier topics.
    :vartype topic_uid: str or None
    :ivar label: Human-readable topic label.
    :vartype label: str
    :ivar keywords: Topic keywords.
    :vartype keywords: list[str]
    :ivar document_count: Total topic documents in the snapshot.
    :vartype document_count: int
    :ivar trend_eligible_document_count: Topic documents with dates.published_at.
    :vartype trend_eligible_document_count: int
    :ivar document_ids: Topic document identifiers.
    :vartype document_ids: list[str]
    :ivar window_metrics: Metrics keyed by window.
    :vartype window_metrics: dict[str, TopicTrendWindowMetric]
    """

    rank: int = Field(ge=1)
    topic_id: Optional[int] = None
    topic_uid: Optional[str] = None
    label: str = Field(min_length=1)
    keywords: List[str] = Field(default_factory=list)
    document_count: int = Field(ge=0)
    trend_eligible_document_count: int = Field(ge=0)
    document_ids: List[str] = Field(default_factory=list)
    window_metrics: Dict[str, TopicTrendWindowMetric] = Field(default_factory=dict)


class TopicTrendOutput(AnalysisSchemaModel):
    """
    Topic trend analysis output.

    :ivar schema_version: Schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier.
    :vartype analysis_id: str
    :ivar snapshot_id: Topic governance snapshot identifier.
    :vartype snapshot_id: str
    :ivar generated_at: Deterministic generation timestamp derived from as_of.
    :vartype generated_at: str
    :ivar inputs: Reproducibility inputs.
    :vartype inputs: dict[str, Any]
    :ivar as_of: Publication date used as the window anchor.
    :vartype as_of: str
    :ivar windows: Window identifiers.
    :vartype windows: list[str]
    :ivar rank_window: Window used for ranking.
    :vartype rank_window: str
    :ivar summary: Corpus-level trend summary.
    :vartype summary: dict[str, Any]
    :ivar canonical_topics: Ranked canonical topic coverage.
    :vartype canonical_topics: list[TopicTrendEntry]
    :ivar discovered_topics: Ranked discovered topic trends.
    :vartype discovered_topics: list[TopicTrendEntry]
    :ivar proposals: Unified steering proposal records.
    :vartype proposals: list[SteeringProposal]
    :ivar artifact_paths: Written artifact paths.
    :vartype artifact_paths: dict[str, str]
    :ivar warnings: Warning messages.
    :vartype warnings: list[str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=TOPIC_GOVERNANCE_ANALYSIS_ID)
    snapshot_id: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    as_of: str = Field(min_length=1)
    windows: List[str] = Field(default_factory=list)
    rank_window: str = Field(min_length=1)
    summary: Dict[str, Any] = Field(default_factory=dict)
    canonical_topics: List[TopicTrendEntry] = Field(default_factory=list)
    discovered_topics: List[TopicTrendEntry] = Field(default_factory=list)
    proposals: List[SteeringProposal] = Field(default_factory=list)
    artifact_paths: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

    @field_validator("analysis_id")
    @classmethod
    def _validate_analysis_id(cls, value: str) -> str:
        if value != TOPIC_GOVERNANCE_ANALYSIS_ID:
            raise ValueError(f"analysis_id must be {TOPIC_GOVERNANCE_ANALYSIS_ID}")
        return value


class PublicationDateMigrationOutput(AnalysisSchemaModel):
    """
    Output for migrating legacy publication date metadata.

    :ivar schema_version: Schema version.
    :vartype schema_version: int
    :ivar scanned_sidecars: Sidecar files scanned.
    :vartype scanned_sidecars: int
    :ivar migrated_sidecars: Sidecar files changed.
    :vartype migrated_sidecars: int
    :ivar migrated_fields: Field migration counts.
    :vartype migrated_fields: dict[str, int]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    scanned_sidecars: int = Field(ge=0)
    migrated_sidecars: int = Field(ge=0)
    migrated_fields: Dict[str, int] = Field(default_factory=dict)


def build_topic_trends(
    *,
    corpus: Corpus,
    topic_modeling_snapshot_id: str,
    classifier_id: Optional[str],
    windows: Sequence[str],
    as_of: Optional[str],
    rank_window: str,
) -> TopicTrendOutput:
    """
    Build and persist a temporal topic intelligence report.

    :param corpus: Corpus containing catalog and analysis artifacts.
    :type corpus: biblicus.corpus.Corpus
    :param topic_modeling_snapshot_id: Topic modeling snapshot identifier.
    :type topic_modeling_snapshot_id: str
    :param classifier_id: Optional classifier identifier for canonical topic coverage.
    :type classifier_id: str or None
    :param windows: Trend windows to compute.
    :type windows: Sequence[str]
    :param as_of: Optional publication date anchor.
    :type as_of: str or None
    :param rank_window: Window used for ranking.
    :type rank_window: str
    :return: Topic trend output.
    :rtype: TopicTrendOutput
    """
    parsed_windows = _parse_windows(windows)
    if rank_window not in parsed_windows:
        raise ValueError("rank_window must be included in windows")

    catalog = corpus.load_catalog()
    topic_modeling_output = _load_topic_modeling_output(
        corpus=corpus, snapshot_id=topic_modeling_snapshot_id
    )
    item_dates, undated_item_ids, date_warnings = _trend_item_dates(catalog.items)
    anchor = _resolve_as_of(as_of=as_of, item_dates=item_dates)
    topic_items = _topic_items(topic_modeling_output)
    topic_keywords = _topic_keywords(topic_modeling_output)
    topic_labels = _topic_labels(topic_modeling_output)
    eligible_topic_items = {
        topic_id: [item_id for item_id in item_ids if item_id in item_dates]
        for topic_id, item_ids in topic_items.items()
    }
    eligible_item_ids = sorted(
        {item_id for item_ids in eligible_topic_items.values() for item_id in item_ids}
    )
    corpus_windows = _window_item_counts(
        item_ids=eligible_item_ids,
        item_dates=item_dates,
        windows=parsed_windows,
        as_of=anchor,
    )

    discovered_topics = _rank_discovered_topics(
        topic_items=topic_items,
        eligible_topic_items=eligible_topic_items,
        topic_keywords=topic_keywords,
        topic_labels=topic_labels,
        item_dates=item_dates,
        corpus_windows=corpus_windows,
        windows=parsed_windows,
        as_of=anchor,
        rank_window=rank_window,
    )
    canonical_topics, canonical_warnings = _canonical_topic_trends(
        corpus=corpus,
        classifier_id=classifier_id,
        topic_modeling_output=topic_modeling_output,
        item_ids=eligible_item_ids,
        item_dates=item_dates,
        corpus_windows=corpus_windows,
        windows=parsed_windows,
        as_of=anchor,
        rank_window=rank_window,
    )
    proposals = _governance_proposals(discovered_topics=discovered_topics, rank_window=rank_window)
    inputs = {
        "topic_modeling_snapshot_id": topic_modeling_snapshot_id,
        "classifier_id": classifier_id,
        "catalog_generated_at": catalog.generated_at,
        "windows": list(parsed_windows),
        "as_of": anchor.isoformat(),
        "rank_window": rank_window,
    }
    snapshot_id = _topic_governance_snapshot_id(inputs)
    generated_at = f"{anchor.isoformat()}T00:00:00+00:00"
    output = TopicTrendOutput(
        snapshot_id=snapshot_id,
        generated_at=generated_at,
        inputs=inputs,
        as_of=anchor.isoformat(),
        windows=list(parsed_windows),
        rank_window=rank_window,
        summary={
            "catalog_items": len(catalog.items),
            "topic_modeling_documents": len(_topic_modeling_document_ids(topic_modeling_output)),
            "trend_eligible_items": len(item_dates),
            "trend_eligible_topic_documents": len(eligible_item_ids),
            "undated_items": len(undated_item_ids),
            "ranking_window": rank_window,
        },
        canonical_topics=canonical_topics,
        discovered_topics=discovered_topics,
        proposals=proposals,
        warnings=date_warnings + canonical_warnings,
    )
    artifact_paths = _write_topic_trend_artifacts(corpus=corpus, output=output)
    return output.model_copy(update={"artifact_paths": artifact_paths})


def migrate_publication_dates(*, corpus: Corpus) -> PublicationDateMigrationOutput:
    """
    Migrate legacy sidecar publication fields into the canonical dates block.

    :param corpus: Corpus whose sidecars should be migrated.
    :type corpus: biblicus.corpus.Corpus
    :return: Migration output.
    :rtype: PublicationDateMigrationOutput
    :raises ValueError: If legacy and canonical date values conflict.
    """
    scanned = 0
    changed = 0
    migrated_fields: Counter[str] = Counter()
    for sidecar_path in sorted(corpus.root.rglob("*.biblicus.yml")):
        scanned += 1
        payload = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Sidecar metadata must be a mapping/object: {sidecar_path}")
        dates = payload.get("dates")
        if dates is None:
            dates = {}
        if not isinstance(dates, dict):
            raise ValueError(f"Sidecar dates must be a mapping/object: {sidecar_path}")
        provenance = payload.get("date_provenance")
        if provenance is None:
            provenance = {}
        if not isinstance(provenance, dict):
            raise ValueError(f"Sidecar date_provenance must be a mapping/object: {sidecar_path}")
        changed_this_file = False
        for old_key, new_key in [("published", "published_at"), ("updated", "updated_at")]:
            if old_key not in payload:
                continue
            legacy_value = payload[old_key]
            existing_value = dates.get(new_key)
            if existing_value is not None and existing_value != legacy_value:
                raise ValueError(
                    f"Legacy {old_key} conflicts with dates.{new_key} in {sidecar_path}"
                )
            dates[new_key] = legacy_value
            provenance.setdefault(new_key, "metadata-migration")
            payload.pop(old_key)
            migrated_fields[new_key] += 1
            changed_this_file = True
        if changed_this_file:
            payload["dates"] = dates
            payload["date_provenance"] = provenance
            sidecar_path.write_text(
                yaml.safe_dump(
                    payload,
                    sort_keys=False,
                    allow_unicode=True,
                    default_flow_style=False,
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            changed += 1
    return PublicationDateMigrationOutput(
        scanned_sidecars=scanned,
        migrated_sidecars=changed,
        migrated_fields=dict(sorted(migrated_fields.items())),
    )


def topic_trends_markdown(output: TopicTrendOutput) -> str:
    """
    Render topic trend output as Markdown.

    :param output: Topic trend output.
    :type output: TopicTrendOutput
    :return: Markdown report.
    :rtype: str
    """
    payload = output.model_dump(mode="json")
    lines = [
        "# Topic Trend Report",
        "",
        f"- Snapshot: `{payload['snapshot_id']}`",
        f"- As of: `{payload['as_of']}`",
        f"- Rank window: `{payload['rank_window']}`",
        f"- Trend-eligible items: {payload['summary']['trend_eligible_items']}",
        f"- Undated items: {payload['summary']['undated_items']}",
        "",
        "## Discovered Topics",
        "",
        _topic_table(payload["discovered_topics"], payload["rank_window"]),
        "",
        "## Canonical Topics",
        "",
        _topic_table(payload["canonical_topics"], payload["rank_window"]),
        "",
        "## Governance Proposals",
        "",
    ]
    if payload["proposals"]:
        lines.extend(
            [
                "| Proposal | Kind | Recommendation | Topic | Seeds | Holdouts |",
                "| --- | --- | --- | --- | ---: | ---: |",
            ]
        )
        for proposal in payload["proposals"]:
            proposal_payload = proposal.get("payload", {})
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown_cell(proposal["proposal_id"]),
                        _markdown_cell(proposal["proposal_kind"]),
                        _markdown_cell(proposal["recommendation"]),
                        _markdown_cell(proposal_payload.get("topic_uid", "")),
                        str(len(proposal_payload.get("suggested_seed_item_ids", []))),
                        str(len(proposal_payload.get("suggested_holdout_item_ids", []))),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No proposals.")
    if payload["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    return "\n".join(lines)


def _load_topic_modeling_output(*, corpus: Corpus, snapshot_id: str) -> TopicModelingOutput:
    path = corpus.analysis_dir / "topic-modeling" / snapshot_id / "output.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing topic modeling output: {path}")
    return TopicModelingOutput.model_validate_json(path.read_text(encoding="utf-8"))


def _parse_windows(windows: Sequence[str]) -> List[str]:
    values: List[str] = []
    for window in windows:
        for token in str(window).split(","):
            cleaned = token.strip()
            if cleaned:
                values.append(cleaned)
    if not values:
        raise ValueError("At least one trend window is required")
    for value in values:
        _window_days(value)
    return values


def _window_days(window: str) -> Optional[int]:
    if window == "all":
        return None
    if window.endswith("d"):
        return int(window[:-1])
    if window.endswith("y"):
        return int(window[:-1]) * 365
    raise ValueError("Trend windows must use d, y, or all")


def _trend_item_dates(items: Dict[str, Any]) -> tuple[Dict[str, date], List[str], List[str]]:
    item_dates: Dict[str, date] = {}
    excluded: List[str] = []
    missing_dates: List[str] = []
    warnings: List[str] = []
    invalid_dates: List[str] = []
    for item_id, item in items.items():
        published_at = item.dates.published_at if item.dates is not None else None
        if not published_at:
            excluded.append(item_id)
            missing_dates.append(item_id)
            continue
        try:
            item_dates[item_id] = _parse_publication_date(published_at)
        except ValueError:
            excluded.append(item_id)
            invalid_dates.append(item_id)
    if missing_dates:
        warnings.append(
            f"{len(missing_dates)} item(s) missing dates.published_at were excluded from trend metrics"
        )
    if invalid_dates:
        warnings.append(
            f"{len(invalid_dates)} item(s) had invalid dates.published_at and were excluded from trend metrics"
        )
    return item_dates, sorted(excluded), warnings


def _parse_publication_date(value: str) -> date:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("dates.published_at must not be empty")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        return date.fromisoformat(cleaned)
    timestamp = cleaned.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.date()


def _resolve_as_of(*, as_of: Optional[str], item_dates: Dict[str, date]) -> date:
    if as_of:
        return _parse_publication_date(as_of)
    if not item_dates:
        raise ValueError("Topic trends require at least one item with dates.published_at")
    return max(item_dates.values())


def _topic_items(output: TopicModelingOutput) -> Dict[int, List[str]]:
    return {topic.topic_id: list(topic.document_ids) for topic in output.report.topics}


def _topic_keywords(output: TopicModelingOutput) -> Dict[int, List[str]]:
    return {
        topic.topic_id: [keyword.keyword for keyword in topic.keywords]
        for topic in output.report.topics
    }


def _topic_labels(output: TopicModelingOutput) -> Dict[int, str]:
    return {topic.topic_id: topic.label for topic in output.report.topics}


def _topic_modeling_document_ids(output: TopicModelingOutput) -> List[str]:
    item_ids: List[str] = []
    for topic in output.report.topics:
        item_ids.extend(topic.document_ids)
    return item_ids


def _window_item_counts(
    *,
    item_ids: Sequence[str],
    item_dates: Dict[str, date],
    windows: Sequence[str],
    as_of: date,
) -> Dict[str, int]:
    return {
        window: len(
            _window_items(item_ids=item_ids, item_dates=item_dates, window=window, as_of=as_of)
        )
        for window in windows
    }


def _window_items(
    *,
    item_ids: Sequence[str],
    item_dates: Dict[str, date],
    window: str,
    as_of: date,
) -> List[str]:
    days = _window_days(window)
    if days is None:
        return [item_id for item_id in item_ids if item_dates[item_id] <= as_of]
    start = as_of - timedelta(days=days)
    return [item_id for item_id in item_ids if start <= item_dates[item_id] <= as_of]


def _rank_discovered_topics(
    *,
    topic_items: Dict[int, List[str]],
    eligible_topic_items: Dict[int, List[str]],
    topic_keywords: Dict[int, List[str]],
    topic_labels: Dict[int, str],
    item_dates: Dict[str, date],
    corpus_windows: Dict[str, int],
    windows: Sequence[str],
    as_of: date,
    rank_window: str,
) -> List[TopicTrendEntry]:
    rows: List[TopicTrendEntry] = []
    for topic_id, item_ids in topic_items.items():
        eligible_ids = eligible_topic_items.get(topic_id, [])
        rows.append(
            TopicTrendEntry(
                rank=1,
                topic_id=topic_id,
                label=topic_labels.get(topic_id)
                or _topic_label(topic_keywords.get(topic_id, []), topic_id=topic_id),
                keywords=topic_keywords.get(topic_id, []),
                document_count=len(item_ids),
                trend_eligible_document_count=len(eligible_ids),
                document_ids=list(item_ids),
                window_metrics=_metrics_for_items(
                    item_ids=eligible_ids,
                    item_dates=item_dates,
                    corpus_windows=corpus_windows,
                    windows=windows,
                    as_of=as_of,
                ),
            )
        )
    return _rank_rows(rows=rows, rank_window=rank_window)


def _canonical_topic_trends(
    *,
    corpus: Corpus,
    classifier_id: Optional[str],
    topic_modeling_output: TopicModelingOutput,
    item_ids: Sequence[str],
    item_dates: Dict[str, date],
    corpus_windows: Dict[str, int],
    windows: Sequence[str],
    as_of: date,
    rank_window: str,
) -> tuple[List[TopicTrendEntry], List[str]]:
    if classifier_id is None:
        return [], ["No classifier was provided; canonical topic coverage was not computed"]
    extraction_snapshot = ExtractionSnapshotReference.model_validate(
        topic_modeling_output.snapshot.input.extraction_snapshot.model_dump(mode="json")
    )
    warnings: List[str] = []
    bundle = _load_model_bundle(corpus=corpus, classifier_id=classifier_id)
    topic_model = _load_bertopic_model(bundle["run_dir"] / "model")
    grouped: Dict[str, Dict[str, Any]] = {}
    for item_id in item_ids:
        try:
            prediction = _classify_item_with_bundle(
                corpus=corpus,
                bundle=bundle,
                topic_model=topic_model,
                item_id=item_id,
                extraction_snapshot=extraction_snapshot,
                review_threshold=0,
                top_k=1,
                recorded=False,
            )
        except ValueError as exc:
            warnings.append(str(exc))
            continue
        if prediction.topic_uid is None:
            continue
        entry = grouped.setdefault(
            prediction.topic_uid,
            {
                "display_name": prediction.display_name or prediction.topic_uid,
                "document_ids": [],
            },
        )
        entry["document_ids"].append(item_id)
    rows: List[TopicTrendEntry] = []
    for topic_uid, payload in grouped.items():
        topic_item_ids = list(payload["document_ids"])
        rows.append(
            TopicTrendEntry(
                rank=1,
                topic_uid=topic_uid,
                label=str(payload["display_name"]),
                keywords=[],
                document_count=len(topic_item_ids),
                trend_eligible_document_count=len(topic_item_ids),
                document_ids=topic_item_ids,
                window_metrics=_metrics_for_items(
                    item_ids=topic_item_ids,
                    item_dates=item_dates,
                    corpus_windows=corpus_windows,
                    windows=windows,
                    as_of=as_of,
                ),
            )
        )
    return _rank_rows(rows=rows, rank_window=rank_window), warnings


def _metrics_for_items(
    *,
    item_ids: Sequence[str],
    item_dates: Dict[str, date],
    corpus_windows: Dict[str, int],
    windows: Sequence[str],
    as_of: date,
) -> Dict[str, TopicTrendWindowMetric]:
    baseline_count = len(
        _window_items(item_ids=item_ids, item_dates=item_dates, window="all", as_of=as_of)
    )
    corpus_baseline_count = corpus_windows.get("all", 0)
    baseline_share = baseline_count / corpus_baseline_count if corpus_baseline_count else 0.0
    metrics: Dict[str, TopicTrendWindowMetric] = {}
    for window in windows:
        window_count = len(
            _window_items(item_ids=item_ids, item_dates=item_dates, window=window, as_of=as_of)
        )
        corpus_count = corpus_windows[window]
        share = window_count / corpus_count if corpus_count else 0.0
        momentum = share / baseline_share if baseline_share else 0.0
        metrics[window] = TopicTrendWindowMetric(
            window=window,
            document_count=window_count,
            corpus_document_count=corpus_count,
            share=round(share, 6),
            baseline_share=round(baseline_share, 6),
            momentum_score=round(momentum, 6),
        )
    return metrics


def _rank_rows(*, rows: Sequence[TopicTrendEntry], rank_window: str) -> List[TopicTrendEntry]:
    ranked = sorted(
        rows,
        key=lambda row: (
            -row.window_metrics[rank_window].momentum_score,
            -row.window_metrics[rank_window].document_count,
            row.label,
        ),
    )
    return [row.model_copy(update={"rank": index}) for index, row in enumerate(ranked, start=1)]


def _topic_label(keywords: Sequence[str], *, topic_id: int) -> str:
    meaningful = _meaningful_keywords(keywords)
    if len(meaningful) >= 2:
        return f"{meaningful[0]} {meaningful[1]}"
    if meaningful:
        return meaningful[0]
    return f"Topic {topic_id}"


def _governance_proposals(
    *, discovered_topics: Sequence[TopicTrendEntry], rank_window: str
) -> List[SteeringProposal]:
    proposals: List[SteeringProposal] = []
    for topic in discovered_topics:
        if topic.topic_id == -1 or topic.trend_eligible_document_count == 0:
            continue
        meaningful_keywords = _meaningful_keywords(topic.keywords)
        topic_uid = _slug_from_keywords(meaningful_keywords, fallback=topic.label)
        seeds = topic.document_ids[:3]
        holdouts = topic.document_ids[3:5]
        evidence = {
            "topic_id": topic.topic_id,
            "item_ids": topic.document_ids,
            "keywords": topic.keywords[:8],
            "label": topic.label,
            "rank_window": rank_window,
            "rank_window_metrics": topic.window_metrics[rank_window].model_dump(mode="json"),
        }
        description = f"Discovered topic with keywords: {', '.join(meaningful_keywords[:5])}."
        proposal_id = f"new-topic:{topic_uid}"
        confidence = min(
            1.0,
            topic.window_metrics[rank_window].momentum_score / 10.0,
        )
        proposals.append(
            topic_governance_proposal(
                proposal_id=proposal_id,
                topic_uid=topic_uid,
                display_name=topic.label,
                description=description,
                evidence=evidence,
                suggested_seed_item_ids=seeds,
                suggested_holdout_item_ids=holdouts,
                rationale=(
                    "The discovered topic has dated evidence and should be reviewed "
                    "before becoming canonical."
                ),
                confidence=round(confidence, 6),
            )
        )
    return proposals


def _slug_from_keywords(keywords: Sequence[str], *, fallback: str) -> str:
    source_terms = list(keywords[:2]) if len(keywords) >= 2 else [fallback]
    source = " ".join(source_terms)
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", source.lower()).strip("-")
    return cleaned or "discovered-topic"


def _meaningful_keywords(keywords: Sequence[str]) -> List[str]:
    cleaned = [
        keyword for keyword in keywords if keyword.strip().lower() not in PROPOSAL_KEYWORD_STOPWORDS
    ]
    return cleaned or list(keywords)


def _display_name(topic_uid: str) -> str:
    return " ".join(part.capitalize() for part in topic_uid.split("-"))


def _topic_governance_snapshot_id(inputs: Dict[str, Any]) -> str:
    payload = json.dumps(
        {"analysis_id": TOPIC_GOVERNANCE_ANALYSIS_ID, "inputs": inputs},
        sort_keys=True,
    )
    return hash_text(payload)


def _write_topic_trend_artifacts(*, corpus: Corpus, output: TopicTrendOutput) -> Dict[str, str]:
    run_dir = corpus.analysis_run_dir(
        analysis_id=TOPIC_GOVERNANCE_ANALYSIS_ID,
        snapshot_id=output.snapshot_id,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": run_dir / "manifest.json",
        "output": run_dir / "output.json",
        "proposals": run_dir / "proposals.json",
        "report": run_dir / "report.md",
    }
    artifact_paths = {key: str(path) for key, path in paths.items()}
    final_output = output.model_copy(update={"artifact_paths": artifact_paths})
    paths["manifest"].write_text(
        json.dumps(
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "analysis_id": TOPIC_GOVERNANCE_ANALYSIS_ID,
                "snapshot_id": final_output.snapshot_id,
                "generated_at": final_output.generated_at,
                "inputs": final_output.inputs,
                "artifact_paths": artifact_paths,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["output"].write_text(final_output.model_dump_json(indent=2) + "\n", encoding="utf-8")
    paths["proposals"].write_text(
        json.dumps(
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "snapshot_id": final_output.snapshot_id,
                "proposals": [
                    proposal.model_dump(mode="json") for proposal in final_output.proposals
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["report"].write_text(topic_trends_markdown(final_output) + "\n", encoding="utf-8")
    latest_path = corpus.analysis_dir / TOPIC_GOVERNANCE_ANALYSIS_ID / "latest.json"
    latest_path.write_text(
        json.dumps(
            {"snapshot_id": final_output.snapshot_id, "generated_at": final_output.generated_at},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact_paths


def _topic_table(rows: Sequence[Dict[str, Any]], rank_window: str) -> str:
    if not rows:
        return "No topics."
    lines = [
        "| Rank | Topic ID | Label | Documents | Window Count | Momentum | Keywords |",
        "| ---: | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        metric = row["window_metrics"][rank_window]
        topic = row.get("topic_uid") or row.get("topic_id")
        keywords = ", ".join(row.get("keywords", [])[:5])
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["rank"]),
                    _markdown_cell(str(topic)),
                    _markdown_cell(str(row["label"])),
                    str(row["trend_eligible_document_count"]),
                    str(metric["document_count"]),
                    f"{float(metric['momentum_score']):.3f}",
                    _markdown_cell(keywords),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
