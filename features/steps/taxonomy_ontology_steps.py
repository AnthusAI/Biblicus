from __future__ import annotations

import json
from pathlib import Path

from behave import given, then, when

from biblicus.corpus import Corpus
from features.environment import run_biblicus
from features.steps.graph_extraction_steps import _install_fake_neo4j_module


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _title_item_ids(context, corpus_name: str) -> dict[str, str]:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    catalog = corpus.load_catalog()
    return {
        item.title: item_id
        for item_id, item in catalog.items.items()
        if item.title is not None and item.title.strip()
    }


def _taxonomy_payload(
    context, corpus_name: str, root_uid: str, child_uid: str
) -> dict[str, object]:
    title_ids = _title_item_ids(context, corpus_name)
    child_seed_ids = [title_ids["Agent Memory"]] if "Agent Memory" in title_ids else []
    return {
        "schema_version": 1,
        "taxonomy_id": "bdd-taxonomy",
        "display_name": "BDD Taxonomy",
        "description": "Accepted BDD taxonomy.",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "nodes": [
            {
                "topic_uid": root_uid,
                "parent_topic_uid": None,
                "display_name": "Agent Systems",
                "description": "Agent systems.",
                "status": "accepted",
                "seed_item_ids": [],
                "holdout_item_ids": [],
            },
            {
                "topic_uid": child_uid,
                "parent_topic_uid": root_uid,
                "display_name": "Agent Memory",
                "description": "Agent memory.",
                "status": "accepted",
                "seed_item_ids": child_seed_ids,
                "holdout_item_ids": [],
            },
        ],
    }


@given(
    'an accepted taxonomy input "{input_file}" exists for corpus "{corpus_name}" with root "{root_uid}" and child "{child_uid}"'
)
def step_accepted_taxonomy_input_exists(
    context, input_file: str, corpus_name: str, root_uid: str, child_uid: str
) -> None:
    _write_json(
        context.workdir / input_file, _taxonomy_payload(context, corpus_name, root_uid, child_uid)
    )


@given('a malformed taxonomy input "{input_file}" exists with problem "{problem}"')
def step_malformed_taxonomy_input_exists(context, input_file: str, problem: str) -> None:
    payload = {
        "schema_version": 1,
        "taxonomy_id": "bad-taxonomy",
        "display_name": "Bad Taxonomy",
        "description": "Malformed taxonomy.",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "nodes": [
            {
                "topic_uid": "agent-systems",
                "parent_topic_uid": None,
                "display_name": "Agent Systems",
                "description": "Agent systems.",
                "status": "accepted",
                "seed_item_ids": [],
                "holdout_item_ids": [],
            }
        ],
    }
    if problem == "duplicate":
        payload["nodes"].append(dict(payload["nodes"][0]))
    elif problem == "unknown-parent":
        payload["nodes"][0]["parent_topic_uid"] = "missing-parent"
    elif problem == "cycle":
        payload["nodes"] = [
            {
                "topic_uid": "agent-systems",
                "parent_topic_uid": "agent-memory",
                "display_name": "Agent Systems",
                "description": "Agent systems.",
                "status": "accepted",
                "seed_item_ids": [],
                "holdout_item_ids": [],
            },
            {
                "topic_uid": "agent-memory",
                "parent_topic_uid": "agent-systems",
                "display_name": "Agent Memory",
                "description": "Agent memory.",
                "status": "accepted",
                "seed_item_ids": [],
                "holdout_item_ids": [],
            },
        ]
    _write_json(context.workdir / input_file, payload)


@when('I record taxonomy input "{input_file}" in corpus "{corpus_name}"')
def step_record_taxonomy_input(context, input_file: str, corpus_name: str) -> None:
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "taxonomy",
            "record",
            "--input",
            str(context.workdir / input_file),
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_taxonomy_record = json.loads(result.stdout)


@when('I attempt to record taxonomy input "{input_file}" in corpus "{corpus_name}"')
def step_attempt_record_taxonomy_input(context, input_file: str, corpus_name: str) -> None:
    step_record_taxonomy_input(context, input_file, corpus_name)


@when('I discover taxonomy children in corpus "{corpus_name}" with classifier "{classifier_id}"')
def step_discover_taxonomy_children(context, corpus_name: str, classifier_id: str) -> None:
    snapshot_ref = f"{context.last_extractor_id}:{context.last_extraction_snapshot_id}"
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "taxonomy",
            "discover",
            "--classifier",
            classifier_id,
            "--extraction-snapshot",
            snapshot_ref,
        ],
        extra_env=getattr(context, "extra_env", None),
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_taxonomy_discovery = json.loads(result.stdout)


