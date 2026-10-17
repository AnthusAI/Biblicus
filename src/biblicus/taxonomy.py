"""
Accepted taxonomy contracts and hierarchical discovery for Biblicus.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import Field, ValidationError, field_validator, model_validator

from .analysis.models import TopicModelingConfiguration
from .analysis.schema import AnalysisSchemaModel
from .analysis.topic_modeling import TopicModelingDocument, run_topic_modeling_for_documents
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .models import ExtractionSnapshotReference
from .retrieval import hash_text
from .steering_feedback import (
    SteeringFeedback,
    steering_feedback_ref,
    taxonomy_candidate_suppression,
)
from .steering_proposals import SteeringProposal, SteeringSignal
from .time import utc_now_iso
from .topic_classifier import _load_model_bundle, load_topic_classifier_seed_manifest

TAXONOMY_ANALYSIS_ID = "taxonomy"
TAXONOMY_DISCOVERY_ANALYSIS_ID = "taxonomy-discovery"
BERTOPIC_DEFAULT_UMAP_N_COMPONENTS = 5


class TaxonomyNode(AnalysisSchemaModel):
    """
    Accepted taxonomy node.

    :ivar topic_uid: Stable topic identity.
    :vartype topic_uid: str
    :ivar parent_topic_uid: Optional parent topic identity.
    :vartype parent_topic_uid: str or None
    :ivar display_name: Human-readable topic name.
    :vartype display_name: str
    :ivar description: Reviewed topic description.
    :vartype description: str
    :ivar status: Accepted taxonomy node status.
    :vartype status: str
    :ivar seed_item_ids: Reviewed seed item identifiers.
    :vartype seed_item_ids: list[str]
    :ivar holdout_item_ids: Reviewed holdout item identifiers.
    :vartype holdout_item_ids: list[str]
    :ivar source: Optional application source metadata.
    :vartype source: dict[str, Any]
    :ivar provenance: Optional provenance metadata.
    :vartype provenance: dict[str, Any]
    """

    topic_uid: str = Field(min_length=1)
    parent_topic_uid: Optional[str] = None
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: Literal["accepted", "archived"] = "accepted"
    seed_item_ids: List[str] = Field(default_factory=list)
    holdout_item_ids: List[str] = Field(default_factory=list)
    source: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("topic_uid", "parent_topic_uid", mode="before")
    @classmethod
    def _strip_topic_identity(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return value


class TaxonomyManifest(AnalysisSchemaModel):
    """
    Accepted taxonomy manifest exported by an external steering application.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar taxonomy_id: Stable taxonomy identity.
    :vartype taxonomy_id: str
    :ivar display_name: Human-readable taxonomy name.
    :vartype display_name: str
    :ivar description: Taxonomy description.
    :vartype description: str
    :ivar generated_at: External generation timestamp.
    :vartype generated_at: str
    :ivar snapshot_id: Deterministic Biblicus snapshot identity.
    :vartype snapshot_id: str or None
    :ivar nodes: Accepted taxonomy nodes.
    :vartype nodes: list[TaxonomyNode]
    :ivar source: Optional application source metadata.
    :vartype source: dict[str, Any]
    :ivar provenance: Optional provenance metadata.
    :vartype provenance: dict[str, Any]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    taxonomy_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    snapshot_id: Optional[str] = None
    nodes: List[TaxonomyNode] = Field(min_length=1)
    source: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_taxonomy_tree(self) -> "TaxonomyManifest":
        if self.schema_version != ANALYSIS_SCHEMA_VERSION:
            raise ValueError(f"Unsupported taxonomy schema version: {self.schema_version}")
        counts = Counter(node.topic_uid for node in self.nodes)
        duplicates = sorted(topic_uid for topic_uid, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"Duplicate topic_uid: {', '.join(duplicates)}")
        node_ids = set(counts)
        unknown_parents = sorted(
            {
                node.parent_topic_uid
                for node in self.nodes
                if node.parent_topic_uid is not None and node.parent_topic_uid not in node_ids
            }
        )
        if unknown_parents:
            raise ValueError(f"Unknown parent_topic_uid: {', '.join(unknown_parents)}")
        parent_by_topic = {node.topic_uid: node.parent_topic_uid for node in self.nodes}
        for node in self.nodes:
            _validate_no_cycle(topic_uid=node.topic_uid, parent_by_topic=parent_by_topic)
        return self


