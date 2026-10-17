from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml
from behave import given, then, when

from biblicus.corpus import Corpus
from biblicus.topic_classifier import load_topic_classifier_seed_manifest
from features.environment import run_biblicus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _title_item_ids(context, corpus_name: str) -> Dict[str, str]:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    return {
        item.title: item.id
        for item in corpus.load_catalog().items.values()
        if isinstance(item.title, str)
    }


def _sidecar_path(corpus: Corpus, item_id: str) -> Path:
    item = corpus.get_item(item_id)
    content_path = corpus.root / item.relpath
    return content_path.with_name(content_path.name + ".biblicus.yml")


@when('item titled "{title}" in corpus "{corpus_name}" has steering intake status "{status}"')
def step_item_has_steering_intake_status(
    context, title: str, corpus_name: str, status: str
) -> None:
    corpus_path = _corpus_path(context, corpus_name)
    corpus = Corpus.open(corpus_path)
    item_id = _title_item_ids(context, corpus_name)[title]
    sidecar_path = _sidecar_path(corpus, item_id)
    payload: Dict[str, Any] = {}
    if sidecar_path.is_file():
        loaded = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            payload = dict(loaded)
    curation = payload.get("curation")
    if not isinstance(curation, dict):
        curation = {}
    curation["intake_status"] = status
    curation["intake_assessment"] = {
        "decision": status,
        "classifier_id": "steering-classifier",
        "model_version": "bdd-model",
    }
    payload["curation"] = curation
    sidecar_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    result = run_biblicus(context, ["--corpus", str(corpus_path), "reindex"])
    assert result.returncode == 0, result.stderr


