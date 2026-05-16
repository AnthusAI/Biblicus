from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from biblicus import cli as cli_module
from biblicus import taxonomy as taxonomy_module
from biblicus.corpus import Corpus
from biblicus.models import ExtractionSnapshotReference
from biblicus.ontology import (
    OntologyManifest,
    OntologyRelationshipType,
    _assertion_matches_ref,
    _resolve_ontology_snapshot_id,
    build_ontology_graph_overlay,
    load_ontology_manifest,
    load_recorded_ontology_manifest,
    query_ontology_assertions,
    record_ontology_manifest,
)
from biblicus.ontology import (
    _read_json_object as _read_ontology_json_object,
)
from biblicus.ontology import (
    _required_snapshot_id as _required_ontology_snapshot_id,
)
from biblicus.ontology import (
    _required_taxonomy_snapshot_id as _required_ontology_taxonomy_snapshot_id,
)
from biblicus.steering_proposals import SteeringProposalBundle
from biblicus.taxonomy import (
    TaxonomyDiscoveryOutput,
    TaxonomyManifest,
    TaxonomyNode,
    _child_description,
    _documents_for_items,
    _markdown_cell,
    _resolve_taxonomy_snapshot_id,
    _slug,
    _string_list,
    _taxonomy_from_seed_manifest,
    _topic_map_member_ids,
    _unique_child_topic_uid,
    load_latest_taxonomy_manifest,
    load_recorded_taxonomy_manifest,
    load_taxonomy_manifest,
    record_taxonomy_manifest,
    taxonomy_discovery_markdown,
)
from biblicus.taxonomy import (
    _read_json_object as _read_taxonomy_json_object,
)
from biblicus.taxonomy import (
    _required_snapshot_id as _required_taxonomy_snapshot_id,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _taxonomy_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "taxonomy_id": "test-taxonomy",
        "display_name": "Test Taxonomy",
        "description": "A reviewed taxonomy.",
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
            },
            {
                "topic_uid": "agent-memory",
                "parent_topic_uid": "agent-systems",
                "display_name": "Agent Memory",
                "description": "Agent memory systems.",
                "status": "accepted",
                "seed_item_ids": [],
                "holdout_item_ids": [],
            },
        ],
    }


def _ontology_payload(source_ref: str = "item:item-one") -> dict[str, object]:
    return {
        "schema_version": 1,
        "ontology_id": "test-ontology",
        "display_name": "Test Ontology",
        "description": "Reviewed relationship assertions.",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "relationship_types": [
            {
                "relationship_uid": "influenced",
                "display_name": "Influenced",
                "description": "One concept influenced another.",
                "directed": True,
            }
        ],
        "assertions": [
            {
                "assertion_id": "assertion-one",
                "source_ref": source_ref,
                "relationship_uid": "influenced",
                "target_ref": "topic:agent-memory",
                "direction": "outbound",
                "evidence_item_ids": ["item-one"],
                "confidence": 0.8,
            }
        ],
    }


def _write_seed_manifest(corpus: Corpus, seed_item_id: str) -> None:
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
                    "seed_item_ids": [seed_item_id],
                    "holdout_item_ids": [],
                }
            ],
            "unlabeled_policy": "use_minus_one",
        },
    )


