"""
Unified steering proposal artifacts for Biblicus.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import Field, ValidationError, field_validator, model_validator

from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .graph.extraction import load_graph_snapshot_manifest
from .graph.models import GraphSnapshotManifest, parse_graph_snapshot_reference
from .retrieval import hash_text
from .topic_classifier import _load_model_bundle, load_topic_classifier_seed_manifest

STEERING_PROPOSALS_ANALYSIS_ID = "steering-proposals"

STEERING_DOMAINS = {"topic", "graph"}
STEERING_SIGNAL_KINDS = {
    "accepted-topic-missing-graph-entity",
    "taxonomy-child-topic-candidate",
    "topic-membership-edge-candidate",
    "topic-entity-name-collision",
    "possible-duplicate-entity",
    "noisy-generic-entity",
    "topic-relationship-edge-candidate",
    "discovered-topic-candidate",
}
STEERING_PROPOSAL_KINDS = {
    "new-topic",
    "merge-topics",
    "split-topic",
    "archive-topic",
    "relabel-topic",
    "create-taxonomy-node",
    "move-taxonomy-node",
    "merge-taxonomy-nodes",
    "split-taxonomy-node",
    "archive-taxonomy-node",
    "create-topic-entity",
    "map-topic-to-entity",
    "merge-entities",
    "add-entity-alias",
    "add-topic-membership-edge",
    "add-topic-relationship-edge",
    "add-ontology-relationship",
    "add-relationship-type",
    "suppress-entity-or-edge",
}
HUMAN_DECISION_FIELDS = {
    "human_decision",
    "decision",
    "decisions",
    "accepted_by",
    "accepted_at",
    "rejected_by",
    "rejected_at",
    "deferred_by",
    "deferred_at",
}
GENERIC_GRAPH_ENTITY_LABELS = {"ai", "ml", "model", "models", "paper", "papers", "data"}


class SteeringSignal(AnalysisSchemaModel):
    """
    Computational steering candidate derived from Biblicus artifacts.

    :ivar signal_id: Stable signal identifier.
    :vartype signal_id: str
    :ivar signal_kind: Signal type.
    :vartype signal_kind: str
    :ivar domain: Steering domain.
    :vartype domain: str
    :ivar source_artifact_refs: Source artifact references.
    :vartype source_artifact_refs: list[str]
    :ivar metrics: Numeric or logical signal metrics.
    :vartype metrics: dict[str, Any]
    :ivar evidence_item_ids: Evidence item identifiers.
    :vartype evidence_item_ids: list[str]
    :ivar payload: Signal-specific payload.
    :vartype payload: dict[str, Any]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    signal_id: str = Field(min_length=1)
    signal_kind: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    source_artifact_refs: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    evidence_item_ids: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        if value not in STEERING_DOMAINS:
            raise ValueError(f"Unsupported steering domain: {value}")
        return value

    @field_validator("signal_kind")
    @classmethod
    def _validate_signal_kind(cls, value: str) -> str:
        if value not in STEERING_SIGNAL_KINDS:
            raise ValueError(f"Unsupported steering signal kind: {value}")
        return value


