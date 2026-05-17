from __future__ import annotations

import json
from pathlib import Path

import pytest

from biblicus.steering_feedback import (
    graph_signal_suppression,
    load_steering_feedback,
    normalize_feedback_text,
    steering_feedback_ref,
    taxonomy_candidate_suppression,
)
from biblicus.steering_proposals import SteeringSignal


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _feedback_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "export_kind": "papyrus-steering-feedback",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "source": {
            "system": "papyrus",
            "topic_set_id": "topic-set-one",
            "corpus_id": "corpus-one",
            "classifier_id": "steering-classifier",
        },
        "topic_set": {
            "topic_set_id": "topic-set-one",
            "corpus_id": "corpus-one",
            "classifier_id": "steering-classifier",
            "display_name": "Topic Set",
            "description": "Reviewed topics.",
        },
        "decisions": [
            {
                "decision_id": "decision-one",
                "proposal_id": "create-taxonomy-node:memory",
                "topic_set_id": "topic-set-one",
                "action": "reject",
                "selected_topic_uid": "agent-systems",
                "note": "Too broad.",
                "actor_label": "editor@example.com",
                "actor_sub": "editor-sub",
                "created_at": "2026-05-16T00:00:00+00:00",
            }
        ],
        "accepted_proposals": [],
        "rejected_proposals": [
            {
                "proposal_id": "create-taxonomy-node:memory",
                "proposal_kind": "create-taxonomy-node",
                "steering_domain": "topic",
                "status": "rejected",
                "human_action": "reject",
                "decided_at": "2026-05-16T00:00:00+00:00",
                "decided_by": "editor@example.com",
                "decision_id": "decision-one",
                "topic_set_id": "topic-set-one",
                "corpus_id": "corpus-one",
                "topic_uid": "agent-systems-memory",
                "target_topic_uid": "agent-systems",
                "graph_entity_id": None,
                "relationship_type": None,
                "display_name": "Agent Memory",
                "subtitle": None,
                "description": None,
                "summary": "Too broad.",
                "evidence_item_ids": [],
                "suggested_seed_item_ids": [],
                "suggested_holdout_item_ids": [],
                "source_snapshot_id": None,
            }
        ],
        "suppressions": [
            {
                "suppression_id": "suppression-taxonomy-memory",
                "proposal_id": "create-taxonomy-node:memory",
                "proposal_kind": "create-taxonomy-node",
                "steering_domain": "topic",
                "reason": "Too broad.",
                "decided_at": "2026-05-16T00:00:00+00:00",
                "decided_by": "editor@example.com",
                "scope": {
                    "topic_set_id": "topic-set-one",
                    "corpus_id": "corpus-one",
                    "classifier_id": "steering-classifier",
                    "root_topic_uid": "agent-systems",
                },
                "match": {
                    "topic_uid": "agent-systems-memory",
                    "display_name": "Agent Memory",
                    "normalized_display_name": "agent memory",
                    "relationship_type": None,
                    "graph_entity_id": None,
                },
                "evidence_item_ids": [],
            },
            {
                "suppression_id": "suppression-topic-entity",
                "proposal_id": "create-topic-entity:agent-systems",
                "proposal_kind": "create-topic-entity",
                "steering_domain": "graph",
                "reason": "Already covered.",
                "decided_at": "2026-05-16T00:00:00+00:00",
                "decided_by": "editor@example.com",
                "scope": {
                    "topic_set_id": "topic-set-one",
                    "corpus_id": "corpus-one",
                    "classifier_id": "steering-classifier",
                    "root_topic_uid": "agent-systems",
                },
                "match": {
                    "topic_uid": "agent-systems",
                    "display_name": "Agent Systems",
                    "normalized_display_name": "agent systems",
                    "relationship_type": None,
                    "graph_entity_id": "topic:agent-systems",
                },
                "evidence_item_ids": [],
            },
        ],
    }


def test_load_steering_feedback_validates_papyrus_export(tmp_path: Path) -> None:
    """Steering feedback loading accepts the Papyrus suppression export shape."""
    path = tmp_path / "feedback.json"
    _write_json(path, _feedback_payload())

    feedback = load_steering_feedback(path)

    assert feedback.export_kind == "papyrus-steering-feedback"
    assert len(feedback.decisions) == 1
    assert len(feedback.suppressions) == 2
    assert steering_feedback_ref(feedback).startswith("steering-feedback:")


def test_load_steering_feedback_rejects_malformed_input(tmp_path: Path) -> None:
    """Steering feedback loading rejects malformed or non-object input."""
    path = tmp_path / "feedback.json"
    payload = _feedback_payload()
    payload["unexpected"] = "not allowed"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="Invalid steering feedback"):
        load_steering_feedback(path)

    list_path = tmp_path / "list.json"
    _write_json(list_path, [])
    with pytest.raises(ValueError, match="must contain an object"):
        load_steering_feedback(list_path)


def test_taxonomy_candidate_suppression_matches_scope_and_label(tmp_path: Path) -> None:
    """Taxonomy suppression respects classifier, root topic, and normalized label scope."""
    path = tmp_path / "feedback.json"
    _write_json(path, _feedback_payload())
    feedback = load_steering_feedback(path)

    matched = taxonomy_candidate_suppression(
        feedback=feedback,
        classifier_id="steering-classifier",
        root_topic_uid="agent-systems",
        topic_uid="agent-systems-other",
        display_name="Agent Memory",
    )
    ignored = taxonomy_candidate_suppression(
        feedback=feedback,
        classifier_id="other-classifier",
        root_topic_uid="agent-systems",
        topic_uid="agent-systems-memory",
        display_name="Agent Memory",
    )

    assert matched is not None
    assert matched.suppression_id == "suppression-taxonomy-memory"
    assert ignored is None


def test_graph_signal_suppression_matches_topic_entity_signal(tmp_path: Path) -> None:
    """Graph suppression matches missing topic entity signals by topic and node identity."""
    path = tmp_path / "feedback.json"
    _write_json(path, _feedback_payload())
    feedback = load_steering_feedback(path)
    signal = SteeringSignal(
        signal_id="accepted-topic-missing-graph-entity:agent-systems",
        signal_kind="accepted-topic-missing-graph-entity",
        domain="graph",
        source_artifact_refs=["graph:simple-entities:one"],
        metrics={"confidence": 1.0},
        evidence_item_ids=[],
        payload={
            "topic_uid": "agent-systems",
            "display_name": "Agent Systems",
            "expected_node_id": "topic:agent-systems",
        },
    )

    matched = graph_signal_suppression(
        feedback=feedback,
        classifier_id="steering-classifier",
        signal=signal,
    )

    assert matched is not None
    assert matched.suppression_id == "suppression-topic-entity"
    assert normalize_feedback_text("  Agent   Systems  ") == "agent systems"
