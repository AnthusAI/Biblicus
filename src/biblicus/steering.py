"""
Steering JSON contracts for external Biblicus integrations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from pydantic import Field, ValidationError, model_validator

from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .steering_proposals import (
    STEERING_PROPOSALS_ANALYSIS_ID,
    SteeringProposal,
    SteeringProposalBundle,
    load_latest_steering_proposal_bundle,
)
from .topic_classifier import TopicClassifierSeedManifest, load_topic_classifier_seed_manifest

STEERING_ARTIFACT_KINDS: Sequence[str] = (
    "extraction",
    "retrieval",
    "topic-modeling",
    "topic-classifier",
    "topic-context",
    "topic-governance",
    "topic-granularity",
    "taxonomy",
    "taxonomy-discovery",
    "ontology",
    "steering-proposals",
    "graph",
)

APP_ONLY_TOPIC_FIELDS = {"subheading", "aliases", "editor_notes", "ranking_hints"}

TOPIC_ANALYSIS_KIND_BY_ID = {
    "topic-modeling": "topic-modeling",
    "topic-context": "topic-context",
    "topic-governance": "topic-governance",
    "topic-granularity-sweep": "topic-granularity",
    "taxonomy": "taxonomy",
    "taxonomy-discovery": "taxonomy-discovery",
    "ontology": "ontology",
    STEERING_PROPOSALS_ANALYSIS_ID: "steering-proposals",
}


class SteeringCorpusIdentity(AnalysisSchemaModel):
    """
    Corpus identity exported to an external steering system.

    :ivar corpus_uri: Canonical corpus uniform resource identifier.
    :vartype corpus_uri: str
    :ivar corpus_path: Local corpus path used by the worker.
    :vartype corpus_path: str
    :ivar name: Corpus directory name.
    :vartype name: str
    :ivar generated_at: Catalog generation timestamp used for this bundle.
    :vartype generated_at: str
    :ivar item_count: Number of catalog items.
    :vartype item_count: int
    """

    corpus_uri: str
    corpus_path: str
    name: str
    generated_at: str
    item_count: int = Field(ge=0)


class SteeringCatalogItem(AnalysisSchemaModel):
    """
    Catalog item projection for the steering export contract.

    :ivar item_id: Biblicus item identifier.
    :vartype item_id: str
    :ivar relpath: Relative raw item path.
    :vartype relpath: str
    :ivar sha256: Stored item digest.
    :vartype sha256: str
    :ivar byte_count: Stored item byte count.
    :vartype byte_count: int
    :ivar media_type: Item media type.
    :vartype media_type: str
    :ivar title: Item title.
    :vartype title: str or None
    :ivar source_uri: Provenance uniform resource identifier.
    :vartype source_uri: str or None
    :ivar tags: Catalog tags.
    :vartype tags: list[str]
    :ivar dates: Canonical item dates.
    :vartype dates: dict[str, Any]
    :ivar intake_status: Research intake status, when present.
    :vartype intake_status: str or None
    :ivar created_at: Catalog item creation timestamp.
    :vartype created_at: str
    :ivar metadata: Full item metadata JSON.
    :vartype metadata: dict[str, Any]
    """

    item_id: str
    relpath: str
    sha256: str
    byte_count: int = Field(ge=0)
    media_type: str
    title: Optional[str] = None
    source_uri: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    dates: Dict[str, Any] = Field(default_factory=dict)
    intake_status: Optional[str] = None
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SteeringTopicDefinition(AnalysisSchemaModel):
    """
    Reviewed topic definition exported from a Biblicus seed manifest.

    :ivar topic_uid: Stable topic identity.
    :vartype topic_uid: str
    :ivar display_name: Human-readable topic name.
    :vartype display_name: str
    :ivar description: Topic definition.
    :vartype description: str
    :ivar seed_item_ids: Reviewed seed item identifiers.
    :vartype seed_item_ids: list[str]
    :ivar holdout_item_ids: Reviewed holdout item identifiers.
    :vartype holdout_item_ids: list[str]
    """

    topic_uid: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    seed_item_ids: List[str] = Field(min_length=1)
    holdout_item_ids: List[str] = Field(default_factory=list)


class SteeringTopicSet(AnalysisSchemaModel):
    """
    Accepted topic set exported to or imported from a steering system.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar classifier_id: Classifier identity.
    :vartype classifier_id: str
    :ivar display_name: Topic set display name.
    :vartype display_name: str
    :ivar description: Topic set description.
    :vartype description: str
    :ivar topics: Reviewed topic definitions.
    :vartype topics: list[SteeringTopicDefinition]
    :ivar unlabeled_policy: Policy for unlabeled training items.
    :vartype unlabeled_policy: str
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    topics: List[SteeringTopicDefinition] = Field(min_length=1)
    unlabeled_policy: str = Field(default="use_minus_one")


