from __future__ import annotations

import json
from pathlib import Path

import pytest

from biblicus.corpus import Corpus
from biblicus.steering import (
    _collect_ignored_app_fields,
    _configuration_metadata,
    _latest_governance_snapshot_id,
    _read_json_file,
    _read_json_file_or_warn,
    _relative_to_corpus,
    _validate_topic_set_payload,
    build_steering_artifact_inventory,
    build_steering_export,
    render_steering_seed_manifest,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _base_topic_set() -> dict[str, object]:
    return {
        "schema_version": 1,
        "classifier_id": "steering-classifier",
        "display_name": "Steering Classifier",
        "description": "Reviewed topics.",
        "topics": [
            {
                "topic_uid": "agent-systems",
                "display_name": "Agent Systems",
                "description": "Agent systems.",
                "seed_item_ids": ["seed-one"],
                "holdout_item_ids": ["holdout-one"],
            }
        ],
        "unlabeled_policy": "use_minus_one",
    }


def _base_unified_proposal(proposal_id: str) -> dict[str, object]:
    return {
        "proposal_id": proposal_id,
        "proposal_kind": "new-topic",
        "domain": "topic",
        "recommendation": "recommend",
        "status": "proposed",
        "author": {"kind": "biblicus", "id": "topic-trends"},
        "source_signal_ids": [],
        "evidence": {"item_ids": []},
        "rationale": "Distinct discovered cluster.",
        "confidence": 0.8,
        "payload": {
            "topic_uid": "automated-discovery",
            "display_name": "Automated Discovery",
            "description": "Automated scientific discovery systems.",
            "suggested_seed_item_ids": [],
            "suggested_holdout_item_ids": [],
        },
    }


def _seed_manifest(path: Path, classifier_id: str = "steering-classifier") -> None:
    payload = _base_topic_set()
    payload["classifier_id"] = classifier_id
    _write_json(path, payload)


def test_steering_export_handles_missing_optional_state(tmp_path: Path) -> None:
    """Export reports items and warnings when optional steering state is absent."""
    corpus = Corpus.init(tmp_path / "corpus")
    corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        tags=["agent"],
        metadata={
            "dates": {"published_at": "2026-01-01"},
            "curation": {"intake_status": "pending_review"},
        },
        source_uri="urn:test:agent",
    )

    bundle = build_steering_export(corpus=corpus, classifier_id="missing-classifier")

    assert bundle.topic_set is None
    assert bundle.proposals == []
    assert bundle.items[0].title == "Agent Memory"
    assert bundle.items[0].dates["published_at"] == "2026-01-01"
    assert bundle.items[0].intake_status == "pending_review"
    assert any("Missing topic classifier seed manifest" in warning for warning in bundle.warnings)
    assert any("No topic-governance snapshot" in warning for warning in bundle.warnings)


def test_steering_export_loads_topic_set_and_latest_governance(tmp_path: Path) -> None:
    """Export loads the accepted topic set and latest governance proposals."""
    corpus = Corpus.init(tmp_path / "corpus")
    corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        metadata={"curation": {"intake_status": 42}},
        source_uri="urn:test:agent",
    )
    _seed_manifest(
        corpus.meta_dir / "topic-classifiers" / "steering-classifier" / "seed-manifest.json"
    )
    snapshot_id = "governance-one"
    run_dir = corpus.analysis_run_dir(analysis_id="topic-governance", snapshot_id=snapshot_id)
    _write_json(
        run_dir / "proposals.json",
        {
            "schema_version": 1,
            "snapshot_id": snapshot_id,
            "proposals": [
                _base_unified_proposal("proposal-one"),
                "not-an-object",
                {"proposal_id": "bad-proposal", "proposal_kind": "unknown"},
            ],
        },
    )
    _write_json(
        corpus.analysis_dir / "topic-governance" / "latest.json",
        {"snapshot_id": snapshot_id},
    )

    bundle = build_steering_export(corpus=corpus, classifier_id="steering-classifier")

    assert bundle.topic_set is not None
    assert bundle.topic_set.topics[0].topic_uid == "agent-systems"
    assert [proposal.proposal_id for proposal in bundle.proposals] == ["proposal-one"]
    assert bundle.items[0].intake_status is None
    assert any("Invalid topic-governance proposal" in warning for warning in bundle.warnings)


