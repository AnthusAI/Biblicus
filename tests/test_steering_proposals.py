from __future__ import annotations

import json
from pathlib import Path

import pytest

from biblicus.corpus import Corpus
from biblicus.steering_proposals import (
    SteeringProposal,
    SteeringProposalBundle,
    SteeringSignal,
    _required_snapshot_id,
    _topic_membership_signals,
    _topic_relationship_signals,
    build_steering_graph_signal_bundle,
    load_latest_steering_proposal_bundle,
    load_recorded_steering_proposal_bundle,
    load_steering_proposal_bundle,
    record_steering_proposal_bundle,
    topic_governance_proposal,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _seed_manifest(corpus: Corpus, item_ids: list[str]) -> None:
    _write_json(
        corpus.meta_dir / "topic-classifiers" / "steering-classifier" / "seed-manifest.json",
        {
            "schema_version": 1,
            "classifier_id": "steering-classifier",
            "display_name": "Steering Classifier",
            "description": "Reviewed topics.",
            "topics": [
                {
                    "topic_uid": "agent-systems",
                    "display_name": "Agent Systems",
                    "description": "Agent systems.",
                    "seed_item_ids": [item_ids[0]],
                    "holdout_item_ids": [],
                }
            ],
            "unlabeled_policy": "use_minus_one",
        },
    )


def _topic_map(corpus: Corpus, item_ids: list[str]) -> None:
    run_dir = corpus.analysis_run_dir(analysis_id="topic-classifier", snapshot_id="model-one")
    _write_json(
        run_dir / "model-manifest.json",
        {"classifier_id": "steering-classifier", "model_version": "model-one"},
    )
    _write_json(
        run_dir / "topic-map.json",
        {
            "schema_version": 1,
            "classifier_id": "steering-classifier",
            "model_version": "model-one",
            "topics": [
                {
                    "topic_uid": "agent-systems",
                    "display_name": "Agent Systems",
                    "description": "Agent systems.",
                    "seed_item_ids": [item_ids[0]],
                    "holdout_item_ids": [],
                    "bertopic_topic_ids": [0],
                }
            ],
            "mappings": [
                {
                    "bertopic_topic_id": 0,
                    "topic_uid": "agent-systems",
                    "display_name": "Agent Systems",
                    "document_ids": item_ids,
                    "keywords": ["agent", "memory", "tools"],
                }
            ],
            "discovered": [],
        },
    )
    _write_json(
        corpus.analysis_dir / "topic-classifier" / "steering-classifier-latest.json",
        {"model_version": "model-one"},
    )


def _graph_manifest(corpus: Corpus) -> None:
    _write_json(
        corpus.graph_snapshot_dir(extractor_id="simple-entities", snapshot_id="graph-one")
        / "manifest.json",
        {
            "snapshot_id": "graph-one",
            "graph_id": "graph-one",
            "configuration": {
                "configuration_id": "graph-config",
                "extractor_id": "simple-entities",
                "name": "Graph",
                "created_at": "2026-05-16T00:00:00+00:00",
                "configuration": {},
            },
            "corpus_uri": corpus.uri,
            "catalog_generated_at": corpus.load_catalog().generated_at,
            "extraction_snapshot": "pipeline:extract-one",
            "created_at": "2026-05-16T00:00:00+00:00",
            "stats": {
                "topic_node_ids": [],
                "entity_labels": ["Agent Systems", "AI", "Agent Systems"],
            },
        },
    )


def _graph_manifest_with_existing_topic_node(corpus: Corpus) -> None:
    _write_json(
        corpus.graph_snapshot_dir(extractor_id="simple-entities", snapshot_id="graph-one")
        / "manifest.json",
        {
            "snapshot_id": "graph-one",
            "graph_id": "graph-one",
            "configuration": {
                "configuration_id": "graph-config",
                "extractor_id": "simple-entities",
                "name": "Graph",
                "created_at": "2026-05-16T00:00:00+00:00",
                "configuration": {},
            },
            "corpus_uri": corpus.uri,
            "catalog_generated_at": corpus.load_catalog().generated_at,
            "extraction_snapshot": "pipeline:extract-one",
            "created_at": "2026-05-16T00:00:00+00:00",
            "stats": {
                "topic_node_ids": ["topic:agent-systems"],
                "entity_labels": "not-a-list",
            },
        },
    )


def _proposal_bundle() -> dict[str, object]:
    return {
        "schema_version": 1,
        "analysis_id": "steering-proposals",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "source_artifact_refs": ["graph:simple-entities:graph-one"],
        "signals": [
            {
                "signal_id": "signal-one",
                "signal_kind": "accepted-topic-missing-graph-entity",
                "domain": "graph",
                "source_artifact_refs": ["graph:simple-entities:graph-one"],
                "metrics": {"confidence": 1.0},
                "evidence_item_ids": ["item-one"],
                "payload": {"topic_uid": "agent-systems"},
            }
        ],
        "proposals": [
            {
                "proposal_id": "proposal-one",
                "proposal_kind": "create-topic-entity",
                "domain": "graph",
                "recommendation": "recommend",
                "author": {"kind": "agent", "id": "unit-test"},
                "source_signal_ids": ["signal-one"],
                "evidence": {"item_ids": ["item-one"]},
                "rationale": "Accepted topics should have graph entities.",
                "confidence": 0.9,
                "payload": {"topic_uid": "agent-systems"},
            }
        ],
    }


def test_graph_signals_include_topic_entity_membership_and_mapping(tmp_path: Path) -> None:
    """Graph signals derive topic entity and membership candidates."""
    corpus = Corpus.init(tmp_path / "corpus")
    first = corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        source_uri="urn:test:agent",
    )
    second = corpus.ingest_item(
        b"tool use agents",
        filename="tools.txt",
        media_type="text/plain",
        title="Tool Agents",
        source_uri="urn:test:tools",
    )
    item_ids = [first.item_id, second.item_id]
    _seed_manifest(corpus, item_ids)
    _topic_map(corpus, item_ids)
    _graph_manifest(corpus)

    bundle = build_steering_graph_signal_bundle(
        corpus=corpus,
        classifier_id="steering-classifier",
        graph_snapshot="simple-entities:graph-one",
    )

    signal_kinds = {signal.signal_kind for signal in bundle.signals}
    assert "accepted-topic-missing-graph-entity" in signal_kinds
    assert "topic-membership-edge-candidate" in signal_kinds
    assert "topic-entity-name-collision" in signal_kinds
    assert "possible-duplicate-entity" in signal_kinds
    assert "noisy-generic-entity" in signal_kinds
    assert bundle.snapshot_id


