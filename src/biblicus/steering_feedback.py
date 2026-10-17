"""
Steering feedback contracts for reviewed proposal suppressions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import Field, ValidationError, field_validator, model_validator

from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION
from .retrieval import hash_text

PAPYRUS_STEERING_FEEDBACK_KIND = "papyrus-steering-feedback"
TAXONOMY_SUPPRESSION_PROPOSAL_KINDS = {"create-taxonomy-node"}
GRAPH_SUPPRESSION_PROPOSAL_KINDS_BY_SIGNAL_KIND = {
    "accepted-topic-missing-graph-entity": {"create-topic-entity"},
    "topic-entity-name-collision": {"map-topic-to-entity", "add-entity-alias"},
    "topic-membership-edge-candidate": {"add-topic-membership-edge"},
    "topic-relationship-edge-candidate": {
        "add-topic-relationship-edge",
        "add-ontology-relationship",
    },
    "possible-duplicate-entity": {"merge-entities"},
    "noisy-generic-entity": {"suppress-entity-or-edge"},
}


class SteeringFeedbackSource(AnalysisSchemaModel):
    """
    Source metadata for an external steering feedback export.

    :ivar system: External system identity.
    :vartype system: str
    :ivar topic_set_id: External topic-set identity.
    :vartype topic_set_id: str or None
    :ivar corpus_id: External corpus identity.
    :vartype corpus_id: str or None
    :ivar classifier_id: External classifier identity.
    :vartype classifier_id: str or None
    """

    system: str = Field(min_length=1)
    topic_set_id: Optional[str] = None
    corpus_id: Optional[str] = None
    classifier_id: Optional[str] = None


class SteeringFeedbackTopicSet(AnalysisSchemaModel):
    """
    Topic-set metadata for an external steering feedback export.

    :ivar topic_set_id: External topic-set identity.
    :vartype topic_set_id: str
    :ivar corpus_id: External corpus identity.
    :vartype corpus_id: str or None
    :ivar classifier_id: External classifier identity.
    :vartype classifier_id: str or None
    :ivar display_name: Human-readable topic-set name.
    :vartype display_name: str or None
    :ivar description: Topic-set description.
    :vartype description: str or None
    """

    topic_set_id: str = Field(min_length=1)
    corpus_id: Optional[str] = None
    classifier_id: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None


class SteeringFeedbackDecision(AnalysisSchemaModel):
    """
    Append-only human decision exported by the steering application.

    :ivar decision_id: External decision identity.
    :vartype decision_id: str
    :ivar proposal_id: External proposal identity.
    :vartype proposal_id: str
    :ivar topic_set_id: External topic-set identity.
    :vartype topic_set_id: str or None
    :ivar action: Human review action.
    :vartype action: str
    :ivar selected_topic_uid: Selected topic identity, when present.
    :vartype selected_topic_uid: str or None
    :ivar note: Reviewer note.
    :vartype note: str or None
    :ivar actor_label: Reviewer label.
    :vartype actor_label: str or None
    :ivar actor_sub: Reviewer subject.
    :vartype actor_sub: str or None
    :ivar created_at: Decision timestamp.
    :vartype created_at: str or None
    """

    decision_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    topic_set_id: Optional[str] = None
    action: Literal["accept", "reject", "edit", "defer"]
    selected_topic_uid: Optional[str] = None
    note: Optional[str] = None
    actor_label: Optional[str] = None
    actor_sub: Optional[str] = None
    created_at: Optional[str] = None


class SteeringFeedbackReviewedProposal(AnalysisSchemaModel):
    """
    Reviewed proposal summary exported by the steering application.

    :ivar proposal_id: External proposal identity.
    :vartype proposal_id: str
    :ivar proposal_kind: Proposal kind.
    :vartype proposal_kind: str
    :ivar steering_domain: Steering domain.
    :vartype steering_domain: str or None
    :ivar status: Reviewed proposal status.
    :vartype status: str
    :ivar human_action: Human review action.
    :vartype human_action: str or None
    :ivar decided_at: Decision timestamp.
    :vartype decided_at: str or None
    :ivar decided_by: Reviewer label.
    :vartype decided_by: str or None
    :ivar decision_id: External decision identity.
    :vartype decision_id: str or None
    :ivar topic_set_id: External topic-set identity.
    :vartype topic_set_id: str or None
    :ivar corpus_id: External corpus identity.
    :vartype corpus_id: str or None
    :ivar topic_uid: Topic identity.
    :vartype topic_uid: str or None
    :ivar target_topic_uid: Target topic identity.
    :vartype target_topic_uid: str or None
    :ivar graph_entity_id: Graph entity identity.
    :vartype graph_entity_id: str or None
    :ivar relationship_type: Relationship type identity.
    :vartype relationship_type: str or None
    :ivar display_name: Display name.
    :vartype display_name: str or None
    :ivar subtitle: Subtitle.
    :vartype subtitle: str or None
    :ivar description: Description.
    :vartype description: str or None
    :ivar summary: Review summary.
    :vartype summary: str or None
    :ivar evidence_item_ids: Evidence item identifiers.
    :vartype evidence_item_ids: list[str]
    :ivar suggested_seed_item_ids: Suggested seed item identifiers.
    :vartype suggested_seed_item_ids: list[str]
    :ivar suggested_holdout_item_ids: Suggested holdout item identifiers.
    :vartype suggested_holdout_item_ids: list[str]
    :ivar source_snapshot_id: Source snapshot identity.
    :vartype source_snapshot_id: str or None
    """

    proposal_id: str = Field(min_length=1)
    proposal_kind: str = Field(min_length=1)
    steering_domain: Optional[str] = None
    status: Literal["accepted", "rejected"]
    human_action: Optional[Literal["accept", "reject", "edit", "defer"]] = None
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    decision_id: Optional[str] = None
    topic_set_id: Optional[str] = None
    corpus_id: Optional[str] = None
    topic_uid: Optional[str] = None
    target_topic_uid: Optional[str] = None
    graph_entity_id: Optional[str] = None
    relationship_type: Optional[str] = None
    display_name: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    evidence_item_ids: List[str] = Field(default_factory=list)
    suggested_seed_item_ids: List[str] = Field(default_factory=list)
    suggested_holdout_item_ids: List[str] = Field(default_factory=list)
    source_snapshot_id: Optional[str] = None


class SteeringSuppressionScope(AnalysisSchemaModel):
    """
    Scope for a reviewed suppression rule.

    :ivar topic_set_id: External topic-set identity.
    :vartype topic_set_id: str or None
    :ivar corpus_id: External corpus identity.
    :vartype corpus_id: str or None
    :ivar classifier_id: External classifier identity.
    :vartype classifier_id: str or None
    :ivar root_topic_uid: Root topic identity for scoped discovery.
    :vartype root_topic_uid: str or None
    """

    topic_set_id: Optional[str] = None
    corpus_id: Optional[str] = None
    classifier_id: Optional[str] = None
    root_topic_uid: Optional[str] = None


class SteeringSuppressionMatch(AnalysisSchemaModel):
    """
    Match fields for a reviewed suppression rule.

    :ivar topic_uid: Topic identity to suppress.
    :vartype topic_uid: str or None
    :ivar display_name: Display name to suppress.
    :vartype display_name: str or None
    :ivar normalized_display_name: Normalized display name to suppress.
    :vartype normalized_display_name: str or None
    :ivar relationship_type: Relationship type to suppress.
    :vartype relationship_type: str or None
    :ivar graph_entity_id: Graph entity identity to suppress.
    :vartype graph_entity_id: str or None
    """

    topic_uid: Optional[str] = None
    display_name: Optional[str] = None
    normalized_display_name: Optional[str] = None
    relationship_type: Optional[str] = None
    graph_entity_id: Optional[str] = None


class SteeringSuppression(AnalysisSchemaModel):
    """
    Normalized suppression rule derived from a rejected proposal.

    :ivar suppression_id: Suppression identity.
    :vartype suppression_id: str
    :ivar proposal_id: Rejected proposal identity.
    :vartype proposal_id: str
    :ivar proposal_kind: Rejected proposal kind.
    :vartype proposal_kind: str
    :ivar steering_domain: Steering domain.
    :vartype steering_domain: str or None
    :ivar reason: Suppression reason.
    :vartype reason: str or None
    :ivar decided_at: Decision timestamp.
    :vartype decided_at: str or None
    :ivar decided_by: Reviewer label.
    :vartype decided_by: str or None
    :ivar scope: Suppression scope.
    :vartype scope: SteeringSuppressionScope
    :ivar match: Suppression match fields.
    :vartype match: SteeringSuppressionMatch
    :ivar evidence_item_ids: Evidence item identifiers.
    :vartype evidence_item_ids: list[str]
    """

    suppression_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    proposal_kind: str = Field(min_length=1)
    steering_domain: Optional[str] = None
    reason: Optional[str] = None
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    scope: SteeringSuppressionScope
    match: SteeringSuppressionMatch
    evidence_item_ids: List[str] = Field(default_factory=list)


class SteeringFeedback(AnalysisSchemaModel):
    """
    External steering feedback export consumed by Biblicus proposal generation.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar export_kind: Feedback export kind.
    :vartype export_kind: str
    :ivar generated_at: Export timestamp.
    :vartype generated_at: str
    :ivar source: Source metadata.
    :vartype source: SteeringFeedbackSource
    :ivar topic_set: Topic-set metadata.
    :vartype topic_set: SteeringFeedbackTopicSet
    :ivar decisions: Append-only decision records.
    :vartype decisions: list[SteeringFeedbackDecision]
    :ivar accepted_proposals: Accepted proposal summaries.
    :vartype accepted_proposals: list[SteeringFeedbackReviewedProposal]
    :ivar rejected_proposals: Rejected proposal summaries.
    :vartype rejected_proposals: list[SteeringFeedbackReviewedProposal]
    :ivar suppressions: Normalized suppression rules.
    :vartype suppressions: list[SteeringSuppression]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    export_kind: Literal["papyrus-steering-feedback"]
    generated_at: str = Field(min_length=1)
    source: SteeringFeedbackSource
    topic_set: SteeringFeedbackTopicSet
    decisions: List[SteeringFeedbackDecision] = Field(default_factory=list)
    accepted_proposals: List[SteeringFeedbackReviewedProposal] = Field(default_factory=list)
    rejected_proposals: List[SteeringFeedbackReviewedProposal] = Field(default_factory=list)
    suppressions: List[SteeringSuppression] = Field(default_factory=list)

    @field_validator("export_kind")
    @classmethod
    def _validate_export_kind(cls, value: str) -> str:
        if value != PAPYRUS_STEERING_FEEDBACK_KIND:
            raise ValueError(f"Unsupported steering feedback export_kind: {value}")
        return value

    @model_validator(mode="after")
    def _validate_schema_version(self) -> "SteeringFeedback":
        if self.schema_version != ANALYSIS_SCHEMA_VERSION:
            raise ValueError(f"Unsupported steering feedback schema_version: {self.schema_version}")
        return self


