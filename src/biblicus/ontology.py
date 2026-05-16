"""
Accepted ontology contracts and graph materialization for Biblicus.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, ValidationError, field_validator, model_validator

from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .graph.extraction import load_graph_snapshot_manifest
from .graph.models import GraphEdge, GraphNode, parse_graph_snapshot_reference
from .graph.neo4j import create_neo4j_driver, resolve_neo4j_settings, write_graph_records
from .retrieval import hash_text
from .taxonomy import (
    TaxonomyManifest,
    ancestor_topic_uids,
    load_recorded_taxonomy_manifest,
    taxonomy_nodes_by_uid,
)

ONTOLOGY_ANALYSIS_ID = "ontology"
ONTOLOGY_OVERLAY_ITEM_ID = "__ontology__"
BUILT_IN_RELATIONSHIP_TYPES = {
    "subtopic_of": "Subtopic Of",
    "member_of_topic": "Member Of Topic",
}


class OntologyRelationshipType(AnalysisSchemaModel):
    """
    Accepted ontology relationship type definition.

    :ivar relationship_uid: Stable relationship identity.
    :vartype relationship_uid: str
    :ivar display_name: Human-readable relationship name.
    :vartype display_name: str
    :ivar description: Relationship description.
    :vartype description: str
    :ivar directed: Whether assertions using this relationship are directed.
    :vartype directed: bool
    :ivar provenance: Optional provenance metadata.
    :vartype provenance: dict[str, Any]
    """

    relationship_uid: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    directed: bool = True
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("relationship_uid", mode="before")
    @classmethod
    def _strip_relationship_uid(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class OntologyAssertion(AnalysisSchemaModel):
    """
    Accepted ontology relationship assertion.

    :ivar assertion_id: Stable assertion identity.
    :vartype assertion_id: str
    :ivar source_ref: Source reference.
    :vartype source_ref: str
    :ivar relationship_uid: Relationship type identity.
    :vartype relationship_uid: str
    :ivar target_ref: Target reference.
    :vartype target_ref: str
    :ivar direction: Assertion direction.
    :vartype direction: str
    :ivar evidence_item_ids: Evidence item identifiers.
    :vartype evidence_item_ids: list[str]
    :ivar confidence: Optional assertion confidence.
    :vartype confidence: float or None
    :ivar provenance: Optional provenance metadata.
    :vartype provenance: dict[str, Any]
    :ivar notes: Optional notes.
    :vartype notes: str or None
    """

    assertion_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    relationship_uid: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    direction: Literal["outbound", "inbound"] = "outbound"
    evidence_item_ids: List[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

    @field_validator("source_ref", "target_ref")
    @classmethod
    def _validate_ref(cls, value: str) -> str:
        if not value.startswith(("item:", "topic:", "graph:")):
            raise ValueError("Ontology refs must start with item:, topic:, or graph:")
        suffix = value.split(":", 1)[1]
        if not suffix:
            raise ValueError("Ontology refs must include an identifier after the prefix")
        return value


class OntologyManifest(AnalysisSchemaModel):
    """
    Accepted ontology relationship manifest exported by an external steering application.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar ontology_id: Stable ontology identity.
    :vartype ontology_id: str
    :ivar display_name: Human-readable ontology name.
    :vartype display_name: str
    :ivar description: Ontology description.
    :vartype description: str
    :ivar generated_at: External generation timestamp.
    :vartype generated_at: str
    :ivar snapshot_id: Deterministic Biblicus snapshot identity.
    :vartype snapshot_id: str or None
    :ivar relationship_types: Accepted relationship type definitions.
    :vartype relationship_types: list[OntologyRelationshipType]
    :ivar assertions: Accepted relationship assertions.
    :vartype assertions: list[OntologyAssertion]
    :ivar provenance: Optional provenance metadata.
    :vartype provenance: dict[str, Any]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    ontology_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    snapshot_id: Optional[str] = None
    relationship_types: List[OntologyRelationshipType] = Field(default_factory=list)
    assertions: List[OntologyAssertion] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_ontology(self) -> "OntologyManifest":
        if self.schema_version != ANALYSIS_SCHEMA_VERSION:
            raise ValueError(f"Unsupported ontology schema version: {self.schema_version}")
        type_counts = Counter(item.relationship_uid for item in self.relationship_types)
        duplicate_types = sorted(key for key, count in type_counts.items() if count > 1)
        if duplicate_types:
            raise ValueError(f"Duplicate relationship_uid: {', '.join(duplicate_types)}")
        assertion_counts = Counter(item.assertion_id for item in self.assertions)
        duplicate_assertions = sorted(key for key, count in assertion_counts.items() if count > 1)
        if duplicate_assertions:
            raise ValueError(f"Duplicate assertion_id: {', '.join(duplicate_assertions)}")
        relationship_uids = set(type_counts).union(BUILT_IN_RELATIONSHIP_TYPES)
        unknown = sorted(
            {
                assertion.relationship_uid
                for assertion in self.assertions
                if assertion.relationship_uid not in relationship_uids
            }
        )
        if unknown:
            raise ValueError(f"Unknown relationship_uid: {', '.join(unknown)}")
        return self