def test_graph_signals_handle_existing_topic_node_and_missing_model(tmp_path: Path) -> None:
    """Graph signals skip existing topic entity signals and warn without a model bundle."""
    corpus = Corpus.init(tmp_path / "corpus")
    item = corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        source_uri="urn:test:agent",
    )
    _seed_manifest(corpus, [item.item_id])
    _graph_manifest_with_existing_topic_node(corpus)

    bundle = build_steering_graph_signal_bundle(
        corpus=corpus,
        classifier_id="steering-classifier",
        graph_snapshot="simple-entities:graph-one",
    )

    signal_kinds = {signal.signal_kind for signal in bundle.signals}
    assert "accepted-topic-missing-graph-entity" not in signal_kinds
    assert any("Missing topic classifier latest pointer" in warning for warning in bundle.warnings)


def test_proposal_bundle_validation_and_recording(tmp_path: Path) -> None:
    """Proposal bundles validate, receive deterministic ids, and record artifacts."""
    corpus = Corpus.init(tmp_path / "corpus")
    input_path = tmp_path / "proposal-bundle.json"
    _write_json(input_path, _proposal_bundle())

    bundle = load_steering_proposal_bundle(input_path)
    second_load = load_steering_proposal_bundle(input_path)
    output = record_steering_proposal_bundle(corpus=corpus, input_path=input_path)
    latest = load_latest_steering_proposal_bundle(corpus=corpus, warnings=[])

    assert bundle.snapshot_id == second_load.snapshot_id
    assert output.snapshot_id == bundle.snapshot_id
    assert output.signal_count == 1
    assert output.proposal_count == 1
    assert latest is not None
    assert latest.proposals[0].proposal_id == "proposal-one"


def test_proposal_bundle_rejects_invalid_payloads(tmp_path: Path) -> None:
    """Proposal bundle validation rejects malformed steering proposal records."""
    duplicate = _proposal_bundle()
    duplicate["proposals"].append(dict(duplicate["proposals"][0]))
    duplicate_path = tmp_path / "duplicate.json"
    _write_json(duplicate_path, duplicate)
    with pytest.raises(ValueError, match="Duplicate proposal_id"):
        load_steering_proposal_bundle(duplicate_path)

    unsupported = _proposal_bundle()
    unsupported["proposals"][0]["proposal_kind"] = "unsupported"
    unsupported_path = tmp_path / "unsupported.json"
    _write_json(unsupported_path, unsupported)
    with pytest.raises(ValueError, match="Unsupported steering proposal kind"):
        load_steering_proposal_bundle(unsupported_path)

    malformed_evidence = _proposal_bundle()
    malformed_evidence["proposals"][0]["evidence"] = []
    malformed_path = tmp_path / "malformed-evidence.json"
    _write_json(malformed_path, malformed_evidence)
    with pytest.raises(ValueError, match="Input should be a valid dictionary"):
        load_steering_proposal_bundle(malformed_path)

    human_decision = _proposal_bundle()
    human_decision["proposals"][0]["human_decision"] = {"decision": "accept"}
    human_decision_path = tmp_path / "human-decision.json"
    _write_json(human_decision_path, human_decision)
    with pytest.raises(ValueError, match="Human decisions must not be stored"):
        load_steering_proposal_bundle(human_decision_path)