def test_steering_artifact_inventory_discovers_supported_kinds(tmp_path: Path) -> None:
    """Artifact inventory discovers all supported steering artifact kinds."""
    corpus = Corpus.init(tmp_path / "corpus")
    _write_json(
        corpus.extracted_dir / "pipeline" / "extract-one" / "manifest.json",
        {
            "snapshot_id": "extract-one",
            "created_at": "2026-05-16T00:00:00+00:00",
            "configuration": {
                "configuration_id": "extract-config",
                "name": "Extract",
                "extractor_id": "pipeline",
            },
        },
    )
    _write_json(
        corpus.retrieval_dir / "scan" / "retrieval-one" / "manifest.json",
        {
            "snapshot_id": "retrieval-one",
            "created_at": "2026-05-16T00:00:00+00:00",
            "configuration": {
                "configuration_id": "retrieval-config",
                "name": "Retrieve",
                "retriever_id": "scan",
            },
        },
    )
    _write_json(
        corpus.analysis_dir / "topic-modeling" / "topic-one" / "manifest.json",
        {
            "snapshot_id": "topic-one",
            "created_at": "2026-05-16T00:00:00+00:00",
            "configuration": {},
        },
    )
    _write_json(
        corpus.analysis_dir / "topic-context" / "context-one" / "manifest.json",
        {"snapshot_id": "context-one", "generated_at": "2026-05-16T00:00:00+00:00"},
    )
    _write_json(
        corpus.analysis_dir / "topic-governance" / "governance-one" / "manifest.json",
        {"snapshot_id": "governance-one", "generated_at": "2026-05-16T00:00:00+00:00"},
    )
    _write_json(
        corpus.analysis_dir / "topic-granularity-sweep" / "granularity-one" / "manifest.json",
        {"snapshot_id": "granularity-one", "generated_at": "2026-05-16T00:00:00+00:00"},
    )
    _write_json(
        corpus.analysis_dir / "steering-proposals" / "proposal-one" / "manifest.json",
        {"snapshot_id": "proposal-one", "generated_at": "2026-05-16T00:00:00+00:00"},
    )
    _write_json(
        corpus.analysis_dir / "topic-classifier" / "model-one" / "model-manifest.json",
        {"model_version": "model-one", "created_at": "2026-05-16T00:00:00+00:00"},
    )
    _write_json(
        corpus.analysis_dir / "unknown-analysis" / "unknown-one" / "manifest.json",
        {"snapshot_id": "unknown-one"},
    )
    _write_json(
        corpus.graph_dir / "simple-entities" / "graph-one" / "manifest.json",
        {
            "snapshot_id": "graph-one",
            "created_at": "2026-05-16T00:00:00+00:00",
            "graph_id": "simple-entities:graph",
        },
    )
    (corpus.graph_dir / "simple-entities" / "bad-graph").mkdir(parents=True)
    (corpus.graph_dir / "simple-entities" / "bad-graph" / "manifest.json").write_text(
        "{",
        encoding="utf-8",
    )
    for short_manifest in [
        corpus.extracted_dir / "orphan" / "manifest.json",
        corpus.retrieval_dir / "orphan" / "manifest.json",
        corpus.graph_dir / "orphan" / "manifest.json",
    ]:
        _write_json(short_manifest, {"snapshot_id": "ignored"})
    for bad_path in [
        corpus.extracted_dir / "pipeline" / "bad-extract" / "manifest.json",
        corpus.retrieval_dir / "scan" / "bad-retrieval" / "manifest.json",
        corpus.analysis_dir / "topic-context" / "bad-context" / "manifest.json",
        corpus.analysis_dir / "topic-classifier" / "bad-model" / "model-manifest.json",
    ]:
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("{", encoding="utf-8")

    inventory = build_steering_artifact_inventory(corpus)

    artifacts_by_kind = inventory.artifacts_by_kind
    assert artifacts_by_kind["extraction"][0].metadata["extractor_id"] == "pipeline"
    assert artifacts_by_kind["retrieval"][0].metadata["retriever_id"] == "scan"
    assert artifacts_by_kind["topic-modeling"]
    assert artifacts_by_kind["topic-context"]
    assert artifacts_by_kind["topic-governance"]
    assert artifacts_by_kind["topic-granularity"]
    assert artifacts_by_kind["steering-proposals"]
    assert artifacts_by_kind["topic-classifier"][0].artifact_id == "unknown-classifier:model-one"
    assert artifacts_by_kind["graph"][0].metadata["graph_id"] == "simple-entities:graph"
    assert any("Invalid JSON file" in warning for warning in inventory.warnings)


def test_steering_governance_warning_branches(tmp_path: Path) -> None:
    """Governance loading reports missing and malformed proposal artifacts."""
    corpus = Corpus.init(tmp_path / "corpus")
    warnings: list[str] = []
    _write_json(corpus.analysis_dir / "topic-governance" / "latest.json", {})
    assert _latest_governance_snapshot_id(corpus, warnings) is None
    assert any("latest pointer has no snapshot_id" in warning for warning in warnings)

    missing_bundle = build_steering_export(
        corpus=corpus,
        classifier_id="missing-classifier",
        topic_governance_snapshot_id="missing-governance",
    )
    assert any(
        "Missing topic-governance proposals artifact" in warning
        for warning in missing_bundle.warnings
    )

    run_dir = corpus.analysis_run_dir(
        analysis_id="topic-governance",
        snapshot_id="bad-proposals",
    )
    _write_json(run_dir / "proposals.json", {"schema_version": 1})
    bad_bundle = build_steering_export(
        corpus=corpus,
        classifier_id="missing-classifier",
        topic_governance_snapshot_id="bad-proposals",
    )
    assert any("has no proposals list" in warning for warning in bad_bundle.warnings)