class TaxonomyRecordOutput(AnalysisSchemaModel):
    """
    Output for recording an accepted taxonomy artifact.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier.
    :vartype analysis_id: str
    :ivar taxonomy_id: Taxonomy identity.
    :vartype taxonomy_id: str
    :ivar snapshot_id: Recorded snapshot identifier.
    :vartype snapshot_id: str
    :ivar node_count: Number of taxonomy nodes.
    :vartype node_count: int
    :ivar root_count: Number of root nodes.
    :vartype root_count: int
    :ivar artifact_paths: Written artifact paths.
    :vartype artifact_paths: dict[str, str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=TAXONOMY_ANALYSIS_ID)
    taxonomy_id: str
    snapshot_id: str
    node_count: int = Field(ge=0)
    root_count: int = Field(ge=0)
    artifact_paths: Dict[str, str] = Field(default_factory=dict)


class TaxonomyDiscoveryOutput(AnalysisSchemaModel):
    """
    Output for taxonomy child discovery.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier.
    :vartype analysis_id: str
    :ivar snapshot_id: Discovery snapshot identifier.
    :vartype snapshot_id: str
    :ivar generated_at: Generation timestamp.
    :vartype generated_at: str
    :ivar classifier_id: Topic classifier identity.
    :vartype classifier_id: str
    :ivar taxonomy_snapshot_id: Accepted taxonomy snapshot used for roots.
    :vartype taxonomy_snapshot_id: str or None
    :ivar extraction_snapshot: Extraction snapshot reference.
    :vartype extraction_snapshot: str
    :ivar signals: Computational child-topic signals.
    :vartype signals: list[SteeringSignal]
    :ivar proposals: Suggested taxonomy proposals.
    :vartype proposals: list[SteeringProposal]
    :ivar warnings: Discovery warnings.
    :vartype warnings: list[str]
    :ivar artifact_paths: Written artifact paths.
    :vartype artifact_paths: dict[str, str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=TAXONOMY_DISCOVERY_ANALYSIS_ID)
    snapshot_id: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    classifier_id: str = Field(min_length=1)
    taxonomy_snapshot_id: Optional[str] = None
    extraction_snapshot: str = Field(min_length=1)
    signals: List[SteeringSignal] = Field(default_factory=list)
    proposals: List[SteeringProposal] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    artifact_paths: Dict[str, str] = Field(default_factory=dict)


def load_taxonomy_manifest(path: Path) -> TaxonomyManifest:
    """
    Load and validate an accepted taxonomy manifest.

    :param path: Taxonomy JSON input path.
    :type path: pathlib.Path
    :return: Validated taxonomy manifest with deterministic snapshot id.
    :rtype: TaxonomyManifest
    """
    payload = _read_json_object(path)
    try:
        manifest = TaxonomyManifest.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid taxonomy manifest: {exc}") from exc
    return _with_taxonomy_snapshot_id(manifest)