def test_taxonomy_manifest_validates_strict_tree_shape(tmp_path: Path) -> None:
    """Taxonomy manifests enforce one parent, known parents, roots, and cycles."""
    valid = _taxonomy_payload()
    path = tmp_path / "taxonomy.json"
    _write_json(path, valid)

    manifest = load_taxonomy_manifest(path)

    assert manifest.snapshot_id
    assert manifest.nodes[1].parent_topic_uid == "agent-systems"

    duplicate = _taxonomy_payload()
    duplicate["nodes"] = [*duplicate["nodes"], duplicate["nodes"][1]]
    with pytest.raises(ValueError, match="Duplicate topic_uid"):
        TaxonomyManifest.model_validate(duplicate)

    unknown_parent = _taxonomy_payload()
    unknown_parent["nodes"][1]["parent_topic_uid"] = "missing-topic"
    with pytest.raises(ValueError, match="Unknown parent_topic_uid"):
        TaxonomyManifest.model_validate(unknown_parent)

    cycle = _taxonomy_payload()
    cycle["nodes"][0]["parent_topic_uid"] = "agent-memory"
    with pytest.raises(ValueError, match="Taxonomy cycle"):
        TaxonomyManifest.model_validate(cycle)

    malformed = _taxonomy_payload()
    malformed["nodes"][0]["subtitle"] = "App-only field"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TaxonomyManifest.model_validate(malformed)

    unsupported_schema = _taxonomy_payload()
    unsupported_schema["schema_version"] = 99
    with pytest.raises(ValidationError, match="Unsupported taxonomy schema version"):
        TaxonomyManifest.model_validate(unsupported_schema)

    no_roots = _taxonomy_payload()
    no_roots["nodes"] = []
    with pytest.raises(ValidationError, match="at least 1 item"):
        TaxonomyManifest.model_validate(no_roots)

    with pytest.raises(ValidationError):
        TaxonomyNode.model_validate(
            {
                "topic_uid": 123,
                "display_name": "Bad",
                "description": "Bad.",
            }
        )


def test_taxonomy_loading_and_helper_error_branches(tmp_path: Path) -> None:
    """Taxonomy helpers fail clearly for missing and malformed artifacts."""
    corpus = Corpus.init(tmp_path / "corpus")
    with pytest.raises(FileNotFoundError, match="Missing taxonomy latest pointer"):
        load_recorded_taxonomy_manifest(corpus=corpus, snapshot_id="latest")
    with pytest.raises(FileNotFoundError, match="Missing taxonomy artifact"):
        load_recorded_taxonomy_manifest(corpus=corpus, snapshot_id="missing")

    _write_json(corpus.analysis_dir / "taxonomy" / "latest.json", {"snapshot_id": ""})
    assert load_latest_taxonomy_manifest(corpus) is None
    with pytest.raises(ValueError, match="Taxonomy latest pointer must contain snapshot_id"):
        _resolve_taxonomy_snapshot_id(corpus=corpus, snapshot_id="latest")

    invalid_json = tmp_path / "bad.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON file"):
        _read_taxonomy_json_object(invalid_json)

    invalid_taxonomy = tmp_path / "invalid-taxonomy.json"
    duplicate = _taxonomy_payload()
    duplicate["nodes"] = [*duplicate["nodes"], duplicate["nodes"][1]]
    _write_json(invalid_taxonomy, duplicate)
    with pytest.raises(ValueError, match="Invalid taxonomy manifest"):
        load_taxonomy_manifest(invalid_taxonomy)

    list_json = tmp_path / "list.json"
    list_json.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain an object"):
        _read_taxonomy_json_object(list_json)

    with pytest.raises(ValueError, match="Taxonomy manifest snapshot_id is missing"):
        _required_taxonomy_snapshot_id(
            TaxonomyManifest.model_validate(_taxonomy_payload()).model_copy(
                update={"snapshot_id": None}
            )
        )