def test_proposal_bundle_rejects_schema_and_reference_errors(tmp_path: Path) -> None:
    """Proposal bundle validation reports unsupported schema and reference failures."""
    invalid_signal_domain = _proposal_bundle()
    invalid_signal_domain["signals"][0]["domain"] = "other"
    invalid_signal_domain_path = tmp_path / "invalid-signal-domain.json"
    _write_json(invalid_signal_domain_path, invalid_signal_domain)
    with pytest.raises(ValueError, match="Unsupported steering domain"):
        load_steering_proposal_bundle(invalid_signal_domain_path)

    invalid_signal_kind = _proposal_bundle()
    invalid_signal_kind["signals"][0]["signal_kind"] = "unknown-signal"
    invalid_signal_kind_path = tmp_path / "invalid-signal-kind.json"
    _write_json(invalid_signal_kind_path, invalid_signal_kind)
    with pytest.raises(ValueError, match="Unsupported steering signal kind"):
        load_steering_proposal_bundle(invalid_signal_kind_path)

    invalid_proposal_domain = _proposal_bundle()
    invalid_proposal_domain["proposals"][0]["domain"] = "other"
    invalid_proposal_domain_path = tmp_path / "invalid-proposal-domain.json"
    _write_json(invalid_proposal_domain_path, invalid_proposal_domain)
    with pytest.raises(ValueError, match="Unsupported steering domain"):
        load_steering_proposal_bundle(invalid_proposal_domain_path)

    invalid_analysis = _proposal_bundle()
    invalid_analysis["analysis_id"] = "other"
    invalid_analysis_path = tmp_path / "invalid-analysis.json"
    _write_json(invalid_analysis_path, invalid_analysis)
    with pytest.raises(ValueError, match="analysis_id must be steering-proposals"):
        load_steering_proposal_bundle(invalid_analysis_path)

    missing_signal = _proposal_bundle()
    missing_signal["proposals"][0]["source_signal_ids"] = ["missing-signal"]
    missing_signal_path = tmp_path / "missing-signal.json"
    _write_json(missing_signal_path, missing_signal)
    with pytest.raises(ValueError, match="reference unknown signal IDs"):
        load_steering_proposal_bundle(missing_signal_path)


def test_proposal_bundle_io_error_branches(tmp_path: Path) -> None:
    """Proposal bundle loading and recorded artifact loading handle broken files."""
    with pytest.raises(FileNotFoundError, match="Steering proposal file not found"):
        load_steering_proposal_bundle(tmp_path / "missing.json")

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid steering proposal JSON"):
        load_steering_proposal_bundle(invalid_json)

    non_object = tmp_path / "non-object.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain an object"):
        load_steering_proposal_bundle(non_object)

    bundle_payload = _proposal_bundle()
    valid_path = tmp_path / "bundle.json"
    _write_json(valid_path, bundle_payload)
    bundle = load_steering_proposal_bundle(valid_path)
    mismatched = dict(bundle_payload)
    mismatched["snapshot_id"] = "not-the-content-hash"
    mismatched_path = tmp_path / "mismatch.json"
    _write_json(mismatched_path, mismatched)
    with pytest.raises(ValueError, match="snapshot_id does not match"):
        load_steering_proposal_bundle(mismatched_path)

    with pytest.raises(ValueError, match="missing snapshot_id"):
        _required_snapshot_id(bundle.model_copy(update={"snapshot_id": None}))