def record_taxonomy_manifest(*, corpus: Corpus, input_path: Path) -> TaxonomyRecordOutput:
    """
    Record a validated taxonomy manifest as a Biblicus analysis artifact.

    :param corpus: Corpus that owns the taxonomy artifact.
    :type corpus: biblicus.corpus.Corpus
    :param input_path: Accepted taxonomy JSON input path.
    :type input_path: pathlib.Path
    :return: Record output.
    :rtype: TaxonomyRecordOutput
    """
    manifest = load_taxonomy_manifest(input_path)
    snapshot_id = _required_snapshot_id(manifest)
    run_dir = corpus.analysis_run_dir(analysis_id=TAXONOMY_ANALYSIS_ID, snapshot_id=snapshot_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {"manifest": run_dir / "manifest.json", "taxonomy": run_dir / "taxonomy.json"}
    artifact_paths = {name: str(path) for name, path in paths.items()}
    _write_json(
        paths["manifest"],
        {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "analysis_id": TAXONOMY_ANALYSIS_ID,
            "taxonomy_id": manifest.taxonomy_id,
            "snapshot_id": snapshot_id,
            "generated_at": manifest.generated_at,
            "node_count": len(manifest.nodes),
            "root_count": len(root_taxonomy_nodes(manifest)),
            "artifact_paths": artifact_paths,
        },
    )
    _write_json(paths["taxonomy"], manifest.model_dump(mode="json"))
    latest_path = corpus.analysis_dir / TAXONOMY_ANALYSIS_ID / "latest.json"
    _write_json(latest_path, {"snapshot_id": snapshot_id, "generated_at": manifest.generated_at})
    return TaxonomyRecordOutput(
        taxonomy_id=manifest.taxonomy_id,
        snapshot_id=snapshot_id,
        node_count=len(manifest.nodes),
        root_count=len(root_taxonomy_nodes(manifest)),
        artifact_paths=artifact_paths,
    )


def load_recorded_taxonomy_manifest(*, corpus: Corpus, snapshot_id: str) -> TaxonomyManifest:
    """
    Load a recorded taxonomy manifest by snapshot id.

    :param corpus: Corpus that owns the taxonomy artifact.
    :type corpus: biblicus.corpus.Corpus
    :param snapshot_id: Taxonomy snapshot id or ``latest``.
    :type snapshot_id: str
    :return: Recorded taxonomy manifest.
    :rtype: TaxonomyManifest
    """
    resolved_snapshot_id = _resolve_taxonomy_snapshot_id(corpus=corpus, snapshot_id=snapshot_id)
    path = (
        corpus.analysis_run_dir(
            analysis_id=TAXONOMY_ANALYSIS_ID,
            snapshot_id=resolved_snapshot_id,
        )
        / "taxonomy.json"
    )
    if not path.is_file():
        raise FileNotFoundError(f"Missing taxonomy artifact: {path}")
    return load_taxonomy_manifest(path)


def load_latest_taxonomy_manifest(corpus: Corpus) -> Optional[TaxonomyManifest]:
    """
    Load the latest taxonomy manifest when one has been recorded.

    :param corpus: Corpus that owns taxonomy artifacts.
    :type corpus: biblicus.corpus.Corpus
    :return: Latest taxonomy manifest or None.
    :rtype: TaxonomyManifest or None
    """
    latest_path = corpus.analysis_dir / TAXONOMY_ANALYSIS_ID / "latest.json"
    if not latest_path.is_file():
        return None
    latest = _read_json_object(latest_path)
    snapshot_id = latest.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        return None
    return load_recorded_taxonomy_manifest(corpus=corpus, snapshot_id=snapshot_id)


def discover_taxonomy_children(
    *,
    corpus: Corpus,
    classifier_id: str,
    extraction_snapshot: ExtractionSnapshotReference,
    steering_feedback: Optional[SteeringFeedback] = None,
) -> TaxonomyDiscoveryOutput:
    """
    Discover candidate child taxonomy nodes under accepted root topics.

    :param corpus: Corpus to analyze.
    :type corpus: biblicus.corpus.Corpus
    :param classifier_id: Topic classifier identity.
    :type classifier_id: str
    :param extraction_snapshot: Extraction snapshot used for topic text.
    :type extraction_snapshot: biblicus.models.ExtractionSnapshotReference
    :param steering_feedback: Optional reviewed steering feedback suppressions.
    :type steering_feedback: biblicus.steering_feedback.SteeringFeedback or None
    :return: Taxonomy discovery output.
    :rtype: TaxonomyDiscoveryOutput
    """
    taxonomy = load_latest_taxonomy_manifest(corpus)
    taxonomy_snapshot_id = taxonomy.snapshot_id if taxonomy is not None else None
    if taxonomy is None:
        taxonomy = _taxonomy_from_seed_manifest(corpus=corpus, classifier_id=classifier_id)
    bundle = _load_model_bundle(corpus=corpus, classifier_id=classifier_id)
    config = TopicModelingConfiguration.model_validate(
        bundle["model_manifest"].get("configuration", {})
    )
    topic_map = bundle["topic_map"]
    roots = root_taxonomy_nodes(taxonomy)
    member_ids_by_topic = _topic_map_member_ids(topic_map)
    signals: List[SteeringSignal] = []
    proposals: List[SteeringProposal] = []
    warnings: List[str] = []
    source_artifact_refs = [
        f"topic-classifier:{classifier_id}",
        f"extraction:{extraction_snapshot.as_string()}",
    ]
    if taxonomy_snapshot_id is not None:
        source_artifact_refs.append(f"taxonomy:{taxonomy_snapshot_id}")
    if steering_feedback is not None:
        source_artifact_refs.append(steering_feedback_ref(steering_feedback))

    for root in roots:
        member_ids = sorted(
            set(member_ids_by_topic.get(root.topic_uid, []))
            .union(root.seed_item_ids)
            .union(root.holdout_item_ids)
        )
        documents = _documents_for_items(
            corpus=corpus,
            item_ids=member_ids,
            extraction_snapshot=extraction_snapshot,
        )
        skip_warning = _scoped_topic_modeling_skip_warning(
            root_uid=root.topic_uid,
            document_count=len(documents),
            config=config,
        )
        if skip_warning is not None:
            warnings.append(skip_warning)
            continue
        try:
            report = run_topic_modeling_for_documents(documents=documents, config=config)
        except ValueError as exc:
            warnings.append(f"Skipping root topic {root.topic_uid}: {exc}")
            continue
        used_child_uids: set[str] = {node.topic_uid for node in taxonomy.nodes}
        for topic in report.topics:
            if topic.topic_id == -1:
                continue
            child_uid = _unique_child_topic_uid(
                root_uid=root.topic_uid,
                label=topic.label,
                keywords=[keyword.keyword for keyword in topic.keywords],
                used=used_child_uids,
            )
            used_child_uids.add(child_uid)
            keywords = [keyword.keyword for keyword in topic.keywords]
            payload = {
                "topic_uid": child_uid,
                "parent_topic_uid": root.topic_uid,
                "display_name": topic.label,
                "description": _child_description(
                    parent=root, label=topic.label, keywords=keywords
                ),
                "document_ids": topic.document_ids,
                "keywords": keywords,
                "topic_id": topic.topic_id,
            }
            suppression = taxonomy_candidate_suppression(
                feedback=steering_feedback,
                classifier_id=classifier_id,
                root_topic_uid=root.topic_uid,
                topic_uid=child_uid,
                display_name=topic.label,
            )
            if suppression is not None:
                warnings.append(
                    "Suppressed taxonomy proposal "
                    f"create-taxonomy-node:{child_uid} from steering feedback "
                    f"{suppression.suppression_id}."
                )
                continue
            signal_id = f"taxonomy-child-topic-candidate:{root.topic_uid}:{topic.topic_id}"
            signals.append(
                SteeringSignal(
                    signal_id=signal_id,
                    signal_kind="taxonomy-child-topic-candidate",
                    domain="topic",
                    source_artifact_refs=source_artifact_refs,
                    metrics={"document_count": topic.document_count},
                    evidence_item_ids=topic.document_ids,
                    payload=payload,
                )
            )
            proposals.append(
                SteeringProposal(
                    proposal_id=f"create-taxonomy-node:{child_uid}",
                    proposal_kind="create-taxonomy-node",
                    domain="topic",
                    recommendation="needs_clarification",
                    author={"kind": "biblicus", "id": "taxonomy-discovery"},
                    source_signal_ids=[signal_id],
                    evidence={"item_ids": topic.document_ids},
                    rationale="Scoped topic discovery found a possible child topic under an accepted root.",
                    confidence=None,
                    payload=payload,
                )
            )

    output_seed = {
        "classifier_id": classifier_id,
        "taxonomy_snapshot_id": taxonomy_snapshot_id,
        "extraction_snapshot": extraction_snapshot.as_string(),
        "signals": [signal.model_dump(mode="json") for signal in signals],
        "proposals": [proposal.model_dump(mode="json") for proposal in proposals],
        "warnings": warnings,
    }
    snapshot_id = hash_text(json.dumps(output_seed, sort_keys=True))
    output = TaxonomyDiscoveryOutput(
        snapshot_id=snapshot_id,
        generated_at=utc_now_iso(),
        classifier_id=classifier_id,
        taxonomy_snapshot_id=taxonomy_snapshot_id,
        extraction_snapshot=extraction_snapshot.as_string(),
        signals=signals,
        proposals=proposals,
        warnings=warnings,
    )
    artifact_paths = _write_taxonomy_discovery_artifacts(corpus=corpus, output=output)
    return output.model_copy(update={"artifact_paths": artifact_paths})


def taxonomy_discovery_markdown(output: TaxonomyDiscoveryOutput) -> str:
    """
    Render taxonomy discovery output as Markdown.

    :param output: Taxonomy discovery output.
    :type output: TaxonomyDiscoveryOutput
    :return: Markdown report.
    :rtype: str
    """
    lines = [
        "# Taxonomy Discovery",
        "",
        f"- Snapshot: `{output.snapshot_id}`",
        f"- Classifier: `{output.classifier_id}`",
        f"- Proposals: {len(output.proposals)}",
        "",
        "| Proposal | Parent | Display Name | Documents | Keywords |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for proposal in output.proposals:
        payload = proposal.payload
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(proposal.proposal_id),
                    _markdown_cell(str(payload.get("parent_topic_uid", ""))),
                    _markdown_cell(str(payload.get("display_name", ""))),
                    str(len(payload.get("document_ids", []))),
                    _markdown_cell(", ".join(str(value) for value in payload.get("keywords", []))),
                ]
            )
            + " |"
        )
    if output.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in output.warnings)
    return "\n".join(lines)