def test_taxonomy_discovery_helpers_cover_edge_branches(tmp_path: Path) -> None:
    """Taxonomy discovery helpers cover seed fallback, text filtering, and formatting branches."""
    corpus = Corpus.init(tmp_path / "corpus")
    first = corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        source_uri="urn:test:agent",
    )
    second = corpus.ingest_item(
        b" ",
        filename="blank.txt",
        media_type="text/plain",
        title="Blank",
        source_uri="urn:test:blank",
    )
    _write_seed_manifest(corpus, first.item_id)
    taxonomy = _taxonomy_from_seed_manifest(corpus=corpus, classifier_id="steering-classifier")

    assert taxonomy.nodes[0].topic_uid == "agent-systems"
    assert _topic_map_member_ids(
        {
            "topics": [
                "bad-topic",
                {"topic_uid": "", "seed_item_ids": ["x"]},
                {"topic_uid": "agent-systems", "seed_item_ids": ["a"], "holdout_item_ids": ["b"]},
            ],
            "mappings": [
                "bad-mapping",
                {"topic_uid": "", "document_ids": ["x"]},
                {"topic_uid": "agent-systems", "document_ids": ["c"]},
            ],
        }
    ) == {"agent-systems": ["a", "b", "c"]}
    assert _string_list("not-a-list") == []
    assert _string_list(["ok", "", 3]) == ["ok"]
    assert _slug("One Two Three Four Five Six Seven") == "one-two-three-four-five-six"
    assert (
        _unique_child_topic_uid(
            root_uid="agent-systems",
            label="",
            keywords=["Memory"],
            used={"agent-systems-memory"},
        )
        == "agent-systems-memory-2"
    )
    assert (
        _unique_child_topic_uid(root_uid="agent-systems", label="", keywords=[], used=set())
        == "agent-systems-child-topic"
    )
    assert _child_description(parent=taxonomy.nodes[0], label="Child", keywords=[]) == (
        "Candidate subtopic under Agent Systems: Child."
    )
    assert _markdown_cell("A|B\nC") == "A\\|B C"

    snapshot_dir = corpus.extracted_dir / "pipeline" / "extract-one"
    _write_json(snapshot_dir / "manifest.json", {"snapshot_id": "extract-one"})
    text_path = snapshot_dir / "text" / f"{first.item_id}.txt"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(" agent memory ", encoding="utf-8")
    blank_path = snapshot_dir / "text" / f"{second.item_id}.txt"
    blank_path.write_text(" ", encoding="utf-8")
    documents = _documents_for_items(
        corpus=corpus,
        item_ids=[first.item_id, second.item_id, "missing"],
        extraction_snapshot=ExtractionSnapshotReference(
            extractor_id="pipeline",
            snapshot_id="extract-one",
        ),
    )

    assert [document.document_id for document in documents] == [first.item_id]

    markdown = taxonomy_discovery_markdown(
        TaxonomyDiscoveryOutput(
            snapshot_id="discovery-one",
            generated_at="2026-05-16T00:00:00+00:00",
            classifier_id="steering-classifier",
            extraction_snapshot="pipeline:extract-one",
            warnings=["needs more documents"],
        )
    )
    assert "needs more documents" in markdown