class SteeringTopicSetInputTopic(SteeringTopicDefinition):
    """
    Topic definition accepted from an application-controlled topic set.

    :ivar subheading: Application-owned display copy.
    :vartype subheading: str or None
    :ivar aliases: Application-owned alternate names.
    :vartype aliases: list[str] or None
    :ivar editor_notes: Application-owned editorial notes.
    :vartype editor_notes: str or None
    :ivar ranking_hints: Application-owned ranking hints.
    :vartype ranking_hints: dict[str, Any] or None
    """

    subheading: Optional[str] = None
    aliases: Optional[List[str]] = None
    editor_notes: Optional[str] = None
    ranking_hints: Optional[Dict[str, Any]] = None


class SteeringTopicSetInput(AnalysisSchemaModel):
    """
    Application-owned accepted topic set input.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar classifier_id: Classifier identity.
    :vartype classifier_id: str
    :ivar display_name: Topic set display name.
    :vartype display_name: str
    :ivar description: Topic set description.
    :vartype description: str
    :ivar topics: Topic definitions with allowed application-only fields.
    :vartype topics: list[SteeringTopicSetInputTopic]
    :ivar unlabeled_policy: Policy for unlabeled training items.
    :vartype unlabeled_policy: str
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    topics: List[SteeringTopicSetInputTopic] = Field(min_length=1)
    unlabeled_policy: str = Field(default="use_minus_one")

    @model_validator(mode="after")
    def _validate_schema(self) -> "SteeringTopicSetInput":
        if self.schema_version != ANALYSIS_SCHEMA_VERSION:
            raise ValueError(f"Unsupported steering schema version: {self.schema_version}")
        if self.unlabeled_policy != "use_minus_one":
            raise ValueError("unlabeled_policy must be 'use_minus_one'")
        return self


class SteeringArtifactReference(AnalysisSchemaModel):
    """
    Stable reference to a Biblicus artifact.

    :ivar kind: Artifact kind.
    :vartype kind: str
    :ivar artifact_id: Stable artifact reference.
    :vartype artifact_id: str
    :ivar path: Corpus-relative artifact path.
    :vartype path: str
    :ivar snapshot_id: Snapshot identifier, when the artifact has one.
    :vartype snapshot_id: str or None
    :ivar created_at: Artifact creation timestamp, when present.
    :vartype created_at: str or None
    :ivar metadata: Stable metadata for the artifact reference.
    :vartype metadata: dict[str, Any]
    """

    kind: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    snapshot_id: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SteeringArtifactInventory(AnalysisSchemaModel):
    """
    Deterministic inventory of Biblicus artifacts.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar generated_at: Catalog timestamp used for deterministic inventory output.
    :vartype generated_at: str
    :ivar corpus: Corpus identity.
    :vartype corpus: SteeringCorpusIdentity
    :ivar artifacts: Flat artifact reference list.
    :vartype artifacts: list[SteeringArtifactReference]
    :ivar artifacts_by_kind: Artifact references grouped by kind.
    :vartype artifacts_by_kind: dict[str, list[SteeringArtifactReference]]
    :ivar warnings: Inventory warnings.
    :vartype warnings: list[str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    generated_at: str
    corpus: SteeringCorpusIdentity
    artifacts: List[SteeringArtifactReference] = Field(default_factory=list)
    artifacts_by_kind: Dict[str, List[SteeringArtifactReference]] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class SteeringExportBundle(AnalysisSchemaModel):
    """
    Full steering bundle for external application import.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar generated_at: Catalog timestamp used for deterministic output.
    :vartype generated_at: str
    :ivar corpus: Corpus identity.
    :vartype corpus: SteeringCorpusIdentity
    :ivar items: Catalog item projections.
    :vartype items: list[SteeringCatalogItem]
    :ivar topic_set: Accepted topic set, when available.
    :vartype topic_set: SteeringTopicSet or None
    :ivar proposals: Normalized steering proposal records.
    :vartype proposals: list[SteeringProposal]
    :ivar proposal_bundles: Recorded steering proposal bundles.
    :vartype proposal_bundles: list[SteeringProposalBundle]
    :ivar artifacts: Artifact references.
    :vartype artifacts: list[SteeringArtifactReference]
    :ivar warnings: Export warnings.
    :vartype warnings: list[str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    generated_at: str
    corpus: SteeringCorpusIdentity
    items: List[SteeringCatalogItem] = Field(default_factory=list)
    topic_set: Optional[SteeringTopicSet] = None
    proposals: List[SteeringProposal] = Field(default_factory=list)
    proposal_bundles: List[SteeringProposalBundle] = Field(default_factory=list)
    artifacts: List[SteeringArtifactReference] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class SteeringRenderSeedManifestOutput(AnalysisSchemaModel):
    """
    Output for a rendered Biblicus seed manifest.

    :ivar schema_version: Contract schema version.
    :vartype schema_version: int
    :ivar classifier_id: Classifier identity.
    :vartype classifier_id: str
    :ivar output_path: Written seed manifest path.
    :vartype output_path: str
    :ivar topic_count: Number of rendered topics.
    :vartype topic_count: int
    :ivar ignored_app_fields: Application-owned fields ignored in the Biblicus output.
    :vartype ignored_app_fields: list[str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str
    output_path: str
    topic_count: int = Field(ge=0)
    ignored_app_fields: List[str] = Field(default_factory=list)


def build_steering_artifact_inventory(corpus: Corpus) -> SteeringArtifactInventory:
    """
    Build a deterministic artifact inventory for a corpus.

    :param corpus: Corpus to inspect.
    :type corpus: biblicus.corpus.Corpus
    :return: Steering artifact inventory.
    :rtype: SteeringArtifactInventory
    """
    catalog = corpus.load_catalog()
    corpus_identity = _corpus_identity(
        corpus, generated_at=catalog.generated_at, item_count=len(catalog.items)
    )
    artifacts, warnings = _discover_artifact_references(corpus)
    artifacts_by_kind: Dict[str, List[SteeringArtifactReference]] = {
        kind: [] for kind in STEERING_ARTIFACT_KINDS
    }
    for artifact in artifacts:
        artifacts_by_kind.setdefault(artifact.kind, []).append(artifact)
    for kind in STEERING_ARTIFACT_KINDS:
        if not artifacts_by_kind.get(kind):
            warnings.append(f"No {kind} artifacts found.")
    return SteeringArtifactInventory(
        generated_at=catalog.generated_at,
        corpus=corpus_identity,
        artifacts=artifacts,
        artifacts_by_kind=artifacts_by_kind,
        warnings=warnings,
    )


def build_steering_export(
    *,
    corpus: Corpus,
    classifier_id: str,
    topic_governance_snapshot_id: Optional[str] = None,
) -> SteeringExportBundle:
    """
    Build a steering export bundle for an external application.

    :param corpus: Corpus to export.
    :type corpus: biblicus.corpus.Corpus
    :param classifier_id: Topic classifier identifier used to load the accepted topic set.
    :type classifier_id: str
    :param topic_governance_snapshot_id: Optional topic governance snapshot identifier.
    :type topic_governance_snapshot_id: str or None
    :return: Steering export bundle.
    :rtype: SteeringExportBundle
    """
    catalog = corpus.load_catalog()
    warnings: List[str] = []
    artifact_inventory = build_steering_artifact_inventory(corpus)
    warnings.extend(artifact_inventory.warnings)
    topic_set = _load_steering_topic_set(
        corpus=corpus,
        classifier_id=classifier_id,
        warnings=warnings,
    )
    proposals = _load_steering_governance_proposals(
        corpus=corpus,
        snapshot_id=topic_governance_snapshot_id,
        warnings=warnings,
    )
    proposal_bundles: List[SteeringProposalBundle] = []
    latest_proposal_bundle = load_latest_steering_proposal_bundle(
        corpus=corpus,
        warnings=warnings,
    )
    if latest_proposal_bundle is not None:
        proposal_bundles.append(latest_proposal_bundle)
        proposals.extend(latest_proposal_bundle.proposals)
    items = [
        _catalog_item_projection(catalog.items[item_id])
        for item_id in _catalog_order(catalog.order, catalog.items.keys())
        if item_id in catalog.items
    ]
    return SteeringExportBundle(
        generated_at=catalog.generated_at,
        corpus=artifact_inventory.corpus,
        items=items,
        topic_set=topic_set,
        proposals=proposals,
        proposal_bundles=proposal_bundles,
        artifacts=artifact_inventory.artifacts,
        warnings=warnings,
    )


def render_steering_seed_manifest(
    *,
    input_path: Path,
    output_path: Path,
) -> SteeringRenderSeedManifestOutput:
    """
    Render an accepted steering topic set as a Biblicus seed manifest.

    :param input_path: Accepted topic-set JSON path.
    :type input_path: pathlib.Path
    :param output_path: Destination seed-manifest JSON path.
    :type output_path: pathlib.Path
    :return: Render summary.
    :rtype: SteeringRenderSeedManifestOutput
    :raises FileNotFoundError: If the input path does not exist.
    :raises ValueError: If the input cannot be rendered as a strict Biblicus seed manifest.
    """
    topic_set_payload = _load_topic_set_payload(input_path)
    ignored_app_fields = _collect_ignored_app_fields(topic_set_payload)
    topic_set = _validate_topic_set_payload(topic_set_payload)
    seed_payload = {
        "schema_version": topic_set.schema_version,
        "classifier_id": topic_set.classifier_id,
        "display_name": topic_set.display_name,
        "description": topic_set.description,
        "topics": [
            {
                "topic_uid": topic.topic_uid,
                "display_name": topic.display_name,
                "description": topic.description,
                "seed_item_ids": topic.seed_item_ids,
                "holdout_item_ids": topic.holdout_item_ids,
            }
            for topic in topic_set.topics
        ],
        "unlabeled_policy": topic_set.unlabeled_policy,
    }
    try:
        seed_manifest = TopicClassifierSeedManifest.model_validate(seed_payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid steering topic set: {exc}") from exc
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(seed_manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return SteeringRenderSeedManifestOutput(
        classifier_id=seed_manifest.classifier_id,
        output_path=str(output_path),
        topic_count=len(seed_manifest.topics),
        ignored_app_fields=ignored_app_fields,
    )


def _corpus_identity(
    corpus: Corpus, *, generated_at: str, item_count: int
) -> SteeringCorpusIdentity:
    return SteeringCorpusIdentity(
        corpus_uri=corpus.uri,
        corpus_path=str(corpus.root),
        name=corpus.root.name,
        generated_at=generated_at,
        item_count=item_count,
    )


def _catalog_order(order: Sequence[str], item_ids: Sequence[str]) -> List[str]:
    ordered = [item_id for item_id in order if item_id in item_ids]
    ordered.extend(sorted(item_id for item_id in item_ids if item_id not in set(ordered)))
    return ordered


def _catalog_item_projection(item) -> SteeringCatalogItem:
    metadata = dict(item.metadata or {})
    curation = metadata.get("curation")
    intake_status = None
    if isinstance(curation, dict):
        raw_status = curation.get("intake_status")
        intake_status = raw_status if isinstance(raw_status, str) else None
    dates = item.dates.model_dump(mode="json") if item.dates is not None else {}
    return SteeringCatalogItem(
        item_id=item.id,
        relpath=item.relpath,
        sha256=item.sha256,
        byte_count=item.bytes,
        media_type=item.media_type,
        title=item.title,
        source_uri=item.source_uri,
        tags=list(item.tags),
        dates=dates,
        intake_status=intake_status,
        created_at=item.created_at,
        metadata=metadata,
    )


def _load_steering_topic_set(
    *,
    corpus: Corpus,
    classifier_id: str,
    warnings: List[str],
) -> Optional[SteeringTopicSet]:
    seed_manifest_path = (
        corpus.meta_dir / "topic-classifiers" / classifier_id / "seed-manifest.json"
    )
    if not seed_manifest_path.is_file():
        warnings.append(f"Missing topic classifier seed manifest: {seed_manifest_path}")
        return None
    seed_manifest = load_topic_classifier_seed_manifest(seed_manifest_path)
    return SteeringTopicSet.model_validate(seed_manifest.model_dump(mode="json"))


def _load_steering_governance_proposals(
    *,
    corpus: Corpus,
    snapshot_id: Optional[str],
    warnings: List[str],
) -> List[SteeringProposal]:
    resolved_snapshot_id = snapshot_id or _latest_governance_snapshot_id(corpus, warnings)
    if resolved_snapshot_id is None:
        return []
    proposals_path = (
        corpus.analysis_run_dir(
            analysis_id="topic-governance",
            snapshot_id=resolved_snapshot_id,
        )
        / "proposals.json"
    )
    if not proposals_path.is_file():
        warnings.append(f"Missing topic-governance proposals artifact: {proposals_path}")
        return []
    payload = _read_json_file(proposals_path)
    proposals = payload.get("proposals")
    if not isinstance(proposals, list):
        warnings.append(
            f"Topic-governance proposals artifact has no proposals list: {proposals_path}"
        )
        return []
    normalized: List[SteeringProposal] = []
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        try:
            normalized.append(SteeringProposal.model_validate(proposal))
        except ValidationError as exc:
            warnings.append(f"Invalid topic-governance proposal: {exc}")
    return normalized


def _latest_governance_snapshot_id(corpus: Corpus, warnings: List[str]) -> Optional[str]:
    latest_path = corpus.analysis_dir / "topic-governance" / "latest.json"
    if not latest_path.is_file():
        warnings.append("No topic-governance snapshot was provided and no latest pointer exists.")
        return None
    payload = _read_json_file(latest_path)
    snapshot_id = payload.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        warnings.append(f"Topic-governance latest pointer has no snapshot_id: {latest_path}")
        return None
    return snapshot_id


def _discover_artifact_references(
    corpus: Corpus,
) -> tuple[List[SteeringArtifactReference], List[str]]:
    artifacts: List[SteeringArtifactReference] = []
    warnings: List[str] = []
    artifacts.extend(_extraction_artifacts(corpus, warnings))
    artifacts.extend(_retrieval_artifacts(corpus, warnings))
    artifacts.extend(_analysis_artifacts(corpus, warnings))
    artifacts.extend(_graph_artifacts(corpus, warnings))
    artifacts.sort(key=lambda artifact: (artifact.kind, artifact.artifact_id, artifact.path))
    return artifacts, warnings


def _extraction_artifacts(corpus: Corpus, warnings: List[str]) -> List[SteeringArtifactReference]:
    artifacts: List[SteeringArtifactReference] = []
    for manifest_path in _manifest_paths(corpus.extracted_dir):
        relative_parts = manifest_path.relative_to(corpus.extracted_dir).parts
        extractor_id, snapshot_id, _ = relative_parts
        payload = _read_json_file_or_warn(manifest_path, warnings)
        if payload is None:
            continue
        configuration = payload.get("configuration") if isinstance(payload, dict) else {}
        metadata = _configuration_metadata(configuration)
        metadata["extractor_id"] = extractor_id
        artifacts.append(
            SteeringArtifactReference(
                kind="extraction",
                artifact_id=f"{extractor_id}:{snapshot_id}",
                path=_relative_to_corpus(corpus, manifest_path),
                snapshot_id=snapshot_id,
                created_at=_string_value(payload.get("created_at")),
                metadata=metadata,
            )
        )
    return artifacts


def _retrieval_artifacts(corpus: Corpus, warnings: List[str]) -> List[SteeringArtifactReference]:
    artifacts: List[SteeringArtifactReference] = []
    for manifest_path in _manifest_paths(corpus.retrieval_dir):
        relative_parts = manifest_path.relative_to(corpus.retrieval_dir).parts
        retriever_id, snapshot_id, _ = relative_parts
        payload = _read_json_file_or_warn(manifest_path, warnings)
        if payload is None:
            continue
        configuration = payload.get("configuration") if isinstance(payload, dict) else {}
        metadata = _configuration_metadata(configuration)
        metadata["retriever_id"] = retriever_id
        artifacts.append(
            SteeringArtifactReference(
                kind="retrieval",
                artifact_id=f"{retriever_id}:{snapshot_id}",
                path=_relative_to_corpus(corpus, manifest_path),
                snapshot_id=snapshot_id,
                created_at=_string_value(payload.get("created_at")),
                metadata=metadata,
            )
        )
    return artifacts


def _analysis_artifacts(corpus: Corpus, warnings: List[str]) -> List[SteeringArtifactReference]:
    artifacts: List[SteeringArtifactReference] = []
    artifacts.extend(_topic_classifier_artifacts(corpus, warnings))
    if not corpus.analysis_dir.is_dir():
        return artifacts
    for analysis_dir in sorted(path for path in corpus.analysis_dir.iterdir() if path.is_dir()):
        if analysis_dir.name == "topic-classifier":
            continue
        kind = TOPIC_ANALYSIS_KIND_BY_ID.get(analysis_dir.name)
        if kind is None:
            continue
        for manifest_path in sorted(analysis_dir.glob("*/manifest.json")):
            snapshot_id = manifest_path.parent.name
            payload = _read_json_file_or_warn(manifest_path, warnings)
            if payload is None:
                continue
            artifacts.append(
                SteeringArtifactReference(
                    kind=kind,
                    artifact_id=f"{analysis_dir.name}:{snapshot_id}",
                    path=_relative_to_corpus(corpus, manifest_path),
                    snapshot_id=snapshot_id,
                    created_at=_string_value(
                        payload.get("created_at") or payload.get("generated_at")
                    ),
                    metadata={"analysis_id": analysis_dir.name},
                )
            )
    return artifacts


def _topic_classifier_artifacts(
    corpus: Corpus, warnings: List[str]
) -> List[SteeringArtifactReference]:
    artifacts: List[SteeringArtifactReference] = []
    classifier_dir = corpus.analysis_dir / "topic-classifier"
    if not classifier_dir.is_dir():
        return artifacts
    for manifest_path in sorted(classifier_dir.glob("*/model-manifest.json")):
        model_version = manifest_path.parent.name
        payload = _read_json_file_or_warn(manifest_path, warnings)
        if payload is None:
            continue
        classifier_id = _string_value(payload.get("classifier_id")) or "unknown-classifier"
        artifacts.append(
            SteeringArtifactReference(
                kind="topic-classifier",
                artifact_id=f"{classifier_id}:{model_version}",
                path=_relative_to_corpus(corpus, manifest_path),
                snapshot_id=model_version,
                created_at=_string_value(payload.get("created_at")),
                metadata={
                    "analysis_id": "topic-classifier",
                    "classifier_id": classifier_id,
                    "model_version": model_version,
                },
            )
        )
    return artifacts


def _graph_artifacts(corpus: Corpus, warnings: List[str]) -> List[SteeringArtifactReference]:
    artifacts: List[SteeringArtifactReference] = []
    for manifest_path in _manifest_paths(corpus.graph_dir):
        relative_parts = manifest_path.relative_to(corpus.graph_dir).parts
        extractor_id, snapshot_id, _ = relative_parts
        payload = _read_json_file_or_warn(manifest_path, warnings)
        if payload is None:
            continue
        artifacts.append(
            SteeringArtifactReference(
                kind="graph",
                artifact_id=f"{extractor_id}:{snapshot_id}",
                path=_relative_to_corpus(corpus, manifest_path),
                snapshot_id=snapshot_id,
                created_at=_string_value(payload.get("created_at")),
                metadata={
                    "extractor_id": extractor_id,
                    "graph_id": _string_value(payload.get("graph_id")),
                },
            )
        )
    return artifacts


def _manifest_paths(root: Path) -> List[Path]:
    if not root.is_dir():
        return []
    return sorted(root.glob("*/*/manifest.json"))


def _configuration_metadata(configuration: object) -> Dict[str, Any]:
    if not isinstance(configuration, dict):
        return {}
    metadata: Dict[str, Any] = {}
    for key in ["configuration_id", "name", "retriever_id", "extractor_id", "analysis_id"]:
        value = configuration.get(key)
        if value is not None:
            metadata[key] = value
    return metadata


def _relative_to_corpus(corpus: Corpus, path: Path) -> str:
    try:
        return path.resolve().relative_to(corpus.root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _read_json_file(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FileNotFoundError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _read_json_file_or_warn(path: Path, warnings: List[str]) -> Optional[Dict[str, Any]]:
    try:
        return _read_json_file(path)
    except (FileNotFoundError, ValueError) as exc:
        warnings.append(str(exc))
        return None


def _string_value(value: object) -> Optional[str]:
    return value if isinstance(value, str) else None


def _load_topic_set_payload(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Steering topic-set file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid steering topic-set JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Steering topic-set input must be a mapping/object: {path}")
    return payload


def _validate_topic_set_payload(payload: Dict[str, Any]) -> SteeringTopicSetInput:
    allowed_top_level_fields = {
        "schema_version",
        "classifier_id",
        "display_name",
        "description",
        "topics",
        "unlabeled_policy",
    }
    _reject_unknown_fields(
        payload,
        allowed=allowed_top_level_fields,
        location="topic-set",
    )
    raw_topics = payload.get("topics")
    if isinstance(raw_topics, list):
        allowed_topic_fields = {
            "topic_uid",
            "display_name",
            "description",
            "seed_item_ids",
            "holdout_item_ids",
            *APP_ONLY_TOPIC_FIELDS,
        }
        for index, raw_topic in enumerate(raw_topics):
            if isinstance(raw_topic, dict):
                _reject_unknown_fields(
                    raw_topic,
                    allowed=allowed_topic_fields,
                    location=f"topics[{index}]",
                )
    try:
        return SteeringTopicSetInput.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid steering topic set: {exc}") from exc


def _reject_unknown_fields(payload: Dict[str, Any], *, allowed: set[str], location: str) -> None:
    unknown_fields = sorted(set(payload) - allowed)
    if unknown_fields:
        field_list = ", ".join(f"{location}.{field_name}" for field_name in unknown_fields)
        raise ValueError(f"Unknown steering topic-set fields: {field_list}")


def _collect_ignored_app_fields(payload: Dict[str, Any]) -> List[str]:
    ignored_fields: set[str] = set()
    raw_topics = payload.get("topics")
    if isinstance(raw_topics, list):
        for raw_topic in raw_topics:
            if isinstance(raw_topic, dict):
                ignored_fields.update(set(raw_topic).intersection(APP_ONLY_TOPIC_FIELDS))
    return sorted(ignored_fields)