class SteeringProposal(AnalysisSchemaModel):
    """
    Reviewable steering recommendation authored outside human decision state.

    :ivar proposal_id: Stable proposal identifier.
    :vartype proposal_id: str
    :ivar proposal_kind: Proposal type.
    :vartype proposal_kind: str
    :ivar domain: Steering domain.
    :vartype domain: str
    :ivar recommendation: Proposal recommendation.
    :vartype recommendation: str
    :ivar status: Proposal artifact status.
    :vartype status: str
    :ivar author: Proposal author metadata.
    :vartype author: dict[str, Any]
    :ivar source_signal_ids: Signal identifiers used by this proposal.
    :vartype source_signal_ids: list[str]
    :ivar evidence: Proposal evidence payload.
    :vartype evidence: dict[str, Any]
    :ivar rationale: Proposal rationale.
    :vartype rationale: str
    :ivar confidence: Optional proposal confidence.
    :vartype confidence: float or None
    :ivar payload: Proposal-specific payload.
    :vartype payload: dict[str, Any]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    proposal_id: str = Field(min_length=1)
    proposal_kind: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    recommendation: Literal["recommend", "do_not_recommend", "needs_clarification"]
    status: Literal["proposed"] = "proposed"
    author: Dict[str, Any] = Field(default_factory=dict)
    source_signal_ids: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(min_length=1)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    payload: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _reject_human_decisions(cls, value: object) -> object:
        if isinstance(value, dict):
            _reject_human_decision_fields(value)
        return value

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        if value not in STEERING_DOMAINS:
            raise ValueError(f"Unsupported steering domain: {value}")
        return value

    @field_validator("proposal_kind")
    @classmethod
    def _validate_proposal_kind(cls, value: str) -> str:
        if value not in STEERING_PROPOSAL_KINDS:
            raise ValueError(f"Unsupported steering proposal kind: {value}")
        return value


class SteeringProposalBundle(AnalysisSchemaModel):
    """
    Validated steering proposal artifact bundle.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier.
    :vartype analysis_id: str
    :ivar snapshot_id: Deterministic proposal snapshot identifier.
    :vartype snapshot_id: str or None
    :ivar generated_at: Generation timestamp.
    :vartype generated_at: str
    :ivar source_artifact_refs: Source artifact references.
    :vartype source_artifact_refs: list[str]
    :ivar signals: Computational signal records.
    :vartype signals: list[SteeringSignal]
    :ivar proposals: Proposal judgment records.
    :vartype proposals: list[SteeringProposal]
    :ivar warnings: Bundle warnings.
    :vartype warnings: list[str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=STEERING_PROPOSALS_ANALYSIS_ID)
    snapshot_id: Optional[str] = None
    generated_at: str = Field(min_length=1)
    source_artifact_refs: List[str] = Field(default_factory=list)
    signals: List[SteeringSignal] = Field(default_factory=list)
    proposals: List[SteeringProposal] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _reject_bundle_human_decisions(cls, value: object) -> object:
        if isinstance(value, dict):
            _reject_human_decision_fields(value)
        return value

    @model_validator(mode="after")
    def _validate_bundle(self) -> "SteeringProposalBundle":
        if self.analysis_id != STEERING_PROPOSALS_ANALYSIS_ID:
            raise ValueError(f"analysis_id must be {STEERING_PROPOSALS_ANALYSIS_ID}")
        _validate_unique_ids("signal_id", [signal.signal_id for signal in self.signals])
        _validate_unique_ids("proposal_id", [proposal.proposal_id for proposal in self.proposals])
        signal_ids = {signal.signal_id for signal in self.signals}
        missing_signal_ids = sorted(
            {
                signal_id
                for proposal in self.proposals
                for signal_id in proposal.source_signal_ids
                if signal_id not in signal_ids
            }
        )
        if missing_signal_ids:
            raise ValueError(
                "Steering proposals reference unknown signal IDs: " + ", ".join(missing_signal_ids)
            )
        return self