def test_taxonomy_discovery_records_accepted_taxonomy_success_and_warnings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Taxonomy discovery uses accepted taxonomy roots and emits proposal-only child topics."""
    corpus = Corpus.init(tmp_path / "corpus")
    first = corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        source_uri="urn:test:agent",
    )
    second = corpus.ingest_item(
        b"agent tools",
        filename="tools.txt",
        media_type="text/plain",
        title="Agent Tools",
        source_uri="urn:test:tools",
    )
    third = corpus.ingest_item(
        b"agent planning",
        filename="planning.txt",
        media_type="text/plain",
        title="Agent Planning",
        source_uri="urn:test:planning",
    )
    taxonomy_payload = _taxonomy_payload()
    taxonomy_payload["nodes"][0]["seed_item_ids"] = [
        first.item_id,
        second.item_id,
        third.item_id,
    ]
    taxonomy_input = tmp_path / "taxonomy.json"
    _write_json(taxonomy_input, taxonomy_payload)
    taxonomy_record = record_taxonomy_manifest(corpus=corpus, input_path=taxonomy_input)
    snapshot_dir = corpus.extracted_dir / "pipeline" / "extract-one"
    (snapshot_dir / "text").mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "text" / f"{first.item_id}.txt").write_text("agent memory", encoding="utf-8")
    (snapshot_dir / "text" / f"{second.item_id}.txt").write_text("agent tools", encoding="utf-8")
    (snapshot_dir / "text" / f"{third.item_id}.txt").write_text("agent planning", encoding="utf-8")

    monkeypatch.setattr(
        taxonomy_module,
        "_load_model_bundle",
        lambda *, corpus, classifier_id: {
            "model_manifest": {
                "configuration": {
                    "bertopic_analysis": {
                        "umap_model": {"parameters": {"n_components": 1}},
                    }
                }
            },
            "topic_map": {"mappings": []},
        },
    )
    monkeypatch.setattr(
        taxonomy_module,
        "run_topic_modeling_for_documents",
        lambda *, documents, config: SimpleNamespace(
            topics=[
                SimpleNamespace(
                    topic_id=-1,
                    label="Outlier",
                    keywords=[],
                    document_count=0,
                    document_ids=[],
                ),
                SimpleNamespace(
                    topic_id=3,
                    label="Agent Memory",
                    keywords=[SimpleNamespace(keyword="memory")],
                    document_count=len(documents),
                    document_ids=[document.document_id for document in documents],
                ),
            ]
        ),
    )

    output = taxonomy_module.discover_taxonomy_children(
        corpus=corpus,
        classifier_id="steering-classifier",
        extraction_snapshot=ExtractionSnapshotReference(
            extractor_id="pipeline",
            snapshot_id="extract-one",
        ),
    )

    assert output.taxonomy_snapshot_id == taxonomy_record.snapshot_id
    assert output.signals[0].source_artifact_refs[-1] == f"taxonomy:{taxonomy_record.snapshot_id}"
    assert output.proposals[0].proposal_kind == "create-taxonomy-node"
    markdown = taxonomy_discovery_markdown(output)
    assert "create-taxonomy-node" in markdown

    monkeypatch.setattr(
        taxonomy_module,
        "run_topic_modeling_for_documents",
        lambda *, documents, config: (_ for _ in ()).throw(ValueError("too small")),
    )
    warned = taxonomy_module.discover_taxonomy_children(
        corpus=corpus,
        classifier_id="steering-classifier",
        extraction_snapshot=ExtractionSnapshotReference(
            extractor_id="pipeline",
            snapshot_id="extract-one",
        ),
    )

    assert "too small" in warned.warnings[0]


def test_taxonomy_discovery_skips_buckets_too_small_for_configured_umap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scoped taxonomy discovery skips roots that are too small for configured UMAP."""
    corpus = Corpus.init(tmp_path / "corpus")
    first = corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        source_uri="urn:test:agent",
    )
    second = corpus.ingest_item(
        b"agent tools",
        filename="tools.txt",
        media_type="text/plain",
        title="Agent Tools",
        source_uri="urn:test:tools",
    )
    taxonomy_payload = _taxonomy_payload()
    taxonomy_payload["nodes"][0]["seed_item_ids"] = [first.item_id, second.item_id]
    taxonomy_input = tmp_path / "taxonomy.json"
    _write_json(taxonomy_input, taxonomy_payload)
    record_taxonomy_manifest(corpus=corpus, input_path=taxonomy_input)
    snapshot_dir = corpus.extracted_dir / "pipeline" / "extract-one"
    (snapshot_dir / "text").mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "text" / f"{first.item_id}.txt").write_text("agent memory", encoding="utf-8")
    (snapshot_dir / "text" / f"{second.item_id}.txt").write_text("agent tools", encoding="utf-8")

    monkeypatch.setattr(
        taxonomy_module,
        "_load_model_bundle",
        lambda *, corpus, classifier_id: {
            "model_manifest": {
                "configuration": {
                    "bertopic_analysis": {
                        "umap_model": {"parameters": {"n_components": 5}},
                    }
                }
            },
            "topic_map": {"mappings": []},
        },
    )

    def fail_if_called(*, documents, config):
        raise AssertionError("BERTopic should not run for undersized scoped buckets")

    monkeypatch.setattr(taxonomy_module, "run_topic_modeling_for_documents", fail_if_called)

    output = taxonomy_module.discover_taxonomy_children(
        corpus=corpus,
        classifier_id="steering-classifier",
        extraction_snapshot=ExtractionSnapshotReference(
            extractor_id="pipeline",
            snapshot_id="extract-one",
        ),
    )

    assert output.signals == []
    assert output.proposals == []
    assert "requires at least 7 documents" in output.warnings[0]
    assert "UMAP n_components=5" in output.warnings[0]


