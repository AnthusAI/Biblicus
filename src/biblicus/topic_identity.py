"""
Stable cluster identity across topic-model runs.

BERTopic topic identifiers restart from zero on every run, so a topic number cannot say whether a
cluster is new or continuing. This module matches the clusters of a run to the clusters of the
previous run by the Jaccard overlap of their member item identifiers, carries a stable cluster
identifier forward, and reports one lifecycle event per cluster: ``new``, ``continued``,
``merged`` or ``split``. Clusters of the previous run that no current cluster overlaps are
reported as ``gone``.

Biblicus supplies identity and statistics only. Names, acceptance and publication belong to the
consumer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional, Sequence, Set, Tuple

from pydantic import Field, model_validator

from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .retrieval import hash_text
from .topic_trends import (
    TOPIC_GOVERNANCE_ANALYSIS_ID,
    TopicTrendOutput,
    _load_topic_modeling_output,
    _trend_item_dates,
)

TOPIC_IDENTITY_ANALYSIS_ID = "topic-identity"
IDENTITY_SERIES_WEEKS = 8
OUTLIER_TOPIC_ID = -1
TOP_TERM_LIMIT = 10

TopicIdentityEvent = Literal["new", "continued", "merged", "split"]


class TopicIdentityCluster(AnalysisSchemaModel):
    """
    One cluster of the current run with its stable identity.

    :ivar uid: Stable cluster identifier, carried forward across runs.
    :vartype uid: str
    :ivar topic_id: BERTopic topic identifier inside the current run.
    :vartype topic_id: int
    :ivar event: Lifecycle event relative to the previous run.
    :vartype event: str
    :ivar predecessor_uids: Stable identifiers of every previous cluster that overlaps this one.
    :vartype predecessor_uids: list[str]
    :ivar successor_uids: For a split, the identifiers of every cluster the predecessor became.
    :vartype successor_uids: list[str]
    :ivar label: Topic label from the topic modeling run.
    :vartype label: str
    :ivar top_terms: Highest-ranked topic keywords.
    :vartype top_terms: list[str]
    :ivar member_item_count: Number of member items.
    :vartype member_item_count: int
    :ivar member_item_ids: Member item identifiers, sorted.
    :vartype member_item_ids: list[str]
    :ivar first_seen: Date of the first run that contained this cluster, carried forward.
    :vartype first_seen: str
    :ivar earliest_published_at: Earliest published date among member items, or None.
    :vartype earliest_published_at: str or None
    :ivar weekly_series: Eight weekly counts oldest to newest, or None without weekly bins.
    :vartype weekly_series: list[int] or None
    """

    uid: str = Field(min_length=1)
    topic_id: int
    event: TopicIdentityEvent
    predecessor_uids: List[str] = Field(default_factory=list)
    successor_uids: List[str] = Field(default_factory=list)
    label: str = Field(min_length=1)
    top_terms: List[str] = Field(default_factory=list)
    member_item_count: int = Field(ge=0)
    member_item_ids: List[str] = Field(default_factory=list)
    first_seen: str = Field(min_length=1)
    earliest_published_at: Optional[str] = None
    weekly_series: Optional[List[int]] = None


class TopicIdentityGoneCluster(AnalysisSchemaModel):
    """
    A previous-run cluster that no current cluster overlaps above the threshold.

    :ivar uid: Stable cluster identifier.
    :vartype uid: str
    :ivar label: Topic label from the previous run.
    :vartype label: str
    :ivar top_terms: Topic keywords from the previous run.
    :vartype top_terms: list[str]
    :ivar member_item_count: Member item count in the previous run.
    :vartype member_item_count: int
    :ivar first_seen: Date of the first run that contained this cluster.
    :vartype first_seen: str
    :ivar last_seen_run_id: Previous run identifier.
    :vartype last_seen_run_id: str
    """

    uid: str = Field(min_length=1)
    label: str = Field(min_length=1)
    top_terms: List[str] = Field(default_factory=list)
    member_item_count: int = Field(ge=0)
    first_seen: str = Field(min_length=1)
    last_seen_run_id: str = Field(min_length=1)


class TopicIdentityOutput(AnalysisSchemaModel):
    """
    Cluster identity report for one topic modeling run.

    The report is written to ``analysis/topic-identity/<run_id>/output.json``. It is deterministic:
    the same two runs and threshold always produce the same identifiers and events.

    :ivar schema_version: Schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier. Always ``topic-identity``.
    :vartype analysis_id: str
    :ivar run_id: Topic modeling snapshot identifier of the current run.
    :vartype run_id: str
    :ivar previous_run_id: Topic modeling snapshot identifier of the previous run, or None.
    :vartype previous_run_id: str or None
    :ivar generated_at: Creation timestamp of the current topic modeling run.
    :vartype generated_at: str
    :ivar threshold: Jaccard overlap threshold used for matching.
    :vartype threshold: float
    :ivar trends_snapshot_id: Topic trends snapshot that supplied weekly series, or None.
    :vartype trends_snapshot_id: str or None
    :ivar series_iso_weeks: ISO week labels of ``weekly_series``, oldest to newest, or None.
    :vartype series_iso_weeks: list[str] or None
    :ivar document_count: Documents assigned to any topic, outliers included.
    :vartype document_count: int
    :ivar outlier_document_count: Documents BERTopic left unclustered.
    :vartype outlier_document_count: int
    :ivar cluster_count: Clusters in the current run, outliers excluded.
    :vartype cluster_count: int
    :ivar event_counts: Number of clusters per event, including ``gone``.
    :vartype event_counts: dict[str, int]
    :ivar clusters: Current-run clusters with identity.
    :vartype clusters: list[TopicIdentityCluster]
    :ivar gone: Previous-run clusters with no current match.
    :vartype gone: list[TopicIdentityGoneCluster]
    :ivar artifact_paths: Written artifact paths.
    :vartype artifact_paths: dict[str, str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=TOPIC_IDENTITY_ANALYSIS_ID)
    run_id: str = Field(min_length=1)
    previous_run_id: Optional[str] = None
    generated_at: str = Field(min_length=1)
    threshold: float = Field(gt=0, le=1)
    trends_snapshot_id: Optional[str] = None
    series_iso_weeks: Optional[List[str]] = None
    document_count: int = Field(ge=0)
    outlier_document_count: int = Field(ge=0)
    cluster_count: int = Field(ge=0)
    event_counts: Dict[str, int] = Field(default_factory=dict)
    clusters: List[TopicIdentityCluster] = Field(default_factory=list)
    gone: List[TopicIdentityGoneCluster] = Field(default_factory=list)
    artifact_paths: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_analysis_id(self) -> "TopicIdentityOutput":
        if self.analysis_id != TOPIC_IDENTITY_ANALYSIS_ID:
            raise ValueError(f"analysis_id must be {TOPIC_IDENTITY_ANALYSIS_ID}")
        return self