def root_taxonomy_nodes(taxonomy: TaxonomyManifest) -> List[TaxonomyNode]:
    """
    Return accepted root taxonomy nodes.

    :param taxonomy: Taxonomy manifest.
    :type taxonomy: TaxonomyManifest
    :return: Root taxonomy nodes.
    :rtype: list[TaxonomyNode]
    """
    return [
        node
        for node in taxonomy.nodes
        if node.parent_topic_uid is None and node.status == "accepted"
    ]


def taxonomy_nodes_by_uid(taxonomy: TaxonomyManifest) -> Dict[str, TaxonomyNode]:
    """
    Return accepted taxonomy nodes keyed by topic identity.

    :param taxonomy: Taxonomy manifest.
    :type taxonomy: TaxonomyManifest
    :return: Taxonomy node map.
    :rtype: dict[str, TaxonomyNode]
    """
    return {node.topic_uid: node for node in taxonomy.nodes if node.status == "accepted"}


def ancestor_topic_uids(*, taxonomy: TaxonomyManifest, topic_uid: str) -> List[str]:
    """
    Return accepted ancestor topic identities for a taxonomy node.

    :param taxonomy: Taxonomy manifest.
    :type taxonomy: TaxonomyManifest
    :param topic_uid: Topic identity.
    :type topic_uid: str
    :return: Ancestor topic identities from nearest parent to root.
    :rtype: list[str]
    """
    parent_by_topic = {node.topic_uid: node.parent_topic_uid for node in taxonomy.nodes}
    ancestors: List[str] = []
    current = parent_by_topic.get(topic_uid)
    while current is not None:
        ancestors.append(current)
        current = parent_by_topic.get(current)
    return ancestors