def test_render_steering_seed_manifest_writes_strict_manifest(tmp_path: Path) -> None:
    """Seed-manifest rendering omits application-only topic fields."""
    payload = _base_topic_set()
    payload["topics"][0]["subheading"] = "Display copy"
    payload["topics"][0]["aliases"] = ["Agents"]
    payload["topics"][0]["editor_notes"] = "Application owned"
    payload["topics"][0]["ranking_hints"] = {"rank": 1}
    input_path = tmp_path / "topic-set.json"
    output_path = tmp_path / "seed-manifest.json"
    _write_json(input_path, payload)

    output = render_steering_seed_manifest(input_path=input_path, output_path=output_path)

    rendered = json.loads(output_path.read_text(encoding="utf-8"))
    assert output.topic_count == 1
    assert output.ignored_app_fields == ["aliases", "editor_notes", "ranking_hints", "subheading"]
    assert rendered["topics"][0]["topic_uid"] == "agent-systems"
    assert "subheading" not in rendered["topics"][0]


def test_render_steering_seed_manifest_error_branches(tmp_path: Path) -> None:
    """Seed-manifest rendering rejects malformed steering topic sets."""
    with pytest.raises(FileNotFoundError, match="Steering topic-set file not found"):
        render_steering_seed_manifest(
            input_path=tmp_path / "missing.json",
            output_path=tmp_path / "out.json",
        )

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid steering topic-set JSON"):
        render_steering_seed_manifest(input_path=invalid_json, output_path=tmp_path / "out.json")

    non_object = tmp_path / "non-object.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a mapping/object"):
        render_steering_seed_manifest(input_path=non_object, output_path=tmp_path / "out.json")

    unsupported_schema = _base_topic_set()
    unsupported_schema["schema_version"] = 99
    unsupported_schema_path = tmp_path / "unsupported-schema.json"
    _write_json(unsupported_schema_path, unsupported_schema)
    with pytest.raises(ValueError, match="Unsupported steering schema version"):
        render_steering_seed_manifest(
            input_path=unsupported_schema_path,
            output_path=tmp_path / "out.json",
        )

    invalid_policy = _base_topic_set()
    invalid_policy["unlabeled_policy"] = "other"
    invalid_policy_path = tmp_path / "invalid-policy.json"
    _write_json(invalid_policy_path, invalid_policy)
    with pytest.raises(ValueError, match="unlabeled_policy must be 'use_minus_one'"):
        render_steering_seed_manifest(
            input_path=invalid_policy_path,
            output_path=tmp_path / "out.json",
        )

    unknown_top_level = _base_topic_set()
    unknown_top_level["extra"] = "bad"
    unknown_top_level_path = tmp_path / "unknown-top.json"
    _write_json(unknown_top_level_path, unknown_top_level)
    with pytest.raises(ValueError, match="Unknown steering topic-set fields"):
        render_steering_seed_manifest(
            input_path=unknown_top_level_path,
            output_path=tmp_path / "out.json",
        )

    duplicate = _base_topic_set()
    duplicate["topics"].append(dict(duplicate["topics"][0]))
    duplicate_path = tmp_path / "duplicate.json"
    _write_json(duplicate_path, duplicate)
    with pytest.raises(ValueError, match="Duplicate topic_uid"):
        render_steering_seed_manifest(input_path=duplicate_path, output_path=tmp_path / "out.json")


def test_steering_helper_branches(tmp_path: Path) -> None:
    """Steering helpers expose clear branch behavior for invalid inputs."""
    corpus = Corpus.init(tmp_path / "corpus")
    warnings: list[str] = []
    missing_json = tmp_path / "missing.json"
    assert _read_json_file_or_warn(missing_json, warnings) is None
    assert warnings and "JSON file not found" in warnings[0]

    list_json = tmp_path / "list.json"
    list_json.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain an object"):
        _read_json_file(list_json)

    assert _configuration_metadata(["not", "a", "mapping"]) == {}
    assert _relative_to_corpus(corpus, tmp_path.parent / "outside.json").endswith("outside.json")
    assert _collect_ignored_app_fields({"topics": ["not-a-topic"]}) == []
    assert _collect_ignored_app_fields({"topics": "not-a-list"}) == []

    payload = _base_topic_set()
    payload["topics"] = "not-a-list"
    with pytest.raises(ValueError, match="Input should be a valid list"):
        _validate_topic_set_payload(payload)

    payload = _base_topic_set()
    payload["topics"] = ["not-a-topic"]
    with pytest.raises(ValueError, match="Input should be a valid dictionary"):
        _validate_topic_set_payload(payload)