class _WeeklySeries(AnalysisSchemaModel):
    iso_weeks: List[str]
    series: Dict[int, List[int]]


def build_topic_identity(
    *,
    corpus: Corpus,
    current_run_id: str,
    previous_run_id: Optional[str],
    threshold: float,
    trends_snapshot_id: Optional[str],
) -> TopicIdentityOutput:
    """
    Match the clusters of a topic modeling run to the previous run and persist the result.

    The previous run must already have a topic identity report, because stable identifiers are
    carried forward from it. The first run has no previous run and every cluster is ``new``.

    :param corpus: Corpus containing the topic modeling runs.
    :type corpus: biblicus.corpus.Corpus
    :param current_run_id: Topic modeling snapshot identifier to identify.
    :type current_run_id: str
    :param previous_run_id: Previous topic modeling snapshot identifier, or None for the first run.
    :type previous_run_id: str or None
    :param threshold: Minimum Jaccard overlap, greater than 0 and at most 1, for two clusters to match.
    :type threshold: float
    :param trends_snapshot_id: Topic trends snapshot carrying weekly bins, or None.
    :type trends_snapshot_id: str or None
    :return: Cluster identity report.
    :rtype: TopicIdentityOutput
    :raises ValueError: If the threshold is out of range, the runs are the same, or the weekly bins
        do not belong to the current run.
    :raises FileNotFoundError: If a required run, identity report or trends snapshot is missing.
    """
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be greater than 0 and at most 1")
    if previous_run_id == current_run_id:
        raise ValueError("previous run must differ from the current run")

    modeling = _load_topic_modeling_output(corpus=corpus, snapshot_id=current_run_id)
    run_date = _run_date(modeling.generated_at)
    topics = modeling.report.topics
    clustered = [topic for topic in topics if topic.topic_id != OUTLIER_TOPIC_ID]
    previous_clusters = (
        _load_previous_identity(corpus=corpus, run_id=previous_run_id).clusters
        if previous_run_id is not None
        else []
    )
    weekly = _load_weekly_series(
        corpus=corpus, trends_snapshot_id=trends_snapshot_id, current_run_id=current_run_id
    )
    item_dates, _, _ = _trend_item_dates(corpus.load_catalog().items)

    current_members = {topic.topic_id: set(topic.document_ids) for topic in clustered}
    edges = _matching_edges(
        previous=previous_clusters, current_members=current_members, threshold=threshold
    )
    assigned = _assign_uids(
        edges=edges, previous=previous_clusters, current_ids=sorted(current_members)
    )
    uids = {
        topic_id: assigned.get(topic_id) or _new_uid(current_run_id, topic_id)
        for topic_id in current_members
    }
    predecessors_of = _group(edges, key=1, value=0)
    successors_of = _group(edges, key=0, value=1)

    clusters: List[TopicIdentityCluster] = []
    for topic in sorted(clustered, key=lambda candidate: candidate.topic_id):
        pred_indexes = predecessors_of.get(topic.topic_id, [])
        event, successor_ids = _event_for(
            predecessor_count=len(pred_indexes),
            sole_predecessor_successors=(
                successors_of[pred_indexes[0]] if len(pred_indexes) == 1 else []
            ),
        )
        members = sorted(topic.document_ids)
        dated = [item_dates[item_id] for item_id in members if item_id in item_dates]
        first_seen = (
            min(previous_clusters[index].first_seen for index in pred_indexes)
            if pred_indexes
            else run_date
        )
        clusters.append(
            TopicIdentityCluster(
                uid=uids[topic.topic_id],
                topic_id=topic.topic_id,
                event=event,
                predecessor_uids=sorted(previous_clusters[index].uid for index in pred_indexes),
                successor_uids=sorted(uids[successor] for successor in successor_ids),
                label=topic.label,
                top_terms=[keyword.keyword for keyword in topic.keywords][:TOP_TERM_LIMIT],
                member_item_count=len(members),
                member_item_ids=members,
                first_seen=first_seen,
                earliest_published_at=min(dated).isoformat() if dated else None,
                weekly_series=weekly.series.get(topic.topic_id) if weekly else None,
            )
        )

    gone = [
        TopicIdentityGoneCluster(
            uid=cluster.uid,
            label=cluster.label,
            top_terms=cluster.top_terms,
            member_item_count=cluster.member_item_count,
            first_seen=cluster.first_seen,
            last_seen_run_id=previous_run_id,
        )
        for index, cluster in enumerate(previous_clusters)
        if index not in successors_of
    ]
    event_counts = {name: 0 for name in ("new", "continued", "merged", "split")}
    for cluster in clusters:
        event_counts[cluster.event] += 1
    event_counts["gone"] = len(gone)

    output = TopicIdentityOutput(
        run_id=current_run_id,
        previous_run_id=previous_run_id,
        generated_at=modeling.generated_at,
        threshold=threshold,
        trends_snapshot_id=trends_snapshot_id,
        series_iso_weeks=weekly.iso_weeks if weekly else None,
        document_count=sum(len(topic.document_ids) for topic in topics),
        outlier_document_count=sum(
            len(topic.document_ids) for topic in topics if topic.topic_id == OUTLIER_TOPIC_ID
        ),
        cluster_count=len(clustered),
        event_counts=event_counts,
        clusters=clusters,
        gone=gone,
    )
    return _write_identity_output(corpus=corpus, output=output)