def _taxonomy_from_seed_manifest(*, corpus: Corpus, classifier_id: str) -> TaxonomyManifest:
    seed_manifest = load_topic_classifier_seed_manifest(
        corpus.meta_dir / "topic-classifiers" / classifier_id / "seed-manifest.json"
    )
    return _with_taxonomy_snapshot_id(
        TaxonomyManifest(
            taxonomy_id=classifier_id,
            display_name=seed_manifest.display_name,
            description=seed_manifest.description,
            generated_at=utc_now_iso(),
            nodes=[
                TaxonomyNode(
                    topic_uid=topic.topic_uid,
                    parent_topic_uid=None,
                    display_name=topic.display_name,
                    description=topic.description,
                    status="accepted",
                    seed_item_ids=list(topic.seed_item_ids),
                    holdout_item_ids=list(topic.holdout_item_ids),
                )
                for topic in seed_manifest.topics
            ],
        )
    )


def _validate_no_cycle(*, topic_uid: str, parent_by_topic: Dict[str, Optional[str]]) -> None:
    seen: set[str] = set()
    current: Optional[str] = topic_uid
    while current is not None:
        if current in seen:
            raise ValueError(f"Taxonomy cycle includes topic_uid: {topic_uid}")
        seen.add(current)
        current = parent_by_topic.get(current)