class OntologyRecordOutput(AnalysisSchemaModel):
    """
    Output for recording an accepted ontology artifact.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier.
    :vartype analysis_id: str
    :ivar ontology_id: Ontology identity.
    :vartype ontology_id: str
    :ivar snapshot_id: Recorded snapshot identifier.
    :vartype snapshot_id: str
    :ivar relationship_type_count: Relationship type count.
    :vartype relationship_type_count: int
    :ivar assertion_count: Assertion count.
    :vartype assertion_count: int
    :ivar artifact_paths: Written artifact paths.
    :vartype artifact_paths: dict[str, str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=ONTOLOGY_ANALYSIS_ID)
    ontology_id: str
    snapshot_id: str
    relationship_type_count: int = Field(ge=0)
    assertion_count: int = Field(ge=0)
    artifact_paths: Dict[str, str] = Field(default_factory=dict)


class OntologyApplyOutput(AnalysisSchemaModel):
    """
    Output for applying accepted taxonomy and ontology to a graph snapshot.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar taxonomy_snapshot_id: Taxonomy snapshot id.
    :vartype taxonomy_snapshot_id: str
    :ivar ontology_snapshot_id: Ontology snapshot id.
    :vartype ontology_snapshot_id: str
    :ivar graph_snapshot: Graph snapshot reference.
    :vartype graph_snapshot: str
    :ivar nodes_written: Number of overlay nodes written.
    :vartype nodes_written: int
    :ivar edges_written: Number of overlay edges written.
    :vartype edges_written: int
    :ivar edge_types: Edge types written.
    :vartype edge_types: list[str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    taxonomy_snapshot_id: str
    ontology_snapshot_id: str
    graph_snapshot: str
    nodes_written: int = Field(ge=0)
    edges_written: int = Field(ge=0)
    edge_types: List[str] = Field(default_factory=list)


class OntologyQueryOutput(AnalysisSchemaModel):
    """
    Output for querying accepted ontology assertions.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar ontology_snapshot_id: Ontology snapshot id.
    :vartype ontology_snapshot_id: str
    :ivar source_ref: Query source reference.
    :vartype source_ref: str or None
    :ivar relationship_uid: Query relationship identity.
    :vartype relationship_uid: str or None
    :ivar direction: Query direction.
    :vartype direction: str
    :ivar assertions: Matching accepted assertions.
    :vartype assertions: list[OntologyAssertion]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    ontology_snapshot_id: str
    source_ref: Optional[str] = None
    relationship_uid: Optional[str] = None
    direction: Literal["outbound", "inbound", "both"]
    assertions: List[OntologyAssertion] = Field(default_factory=list)


def load_ontology_manifest(path: Path) -> OntologyManifest:
    """
    Load and validate an accepted ontology manifest.

    :param path: Ontology JSON input path.
    :type path: pathlib.Path
    :return: Validated ontology manifest with deterministic snapshot id.
    :rtype: OntologyManifest
    """
    payload = _read_json_object(path)
    try:
        manifest = OntologyManifest.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid ontology manifest: {exc}") from exc
    return _with_ontology_snapshot_id(manifest)


def record_ontology_manifest(*, corpus: Corpus, input_path: Path) -> OntologyRecordOutput:
    """
    Record a validated ontology manifest as a Biblicus analysis artifact.

    :param corpus: Corpus that owns the ontology artifact.
    :type corpus: biblicus.corpus.Corpus
    :param input_path: Accepted ontology JSON input path.
    :type input_path: pathlib.Path
    :return: Record output.
    :rtype: OntologyRecordOutput
    """
    manifest = load_ontology_manifest(input_path)
    snapshot_id = _required_snapshot_id(manifest)
    run_dir = corpus.analysis_run_dir(analysis_id=ONTOLOGY_ANALYSIS_ID, snapshot_id=snapshot_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {"manifest": run_dir / "manifest.json", "ontology": run_dir / "ontology.json"}
    artifact_paths = {name: str(path) for name, path in paths.items()}
    _write_json(
        paths["manifest"],
        {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "analysis_id": ONTOLOGY_ANALYSIS_ID,
            "ontology_id": manifest.ontology_id,
            "snapshot_id": snapshot_id,
            "generated_at": manifest.generated_at,
            "relationship_type_count": len(manifest.relationship_types),
            "assertion_count": len(manifest.assertions),
            "artifact_paths": artifact_paths,
        },
    )
    _write_json(paths["ontology"], manifest.model_dump(mode="json"))
    latest_path = corpus.analysis_dir / ONTOLOGY_ANALYSIS_ID / "latest.json"
    _write_json(latest_path, {"snapshot_id": snapshot_id, "generated_at": manifest.generated_at})
    return OntologyRecordOutput(
        ontology_id=manifest.ontology_id,
        snapshot_id=snapshot_id,
        relationship_type_count=len(manifest.relationship_types),
        assertion_count=len(manifest.assertions),
        artifact_paths=artifact_paths,
    )


def load_recorded_ontology_manifest(*, corpus: Corpus, snapshot_id: str) -> OntologyManifest:
    """
    Load a recorded ontology manifest by snapshot id.

    :param corpus: Corpus that owns the ontology artifact.
    :type corpus: biblicus.corpus.Corpus
    :param snapshot_id: Ontology snapshot id or ``latest``.
    :type snapshot_id: str
    :return: Recorded ontology manifest.
    :rtype: OntologyManifest
    """
    resolved_snapshot_id = _resolve_ontology_snapshot_id(corpus=corpus, snapshot_id=snapshot_id)
    path = (
        corpus.analysis_run_dir(
            analysis_id=ONTOLOGY_ANALYSIS_ID,
            snapshot_id=resolved_snapshot_id,
        )
        / "ontology.json"
    )
    if not path.is_file():
        raise FileNotFoundError(f"Missing ontology artifact: {path}")
    return load_ontology_manifest(path)


def apply_ontology_to_graph(
    *,
    corpus: Corpus,
    taxonomy_snapshot_id: str,
    ontology_snapshot_id: str,
    graph_snapshot: str,
) -> OntologyApplyOutput:
    """
    Materialize accepted taxonomy and ontology assertions into a graph snapshot overlay.

    :param corpus: Corpus that owns the graph snapshot.
    :type corpus: biblicus.corpus.Corpus
    :param taxonomy_snapshot_id: Taxonomy snapshot id or ``latest``.
    :type taxonomy_snapshot_id: str
    :param ontology_snapshot_id: Ontology snapshot id or ``latest``.
    :type ontology_snapshot_id: str
    :param graph_snapshot: Graph snapshot reference in extractor:snapshot form.
    :type graph_snapshot: str
    :return: Apply output.
    :rtype: OntologyApplyOutput
    """
    taxonomy = load_recorded_taxonomy_manifest(corpus=corpus, snapshot_id=taxonomy_snapshot_id)
    ontology = load_recorded_ontology_manifest(corpus=corpus, snapshot_id=ontology_snapshot_id)
    graph_reference = parse_graph_snapshot_reference(graph_snapshot)
    graph_manifest = load_graph_snapshot_manifest(
        corpus,
        extractor_id=graph_reference.extractor_id,
        snapshot_id=graph_reference.snapshot_id,
    )
    nodes, edges = build_ontology_graph_overlay(
        corpus=corpus,
        taxonomy=taxonomy,
        ontology=ontology,
    )
    settings = resolve_neo4j_settings()
    driver = create_neo4j_driver(settings)
    try:
        write_graph_records(
            driver=driver,
            settings=settings,
            corpus_id=corpus.uri,
            graph_id=graph_manifest.graph_id,
            extraction_snapshot=graph_reference.as_string(),
            item_id=ONTOLOGY_OVERLAY_ITEM_ID,
            nodes=nodes,
            edges=edges,
        )
    finally:
        driver.close()
    return OntologyApplyOutput(
        taxonomy_snapshot_id=_required_taxonomy_snapshot_id(taxonomy),
        ontology_snapshot_id=_required_snapshot_id(ontology),
        graph_snapshot=graph_reference.as_string(),
        nodes_written=len(nodes),
        edges_written=len(edges),
        edge_types=sorted({edge.edge_type for edge in edges}),
    )


def query_ontology_assertions(
    *,
    corpus: Corpus,
    ontology_snapshot_id: str,
    source_ref: Optional[str],
    relationship_uid: Optional[str],
    direction: Literal["outbound", "inbound", "both"],
) -> OntologyQueryOutput:
    """
    Query accepted ontology assertions from a recorded ontology manifest.

    :param corpus: Corpus that owns the ontology artifact.
    :type corpus: biblicus.corpus.Corpus
    :param ontology_snapshot_id: Ontology snapshot id or ``latest``.
    :type ontology_snapshot_id: str
    :param source_ref: Optional source reference filter.
    :type source_ref: str or None
    :param relationship_uid: Optional relationship type filter.
    :type relationship_uid: str or None
    :param direction: Query direction.
    :type direction: str
    :return: Query output.
    :rtype: OntologyQueryOutput
    """
    ontology = load_recorded_ontology_manifest(corpus=corpus, snapshot_id=ontology_snapshot_id)
    matches: List[OntologyAssertion] = []
    for assertion in ontology.assertions:
        if relationship_uid is not None and assertion.relationship_uid != relationship_uid:
            continue
        if source_ref is not None and not _assertion_matches_ref(
            assertion=assertion,
            source_ref=source_ref,
            direction=direction,
        ):
            continue
        matches.append(assertion)
    return OntologyQueryOutput(
        ontology_snapshot_id=_required_snapshot_id(ontology),
        source_ref=source_ref,
        relationship_uid=relationship_uid,
        direction=direction,
        assertions=matches,
    )


def build_ontology_graph_overlay(
    *,
    corpus: Corpus,
    taxonomy: TaxonomyManifest,
    ontology: OntologyManifest,
) -> tuple[List[GraphNode], List[GraphEdge]]:
    """
    Build graph nodes and edges for accepted taxonomy and ontology state.

    :param corpus: Corpus used for item labels.
    :type corpus: biblicus.corpus.Corpus
    :param taxonomy: Accepted taxonomy manifest.
    :type taxonomy: TaxonomyManifest
    :param ontology: Accepted ontology manifest.
    :return: Overlay nodes and edges.
    :rtype: tuple[list[GraphNode], list[GraphEdge]]
    """
    catalog = corpus.load_catalog()
    nodes_by_id: Dict[str, GraphNode] = {}
    edges_by_id: Dict[str, GraphEdge] = {}
    topic_nodes = taxonomy_nodes_by_uid(taxonomy)
    for node in topic_nodes.values():
        graph_node = GraphNode(
            node_id=f"topic:{node.topic_uid}",
            node_type="topic",
            label=node.display_name,
            properties={
                "topic_uid": node.topic_uid,
                "description": node.description,
                "status": node.status,
            },
        )
        nodes_by_id[graph_node.node_id] = graph_node
    for node in topic_nodes.values():
        if node.parent_topic_uid is not None:
            edges_by_id[
                _edge_id("subtopic_of", f"topic:{node.topic_uid}", f"topic:{node.parent_topic_uid}")
            ] = GraphEdge(
                edge_id=_edge_id(
                    "subtopic_of", f"topic:{node.topic_uid}", f"topic:{node.parent_topic_uid}"
                ),
                src=f"topic:{node.topic_uid}",
                dst=f"topic:{node.parent_topic_uid}",
                edge_type="subtopic_of",
                properties={"source": "taxonomy"},
            )
    for node in topic_nodes.values():
        member_item_ids = sorted(set(node.seed_item_ids).union(node.holdout_item_ids))
        target_topic_uids = [
            node.topic_uid,
            *ancestor_topic_uids(taxonomy=taxonomy, topic_uid=node.topic_uid),
        ]
        for item_id in member_item_ids:
            item_node = _item_graph_node(catalog=catalog, item_id=item_id)
            nodes_by_id[item_node.node_id] = item_node
            for topic_uid in target_topic_uids:
                edge_id = _edge_id("member_of_topic", item_node.node_id, f"topic:{topic_uid}")
                edges_by_id[edge_id] = GraphEdge(
                    edge_id=edge_id,
                    src=item_node.node_id,
                    dst=f"topic:{topic_uid}",
                    edge_type="member_of_topic",
                    properties={"source": "taxonomy", "topic_uid": topic_uid},
                )
    for assertion in ontology.assertions:
        src_ref, dst_ref = _assertion_refs(assertion)
        src_node = _ref_graph_node(ref=src_ref, catalog=catalog, taxonomy_nodes=topic_nodes)
        dst_node = _ref_graph_node(ref=dst_ref, catalog=catalog, taxonomy_nodes=topic_nodes)
        nodes_by_id[src_node.node_id] = src_node
        nodes_by_id[dst_node.node_id] = dst_node
        edge_id = _edge_id(assertion.relationship_uid, src_node.node_id, dst_node.node_id)
        edges_by_id[edge_id] = GraphEdge(
            edge_id=edge_id,
            src=src_node.node_id,
            dst=dst_node.node_id,
            edge_type=assertion.relationship_uid,
            properties={
                "source": "ontology",
                "assertion_id": assertion.assertion_id,
                "evidence_item_ids": assertion.evidence_item_ids,
                "confidence": assertion.confidence,
                "notes": assertion.notes,
            },
        )
    return list(nodes_by_id.values()), list(edges_by_id.values())


def _assertion_matches_ref(
    *,
    assertion: OntologyAssertion,
    source_ref: str,
    direction: Literal["outbound", "inbound", "both"],
) -> bool:
    if direction == "outbound":
        return assertion.source_ref == source_ref
    if direction == "inbound":
        return assertion.target_ref == source_ref
    return assertion.source_ref == source_ref or assertion.target_ref == source_ref


def _assertion_refs(assertion: OntologyAssertion) -> tuple[str, str]:
    if assertion.direction == "outbound":
        return assertion.source_ref, assertion.target_ref
    return assertion.target_ref, assertion.source_ref


def _item_graph_node(*, catalog, item_id: str) -> GraphNode:
    item = catalog.items.get(item_id)
    label = item.title if item is not None and item.title else item_id
    return GraphNode(
        node_id=f"item:{item_id}",
        node_type="item",
        label=label,
        properties={"item_id": item_id},
    )


def _ref_graph_node(*, ref: str, catalog, taxonomy_nodes: Dict[str, Any]) -> GraphNode:
    prefix, value = ref.split(":", 1)
    if prefix == "item":
        return _item_graph_node(catalog=catalog, item_id=value)
    if prefix == "topic":
        topic = taxonomy_nodes.get(value)
        if topic is not None:
            return GraphNode(
                node_id=f"topic:{value}",
                node_type="topic",
                label=topic.display_name,
                properties={"topic_uid": value, "description": topic.description},
            )
        return GraphNode(
            node_id=f"topic:{value}",
            node_type="topic",
            label=value,
            properties={"topic_uid": value},
        )
    return GraphNode(
        node_id=value,
        node_type="entity",
        label=value,
        properties={"graph_ref": ref},
    )


def _with_ontology_snapshot_id(manifest: OntologyManifest) -> OntologyManifest:
    payload = manifest.model_dump(mode="json", exclude={"snapshot_id"})
    snapshot_id = manifest.snapshot_id or hash_text(json.dumps(payload, sort_keys=True))
    return manifest.model_copy(update={"snapshot_id": snapshot_id})


def _required_snapshot_id(manifest: OntologyManifest) -> str:
    if manifest.snapshot_id is None:
        raise ValueError("Ontology manifest snapshot_id is missing")
    return manifest.snapshot_id


def _required_taxonomy_snapshot_id(manifest: TaxonomyManifest) -> str:
    if manifest.snapshot_id is None:
        raise ValueError("Taxonomy manifest snapshot_id is missing")
    return manifest.snapshot_id


def _resolve_ontology_snapshot_id(*, corpus: Corpus, snapshot_id: str) -> str:
    if snapshot_id != "latest":
        return snapshot_id
    latest_path = corpus.analysis_dir / ONTOLOGY_ANALYSIS_ID / "latest.json"
    if not latest_path.is_file():
        raise FileNotFoundError("Missing ontology latest pointer")
    latest = _read_json_object(latest_path)
    resolved = latest.get("snapshot_id")
    if not isinstance(resolved, str) or not resolved.strip():
        raise ValueError("Ontology latest pointer must contain snapshot_id")
    return resolved


def _edge_id(edge_type: str, src: str, dst: str) -> str:
    return f"{edge_type}:{hash_text(f'{edge_type}:{src}:{dst}')}"


def _read_json_object(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