def test_recorded_proposal_artifact_error_branches(tmp_path: Path) -> None:
    """Recorded proposal bundle loading reports missing and malformed artifacts."""
    corpus = Corpus.init(tmp_path / "corpus")
    warnings: list[str] = []
    assert load_latest_steering_proposal_bundle(corpus=corpus, warnings=warnings) is None
    assert warnings == []

    _write_json(corpus.analysis_dir / "steering-proposals" / "latest.json", {})
    assert load_latest_steering_proposal_bundle(corpus=corpus, warnings=warnings) is None
    assert any("latest pointer has no snapshot_id" in warning for warning in warnings)

    warnings.clear()
    assert (
        load_recorded_steering_proposal_bundle(
            corpus=corpus,
            snapshot_id="missing",
            warnings=warnings,
        )
        is None
    )
    assert any("Missing steering proposal artifact files" in warning for warning in warnings)

    warnings.clear()
    run_dir = corpus.analysis_run_dir(
        analysis_id="steering-proposals",
        snapshot_id="bad",
    )
    _write_json(
        run_dir / "manifest.json",
        {"generated_at": "2026-05-16T00:00:00+00:00", "source_artifact_refs": []},
    )
    _write_json(run_dir / "signals.json", {"signals": []})
    _write_json(run_dir / "proposals.json", {"proposals": [{"proposal_id": "bad"}]})
    assert (
        load_recorded_steering_proposal_bundle(
            corpus=corpus,
            snapshot_id="bad",
            warnings=warnings,
        )
        is None
    )
    assert any("Invalid steering proposal artifact" in warning for warning in warnings)


def test_signal_helpers_cover_invalid_rows_and_relationships() -> None:
    """Signal helper branches skip malformed rows and emit relationship candidates."""
    membership = _topic_membership_signals(
        topic_map={
            "topics": [
                "not-a-dict",
                {"topic_uid": "   "},
                {"topic_uid": "empty-topic", "seed_item_ids": []},
            ],
            "mappings": [
                "not-a-dict",
                {"topic_uid": "   "},
                {
                    "topic_uid": "agent-systems",
                    "display_name": "Agent Systems",
                    "document_ids": ["item-one"],
                },
                {
                    "topic_uid": "mapped-no-name",
                    "display_name": 42,
                    "document_ids": ["item-two"],
                },
            ],
        },
        source_artifact_refs=["topic-classifier:model-one"],
    )
    relationships = _topic_relationship_signals(
        topic_map={
            "mappings": [
                "not-a-dict",
                {"topic_uid": "   "},
                {
                    "topic_uid": "agent-systems",
                    "document_ids": ["item-one"],
                    "keywords": ["agent", "memory", "tools"],
                },
                {
                    "topic_uid": "tool-agents",
                    "document_ids": ["item-two"],
                    "keywords": ["agent", "memory", "benchmarks"],
                },
                {
                    "topic_uid": "weak-topic",
                    "document_ids": ["item-three"],
                    "keywords": ["agent", "other"],
                },
            ]
        },
        source_artifact_refs=["topic-classifier:model-one"],
    )

    assert [signal.payload["topic_uid"] for signal in membership] == [
        "agent-systems",
        "mapped-no-name",
    ]
    assert relationships[0].signal_kind == "topic-relationship-edge-candidate"
    assert relationships[0].metrics["shared_keyword_count"] == 2


def test_direct_schema_models_reject_invalid_inputs() -> None:
    """Direct schema validation catches invalid signal and proposal inputs."""
    assert SteeringProposal._reject_human_decisions([]) == []
    assert SteeringProposalBundle._reject_bundle_human_decisions([]) == []

    with pytest.raises(ValueError, match="Unsupported steering domain"):
        SteeringSignal(
            signal_id="bad-domain",
            signal_kind="accepted-topic-missing-graph-entity",
            domain="other",
        )
    with pytest.raises(ValueError, match="Unsupported steering proposal kind"):
        SteeringProposal(
            proposal_id="bad-kind",
            proposal_kind="other",
            domain="graph",
            recommendation="recommend",
            rationale="Invalid kind.",
        )
    with pytest.raises(ValueError, match="Duplicate signal_id"):
        SteeringProposalBundle(
            generated_at="2026-05-16T00:00:00+00:00",
            signals=[
                SteeringSignal(
                    signal_id="duplicate",
                    signal_kind="accepted-topic-missing-graph-entity",
                    domain="graph",
                ),
                SteeringSignal(
                    signal_id="duplicate",
                    signal_kind="accepted-topic-missing-graph-entity",
                    domain="graph",
                ),
            ],
        )


def test_topic_governance_proposal_uses_unified_contract() -> None:
    """Topic trend governance can emit unified steering proposals."""
    proposal = topic_governance_proposal(
        proposal_id="new-topic:agent-systems",
        topic_uid="agent-systems",
        display_name="Agent Systems",
        description="Agent systems.",
        evidence={"item_ids": ["item-one"]},
        suggested_seed_item_ids=["item-one"],
        suggested_holdout_item_ids=[],
        rationale="Distinct discovered cluster.",
        confidence=0.7,
    )

    assert proposal.proposal_kind == "new-topic"
    assert proposal.domain == "topic"
    assert proposal.recommendation == "recommend"
    assert proposal.payload["topic_uid"] == "agent-systems"