@given(
    'steering classifier "{classifier_id}" in corpus "{corpus_name}" uses UMAP n_components {n_components:d}'
)
def step_steering_classifier_uses_umap_components(
    context, classifier_id: str, corpus_name: str, n_components: int
) -> None:
    _update_steering_classifier_bertopic_analysis(
        context,
        classifier_id=classifier_id,
        corpus_name=corpus_name,
        values={"umap_model": {"parameters": {"n_components": n_components}}},
    )


@given('steering classifier "{classifier_id}" in corpus "{corpus_name}" uses BERTopic default UMAP')
def step_steering_classifier_uses_default_umap(
    context, classifier_id: str, corpus_name: str
) -> None:
    _update_steering_classifier_bertopic_analysis(
        context,
        classifier_id=classifier_id,
        corpus_name=corpus_name,
        values={"umap_model": None},
    )


def _update_steering_classifier_bertopic_analysis(
    context, *, classifier_id: str, corpus_name: str, values: dict[str, object]
) -> None:
    corpus = Corpus.open(_corpus_path(context, corpus_name))
    latest_path = corpus.analysis_dir / "topic-classifier" / f"{classifier_id}-latest.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    model_version = latest["model_version"]
    manifest_path = (
        corpus.analysis_run_dir(analysis_id="topic-classifier", snapshot_id=model_version)
        / "model-manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    configuration = manifest.setdefault("configuration", {})
    bertopic_analysis = configuration.setdefault("bertopic_analysis", {})
    bertopic_analysis.update(values)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


@given('a steering proposal bundle "{input_file}" exists with taxonomy and ontology proposals')
def step_taxonomy_ontology_proposal_bundle_exists(context, input_file: str) -> None:
    payload = {
        "schema_version": 1,
        "analysis_id": "steering-proposals",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "source_artifact_refs": ["taxonomy:taxonomy-one"],
        "signals": [
            {
                "signal_id": "signal-taxonomy",
                "signal_kind": "taxonomy-child-topic-candidate",
                "domain": "topic",
                "source_artifact_refs": ["taxonomy:taxonomy-one"],
                "metrics": {"document_count": 2},
                "evidence_item_ids": [],
                "payload": {"topic_uid": "agent-memory"},
            }
        ],
        "proposals": [
            {
                "proposal_id": "create-taxonomy-node:agent-memory",
                "proposal_kind": "create-taxonomy-node",
                "domain": "topic",
                "recommendation": "recommend",
                "source_signal_ids": ["signal-taxonomy"],
                "evidence": {},
                "rationale": "Add the child topic.",
                "payload": {"topic_uid": "agent-memory"},
            },
            {
                "proposal_id": "add-ontology-relationship:one",
                "proposal_kind": "add-ontology-relationship",
                "domain": "graph",
                "recommendation": "needs_clarification",
                "source_signal_ids": ["signal-taxonomy"],
                "evidence": {},
                "rationale": "Add the relationship assertion.",
                "payload": {"relationship_uid": "influenced"},
            },
            {
                "proposal_id": "add-relationship-type:influenced",
                "proposal_kind": "add-relationship-type",
                "domain": "graph",
                "recommendation": "recommend",
                "source_signal_ids": ["signal-taxonomy"],
                "evidence": {},
                "rationale": "Add the relationship type.",
                "payload": {"relationship_uid": "influenced"},
            },
        ],
    }
    _write_json(context.workdir / input_file, payload)


@given(
    'an accepted ontology input "{input_file}" exists in corpus "{corpus_name}" linking title "{title}" to topic "{topic_uid}"'
)
def step_accepted_ontology_input_exists(
    context, input_file: str, corpus_name: str, title: str, topic_uid: str
) -> None:
    title_ids = _title_item_ids(context, corpus_name)
    item_id = title_ids[title]
    payload = {
        "schema_version": 1,
        "ontology_id": "bdd-ontology",
        "display_name": "BDD Ontology",
        "description": "Accepted BDD ontology.",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "relationship_types": [
            {
                "relationship_uid": "influenced",
                "display_name": "Influenced",
                "description": "The source influenced the target.",
                "directed": True,
            }
        ],
        "assertions": [
            {
                "assertion_id": "assertion-one",
                "source_ref": f"item:{item_id}",
                "relationship_uid": "influenced",
                "target_ref": f"topic:{topic_uid}",
                "direction": "outbound",
                "evidence_item_ids": [item_id],
                "confidence": 0.8,
            }
        ],
    }
    _write_json(context.workdir / input_file, payload)


@when('I record ontology input "{input_file}" in corpus "{corpus_name}"')
def step_record_ontology_input(context, input_file: str, corpus_name: str) -> None:
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "ontology",
            "record",
            "--input",
            str(context.workdir / input_file),
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_ontology_record = json.loads(result.stdout)


@when(
    'I apply ontology snapshot "{ontology_snapshot}" and taxonomy snapshot "{taxonomy_snapshot}" to graph "{graph_snapshot}" in corpus "{corpus_name}"'
)
def step_apply_ontology(
    context, ontology_snapshot: str, taxonomy_snapshot: str, graph_snapshot: str, corpus_name: str
) -> None:
    _install_fake_neo4j_module(context)
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "ontology",
            "apply",
            "--taxonomy",
            taxonomy_snapshot,
            "--relationships",
            ontology_snapshot,
            "--graph-snapshot",
            graph_snapshot,
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_ontology_apply = json.loads(result.stdout)


@when(
    'I query ontology relationships in corpus "{corpus_name}" from title "{title}" with relationship "{relationship_uid}" and direction "{direction}"'
)
def step_query_ontology(
    context, corpus_name: str, title: str, relationship_uid: str, direction: str
) -> None:
    title_ids = _title_item_ids(context, corpus_name)
    result = run_biblicus(
        context,
        [
            "--corpus",
            str(_corpus_path(context, corpus_name)),
            "ontology",
            "query",
            "--relationships",
            "latest",
            "--source-ref",
            f"item:{title_ids[title]}",
            "--relationship",
            relationship_uid,
            "--direction",
            direction,
        ],
    )
    context.last_result = result
    if result.returncode == 0:
        context.last_ontology_query = json.loads(result.stdout)


@then('the taxonomy artifact includes topic "{topic_uid}" under "{parent_topic_uid}"')
def step_taxonomy_artifact_includes_topic(context, topic_uid: str, parent_topic_uid: str) -> None:
    taxonomy_path = Path(context.last_taxonomy_record["artifact_paths"]["taxonomy"])
    payload = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    nodes = {node["topic_uid"]: node for node in payload["nodes"]}
    assert nodes[topic_uid]["parent_topic_uid"] == parent_topic_uid, payload


@then('taxonomy input "{input_file}" still includes {count:d} nodes')
def step_taxonomy_input_still_includes_count(context, input_file: str, count: int) -> None:
    payload = json.loads((context.workdir / input_file).read_text(encoding="utf-8"))
    assert len(payload["nodes"]) == count, payload


@then('the taxonomy discovery output includes proposal kind "{proposal_kind}"')
def step_taxonomy_discovery_includes_proposal_kind(context, proposal_kind: str) -> None:
    proposal_kinds = {
        proposal["proposal_kind"] for proposal in context.last_taxonomy_discovery["proposals"]
    }
    assert proposal_kind in proposal_kinds, context.last_taxonomy_discovery


@then('the taxonomy discovery output includes warning "{expected}"')
def step_taxonomy_discovery_output_includes_warning(context, expected: str) -> None:
    warnings = context.last_taxonomy_discovery["warnings"]
    assert any(expected in warning for warning in warnings), context.last_taxonomy_discovery


@then('the steering proposal bundle includes proposal kinds "{proposal_kinds}"')
def step_steering_proposal_bundle_includes_kinds(context, proposal_kinds: str) -> None:
    expected = {entry.strip() for entry in proposal_kinds.split(",") if entry.strip()}
    actual = {
        proposal["proposal_kind"] for proposal in context.last_steering_proposal_bundle["proposals"]
    }
    assert expected.issubset(actual), context.last_steering_proposal_bundle


@then('the steering signal bundle includes missing graph entity for topic "{topic_uid}"')
def step_steering_signal_bundle_includes_missing_topic(context, topic_uid: str) -> None:
    for signal in context.last_steering_signal_bundle["signals"]:
        if (
            signal["signal_kind"] == "accepted-topic-missing-graph-entity"
            and signal["payload"]["topic_uid"] == topic_uid
        ):
            return
    raise AssertionError(f"Missing graph entity signal for topic {topic_uid}")


@then('the ontology apply output includes edge type "{edge_type}"')
def step_ontology_apply_output_includes_edge_type(context, edge_type: str) -> None:
    assert edge_type in context.last_ontology_apply["edge_types"], context.last_ontology_apply


@then(
    'the ontology query output includes relationship "{relationship_uid}" to target "{target_ref}"'
)
def step_ontology_query_output_includes_relationship(
    context, relationship_uid: str, target_ref: str
) -> None:
    for assertion in context.last_ontology_query["assertions"]:
        if (
            assertion["relationship_uid"] == relationship_uid
            and assertion["target_ref"] == target_ref
        ):
            return
    raise AssertionError(f"Missing ontology relationship {relationship_uid} to {target_ref}")