def load_steering_feedback(path: Path) -> SteeringFeedback:
    """
    Load and validate a Papyrus steering feedback JSON file.

    :param path: Steering feedback JSON path.
    :type path: pathlib.Path
    :return: Validated steering feedback export.
    :rtype: SteeringFeedback
    :raises FileNotFoundError: If the feedback file does not exist.
    :raises ValueError: If the feedback file is malformed.
    """
    payload = _read_json_object(path)
    try:
        return SteeringFeedback.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid steering feedback: {exc}") from exc


def steering_feedback_ref(feedback: SteeringFeedback) -> str:
    """
    Return a deterministic source reference for a steering feedback export.

    :param feedback: Steering feedback export.
    :type feedback: SteeringFeedback
    :return: Feedback source reference.
    :rtype: str
    """
    payload = feedback.model_dump(mode="json")
    return "steering-feedback:" + hash_text(json.dumps(payload, sort_keys=True))


def taxonomy_candidate_suppression(
    *,
    feedback: Optional[SteeringFeedback],
    classifier_id: str,
    root_topic_uid: str,
    topic_uid: str,
    display_name: str,
) -> Optional[SteeringSuppression]:
    """
    Find a feedback suppression matching a taxonomy child-topic candidate.

    :param feedback: Optional steering feedback export.
    :type feedback: SteeringFeedback or None
    :param classifier_id: Current classifier identity.
    :type classifier_id: str
    :param root_topic_uid: Current root topic identity.
    :type root_topic_uid: str
    :param topic_uid: Candidate child topic identity.
    :type topic_uid: str
    :param display_name: Candidate display name.
    :type display_name: str
    :return: Matching suppression or None.
    :rtype: SteeringSuppression or None
    """
    if feedback is None:
        return None
    for suppression in feedback.suppressions:
        if suppression.proposal_kind not in TAXONOMY_SUPPRESSION_PROPOSAL_KINDS:
            continue
        if not _scope_matches(
            suppression=suppression,
            classifier_id=classifier_id,
            root_topic_uids=[root_topic_uid],
        ):
            continue
        if _match_fields_match(
            suppression=suppression,
            topic_uids=[topic_uid],
            display_names=[display_name],
            relationship_types=[],
            graph_entity_ids=[],
        ):
            return suppression
    return None