def test_taxonomy_discovery_skips_buckets_too_small_for_bertopic_default_umap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scoped taxonomy discovery treats a null UMAP config as BERTopic's effective default."""
    corpus = Corpus.init(tmp_path / "corpus")
    items = [
        corpus.ingest_item(
            f"agent document {index}".encode("utf-8"),
            filename=f"agent-{index}.txt",
            media_type="text/plain",
            title=f"Agent {index}",
            source_uri=f"urn:test:agent:{index}",
        )
        for index in range(4)
    ]
    taxonomy_payload = _taxonomy_payload()
    taxonomy_payload["nodes"][0]["seed_item_ids"] = [item.item_id for item in items]
    taxonomy_input = tmp_path / "taxonomy.json"
    _write_json(taxonomy_input, taxonomy_payload)
    record_taxonomy_manifest(corpus=corpus, input_path=taxonomy_input)
    snapshot_dir = corpus.extracted_dir / "pipeline" / "extract-one"
    (snapshot_dir / "text").mkdir(parents=True, exist_ok=True)
    for index, item in enumerate(items):
        (snapshot_dir / "text" / f"{item.item_id}.txt").write_text(
            f"agent document {index}",
            encoding="utf-8",
        )
    monkeypatch.setattr(
        taxonomy_module,
        "_load_model_bundle",
        lambda *, corpus, classifier_id: {
            "model_manifest": {
                "configuration": {
                    "bertopic_analysis": {
                        "umap_model": None,
                    }
                }
            },
            "topic_map": {"mappings": []},
        },
    )

    def fail_if_called(*, documents, config):
        raise AssertionError("BERTopic should not run for implicit default UMAP undersizing")

    monkeypatch.setattr(taxonomy_module, "run_topic_modeling_for_documents", fail_if_called)

    output = taxonomy_module.discover_taxonomy_children(
        corpus=corpus,
        classifier_id="steering-classifier",
        extraction_snapshot=ExtractionSnapshotReference(
            extractor_id="pipeline",
            snapshot_id="extract-one",
        ),
    )

    assert output.signals == []
    assert output.proposals == []
    assert "requires at least 7 documents" in output.warnings[0]
    assert "BERTopic default UMAP n_components=5" in output.warnings[0]