def topic_identity_path(*, corpus: Corpus, run_id: str) -> Path:
    """
    Resolve the path of the topic identity report for a run.

    :param corpus: Corpus containing the analysis artifacts.
    :type corpus: biblicus.corpus.Corpus
    :param run_id: Topic modeling snapshot identifier.
    :type run_id: str
    :return: Path of ``output.json``.
    :rtype: pathlib.Path
    """
    return (
        corpus.analysis_run_dir(analysis_id=TOPIC_IDENTITY_ANALYSIS_ID, snapshot_id=run_id)
        / "output.json"
    )


def topic_identity_markdown(output: TopicIdentityOutput) -> str:
    """
    Render a topic identity report as Markdown.

    :param output: Topic identity output.
    :type output: TopicIdentityOutput
    :return: Markdown report.
    :rtype: str
    """
    lines = [
        "# Topic Identity Report",
        "",
        f"- Run: `{output.run_id}`",
        f"- Previous run: `{output.previous_run_id}`",
        f"- Threshold: {output.threshold}",
        f"- Documents: {output.document_count} ({output.outlier_document_count} outliers)",
        f"- Clusters: {output.cluster_count}",
        "- Events: "
        + ", ".join(f"{name} {count}" for name, count in sorted(output.event_counts.items())),
        "",
        "| Cluster | Event | Items | Predecessors | Top terms |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for cluster in output.clusters:
        lines.append(
            f"| `{cluster.uid}` | {cluster.event} | {cluster.member_item_count} | "
            f"{', '.join(cluster.predecessor_uids)} | {', '.join(cluster.top_terms)} |"
        )
    if output.gone:
        lines.extend(["", "## Gone", ""])
        lines.extend(f"- `{cluster.uid}` {cluster.label}" for cluster in output.gone)
    return "\n".join(lines)


def _run_date(generated_at: str) -> str:
    parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.date().isoformat()


def _new_uid(run_id: str, topic_id: int) -> str:
    return "cl-" + hash_text(f"{run_id}:{topic_id}")[:12]


def _jaccard(left: Set[str], right: Set[str]) -> float:
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def _matching_edges(
    *,
    previous: Sequence[TopicIdentityCluster],
    current_members: Dict[int, Set[str]],
    threshold: float,
) -> List[Tuple[int, int, float]]:
    edges: List[Tuple[int, int, float]] = []
    for previous_index, cluster in enumerate(previous):
        previous_members = set(cluster.member_item_ids)
        for topic_id in sorted(current_members):
            overlap = _jaccard(previous_members, current_members[topic_id])
            if overlap >= threshold:
                edges.append((previous_index, topic_id, overlap))
    return edges


def _assign_uids(
    *,
    edges: Sequence[Tuple[int, int, float]],
    previous: Sequence[TopicIdentityCluster],
    current_ids: Sequence[int],
) -> Dict[int, str]:
    assigned: Dict[int, str] = {}
    used_previous: Set[int] = set()
    ranked = sorted(edges, key=lambda edge: (-edge[2], previous[edge[0]].uid, edge[1]))
    for previous_index, topic_id, _ in ranked:
        if previous_index in used_previous or topic_id in assigned:
            continue
        assigned[topic_id] = previous[previous_index].uid
        used_previous.add(previous_index)
    return {topic_id: assigned[topic_id] for topic_id in current_ids if topic_id in assigned}


def _group(
    edges: Sequence[Tuple[int, int, float]], *, key: int, value: int
) -> Dict[int, List[int]]:
    grouped: Dict[int, List[int]] = {}
    for edge in edges:
        grouped.setdefault(edge[key], []).append(edge[value])
    return grouped


def _event_for(
    *, predecessor_count: int, sole_predecessor_successors: Sequence[int]
) -> Tuple[TopicIdentityEvent, List[int]]:
    if predecessor_count == 0:
        return "new", []
    if predecessor_count >= 2:
        return "merged", []
    if len(sole_predecessor_successors) >= 2:
        return "split", list(sole_predecessor_successors)
    return "continued", []


def _load_previous_identity(*, corpus: Corpus, run_id: Optional[str]) -> TopicIdentityOutput:
    path = topic_identity_path(corpus=corpus, run_id=run_id)
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing topic identity for previous run {run_id}: {path}. "
            f"Run `biblicus analyze topic-identity --current {run_id}` first."
        )
    return TopicIdentityOutput.model_validate_json(path.read_text(encoding="utf-8"))