@given(
    'a steering topic classifier seed manifest exists in corpus "{corpus_name}" for classifier "{classifier_id}"'
)
def step_steering_seed_manifest_exists(context, corpus_name: str, classifier_id: str) -> None:
    title_ids = _title_item_ids(context, corpus_name)
    seed_item_id = title_ids["Agent Memory"]
    manifest_path = (
        _corpus_path(context, corpus_name)
        / "metadata"
        / "topic-classifiers"
        / classifier_id
        / "seed-manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "classifier_id": classifier_id,
        "display_name": "Steering Classifier",
        "description": "Accepted topics for steering tests.",
        "topics": [
            {
                "topic_uid": "agent-systems",
                "display_name": "Agent Systems",
                "description": "Agent memory, tool use, and planning systems.",
                "seed_item_ids": [seed_item_id],
                "holdout_item_ids": [],
            }
        ],
        "unlabeled_policy": "use_minus_one",
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given('a steering topic-governance snapshot "{snapshot_id}" exists in corpus "{corpus_name}"')
def step_steering_governance_snapshot_exists(context, snapshot_id: str, corpus_name: str) -> None:
    run_dir = _corpus_path(context, corpus_name) / "analysis" / "topic-governance" / snapshot_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "analysis_id": "topic-governance",
        "snapshot_id": snapshot_id,
        "generated_at": "2026-05-16T00:00:00+00:00",
        "inputs": {},
        "artifact_paths": {"proposals": str(run_dir / "proposals.json")},
    }
    proposals = {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "proposals": [
            {
                "proposal_id": "new-topic:automated-discovery",
                "proposal_kind": "new-topic",
                "domain": "topic",
                "recommendation": "recommend",
                "status": "proposed",
                "author": {"kind": "biblicus", "id": "topic-trends"},
                "source_signal_ids": [],
                "evidence": {"item_ids": []},
                "confidence": 0.8,
                "rationale": "Distinct discovered cluster.",
                "payload": {
                    "topic_uid": "automated-discovery",
                    "display_name": "Automated Discovery",
                    "description": "Automated scientific discovery systems.",
                    "suggested_seed_item_ids": [],
                    "suggested_holdout_item_ids": [],
                },
            }
        ],
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (run_dir / "proposals.json").write_text(
        json.dumps(proposals, indent=2) + "\n", encoding="utf-8"
    )


@when(
    'I export the steering bundle for corpus "{corpus_name}" with classifier "{classifier_id}" and governance snapshot "{snapshot_id}"'
)
def step_export_steering_bundle(
    context, corpus_name: str, classifier_id: str, snapshot_id: str
) -> None:
    args = [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "steering",
        "export",
        "--classifier",
        classifier_id,
        "--topic-governance-snapshot",
        snapshot_id,
    ]
    result = run_biblicus(context, args)
    context.last_result = result
    if result.returncode == 0:
        context.last_steering_export = json.loads(result.stdout)


@when('I export the steering bundle for corpus "{corpus_name}" with classifier "{classifier_id}"')
def step_export_steering_bundle_without_governance(
    context, corpus_name: str, classifier_id: str
) -> None:
    args = [
        "--corpus",
        str(_corpus_path(context, corpus_name)),
        "steering",
        "export",
        "--classifier",
        classifier_id,
    ]
    result = run_biblicus(context, args)
    context.last_result = result
    if result.returncode == 0:
        context.last_steering_export = json.loads(result.stdout)


@when('I list steering artifacts for corpus "{corpus_name}"')
def step_list_steering_artifacts(context, corpus_name: str) -> None:
    existing = getattr(context, "last_steering_artifact_inventory", None)
    if existing is not None:
        context.previous_steering_artifact_inventory = existing
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "steering",
            "artifacts",
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_steering_artifact_inventory = json.loads(result.stdout)


@when('I render a steering seed manifest from "{input_file}" to "{output_file}"')
def step_render_steering_seed_manifest(context, input_file: str, output_file: str) -> None:
    result = run_biblicus(
        context,
        [
            "steering",
            "render-seed-manifest",
            "--input",
            str(context.workdir / input_file),
            "--output",
            str(context.workdir / output_file),
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_steering_render = json.loads(result.stdout)


@when('I attempt to render a steering seed manifest from "{input_file}" to "{output_file}"')
def step_attempt_render_steering_seed_manifest(context, input_file: str, output_file: str) -> None:
    result = run_biblicus(
        context,
        [
            "steering",
            "render-seed-manifest",
            "--input",
            str(context.workdir / input_file),
            "--output",
            str(context.workdir / output_file),
        ],
    )
    context.last_result = result


@given(
    'a steering analysis artifact kind "{kind}" with snapshot "{snapshot_id}" exists in corpus "{corpus_name}"'
)
@when(
    'a steering analysis artifact kind "{kind}" with snapshot "{snapshot_id}" exists in corpus "{corpus_name}"'
)
def step_steering_analysis_artifact_exists(
    context, kind: str, snapshot_id: str, corpus_name: str
) -> None:
    analysis_id_by_kind = {
        "topic-context": "topic-context",
        "topic-governance": "topic-governance",
        "topic-modeling": "topic-modeling",
        "topic-granularity": "topic-granularity-sweep",
        "steering-proposals": "steering-proposals",
    }
    analysis_id = analysis_id_by_kind[kind]
    run_dir = _corpus_path(context, corpus_name) / "analysis" / analysis_id / snapshot_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "analysis_id": analysis_id,
        "snapshot_id": snapshot_id,
        "generated_at": "2026-05-16T00:00:00+00:00",
        "inputs": {},
        "artifact_paths": {},
    }
    (run_dir / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given('a steering graph artifact snapshot "{snapshot_id}" exists in corpus "{corpus_name}"')
@when('a steering graph artifact snapshot "{snapshot_id}" exists in corpus "{corpus_name}"')
def step_steering_graph_artifact_exists(context, snapshot_id: str, corpus_name: str) -> None:
    run_dir = _corpus_path(context, corpus_name) / "graph" / "simple-entities" / snapshot_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_id": snapshot_id,
        "graph_id": "simple-entities:bdd",
        "created_at": "2026-05-16T00:00:00+00:00",
    }
    (run_dir / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given(
    'a steering graph snapshot "{snapshot_id}" exists in corpus "{corpus_name}" with entity labels "{labels}"'
)
def step_steering_graph_snapshot_with_labels(
    context, snapshot_id: str, corpus_name: str, labels: str
) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    run_dir = corpus.root / "graph" / "simple-entities" / snapshot_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "snapshot_id": snapshot_id,
        "graph_id": "simple-entities:bdd",
        "configuration": {
            "configuration_id": "bdd-configuration",
            "extractor_id": "simple-entities",
            "name": "BDD graph",
            "created_at": "2026-05-16T00:00:00+00:00",
            "configuration": {},
        },
        "corpus_uri": corpus.uri,
        "catalog_generated_at": corpus.load_catalog().generated_at,
        "extraction_snapshot": "pipeline:bdd",
        "created_at": "2026-05-16T00:00:00+00:00",
        "stats": {
            "topic_node_ids": [],
            "entity_labels": [label.strip() for label in labels.split(",") if label.strip()],
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@given(
    'a steering classifier topic map exists in corpus "{corpus_name}" for classifier "{classifier_id}"'
)
def step_steering_classifier_topic_map_exists(
    context, corpus_name: str, classifier_id: str
) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    title_ids = _title_item_ids(context, corpus_name)
    model_version = "bdd-model"
    run_dir = corpus.analysis_run_dir(analysis_id="topic-classifier", snapshot_id=model_version)
    run_dir.mkdir(parents=True, exist_ok=True)
    model_manifest = {
        "schema_version": 1,
        "classifier_id": classifier_id,
        "model_version": model_version,
        "created_at": "2026-05-16T00:00:00+00:00",
        "configuration": {},
        "extraction_snapshot": {"extractor_id": "pipeline", "snapshot_id": "bdd"},
    }
    topic_map = {
        "schema_version": 1,
        "classifier_id": classifier_id,
        "model_version": model_version,
        "generated_at": "2026-05-16T00:00:00+00:00",
        "topics": [
            {
                "topic_uid": "agent-systems",
                "display_name": "Agent Systems",
                "description": "Agent memory, tool use, and planning systems.",
                "seed_item_ids": [title_ids["Agent Memory"]],
                "holdout_item_ids": [],
                "bertopic_topic_ids": [0],
            }
        ],
        "mappings": [
            {
                "bertopic_topic_id": 0,
                "topic_uid": "agent-systems",
                "display_name": "Agent Systems",
                "seed_votes": 1,
                "seed_vote_counts": {"agent-systems": 1},
                "seed_item_ids": [title_ids["Agent Memory"]],
                "document_count": len(title_ids),
                "document_ids": sorted(title_ids.values()),
                "keywords": ["agent", "memory", "tools"],
            }
        ],
        "discovered": [],
    }
    (run_dir / "model-manifest.json").write_text(
        json.dumps(model_manifest, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "topic-map.json").write_text(
        json.dumps(topic_map, indent=2) + "\n", encoding="utf-8"
    )
    latest_path = corpus.analysis_dir / "topic-classifier" / f"{classifier_id}-latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(
        json.dumps({"model_version": model_version}, indent=2) + "\n", encoding="utf-8"
    )


@given('a steering topic-set input "{input_file}" exists with app-only fields')
def step_steering_topic_set_input_exists(context, input_file: str) -> None:
    payload = _base_topic_set_payload()
    payload["topics"][0]["subheading"] = "Application display subheading"
    payload["topics"][0]["aliases"] = ["Agentic Systems"]
    payload["topics"][0]["editor_notes"] = "Only the app stores this note."
    payload["topics"][0]["ranking_hints"] = {"pinned": True}
    (context.workdir / input_file).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


@given(
    'a malformed steering topic-set input "{input_file}" exists with duplicate topic identifiers'
)
def step_malformed_topic_set_duplicate(context, input_file: str) -> None:
    payload = _base_topic_set_payload()
    second_topic = dict(payload["topics"][0])
    second_topic["display_name"] = "Duplicate Agents"
    payload["topics"].append(second_topic)
    (context.workdir / input_file).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


@given('a malformed steering topic-set input "{input_file}" exists with seed holdout overlap')
def step_malformed_topic_set_overlap(context, input_file: str) -> None:
    payload = _base_topic_set_payload()
    payload["topics"][0]["holdout_item_ids"] = ["11111111-1111-4111-8111-111111111111"]
    (context.workdir / input_file).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


@given('a malformed steering topic-set input "{input_file}" exists with unknown fields')
def step_malformed_topic_set_unknown_fields(context, input_file: str) -> None:
    payload = _base_topic_set_payload()
    payload["topics"][0]["unexpected_field"] = "not allowed"
    (context.workdir / input_file).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


@given('a steering proposal bundle "{input_file}" exists with recommendation decisions')
def step_steering_proposal_bundle_exists(context, input_file: str) -> None:
    payload = _base_proposal_bundle()
    (context.workdir / input_file).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


@given('a malformed steering proposal bundle "{input_file}" exists with human decisions')
def step_malformed_steering_proposal_bundle_human_decisions(context, input_file: str) -> None:
    payload = _base_proposal_bundle()
    payload["proposals"][0]["human_decision"] = {"decision": "accept"}
    (context.workdir / input_file).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


@when(
    'I build steering graph signals for corpus "{corpus_name}" with classifier "{classifier_id}" and graph snapshot "{graph_snapshot}"'
)
def step_build_steering_graph_signals(
    context, corpus_name: str, classifier_id: str, graph_snapshot: str
) -> None:
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "steering",
            "graph-signals",
            "--classifier",
            classifier_id,
            "--graph-snapshot",
            graph_snapshot,
            "--format",
            "json",
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_steering_signal_bundle = json.loads(result.stdout)


@when(
    'I build steering graph signals with steering feedback "{feedback_file}" for corpus "{corpus_name}" with classifier "{classifier_id}" and graph snapshot "{graph_snapshot}"'
)
def step_build_steering_graph_signals_with_feedback(
    context, feedback_file: str, corpus_name: str, classifier_id: str, graph_snapshot: str
) -> None:
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "steering",
            "graph-signals",
            "--classifier",
            classifier_id,
            "--graph-snapshot",
            graph_snapshot,
            "--steering-feedback",
            str(context.workdir / feedback_file),
            "--format",
            "json",
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_steering_signal_bundle = json.loads(result.stdout)


@when('I validate steering proposal bundle "{input_file}"')
def step_validate_steering_proposal_bundle(context, input_file: str) -> None:
    result = run_biblicus(
        context,
        [
            "steering",
            "proposals",
            "validate",
            "--input",
            str(context.workdir / input_file),
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_steering_proposal_bundle = json.loads(result.stdout)


@when('I attempt to validate steering proposal bundle "{input_file}"')
def step_attempt_validate_steering_proposal_bundle(context, input_file: str) -> None:
    result = run_biblicus(
        context,
        [
            "steering",
            "proposals",
            "validate",
            "--input",
            str(context.workdir / input_file),
        ],
    )
    context.last_result = result


@when('I record steering proposal bundle "{input_file}" in corpus "{corpus_name}"')
def step_record_steering_proposal_bundle(context, input_file: str, corpus_name: str) -> None:
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "steering",
            "proposals",
            "record",
            "--input",
            str(context.workdir / input_file),
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_steering_proposal_record = json.loads(result.stdout)


@then("the steering export includes {count:d} catalog items with metadata")
def step_steering_export_includes_items(context, count: int) -> None:
    payload = context.last_steering_export
    assert len(payload["items"]) == count, payload
    for item in payload["items"]:
        assert "metadata" in item, item
        assert "media_type" in item, item
        assert "tags" in item, item


@then('the steering export includes intake statuses "{statuses}"')
def step_steering_export_includes_intake_statuses(context, statuses: str) -> None:
    payload = context.last_steering_export
    expected = {status.strip() for status in statuses.split(",") if status.strip()}
    actual = {item["intake_status"] for item in payload["items"]}
    assert expected.issubset(actual), payload


@then('the steering export includes topic "{topic_uid}"')
def step_steering_export_includes_topic(context, topic_uid: str) -> None:
    payload = context.last_steering_export
    topics = {topic["topic_uid"] for topic in payload["topic_set"]["topics"]}
    assert topic_uid in topics, payload


@then('the steering export includes governance proposal "{proposal_id}"')
def step_steering_export_includes_proposal(context, proposal_id: str) -> None:
    payload = context.last_steering_export
    proposal_ids = {proposal["proposal_id"] for proposal in payload["proposals"]}
    assert proposal_id in proposal_ids, payload


@then('the steering export includes proposal "{proposal_id}"')
def step_steering_export_includes_unified_proposal(context, proposal_id: str) -> None:
    payload = context.last_steering_export
    proposal_ids = {proposal["proposal_id"] for proposal in payload["proposals"]}
    assert proposal_id in proposal_ids, payload


@then('the steering export includes artifact kind "{kind}"')
def step_steering_export_includes_artifact_kind(context, kind: str) -> None:
    payload = context.last_steering_export
    kinds = {artifact["kind"] for artifact in payload["artifacts"]}
    assert kind in kinds, payload


@then("the steering export does not include raw item bytes")
def step_steering_export_omits_raw_bytes(context) -> None:
    text = json.dumps(context.last_steering_export)
    assert "agent memory retrieval planning" not in text, text
    assert "raw_bytes" not in text, text


@then("the steering export does not include human decisions")
def step_steering_export_omits_human_decisions(context) -> None:
    text = json.dumps(context.last_steering_export)
    assert "human_decision" not in text, text
    assert "accepted_by" not in text, text
    assert "rejected_by" not in text, text


@then('the steering artifact inventory includes kind "{kind}"')
def step_steering_artifact_inventory_includes_kind(context, kind: str) -> None:
    payload = context.last_steering_artifact_inventory
    assert payload["artifacts_by_kind"][kind], payload


@then('the steering artifact inventory warns that kind "{kind}" is missing')
def step_steering_artifact_inventory_warns_missing(context, kind: str) -> None:
    payload = context.last_steering_artifact_inventory
    assert not payload["artifacts_by_kind"][kind], payload
    assert any(kind in warning for warning in payload["warnings"]), payload


@then("the steering artifact inventory matches the previous inventory")
def step_steering_artifact_inventory_matches_previous(context) -> None:
    assert context.last_steering_artifact_inventory == context.previous_steering_artifact_inventory


@then('the rendered seed manifest contains topic "{topic_uid}"')
def step_rendered_seed_manifest_contains_topic(context, topic_uid: str) -> None:
    output_path = Path(context.last_steering_render["output_path"])
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    topics = {topic["topic_uid"] for topic in payload["topics"]}
    assert topic_uid in topics, payload


@then('the rendered seed manifest omits app-only field "{field_name}"')
def step_rendered_seed_manifest_omits_app_field(context, field_name: str) -> None:
    output_path = Path(context.last_steering_render["output_path"])
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert field_name not in payload["topics"][0], payload


@then("the rendered seed manifest can be loaded as a Biblicus topic classifier seed manifest")
def step_rendered_seed_manifest_loads(context) -> None:
    output_path = Path(context.last_steering_render["output_path"])
    manifest = load_topic_classifier_seed_manifest(output_path)
    assert manifest.classifier_id == "steering-classifier"


@then('the steering signal bundle includes signal kind "{signal_kind}"')
def step_steering_signal_bundle_includes_kind(context, signal_kind: str) -> None:
    payload = context.last_steering_signal_bundle
    signal_kinds = {signal["signal_kind"] for signal in payload["signals"]}
    assert signal_kind in signal_kinds, payload


@then('the steering signal bundle omits signal kind "{signal_kind}"')
def step_steering_signal_bundle_omits_kind(context, signal_kind: str) -> None:
    payload = context.last_steering_signal_bundle
    signal_kinds = {signal["signal_kind"] for signal in payload["signals"]}
    assert signal_kind not in signal_kinds, payload


@then('the steering signal bundle includes warning "{expected}"')
def step_steering_signal_bundle_includes_warning(context, expected: str) -> None:
    payload = context.last_steering_signal_bundle
    assert any(expected in warning for warning in payload["warnings"]), payload


@then('the steering proposal bundle includes recommendations "{recommendations}"')
def step_steering_proposal_bundle_includes_recommendations(context, recommendations: str) -> None:
    payload = context.last_steering_proposal_bundle
    expected = {value.strip() for value in recommendations.split(",") if value.strip()}
    actual = {proposal["recommendation"] for proposal in payload["proposals"]}
    assert expected.issubset(actual), payload


@then('a steering proposal artifact is recorded in corpus "{corpus_name}"')
def step_steering_proposal_artifact_recorded(context, corpus_name: str) -> None:
    snapshot_id = context.last_steering_proposal_record["snapshot_id"]
    run_dir = _corpus_path(context, corpus_name) / "analysis" / "steering-proposals" / snapshot_id
    assert (run_dir / "manifest.json").is_file(), run_dir
    assert (run_dir / "signals.json").is_file(), run_dir
    assert (run_dir / "proposals.json").is_file(), run_dir


def _base_topic_set_payload() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "classifier_id": "steering-classifier",
        "display_name": "Steering Classifier",
        "description": "Accepted topics for steering tests.",
        "topics": [
            {
                "topic_uid": "agent-systems",
                "display_name": "Agent Systems",
                "description": "Agent memory, tool use, and planning systems.",
                "seed_item_ids": ["11111111-1111-4111-8111-111111111111"],
                "holdout_item_ids": ["22222222-2222-4222-8222-222222222222"],
            }
        ],
        "unlabeled_policy": "use_minus_one",
    }


def _base_proposal_bundle() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "analysis_id": "steering-proposals",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "source_artifact_refs": ["graph:simple-entities:graph-one"],
        "signals": [
            {
                "signal_id": "signal:create-topic-entity:agent-systems",
                "signal_kind": "accepted-topic-missing-graph-entity",
                "domain": "graph",
                "source_artifact_refs": ["graph:simple-entities:graph-one"],
                "metrics": {"confidence": 1.0},
                "evidence_item_ids": ["11111111-1111-4111-8111-111111111111"],
                "payload": {
                    "topic_uid": "agent-systems",
                    "expected_node_id": "topic:agent-systems",
                },
            },
            {
                "signal_id": "signal:suppress-entity:ai",
                "signal_kind": "noisy-generic-entity",
                "domain": "graph",
                "source_artifact_refs": ["graph:simple-entities:graph-one"],
                "metrics": {"entity_count": 1},
                "evidence_item_ids": [],
                "payload": {"node_id": "entity:ai", "label": "AI"},
            },
            {
                "signal_id": "signal:map-topic:agent-systems",
                "signal_kind": "topic-entity-name-collision",
                "domain": "graph",
                "source_artifact_refs": ["graph:simple-entities:graph-one"],
                "metrics": {"name_similarity": 1.0},
                "evidence_item_ids": [],
                "payload": {"topic_uid": "agent-systems", "entity_label": "Agent Systems"},
            },
        ],
        "proposals": [
            {
                "proposal_id": "create-topic-entity:agent-systems",
                "proposal_kind": "create-topic-entity",
                "domain": "graph",
                "recommendation": "recommend",
                "author": {"kind": "agent", "id": "bdd-agent"},
                "source_signal_ids": ["signal:create-topic-entity:agent-systems"],
                "evidence": {"item_ids": ["11111111-1111-4111-8111-111111111111"]},
                "rationale": "Accepted topics should have explicit graph entities.",
                "confidence": 0.95,
                "payload": {
                    "topic_uid": "agent-systems",
                    "node_id": "topic:agent-systems",
                },
            },
            {
                "proposal_id": "suppress-entity:ai",
                "proposal_kind": "suppress-entity-or-edge",
                "domain": "graph",
                "recommendation": "do_not_recommend",
                "author": {"kind": "agent", "id": "bdd-agent"},
                "source_signal_ids": ["signal:suppress-entity:ai"],
                "evidence": {},
                "rationale": "The entity is generic, but the evidence is too small to suppress it.",
                "confidence": 0.4,
                "payload": {"node_id": "entity:ai"},
            },
            {
                "proposal_id": "map-topic-to-entity:agent-systems",
                "proposal_kind": "map-topic-to-entity",
                "domain": "graph",
                "recommendation": "needs_clarification",
                "author": {"kind": "agent", "id": "bdd-agent"},
                "source_signal_ids": ["signal:map-topic:agent-systems"],
                "evidence": {},
                "rationale": "The topic label collides with a graph entity label.",
                "confidence": 0.7,
                "payload": {"topic_uid": "agent-systems", "entity_label": "Agent Systems"},
            },
        ],
        "warnings": [],
    }