def graph_signal_suppression(
    *,
    feedback: Optional[SteeringFeedback],
    classifier_id: str,
    signal: Any,
) -> Optional[SteeringSuppression]:
    """
    Find a feedback suppression matching a graph steering signal.

    :param feedback: Optional steering feedback export.
    :type feedback: SteeringFeedback or None
    :param classifier_id: Current classifier identity.
    :type classifier_id: str
    :param signal: Graph steering signal.
    :type signal: Any
    :return: Matching suppression or None.
    :rtype: SteeringSuppression or None
    """
    if feedback is None:
        return None
    signal_kind = getattr(signal, "signal_kind", "")
    proposal_kinds = GRAPH_SUPPRESSION_PROPOSAL_KINDS_BY_SIGNAL_KIND.get(signal_kind)
    if proposal_kinds is None:
        return None
    payload = getattr(signal, "payload", {})
    if not isinstance(payload, dict):
        payload = {}
    root_topic_uids = _payload_topic_uids(payload)
    for suppression in feedback.suppressions:
        if suppression.proposal_kind not in proposal_kinds:
            continue
        if not _scope_matches(
            suppression=suppression,
            classifier_id=classifier_id,
            root_topic_uids=root_topic_uids,
        ):
            continue
        if _match_fields_match(
            suppression=suppression,
            topic_uids=root_topic_uids,
            display_names=_payload_display_names(payload),
            relationship_types=_payload_relationship_types(payload),
            graph_entity_ids=_payload_graph_entity_ids(payload),
        ):
            return suppression
    return None