class SteeringProposalRecordOutput(AnalysisSchemaModel):
    """
    Output for recording a steering proposal bundle.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier.
    :vartype analysis_id: str
    :ivar snapshot_id: Recorded snapshot identifier.
    :vartype snapshot_id: str
    :ivar signal_count: Number of recorded signals.
    :vartype signal_count: int
    :ivar proposal_count: Number of recorded proposals.
    :vartype proposal_count: int
    :ivar artifact_paths: Written artifact paths.
    :vartype artifact_paths: dict[str, str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=STEERING_PROPOSALS_ANALYSIS_ID)
    snapshot_id: str = Field(min_length=1)
    signal_count: int = Field(ge=0)
    proposal_count: int = Field(ge=0)
    artifact_paths: Dict[str, str] = Field(default_factory=dict)


def build_steering_graph_signal_bundle(
    *,
    corpus: Corpus,
    classifier_id: str,
    graph_snapshot: str,
) -> SteeringProposalBundle:
    """
    Build computational topic-informed graph steering signals.

    :param corpus: Corpus to inspect.
    :type corpus: biblicus.corpus.Corpus
    :param classifier_id: Topic classifier identifier.
    :type classifier_id: str
    :param graph_snapshot: Graph snapshot reference in extractor:snapshot form.
    :type graph_snapshot: str
    :return: Steering proposal bundle containing signals and no proposals.
    :rtype: SteeringProposalBundle
    """
    catalog = corpus.load_catalog()
    warnings: List[str] = []
    accepted_topics, taxonomy_ref = _accepted_topics_for_graph_signals(
        corpus=corpus,
        classifier_id=classifier_id,
        warnings=warnings,
    )
    graph_reference = parse_graph_snapshot_reference(graph_snapshot)
    graph_manifest = load_graph_snapshot_manifest(
        corpus,
        extractor_id=graph_reference.extractor_id,
        snapshot_id=graph_reference.snapshot_id,
    )
    source_artifact_refs = [
        f"graph:{graph_reference.as_string()}",
        f"topic-classifier:{classifier_id}",
    ]
    if taxonomy_ref is not None:
        source_artifact_refs.append(taxonomy_ref)
    signals: List[SteeringSignal] = []
    signals.extend(
        _topic_entity_signals(
            accepted_topics=accepted_topics,
            graph_manifest=graph_manifest,
            source_artifact_refs=source_artifact_refs,
        )
    )
    try:
        model_bundle = _load_model_bundle(corpus=corpus, classifier_id=classifier_id)
    except FileNotFoundError as exc:
        warnings.append(str(exc))
        model_bundle = None
    if model_bundle is not None:
        signals.extend(
            _topic_membership_signals(
                topic_map=model_bundle["topic_map"],
                source_artifact_refs=source_artifact_refs,
            )
        )
        signals.extend(
            _topic_relationship_signals(
                topic_map=model_bundle["topic_map"],
                source_artifact_refs=source_artifact_refs,
            )
        )
    bundle = SteeringProposalBundle(
        generated_at=catalog.generated_at,
        source_artifact_refs=source_artifact_refs,
        signals=signals,
        proposals=[],
        warnings=warnings,
    )
    return _with_deterministic_snapshot_id(bundle)


def load_steering_proposal_bundle(path: Path) -> SteeringProposalBundle:
    """
    Load and validate a steering proposal bundle.

    :param path: Proposal bundle JSON path.
    :type path: pathlib.Path
    :return: Validated proposal bundle with deterministic snapshot identifier.
    :rtype: SteeringProposalBundle
    """
    payload = _read_json_object(path)
    try:
        bundle = SteeringProposalBundle.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid steering proposal bundle: {exc}") from exc
    return _with_deterministic_snapshot_id(bundle)


def record_steering_proposal_bundle(
    *,
    corpus: Corpus,
    input_path: Path,
) -> SteeringProposalRecordOutput:
    """
    Record a validated steering proposal bundle as an immutable analysis artifact.

    :param corpus: Corpus that owns the recorded artifact.
    :type corpus: biblicus.corpus.Corpus
    :param input_path: Proposal bundle JSON path.
    :type input_path: pathlib.Path
    :return: Record output.
    :rtype: SteeringProposalRecordOutput
    """
    bundle = load_steering_proposal_bundle(input_path)
    snapshot_id = _required_snapshot_id(bundle)
    run_dir = corpus.analysis_run_dir(
        analysis_id=STEERING_PROPOSALS_ANALYSIS_ID,
        snapshot_id=snapshot_id,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": run_dir / "manifest.json",
        "signals": run_dir / "signals.json",
        "proposals": run_dir / "proposals.json",
    }
    artifact_paths = {name: str(path) for name, path in paths.items()}
    _write_json(
        paths["manifest"],
        {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "analysis_id": STEERING_PROPOSALS_ANALYSIS_ID,
            "snapshot_id": snapshot_id,
            "generated_at": bundle.generated_at,
            "source_artifact_refs": bundle.source_artifact_refs,
            "artifact_paths": artifact_paths,
            "signal_count": len(bundle.signals),
            "proposal_count": len(bundle.proposals),
        },
    )
    _write_json(
        paths["signals"],
        {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "snapshot_id": snapshot_id,
            "signals": [signal.model_dump(mode="json") for signal in bundle.signals],
        },
    )
    _write_json(
        paths["proposals"],
        {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "snapshot_id": snapshot_id,
            "proposals": [proposal.model_dump(mode="json") for proposal in bundle.proposals],
        },
    )
    latest_path = corpus.analysis_dir / STEERING_PROPOSALS_ANALYSIS_ID / "latest.json"
    _write_json(latest_path, {"snapshot_id": snapshot_id, "generated_at": bundle.generated_at})
    return SteeringProposalRecordOutput(
        snapshot_id=snapshot_id,
        signal_count=len(bundle.signals),
        proposal_count=len(bundle.proposals),
        artifact_paths=artifact_paths,
    )


def load_latest_steering_proposal_bundle(
    *,
    corpus: Corpus,
    warnings: List[str],
) -> Optional[SteeringProposalBundle]:
    """
    Load the latest recorded steering proposal bundle when present.

    :param corpus: Corpus to inspect.
    :type corpus: biblicus.corpus.Corpus
    :param warnings: Warnings list to append to.
    :type warnings: list[str]
    :return: Latest proposal bundle or None.
    :rtype: SteeringProposalBundle or None
    """
    latest_path = corpus.analysis_dir / STEERING_PROPOSALS_ANALYSIS_ID / "latest.json"
    if not latest_path.is_file():
        return None
    latest_payload = _read_json_object(latest_path)
    snapshot_id = latest_payload.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        warnings.append(f"Steering proposals latest pointer has no snapshot_id: {latest_path}")
        return None
    return load_recorded_steering_proposal_bundle(
        corpus=corpus,
        snapshot_id=snapshot_id,
        warnings=warnings,
    )


def load_recorded_steering_proposal_bundle(
    *,
    corpus: Corpus,
    snapshot_id: str,
    warnings: List[str],
) -> Optional[SteeringProposalBundle]:
    """
    Load a recorded steering proposal bundle by snapshot identifier.

    :param corpus: Corpus to inspect.
    :type corpus: biblicus.corpus.Corpus
    :param snapshot_id: Proposal snapshot identifier.
    :type snapshot_id: str
    :param warnings: Warnings list to append to.
    :type warnings: list[str]
    :return: Recorded proposal bundle or None.
    :rtype: SteeringProposalBundle or None
    """
    run_dir = corpus.analysis_run_dir(
        analysis_id=STEERING_PROPOSALS_ANALYSIS_ID,
        snapshot_id=snapshot_id,
    )
    manifest_path = run_dir / "manifest.json"
    signals_path = run_dir / "signals.json"
    proposals_path = run_dir / "proposals.json"
    if not manifest_path.is_file() or not signals_path.is_file() or not proposals_path.is_file():
        warnings.append(f"Missing steering proposal artifact files: {run_dir}")
        return None
    manifest = _read_json_object(manifest_path)
    signals_payload = _read_json_object(signals_path)
    proposals_payload = _read_json_object(proposals_path)
    payload = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "analysis_id": STEERING_PROPOSALS_ANALYSIS_ID,
        "snapshot_id": snapshot_id,
        "generated_at": manifest.get("generated_at"),
        "source_artifact_refs": manifest.get("source_artifact_refs", []),
        "signals": signals_payload.get("signals", []),
        "proposals": proposals_payload.get("proposals", []),
        "warnings": manifest.get("warnings", []),
    }
    try:
        return SteeringProposalBundle.model_validate(payload)
    except ValidationError as exc:
        warnings.append(f"Invalid steering proposal artifact: {exc}")
        return None


def topic_governance_proposal(
    *,
    proposal_id: str,
    topic_uid: str,
    display_name: str,
    description: str,
    evidence: Dict[str, Any],
    suggested_seed_item_ids: Sequence[str],
    suggested_holdout_item_ids: Sequence[str],
    rationale: str,
    confidence: Optional[float] = None,
) -> SteeringProposal:
    """
    Create a unified topic governance proposal.

    :param proposal_id: Stable proposal identifier.
    :type proposal_id: str
    :param topic_uid: Proposed topic identity.
    :type topic_uid: str
    :param display_name: Proposed display name.
    :type display_name: str
    :param description: Proposed description.
    :type description: str
    :param evidence: Proposal evidence.
    :type evidence: dict[str, Any]
    :param suggested_seed_item_ids: Suggested seed item identifiers.
    :type suggested_seed_item_ids: collections.abc.Sequence[str]
    :param suggested_holdout_item_ids: Suggested holdout item identifiers.
    :type suggested_holdout_item_ids: collections.abc.Sequence[str]
    :param rationale: Proposal rationale.
    :type rationale: str
    :param confidence: Optional confidence score.
    :type confidence: float or None
    :return: Unified steering proposal.
    :rtype: SteeringProposal
    """
    return SteeringProposal(
        proposal_id=proposal_id,
        proposal_kind="new-topic",
        domain="topic",
        recommendation="recommend",
        author={"kind": "biblicus", "id": "topic-trends"},
        source_signal_ids=[],
        evidence=evidence,
        rationale=rationale,
        confidence=confidence,
        payload={
            "topic_uid": topic_uid,
            "display_name": display_name,
            "description": description,
            "suggested_seed_item_ids": list(suggested_seed_item_ids),
            "suggested_holdout_item_ids": list(suggested_holdout_item_ids),
        },
    )


def _topic_entity_signals(
    *,
    accepted_topics: Sequence[Dict[str, Any]],
    graph_manifest: GraphSnapshotManifest,
    source_artifact_refs: Sequence[str],
) -> List[SteeringSignal]:
    signals: List[SteeringSignal] = []
    topic_node_ids = _string_list(graph_manifest.stats.get("topic_node_ids"))
    entity_labels = _string_list(graph_manifest.stats.get("entity_labels"))
    labels_by_key = {_canonical_key(label): label for label in entity_labels}
    topic_node_id_set = set(topic_node_ids)
    for topic in accepted_topics:
        topic_uid = str(topic["topic_uid"])
        display_name = str(topic["display_name"])
        description = str(topic["description"])
        expected_node_id = f"topic:{topic_uid}"
        if expected_node_id not in topic_node_id_set:
            signals.append(
                SteeringSignal(
                    signal_id=f"accepted-topic-missing-graph-entity:{topic_uid}",
                    signal_kind="accepted-topic-missing-graph-entity",
                    domain="graph",
                    source_artifact_refs=list(source_artifact_refs),
                    metrics={"confidence": 1.0},
                    evidence_item_ids=sorted(
                        [*topic.get("seed_item_ids", []), *topic.get("holdout_item_ids", [])]
                    ),
                    payload={
                        "topic_uid": topic_uid,
                        "parent_topic_uid": topic.get("parent_topic_uid"),
                        "display_name": display_name,
                        "description": description,
                        "expected_node_id": expected_node_id,
                    },
                )
            )
        collision_label = labels_by_key.get(_canonical_key(display_name))
        if collision_label is not None:
            signals.append(
                SteeringSignal(
                    signal_id=f"topic-entity-name-collision:{topic_uid}",
                    signal_kind="topic-entity-name-collision",
                    domain="graph",
                    source_artifact_refs=list(source_artifact_refs),
                    metrics={"name_similarity": 1.0},
                    evidence_item_ids=[],
                    payload={
                        "topic_uid": topic_uid,
                        "parent_topic_uid": topic.get("parent_topic_uid"),
                        "display_name": display_name,
                        "entity_label": collision_label,
                    },
                )
            )
    signals.extend(_duplicate_entity_signals(entity_labels, source_artifact_refs))
    signals.extend(_generic_entity_signals(entity_labels, source_artifact_refs))
    return signals


def _accepted_topics_for_graph_signals(
    *,
    corpus: Corpus,
    classifier_id: str,
    warnings: List[str],
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    from .taxonomy import load_latest_taxonomy_manifest

    taxonomy = load_latest_taxonomy_manifest(corpus)
    if taxonomy is not None:
        accepted = [
            {
                "topic_uid": node.topic_uid,
                "parent_topic_uid": node.parent_topic_uid,
                "display_name": node.display_name,
                "description": node.description,
                "seed_item_ids": list(node.seed_item_ids),
                "holdout_item_ids": list(node.holdout_item_ids),
            }
            for node in taxonomy.nodes
            if node.status == "accepted"
        ]
        return accepted, f"taxonomy:{taxonomy.snapshot_id}"
    seed_manifest_path = (
        corpus.meta_dir / "topic-classifiers" / classifier_id / "seed-manifest.json"
    )
    seed_manifest = load_topic_classifier_seed_manifest(seed_manifest_path)
    return [
        {
            "topic_uid": topic.topic_uid,
            "parent_topic_uid": None,
            "display_name": topic.display_name,
            "description": topic.description,
            "seed_item_ids": list(topic.seed_item_ids),
            "holdout_item_ids": list(topic.holdout_item_ids),
        }
        for topic in seed_manifest.topics
    ], None


def _topic_membership_signals(
    *,
    topic_map: Dict[str, Any],
    source_artifact_refs: Sequence[str],
) -> List[SteeringSignal]:
    item_ids_by_topic: Dict[str, set[str]] = {}
    display_name_by_topic: Dict[str, str] = {}
    for topic in topic_map.get("topics", []):
        if not isinstance(topic, dict):
            continue
        topic_uid = topic.get("topic_uid")
        if not isinstance(topic_uid, str) or not topic_uid.strip():
            continue
        display_name = topic.get("display_name")
        if isinstance(display_name, str):
            display_name_by_topic[topic_uid] = display_name
        item_ids_by_topic.setdefault(topic_uid, set()).update(
            _string_list(topic.get("seed_item_ids"))
        )
        item_ids_by_topic.setdefault(topic_uid, set()).update(
            _string_list(topic.get("holdout_item_ids"))
        )
    for mapping in topic_map.get("mappings", []):
        if not isinstance(mapping, dict):
            continue
        topic_uid = mapping.get("topic_uid")
        if not isinstance(topic_uid, str) or not topic_uid.strip():
            continue
        display_name = mapping.get("display_name")
        if isinstance(display_name, str):
            display_name_by_topic[topic_uid] = display_name
        item_ids_by_topic.setdefault(topic_uid, set()).update(
            _string_list(mapping.get("document_ids"))
        )
    signals: List[SteeringSignal] = []
    for topic_uid in sorted(item_ids_by_topic):
        item_ids = sorted(item_ids_by_topic[topic_uid])
        if not item_ids:
            continue
        signals.append(
            SteeringSignal(
                signal_id=f"topic-membership-edge-candidate:{topic_uid}",
                signal_kind="topic-membership-edge-candidate",
                domain="graph",
                source_artifact_refs=list(source_artifact_refs),
                metrics={"document_count": len(item_ids)},
                evidence_item_ids=item_ids,
                payload={
                    "topic_uid": topic_uid,
                    "display_name": display_name_by_topic.get(topic_uid),
                    "topic_node_id": f"topic:{topic_uid}",
                    "edge_type": "classified_as_topic",
                    "item_ids": item_ids,
                },
            )
        )
    return signals


def _topic_relationship_signals(
    *,
    topic_map: Dict[str, Any],
    source_artifact_refs: Sequence[str],
) -> List[SteeringSignal]:
    keyword_sets: Dict[str, set[str]] = {}
    item_sets: Dict[str, set[str]] = {}
    for mapping in topic_map.get("mappings", []):
        if not isinstance(mapping, dict):
            continue
        topic_uid = mapping.get("topic_uid")
        if not isinstance(topic_uid, str) or not topic_uid.strip():
            continue
        keyword_sets.setdefault(topic_uid, set()).update(
            _canonical_key(keyword) for keyword in _string_list(mapping.get("keywords"))
        )
        item_sets.setdefault(topic_uid, set()).update(_string_list(mapping.get("document_ids")))
    signals: List[SteeringSignal] = []
    for left, right in combinations(sorted(keyword_sets), 2):
        shared_keywords = sorted(keyword_sets[left].intersection(keyword_sets[right]))
        if len(shared_keywords) < 2:
            continue
        evidence_item_ids = sorted(item_sets.get(left, set()).union(item_sets.get(right, set())))
        signals.append(
            SteeringSignal(
                signal_id=f"topic-relationship-edge-candidate:{left}:{right}",
                signal_kind="topic-relationship-edge-candidate",
                domain="graph",
                source_artifact_refs=list(source_artifact_refs),
                metrics={"shared_keyword_count": len(shared_keywords)},
                evidence_item_ids=evidence_item_ids,
                payload={
                    "left_topic_uid": left,
                    "right_topic_uid": right,
                    "edge_type": "related_to",
                    "shared_keywords": shared_keywords,
                },
            )
        )
    return signals


def _duplicate_entity_signals(
    entity_labels: Sequence[str], source_artifact_refs: Sequence[str]
) -> List[SteeringSignal]:
    counts = Counter(_canonical_key(label) for label in entity_labels)
    labels_by_key: Dict[str, List[str]] = {}
    for label in entity_labels:
        labels_by_key.setdefault(_canonical_key(label), []).append(label)
    signals: List[SteeringSignal] = []
    for canonical, count in sorted(counts.items()):
        if count < 2:
            continue
        signals.append(
            SteeringSignal(
                signal_id=f"possible-duplicate-entity:{canonical}",
                signal_kind="possible-duplicate-entity",
                domain="graph",
                source_artifact_refs=list(source_artifact_refs),
                metrics={"duplicate_label_count": count},
                evidence_item_ids=[],
                payload={"canonical": canonical, "labels": sorted(labels_by_key[canonical])},
            )
        )
    return signals


def _generic_entity_signals(
    entity_labels: Sequence[str], source_artifact_refs: Sequence[str]
) -> List[SteeringSignal]:
    signals: List[SteeringSignal] = []
    for label in sorted(entity_labels):
        canonical = _canonical_key(label)
        if canonical not in GENERIC_GRAPH_ENTITY_LABELS:
            continue
        signals.append(
            SteeringSignal(
                signal_id=f"noisy-generic-entity:{canonical}",
                signal_kind="noisy-generic-entity",
                domain="graph",
                source_artifact_refs=list(source_artifact_refs),
                metrics={"generic_entity": True},
                evidence_item_ids=[],
                payload={"node_id": f"entity:{canonical}", "label": label},
            )
        )
    return signals


def _with_deterministic_snapshot_id(bundle: SteeringProposalBundle) -> SteeringProposalBundle:
    snapshot_id = _steering_proposal_snapshot_id(bundle)
    if bundle.snapshot_id is not None and bundle.snapshot_id != snapshot_id:
        raise ValueError("Steering proposal snapshot_id does not match deterministic content hash")
    return bundle.model_copy(update={"snapshot_id": snapshot_id})


def _steering_proposal_snapshot_id(bundle: SteeringProposalBundle) -> str:
    payload = bundle.model_dump(mode="json", exclude={"snapshot_id"})
    return hash_text(json.dumps(payload, sort_keys=True))


def _required_snapshot_id(bundle: SteeringProposalBundle) -> str:
    if bundle.snapshot_id is None:
        raise ValueError("Steering proposal bundle is missing snapshot_id after validation")
    return bundle.snapshot_id


def _validate_unique_ids(field_name: str, values: Sequence[str]) -> None:
    counts = Counter(values)
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate {field_name}: {', '.join(duplicates)}")


def _reject_human_decision_fields(value: Dict[str, Any]) -> None:
    direct_matches = sorted(set(value).intersection(HUMAN_DECISION_FIELDS))
    nested_matches: List[str] = []
    for field_name in ["author", "evidence", "payload"]:
        nested = value.get(field_name)
        if isinstance(nested, dict):
            nested_matches.extend(
                f"{field_name}.{name}"
                for name in sorted(set(nested).intersection(HUMAN_DECISION_FIELDS))
            )
    matches = [*direct_matches, *nested_matches]
    if matches:
        raise ValueError(
            "Human decisions must not be stored in Biblicus steering proposals: "
            + ", ".join(matches)
        )


def _read_json_object(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Steering proposal file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid steering proposal JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Steering proposal JSON must contain an object: {path}")
    return payload


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _string_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _canonical_key(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return re.sub(r"-+", "-", normalized).strip("-")