def test_taxonomy_discovery_falls_back_to_seed_manifest_when_no_taxonomy_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discovery can use root topics from a seed manifest before an accepted taxonomy exists."""
    corpus = Corpus.init(tmp_path / "corpus")
    item = corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        source_uri="urn:test:agent",
    )
    _write_seed_manifest(corpus, item.item_id)
    snapshot_dir = corpus.extracted_dir / "pipeline" / "extract-one"
    (snapshot_dir / "text").mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "text" / f"{item.item_id}.txt").write_text("agent memory", encoding="utf-8")
    monkeypatch.setattr(
        taxonomy_module,
        "_load_model_bundle",
        lambda *, corpus, classifier_id: {
            "model_manifest": {"configuration": {}},
            "topic_map": {"mappings": []},
        },
    )

    output = taxonomy_module.discover_taxonomy_children(
        corpus=corpus,
        classifier_id="steering-classifier",
        extraction_snapshot=ExtractionSnapshotReference(
            extractor_id="pipeline",
            snapshot_id="extract-one",
        ),
    )

    assert output.taxonomy_snapshot_id is None
    assert "requires at least 7 documents" in output.warnings[0]
    assert "BERTopic default UMAP n_components=5" in output.warnings[0]


def test_ontology_manifest_validates_relationship_types_and_refs() -> None:
    """Ontology manifests reject unknown relationship types and malformed refs."""
    valid = OntologyManifest.model_validate(_ontology_payload())
    assert valid.assertions[0].relationship_uid == "influenced"

    unknown = _ontology_payload()
    unknown["assertions"][0]["relationship_uid"] = "unknown"
    with pytest.raises(ValidationError, match="Unknown relationship_uid"):
        OntologyManifest.model_validate(unknown)

    malformed_ref = _ontology_payload(source_ref="bad-ref")
    with pytest.raises(ValidationError, match="Ontology refs must start"):
        OntologyManifest.model_validate(malformed_ref)

    empty_ref = _ontology_payload(source_ref="item:")
    with pytest.raises(ValidationError, match="must include an identifier"):
        OntologyManifest.model_validate(empty_ref)

    duplicate_type = _ontology_payload()
    duplicate_type["relationship_types"].append(dict(duplicate_type["relationship_types"][0]))
    with pytest.raises(ValidationError, match="Duplicate relationship_uid"):
        OntologyManifest.model_validate(duplicate_type)

    duplicate_assertion = _ontology_payload()
    duplicate_assertion["assertions"].append(dict(duplicate_assertion["assertions"][0]))
    with pytest.raises(ValidationError, match="Duplicate assertion_id"):
        OntologyManifest.model_validate(duplicate_assertion)

    unsupported_schema = _ontology_payload()
    unsupported_schema["schema_version"] = 99
    with pytest.raises(ValidationError, match="Unsupported ontology schema version"):
        OntologyManifest.model_validate(unsupported_schema)

    with pytest.raises(ValidationError):
        OntologyRelationshipType.model_validate(
            {
                "relationship_uid": 123,
                "display_name": "Bad",
                "description": "Bad.",
            }
        )


def test_ontology_graph_overlay_is_deterministic_and_typed(tmp_path: Path) -> None:
    """Ontology overlay generation creates deterministic topic, membership, and assertion edges."""
    corpus = Corpus.init(tmp_path / "corpus")
    item = corpus.ingest_item(
        b"agent memory",
        filename="agent.txt",
        media_type="text/plain",
        title="Agent Memory",
        source_uri="urn:test:agent",
    )
    taxonomy_payload = _taxonomy_payload()
    taxonomy_payload["nodes"][1]["seed_item_ids"] = [item.item_id]
    ontology_payload = _ontology_payload(source_ref=f"item:{item.item_id}")

    taxonomy = TaxonomyManifest.model_validate(taxonomy_payload)
    ontology = OntologyManifest.model_validate(ontology_payload)

    first_nodes, first_edges = build_ontology_graph_overlay(
        corpus=corpus,
        taxonomy=taxonomy,
        ontology=ontology,
    )
    second_nodes, second_edges = build_ontology_graph_overlay(
        corpus=corpus,
        taxonomy=taxonomy,
        ontology=ontology,
    )

    assert sorted(node.node_id for node in first_nodes) == sorted(
        node.node_id for node in second_nodes
    )
    assert sorted(edge.edge_id for edge in first_edges) == sorted(
        edge.edge_id for edge in second_edges
    )
    assert {"subtopic_of", "member_of_topic", "influenced"}.issubset(
        {edge.edge_type for edge in first_edges}
    )

    inbound = _ontology_payload(source_ref=f"item:{item.item_id}")
    inbound["assertions"][0]["direction"] = "inbound"
    inbound["assertions"][0]["source_ref"] = "topic:unknown-topic"
    inbound["assertions"][0]["target_ref"] = "graph:external-node"
    inbound_nodes, inbound_edges = build_ontology_graph_overlay(
        corpus=corpus,
        taxonomy=taxonomy,
        ontology=OntologyManifest.model_validate(inbound),
    )
    assert any(node.node_id == "external-node" for node in inbound_nodes)
    assert any(node.node_id == "topic:unknown-topic" for node in inbound_nodes)
    assert any(edge.src == "external-node" for edge in inbound_edges)


def test_recorded_ontology_query_filters_relationships(tmp_path: Path) -> None:
    """Recorded ontology assertions can be queried by source ref and relationship."""
    corpus = Corpus.init(tmp_path / "corpus")
    input_path = tmp_path / "ontology.json"
    _write_json(input_path, _ontology_payload())
    output = record_ontology_manifest(corpus=corpus, input_path=input_path)

    query = query_ontology_assertions(
        corpus=corpus,
        ontology_snapshot_id=output.snapshot_id,
        source_ref="item:item-one",
        relationship_uid="influenced",
        direction="outbound",
    )

    assert len(query.assertions) == 1
    assert query.assertions[0].target_ref == "topic:agent-memory"

    inbound = query_ontology_assertions(
        corpus=corpus,
        ontology_snapshot_id=output.snapshot_id,
        source_ref="topic:agent-memory",
        relationship_uid="influenced",
        direction="inbound",
    )
    both = query_ontology_assertions(
        corpus=corpus,
        ontology_snapshot_id=output.snapshot_id,
        source_ref="topic:agent-memory",
        relationship_uid=None,
        direction="both",
    )
    skipped = query_ontology_assertions(
        corpus=corpus,
        ontology_snapshot_id=output.snapshot_id,
        source_ref="item:item-one",
        relationship_uid="unmatched",
        direction="outbound",
    )
    unmatched_source = query_ontology_assertions(
        corpus=corpus,
        ontology_snapshot_id=output.snapshot_id,
        source_ref="item:missing",
        relationship_uid=None,
        direction="outbound",
    )

    assert len(inbound.assertions) == 1
    assert len(both.assertions) == 1
    assert skipped.assertions == []
    assert unmatched_source.assertions == []


def test_ontology_loading_and_helper_error_branches(tmp_path: Path) -> None:
    """Ontology helpers fail clearly for missing and malformed artifacts."""
    corpus = Corpus.init(tmp_path / "corpus")
    with pytest.raises(FileNotFoundError, match="Missing ontology latest pointer"):
        load_recorded_ontology_manifest(corpus=corpus, snapshot_id="latest")
    with pytest.raises(FileNotFoundError, match="Missing ontology artifact"):
        load_recorded_ontology_manifest(corpus=corpus, snapshot_id="missing")

    _write_json(corpus.analysis_dir / "ontology" / "latest.json", {"snapshot_id": ""})
    with pytest.raises(ValueError, match="Ontology latest pointer must contain snapshot_id"):
        _resolve_ontology_snapshot_id(corpus=corpus, snapshot_id="latest")

    invalid_json = tmp_path / "bad.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON file"):
        _read_ontology_json_object(invalid_json)

    invalid_ontology = tmp_path / "invalid-ontology.json"
    unknown = _ontology_payload()
    unknown["assertions"][0]["relationship_uid"] = "unknown"
    _write_json(invalid_ontology, unknown)
    with pytest.raises(ValueError, match="Invalid ontology manifest"):
        load_ontology_manifest(invalid_ontology)

    list_json = tmp_path / "list.json"
    list_json.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain an object"):
        _read_ontology_json_object(list_json)

    with pytest.raises(ValueError, match="Ontology manifest snapshot_id is missing"):
        _required_ontology_snapshot_id(
            OntologyManifest.model_validate(_ontology_payload()).model_copy(
                update={"snapshot_id": None}
            )
        )
    with pytest.raises(ValueError, match="Taxonomy manifest snapshot_id is missing"):
        _required_ontology_taxonomy_snapshot_id(
            TaxonomyManifest.model_validate(_taxonomy_payload()).model_copy(
                update={"snapshot_id": None}
            )
        )

    assertion = OntologyManifest.model_validate(_ontology_payload()).assertions[0]
    assert _assertion_matches_ref(
        assertion=assertion,
        source_ref="item:item-one",
        direction="outbound",
    )
    assert _assertion_matches_ref(
        assertion=assertion,
        source_ref="topic:agent-memory",
        direction="inbound",
    )
    assert _assertion_matches_ref(
        assertion=assertion,
        source_ref="topic:agent-memory",
        direction="both",
    )


def test_taxonomy_recording_is_reproducible(tmp_path: Path) -> None:
    """Recording the same taxonomy input produces the same snapshot id."""
    corpus = Corpus.init(tmp_path / "corpus")
    input_path = tmp_path / "taxonomy.json"
    _write_json(input_path, _taxonomy_payload())

    first = record_taxonomy_manifest(corpus=corpus, input_path=input_path)
    second = record_taxonomy_manifest(corpus=corpus, input_path=input_path)

    assert first.snapshot_id == second.snapshot_id
    assert first.root_count == 1
    assert first.node_count == 2


def test_taxonomy_and_ontology_proposal_kinds_validate() -> None:
    """Unified steering proposals accept taxonomy and ontology proposal kinds."""
    bundle = SteeringProposalBundle.model_validate(
        {
            "schema_version": 1,
            "analysis_id": "steering-proposals",
            "generated_at": "2026-05-16T00:00:00+00:00",
            "source_artifact_refs": ["taxonomy:one"],
            "signals": [
                {
                    "signal_id": "signal-one",
                    "signal_kind": "taxonomy-child-topic-candidate",
                    "domain": "topic",
                    "source_artifact_refs": ["taxonomy:one"],
                    "metrics": {"document_count": 3},
                    "evidence_item_ids": ["item-one"],
                    "payload": {"topic_uid": "agent-memory"},
                }
            ],
            "proposals": [
                {
                    "proposal_id": "proposal-one",
                    "proposal_kind": "create-taxonomy-node",
                    "domain": "topic",
                    "recommendation": "recommend",
                    "author": {"kind": "agent", "id": "unit"},
                    "source_signal_ids": ["signal-one"],
                    "evidence": {"item_ids": ["item-one"]},
                    "rationale": "Create a child node.",
                    "confidence": 0.7,
                    "payload": {"topic_uid": "agent-memory"},
                },
                {
                    "proposal_id": "proposal-two",
                    "proposal_kind": "add-ontology-relationship",
                    "domain": "graph",
                    "recommendation": "needs_clarification",
                    "author": {"kind": "agent", "id": "unit"},
                    "source_signal_ids": ["signal-one"],
                    "evidence": {"item_ids": ["item-one"]},
                    "rationale": "Add a reviewed graph assertion.",
                    "confidence": None,
                    "payload": {"relationship_uid": "influenced"},
                },
                {
                    "proposal_id": "proposal-three",
                    "proposal_kind": "add-relationship-type",
                    "domain": "graph",
                    "recommendation": "do_not_recommend",
                    "author": {"kind": "agent", "id": "unit"},
                    "source_signal_ids": ["signal-one"],
                    "evidence": {},
                    "rationale": "The relationship type is not specific enough.",
                    "confidence": 0.3,
                    "payload": {"relationship_uid": "vaguely_related"},
                },
            ],
        }
    )

    assert {proposal.proposal_kind for proposal in bundle.proposals} == {
        "create-taxonomy-node",
        "add-ontology-relationship",
        "add-relationship-type",
    }


def test_taxonomy_discover_cli_renders_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The taxonomy discovery command exposes the Markdown report format."""
    corpus = Corpus.init(tmp_path / "corpus")
    output = TaxonomyDiscoveryOutput(
        snapshot_id="snapshot-one",
        generated_at="2026-05-16T00:00:00+00:00",
        classifier_id="classifier-one",
        extraction_snapshot="pipeline:extract-one",
        proposals=[
            {
                "proposal_id": "proposal-one",
                "proposal_kind": "create-taxonomy-node",
                "domain": "topic",
                "recommendation": "needs_clarification",
                "author": {"kind": "biblicus", "id": "taxonomy-discovery"},
                "source_signal_ids": [],
                "evidence": {},
                "rationale": "Candidate child.",
                "confidence": None,
                "payload": {
                    "parent_topic_uid": "agent-systems",
                    "display_name": "Agent Memory",
                    "document_ids": ["item-one"],
                    "keywords": ["memory"],
                },
            }
        ],
    )
    monkeypatch.setattr(
        cli_module,
        "_resolve_extraction_snapshot_for_analysis",
        lambda *, corpus, extraction_snapshot, analysis_label: ExtractionSnapshotReference(
            extractor_id="pipeline",
            snapshot_id="extract-one",
        ),
    )
    monkeypatch.setattr(
        taxonomy_module,
        "discover_taxonomy_children",
        lambda *, corpus, classifier_id, extraction_snapshot: output,
    )

    exit_code = cli_module.cmd_taxonomy_discover(
        SimpleNamespace(
            corpus=str(corpus.root),
            classifier="classifier-one",
            extraction_snapshot="pipeline:extract-one",
            format="markdown",
        )
    )

    assert exit_code == 0
    assert "| proposal-one | agent-systems | Agent Memory | 1 | memory |" in capsys.readouterr().out