def normalize_feedback_text(value: Optional[str]) -> Optional[str]:
    """
    Normalize text for steering feedback matching.

    :param value: Text value.
    :type value: str or None
    :return: Normalized text or None.
    :rtype: str or None
    """
    if value is None or not value.strip():
        return None
    return re.sub(r"\s+", " ", value.strip().lower())


def _scope_matches(
    *,
    suppression: SteeringSuppression,
    classifier_id: str,
    root_topic_uids: Sequence[str],
) -> bool:
    scoped_classifier_id = suppression.scope.classifier_id
    if scoped_classifier_id is not None and scoped_classifier_id != classifier_id:
        return False
    scoped_root_topic_uid = suppression.scope.root_topic_uid
    if scoped_root_topic_uid is not None and scoped_root_topic_uid not in set(root_topic_uids):
        return False
    return True


def _match_fields_match(
    *,
    suppression: SteeringSuppression,
    topic_uids: Sequence[str],
    display_names: Sequence[str],
    relationship_types: Sequence[str],
    graph_entity_ids: Sequence[str],
) -> bool:
    if suppression.match.topic_uid is not None:
        if suppression.match.topic_uid in set(topic_uids):
            return True
    normalized_names = {
        normalized
        for normalized in (normalize_feedback_text(value) for value in display_names)
        if normalized is not None
    }
    normalized_match_names = {
        normalized
        for normalized in (
            normalize_feedback_text(suppression.match.display_name),
            normalize_feedback_text(suppression.match.normalized_display_name),
        )
        if normalized is not None
    }
    if normalized_match_names:
        if normalized_names.intersection(normalized_match_names):
            return True
    if suppression.match.relationship_type is not None:
        if suppression.match.relationship_type in set(relationship_types):
            return True
    if suppression.match.graph_entity_id is not None:
        if suppression.match.graph_entity_id in set(graph_entity_ids):
            return True
    return False


def _payload_topic_uids(payload: Dict[str, Any]) -> List[str]:
    keys = [
        "topic_uid",
        "parent_topic_uid",
        "target_topic_uid",
        "left_topic_uid",
        "right_topic_uid",
    ]
    return _payload_strings(payload, keys)


def _payload_display_names(payload: Dict[str, Any]) -> List[str]:
    names = _payload_strings(
        payload,
        ["display_name", "entity_label", "label", "canonical", "name"],
    )
    labels = payload.get("labels")
    if isinstance(labels, list):
        names.extend(entry for entry in labels if isinstance(entry, str) and entry.strip())
    return names


def _payload_relationship_types(payload: Dict[str, Any]) -> List[str]:
    return _payload_strings(payload, ["edge_type", "relationship_type", "relationship_uid"])


def _payload_graph_entity_ids(payload: Dict[str, Any]) -> List[str]:
    return _payload_strings(
        payload,
        [
            "expected_node_id",
            "node_id",
            "graph_entity_id",
            "entity_id",
            "source_ref",
            "target_ref",
        ],
    )


def _payload_strings(payload: Dict[str, Any], keys: Sequence[str]) -> List[str]:
    values: List[str] = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value)
    return values


def _read_json_object(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Steering feedback file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid steering feedback JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Steering feedback JSON must contain an object: {path}")
    return payload