def _with_taxonomy_snapshot_id(manifest: TaxonomyManifest) -> TaxonomyManifest:
    payload = manifest.model_dump(mode="json", exclude={"snapshot_id"})
    snapshot_id = manifest.snapshot_id or hash_text(json.dumps(payload, sort_keys=True))
    return manifest.model_copy(update={"snapshot_id": snapshot_id})


def _required_snapshot_id(manifest: TaxonomyManifest) -> str:
    if manifest.snapshot_id is None:
        raise ValueError("Taxonomy manifest snapshot_id is missing")
    return manifest.snapshot_id


def _resolve_taxonomy_snapshot_id(*, corpus: Corpus, snapshot_id: str) -> str:
    if snapshot_id != "latest":
        return snapshot_id
    latest_path = corpus.analysis_dir / TAXONOMY_ANALYSIS_ID / "latest.json"
    if not latest_path.is_file():
        raise FileNotFoundError("Missing taxonomy latest pointer")
    latest = _read_json_object(latest_path)
    resolved = latest.get("snapshot_id")
    if not isinstance(resolved, str) or not resolved.strip():
        raise ValueError("Taxonomy latest pointer must contain snapshot_id")
    return resolved


def _topic_map_member_ids(topic_map: Dict[str, Any]) -> Dict[str, List[str]]:
    item_ids_by_topic: Dict[str, set[str]] = {}
    for topic in topic_map.get("topics", []):
        if not isinstance(topic, dict):
            continue
        topic_uid = topic.get("topic_uid")
        if not isinstance(topic_uid, str) or not topic_uid.strip():
            continue
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
        item_ids_by_topic.setdefault(topic_uid, set()).update(
            _string_list(mapping.get("document_ids"))
        )
    return {topic_uid: sorted(item_ids) for topic_uid, item_ids in item_ids_by_topic.items()}


def _documents_for_items(
    *,
    corpus: Corpus,
    item_ids: Sequence[str],
    extraction_snapshot: ExtractionSnapshotReference,
) -> List[TopicModelingDocument]:
    documents: List[TopicModelingDocument] = []
    for item_id in item_ids:
        text = corpus.read_extracted_text(
            extractor_id=extraction_snapshot.extractor_id,
            snapshot_id=extraction_snapshot.snapshot_id,
            item_id=item_id,
        )
        if text is None or not text.strip():
            continue
        documents.append(
            TopicModelingDocument(
                document_id=item_id,
                source_item_id=item_id,
                text=text.strip(),
            )
        )
    return documents