def _load_weekly_series(
    *, corpus: Corpus, trends_snapshot_id: Optional[str], current_run_id: str
) -> Optional[_WeeklySeries]:
    if trends_snapshot_id is None:
        return None
    path = (
        corpus.analysis_run_dir(
            analysis_id=TOPIC_GOVERNANCE_ANALYSIS_ID, snapshot_id=trends_snapshot_id
        )
        / "output.json"
    )
    if not path.is_file():
        raise FileNotFoundError(f"Missing topic trends output: {path}")
    trends = TopicTrendOutput.model_validate_json(path.read_text(encoding="utf-8"))
    if trends.inputs.get("topic_modeling_snapshot_id") != current_run_id:
        raise ValueError("Topic trends snapshot was not built from the current run")
    bins = trends.weekly_bins
    if bins is None:
        raise ValueError("Topic trends snapshot has no weekly bins; rerun with --bin weekly")
    if bins.weeks < IDENTITY_SERIES_WEEKS:
        raise ValueError(f"Weekly bins must cover at least {IDENTITY_SERIES_WEEKS} weeks")
    return _WeeklySeries(
        iso_weeks=bins.iso_weeks[-IDENTITY_SERIES_WEEKS:],
        series={
            row.topic_id: row.counts[-IDENTITY_SERIES_WEEKS:]
            for row in bins.discovered_topics
            if row.topic_id is not None
        },
    )


def _write_identity_output(*, corpus: Corpus, output: TopicIdentityOutput) -> TopicIdentityOutput:
    path = topic_identity_path(corpus=corpus, run_id=output.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    final_output = output.model_copy(update={"artifact_paths": {"output": str(path)}})
    path.write_text(
        json.dumps(final_output.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return final_output


__all__ = [
    "TopicIdentityCluster",
    "TopicIdentityGoneCluster",
    "TopicIdentityOutput",
    "build_topic_identity",
    "topic_identity_markdown",
    "topic_identity_path",
]
