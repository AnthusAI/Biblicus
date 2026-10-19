"""
Steering signal and proposal models shared by steering proposal and taxonomy modules.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION

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
            reject_human_decision_fields(value)
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


def reject_human_decision_fields(value: Dict[str, Any]) -> None:
    """
    Reject payloads that carry human decision state.

    :param value: Candidate proposal or bundle mapping.
    :type value: dict[str, Any]
    :return: None.
    :rtype: None
    :raises ValueError: When human decision fields are present at the top level or nested.
    """
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