def _scoped_topic_modeling_skip_warning(
    *, root_uid: str, document_count: int, config: TopicModelingConfiguration
) -> Optional[str]:
    minimum_documents, reason = _scoped_topic_modeling_document_requirement(config)
    if document_count >= minimum_documents:
        return None
    if minimum_documents == 2:
        return (
            f"Skipping root topic {root_uid}: " "taxonomy discovery requires at least two documents"
        )
    return (
        f"Skipping root topic {root_uid}: taxonomy discovery requires at least "
        f"{minimum_documents} documents for configured scoped topic modeling; "
        f"found {document_count}. {reason}."
    )


def _scoped_topic_modeling_document_requirement(
    config: TopicModelingConfiguration,
) -> tuple[int, str]:
    requirements = [(2, "Topic modeling requires at least two documents")]
    n_components, source = _effective_umap_n_components(config)
    if n_components is not None:
        required_documents = n_components + 2
        requirements.append(
            (
                required_documents,
                f"{source} UMAP n_components={n_components} requires at least "
                f"{required_documents} documents",
            )
        )
    hdbscan_model = config.bertopic_analysis.hdbscan_model
    if hdbscan_model is not None:
        min_cluster_size = _positive_int_parameter(hdbscan_model.parameters.get("min_cluster_size"))
        if min_cluster_size is not None:
            requirements.append(
                (
                    min_cluster_size,
                    f"HDBSCAN min_cluster_size={min_cluster_size} requires at least "
                    f"{min_cluster_size} documents",
                )
            )
    return max(requirements, key=lambda requirement: requirement[0])


def _effective_umap_n_components(config: TopicModelingConfiguration) -> tuple[Optional[int], str]:
    umap_model = config.bertopic_analysis.umap_model
    if umap_model is not None:
        return _positive_int_parameter(umap_model.parameters.get("n_components")), "Configured"
    if "umap_model" in config.bertopic_analysis.parameters:
        return None, "Configured"
    return BERTOPIC_DEFAULT_UMAP_N_COMPONENTS, "BERTopic default"


def _positive_int_parameter(value: object) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 1:
        return None
    return value


def _unique_child_topic_uid(
    *, root_uid: str, label: str, keywords: Sequence[str], used: set[str]
) -> str:
    slug = _slug(label)
    if not slug:
        slug = _slug(" ".join(keywords[:3]))
    if not slug:
        slug = "child-topic"
    base = f"{root_uid}-{slug}"
    candidate = base
    counter = 2
    while candidate in used:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _child_description(*, parent: TaxonomyNode, label: str, keywords: Sequence[str]) -> str:
    keyword_text = ", ".join(keywords[:5])
    if keyword_text:
        return f"Candidate subtopic under {parent.display_name}: {label}. Keywords: {keyword_text}."
    return f"Candidate subtopic under {parent.display_name}: {label}."


def _write_taxonomy_discovery_artifacts(
    *, corpus: Corpus, output: TaxonomyDiscoveryOutput
) -> Dict[str, str]:
    run_dir = corpus.analysis_run_dir(
        analysis_id=TAXONOMY_DISCOVERY_ANALYSIS_ID,
        snapshot_id=output.snapshot_id,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {"manifest": run_dir / "manifest.json", "output": run_dir / "output.json"}
    artifact_paths = {name: str(path) for name, path in paths.items()}
    final_output = output.model_copy(update={"artifact_paths": artifact_paths})
    _write_json(
        paths["manifest"],
        {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "analysis_id": TAXONOMY_DISCOVERY_ANALYSIS_ID,
            "snapshot_id": output.snapshot_id,
            "generated_at": output.generated_at,
            "artifact_paths": artifact_paths,
            "signal_count": len(output.signals),
            "proposal_count": len(output.proposals),
        },
    )
    _write_json(paths["output"], final_output.model_dump(mode="json"))
    latest_path = corpus.analysis_dir / TAXONOMY_DISCOVERY_ANALYSIS_ID / "latest.json"
    _write_json(
        latest_path, {"snapshot_id": output.snapshot_id, "generated_at": output.generated_at}
    )
    return artifact_paths


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


def _string_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, str) and entry.strip()]


def _slug(value: str) -> str:
    parts = re.findall(r"[a-z0-9]+", value.lower())
    return "-".join(parts[:6])


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
