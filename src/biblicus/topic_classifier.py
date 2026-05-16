"""
Topic classifier workflows backed by semi-supervised BERTopic.
"""

from __future__ import annotations

import importlib
import json
import sys
import threading
import time
from collections import Counter
from collections.abc import Sequence as SequenceCollection
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import Field, ValidationError, field_validator, model_validator

from .analysis.models import (
    TopicModelingBerTopicConfig,
    TopicModelingBerTopicReport,
    TopicModelingConfiguration,
    TopicModelingLabelSource,
    TopicModelingLlmExtractionMethod,
    TopicModelingStageStatus,
    TopicModelingTopic,
)
from .analysis.schema import AnalysisSchemaModel
from .analysis.topic_modeling import (
    TopicModelingDocument,
    _apply_entity_removal,
    _apply_lexical_processing,
    _apply_llm_extraction,
    _collect_documents,
    _group_documents_by_topic,
    _resolve_topic_keywords,
)
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .extraction import load_or_build_extraction_snapshot
from .models import ExtractionSnapshotReference
from .retrieval import hash_text
from .time import utc_now_iso

TOPIC_CLASSIFIER_ANALYSIS_ID = "topic-classifier"
UNLABELED_CLASS_LABEL = -1


class TopicClassifierTopic(AnalysisSchemaModel):
    """
    Reviewed seed topic definition for a topic classifier.

    :ivar topic_uid: Stable Biblicus topic identity.
    :vartype topic_uid: str
    :ivar display_name: Human-readable topic name.
    :vartype display_name: str
    :ivar description: Topic definition.
    :vartype description: str
    :ivar seed_item_ids: Reviewed exemplar item identifiers used for supervision.
    :vartype seed_item_ids: list[str]
    :ivar holdout_item_ids: Reviewed item identifiers withheld from supervision.
    :vartype holdout_item_ids: list[str]
    """

    topic_uid: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    seed_item_ids: List[str] = Field(min_length=1)
    holdout_item_ids: List[str] = Field(default_factory=list)

    @field_validator("topic_uid", "display_name", "description", mode="before")
    @classmethod
    def _clean_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("value must not be empty")
            return cleaned
        return value

    @field_validator("seed_item_ids", "holdout_item_ids")
    @classmethod
    def _validate_item_id_list(cls, value: List[str]) -> List[str]:
        cleaned = [item_id.strip() for item_id in value]
        if any(not item_id for item_id in cleaned):
            raise ValueError("item identifiers must not be empty")
        counts = Counter(cleaned)
        duplicates = sorted([item_id for item_id, count in counts.items() if count > 1])
        if duplicates:
            raise ValueError(f"Duplicate item identifiers: {', '.join(duplicates)}")
        return cleaned

    @model_validator(mode="after")
    def _validate_seed_holdout_overlap(self) -> "TopicClassifierTopic":
        overlap = sorted(set(self.seed_item_ids).intersection(self.holdout_item_ids))
        if overlap:
            raise ValueError(f"Item cannot be both seed and holdout: {', '.join(overlap)}")
        return self


class TopicClassifierSeedManifest(AnalysisSchemaModel):
    """
    Strict manifest describing a classifier seed set.

    :ivar schema_version: Manifest schema version.
    :vartype schema_version: int
    :ivar classifier_id: Stable classifier identifier.
    :vartype classifier_id: str
    :ivar display_name: Human-readable classifier name.
    :vartype display_name: str
    :ivar description: Classifier purpose.
    :vartype description: str
    :ivar topics: Reviewed topic definitions.
    :vartype topics: list[TopicClassifierTopic]
    :ivar unlabeled_policy: Policy used for non-seed items.
    :vartype unlabeled_policy: str
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    topics: List[TopicClassifierTopic] = Field(min_length=1)
    unlabeled_policy: str = Field(default="use_minus_one")

    @field_validator("classifier_id", "display_name", "description", mode="before")
    @classmethod
    def _clean_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("value must not be empty")
            return cleaned
        return value

    @model_validator(mode="after")
    def _validate_manifest(self) -> "TopicClassifierSeedManifest":
        if self.schema_version != ANALYSIS_SCHEMA_VERSION:
            raise ValueError(f"Unsupported topic classifier schema version: {self.schema_version}")
        if self.unlabeled_policy != "use_minus_one":
            raise ValueError("unlabeled_policy must be 'use_minus_one'")
        topic_counts = Counter(topic.topic_uid for topic in self.topics)
        duplicate_topics = sorted([uid for uid, count in topic_counts.items() if count > 1])
        if duplicate_topics:
            raise ValueError(f"Duplicate topic_uid: {', '.join(duplicate_topics)}")

        seed_owner: Dict[str, str] = {}
        holdout_owner: Dict[str, str] = {}
        for topic in self.topics:
            for item_id in topic.seed_item_ids:
                previous = seed_owner.get(item_id)
                if previous is not None and previous != topic.topic_uid:
                    raise ValueError(
                        f"Seed item {item_id} is reused in topics {previous} and {topic.topic_uid}"
                    )
                seed_owner[item_id] = topic.topic_uid
            for item_id in topic.holdout_item_ids:
                previous = holdout_owner.get(item_id)
                if previous is not None and previous != topic.topic_uid:
                    raise ValueError(
                        f"Holdout item {item_id} is reused in topics {previous} and {topic.topic_uid}"
                    )
                holdout_owner[item_id] = topic.topic_uid

        cross_over = sorted(set(seed_owner).intersection(holdout_owner))
        if cross_over:
            raise ValueError(f"Holdout item is also listed as a seed: {', '.join(cross_over)}")
        return self


class TopicClassifierTrainOutput(AnalysisSchemaModel):
    """
    Command output for a topic classifier training run.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar classifier_id: Classifier identifier.
    :vartype classifier_id: str
    :ivar model_version: Model version identifier.
    :vartype model_version: str
    :ivar model_manifest_path: Path to the model manifest artifact.
    :vartype model_manifest_path: str
    :ivar topic_map_path: Path to the topic map artifact.
    :vartype topic_map_path: str
    :ivar holdout_evaluation_path: Path to the holdout evaluation artifact.
    :vartype holdout_evaluation_path: str
    :ivar model_path: Path to the persisted BERTopic model directory.
    :vartype model_path: str
    :ivar latest_pointer_path: Path to the classifier latest pointer.
    :vartype latest_pointer_path: str
    :ivar stats: Training statistics.
    :vartype stats: dict[str, Any]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str
    model_version: str
    model_manifest_path: str
    topic_map_path: str
    holdout_evaluation_path: str
    model_path: str
    latest_pointer_path: str
    stats: Dict[str, Any] = Field(default_factory=dict)


class TopicClassifierPrediction(AnalysisSchemaModel):
    """
    Prediction output for a classified corpus item.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar classifier_id: Classifier identifier.
    :vartype classifier_id: str
    :ivar item_id: Corpus item identifier.
    :vartype item_id: str
    :ivar model_version: Model version identifier.
    :vartype model_version: str
    :ivar bertopic_topic_id: BERTopic topic identifier assigned by this model version.
    :vartype bertopic_topic_id: int
    :ivar topic_uid: Stable Biblicus topic identity, when mapped.
    :vartype topic_uid: str or None
    :ivar display_name: Human-readable mapped topic name, when mapped.
    :vartype display_name: str or None
    :ivar score: Prediction confidence when available.
    :vartype score: float or None
    :ivar review_recommended: Whether human review is recommended.
    :vartype review_recommended: bool
    :ivar representative_evidence: Topic keywords and representative item identifiers.
    :vartype representative_evidence: dict[str, Any]
    :ivar topic_candidates: Ranked candidate topics from classifier scores.
    :vartype topic_candidates: list[TopicClassifierTopicCandidate]
    :ivar recorded: Whether the prediction was persisted as an audit record.
    :vartype recorded: bool
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str
    item_id: str
    model_version: str
    bertopic_topic_id: int
    topic_uid: Optional[str] = None
    display_name: Optional[str] = None
    score: Optional[float] = None
    review_recommended: bool
    representative_evidence: Dict[str, Any] = Field(default_factory=dict)
    topic_candidates: List["TopicClassifierTopicCandidate"] = Field(default_factory=list)
    recorded: bool = False


class TopicClassifierTopicCandidate(AnalysisSchemaModel):
    """
    Ranked topic candidate for a classifier prediction.

    :ivar rank: One-based rank within the prediction.
    :vartype rank: int
    :ivar bertopic_topic_id: BERTopic topic identifier.
    :vartype bertopic_topic_id: int
    :ivar topic_uid: Stable Biblicus topic identity, when mapped.
    :vartype topic_uid: str or None
    :ivar display_name: Human-readable topic name, when mapped.
    :vartype display_name: str or None
    :ivar score: Prediction confidence when available.
    :vartype score: float or None
    :ivar representative_evidence: Topic keywords and representative item identifiers.
    :vartype representative_evidence: dict[str, Any]
    """

    rank: int = Field(ge=1)
    bertopic_topic_id: int
    topic_uid: Optional[str] = None
    display_name: Optional[str] = None
    score: Optional[float] = None
    representative_evidence: Dict[str, Any] = Field(default_factory=dict)


class TopicClassifierProjectionItem(AnalysisSchemaModel):
    """
    Cross-corpus topic projection for one target item.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar classifier_id: Classifier identifier.
    :vartype classifier_id: str
    :ivar item_id: Target corpus item identifier.
    :vartype item_id: str
    :ivar title: Target item title when available.
    :vartype title: str or None
    :ivar source_uri: Target item source uniform resource identifier when available.
    :vartype source_uri: str or None
    :ivar model_version: Classifier model version identifier.
    :vartype model_version: str
    :ivar classifier_corpus_uri: Corpus uniform resource identifier that owns the classifier.
    :vartype classifier_corpus_uri: str
    :ivar target_corpus_uri: Corpus uniform resource identifier that owns the target item.
    :vartype target_corpus_uri: str
    :ivar extraction_snapshot: Target corpus extraction snapshot used for classification text.
    :vartype extraction_snapshot: dict[str, Any]
    :ivar bertopic_topic_id: BERTopic topic identifier assigned by this model version.
    :vartype bertopic_topic_id: int
    :ivar topic_uid: Stable Biblicus topic identity, when mapped.
    :vartype topic_uid: str or None
    :ivar display_name: Human-readable mapped topic name, when mapped.
    :vartype display_name: str or None
    :ivar score: Prediction confidence when available.
    :vartype score: float or None
    :ivar review_recommended: Whether human review is recommended.
    :vartype review_recommended: bool
    :ivar representative_evidence: Topic keywords and representative item identifiers.
    :vartype representative_evidence: dict[str, Any]
    :ivar topic_candidates: Ranked candidate topics from classifier scores.
    :vartype topic_candidates: list[TopicClassifierTopicCandidate]
    :ivar recorded: Whether this projection was persisted as an audit record.
    :vartype recorded: bool
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str
    item_id: str
    title: Optional[str] = None
    source_uri: Optional[str] = None
    model_version: str
    classifier_corpus_uri: str
    target_corpus_uri: str
    extraction_snapshot: Dict[str, Any]
    bertopic_topic_id: int
    topic_uid: Optional[str] = None
    display_name: Optional[str] = None
    score: Optional[float] = None
    review_recommended: bool
    representative_evidence: Dict[str, Any] = Field(default_factory=dict)
    topic_candidates: List[TopicClassifierTopicCandidate] = Field(default_factory=list)
    recorded: bool = False


class TopicClassifierProjectionSkippedItem(AnalysisSchemaModel):
    """
    Target item skipped during a classifier projection batch.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar item_id: Target corpus item identifier.
    :vartype item_id: str
    :ivar title: Target item title when available.
    :vartype title: str or None
    :ivar source_uri: Target item source uniform resource identifier when available.
    :vartype source_uri: str or None
    :ivar reason: Reason the item was not projected.
    :vartype reason: str
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    item_id: str
    title: Optional[str] = None
    source_uri: Optional[str] = None
    reason: str = Field(min_length=1)


class TopicClassifierProjectionOutput(AnalysisSchemaModel):
    """
    Output for projecting a canonical classifier onto a target corpus.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar classifier_id: Classifier identifier.
    :vartype classifier_id: str
    :ivar model_version: Classifier model version identifier.
    :vartype model_version: str
    :ivar classifier_corpus_uri: Corpus uniform resource identifier that owns the classifier.
    :vartype classifier_corpus_uri: str
    :ivar target_corpus_uri: Corpus uniform resource identifier that owns the target items.
    :vartype target_corpus_uri: str
    :ivar extraction_snapshot: Target corpus extraction snapshot used for classification text.
    :vartype extraction_snapshot: dict[str, Any]
    :ivar review_threshold: Minimum confidence score before review is recommended.
    :vartype review_threshold: float
    :ivar recorded: Whether projections were persisted as audit records.
    :vartype recorded: bool
    :ivar summary: Projection summary metrics.
    :vartype summary: dict[str, Any]
    :ivar items: Projected item rows.
    :vartype items: list[TopicClassifierProjectionItem]
    :ivar skipped_items: Target items skipped before projection.
    :vartype skipped_items: list[TopicClassifierProjectionSkippedItem]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str
    model_version: str
    classifier_corpus_uri: str
    target_corpus_uri: str
    extraction_snapshot: Dict[str, Any]
    review_threshold: float
    recorded: bool
    summary: Dict[str, Any] = Field(default_factory=dict)
    items: List[TopicClassifierProjectionItem] = Field(default_factory=list)
    skipped_items: List[TopicClassifierProjectionSkippedItem] = Field(default_factory=list)


class TopicClassifierBatchReviewItem(AnalysisSchemaModel):
    """
    Candidate item row for topic classifier batch review.

    :ivar item_id: Corpus item identifier.
    :vartype item_id: str
    :ivar title: Catalog title when available.
    :vartype title: str or None
    :ivar source_uri: Source uniform resource identifier when available.
    :vartype source_uri: str or None
    :ivar proposed_topic_uid: Candidate topic identity from curation metadata.
    :vartype proposed_topic_uid: str or None
    :ivar classifier_topic_uid: Topic identity predicted by the reviewed classifier.
    :vartype classifier_topic_uid: str or None
    :ivar classifier_display_name: Human-readable classifier topic label.
    :vartype classifier_display_name: str or None
    :ivar classifier_bertopic_topic_id: BERTopic topic identifier from the classifier model.
    :vartype classifier_bertopic_topic_id: int
    :ivar classifier_score: Classifier confidence when available.
    :vartype classifier_score: float or None
    :ivar review_recommended: Whether human review is recommended.
    :vartype review_recommended: bool
    :ivar unsupervised_topic_id: BERTopic topic identifier from exploratory discovery.
    :vartype unsupervised_topic_id: int or None
    :ivar unsupervised_keywords: Keywords for the exploratory topic.
    :vartype unsupervised_keywords: list[dict[str, Any]]
    :ivar reviewer_decision: Placeholder for the human review decision.
    :vartype reviewer_decision: str
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    item_id: str
    title: Optional[str] = None
    source_uri: Optional[str] = None
    proposed_topic_uid: Optional[str] = None
    classifier_topic_uid: Optional[str] = None
    classifier_display_name: Optional[str] = None
    classifier_bertopic_topic_id: int
    classifier_score: Optional[float] = None
    review_recommended: bool
    unsupervised_topic_id: Optional[int] = None
    unsupervised_keywords: List[Dict[str, Any]] = Field(default_factory=list)
    reviewer_decision: str = "pending"


class TopicClassifierBatchReviewOutput(AnalysisSchemaModel):
    """
    Batch review output for newly ingested candidate items.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar classifier_id: Classifier identifier.
    :vartype classifier_id: str
    :ivar model_version: Model version identifier.
    :vartype model_version: str
    :ivar extraction_snapshot: Extraction snapshot used for classification text.
    :vartype extraction_snapshot: dict[str, Any]
    :ivar topic_modeling_snapshot_id: Exploratory topic modeling snapshot identifier.
    :vartype topic_modeling_snapshot_id: str
    :ivar filters: Candidate selection filters.
    :vartype filters: dict[str, Any]
    :ivar summary: Aggregate topic review metrics.
    :vartype summary: dict[str, Any]
    :ivar items: Candidate review rows.
    :vartype items: list[TopicClassifierBatchReviewItem]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str
    model_version: str
    extraction_snapshot: Dict[str, Any]
    topic_modeling_snapshot_id: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    items: List[TopicClassifierBatchReviewItem] = Field(default_factory=list)


class TopicClassifierDraftManifestOutput(AnalysisSchemaModel):
    """
    Output for a drafted topic classifier seed manifest.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar classifier_id: Draft classifier identifier.
    :vartype classifier_id: str
    :ivar output_path: Path to the drafted manifest.
    :vartype output_path: str
    :ivar topic_count: Number of topics in the draft.
    :vartype topic_count: int
    :ivar added_topic_uid: Topic identity added to the draft.
    :vartype added_topic_uid: str
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    classifier_id: str
    output_path: str
    topic_count: int
    added_topic_uid: str


def load_topic_classifier_seed_manifest(path: Path) -> TopicClassifierSeedManifest:
    """
    Load and validate a topic classifier seed manifest.

    :param path: Path to the seed manifest.
    :type path: pathlib.Path
    :return: Validated seed manifest.
    :rtype: TopicClassifierSeedManifest
    :raises ValueError: If the manifest cannot be parsed or validated.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TopicClassifierSeedManifest.model_validate(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid topic classifier manifest JSON: {exc}") from exc
    except ValidationError as exc:
        raise ValueError(f"Invalid topic classifier manifest: {exc}") from exc


def train_topic_classifier(
    *,
    corpus: Corpus,
    manifest_path: Path,
    configuration_name: str,
    configuration: Dict[str, object],
    extraction_snapshot: ExtractionSnapshotReference,
) -> TopicClassifierTrainOutput:
    """
    Train a semi-supervised topic classifier model version.

    :param corpus: Corpus containing source items and extraction artifacts.
    :type corpus: Corpus
    :param manifest_path: Path to the classifier seed manifest.
    :type manifest_path: pathlib.Path
    :param configuration_name: Human-readable configuration name.
    :type configuration_name: str
    :param configuration: Topic modeling preprocessing and BERTopic configuration.
    :type configuration: dict[str, object]
    :param extraction_snapshot: Extraction snapshot reference used for text inputs.
    :type extraction_snapshot: ExtractionSnapshotReference
    :return: Training output summary.
    :rtype: TopicClassifierTrainOutput
    """
    config = TopicModelingConfiguration.model_validate(configuration)
    _validate_classifier_configuration(config)
    seed_manifest = load_topic_classifier_seed_manifest(manifest_path)
    catalog = corpus.load_catalog()
    _validate_manifest_item_references(seed_manifest, catalog.items.keys())

    configuration_id = _configuration_id(
        configuration_name=configuration_name,
        configuration=config,
        classifier_id=seed_manifest.classifier_id,
    )
    model_version = _model_version(
        classifier_id=seed_manifest.classifier_id,
        configuration_id=configuration_id,
        manifest_path=manifest_path,
        extraction_snapshot=extraction_snapshot,
        catalog_generated_at=catalog.generated_at,
    )
    run_dir = corpus.analysis_run_dir(
        analysis_id=TOPIC_CLASSIFIER_ANALYSIS_ID,
        snapshot_id=model_version,
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    documents, text_report = _collect_documents(
        corpus=corpus,
        extraction_snapshot=extraction_snapshot,
        config=config.text_source,
    )
    _validate_manifest_documents(seed_manifest, documents)

    llm_report, llm_documents = _apply_llm_extraction(
        documents=documents,
        config=config.llm_extraction,
    )
    entity_report, entity_documents = _apply_entity_removal(
        documents=llm_documents,
        config=config.entity_removal,
        cache_path=run_dir / "entity_removal.jsonl",
    )
    lexical_report, lexical_documents = _apply_lexical_processing(
        documents=entity_documents,
        config=config.lexical_processing,
    )

    training_labels = _training_labels_for_documents(seed_manifest, lexical_documents)
    topic_model, assignments, probabilities, bertopic_report, topics = _fit_bertopic_classifier(
        documents=lexical_documents,
        labels=training_labels,
        config=config.bertopic_analysis,
    )
    topic_map = _build_topic_map(
        classifier_id=seed_manifest.classifier_id,
        model_version=model_version,
        manifest=seed_manifest,
        documents=lexical_documents,
        assignments=assignments,
        topics=topics,
    )
    holdout_evaluation = _build_holdout_evaluation(
        classifier_id=seed_manifest.classifier_id,
        model_version=model_version,
        manifest=seed_manifest,
        documents=lexical_documents,
        assignments=assignments,
        probabilities=probabilities,
        topic_map=topic_map,
    )

    model_path = run_dir / "model"
    _save_bertopic_model(topic_model=topic_model, model_path=model_path)

    artifact_paths = [
        "model-manifest.json",
        "topic-map.json",
        "holdout-evaluation.json",
        "model",
    ]
    if config.entity_removal.enabled:
        artifact_paths.append("entity_removal.jsonl")
    model_manifest = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "analysis_id": TOPIC_CLASSIFIER_ANALYSIS_ID,
        "classifier_id": seed_manifest.classifier_id,
        "model_version": model_version,
        "display_name": seed_manifest.display_name,
        "description": seed_manifest.description,
        "created_at": utc_now_iso(),
        "corpus_uri": catalog.corpus_uri,
        "catalog_generated_at": catalog.generated_at,
        "seed_manifest_path": str(manifest_path),
        "seed_manifest_hash": hash_text(
            json.dumps(seed_manifest.model_dump(mode="json"), sort_keys=True)
        ),
        "configuration_name": configuration_name,
        "configuration_id": configuration_id,
        "configuration": config.model_dump(mode="json"),
        "extraction_snapshot": extraction_snapshot.model_dump(mode="json"),
        "artifact_paths": artifact_paths,
        "stats": {
            "catalog_items": len(catalog.items),
            "documents": len(lexical_documents),
            "seed_items": _seed_count(seed_manifest),
            "holdout_items": _holdout_count(seed_manifest),
            "topics": bertopic_report.topic_count,
            "text_collection": text_report.model_dump(mode="json"),
            "llm_extraction": llm_report.model_dump(mode="json"),
            "entity_removal": entity_report.model_dump(mode="json"),
            "lexical_processing": lexical_report.model_dump(mode="json"),
            "bertopic_analysis": bertopic_report.model_dump(mode="json"),
        },
    }

    model_manifest_path = run_dir / "model-manifest.json"
    topic_map_path = run_dir / "topic-map.json"
    holdout_evaluation_path = run_dir / "holdout-evaluation.json"
    _write_json(model_manifest_path, model_manifest)
    _write_json(topic_map_path, topic_map)
    _write_json(holdout_evaluation_path, holdout_evaluation)
    latest_pointer_path = _write_latest_pointer(
        corpus=corpus,
        classifier_id=seed_manifest.classifier_id,
        model_version=model_version,
    )

    return TopicClassifierTrainOutput(
        classifier_id=seed_manifest.classifier_id,
        model_version=model_version,
        model_manifest_path=str(model_manifest_path),
        topic_map_path=str(topic_map_path),
        holdout_evaluation_path=str(holdout_evaluation_path),
        model_path=str(model_path),
        latest_pointer_path=str(latest_pointer_path),
        stats={
            "documents": len(lexical_documents),
            "seed_items": _seed_count(seed_manifest),
            "holdout_items": _holdout_count(seed_manifest),
            "mapped_topics": len(topic_map["mappings"]),
            "discovered_topics": len(topic_map["discovered"]),
        },
    )


def classify_topic_classifier_item(
    *,
    corpus: Corpus,
    classifier_id: str,
    item_id: str,
    review_threshold: float = 0.35,
    top_k: int = 5,
    extraction_snapshot: Optional[ExtractionSnapshotReference] = None,
    record: bool = False,
) -> TopicClassifierPrediction:
    """
    Classify a single corpus item with the latest classifier model version.

    :param corpus: Corpus containing the item and model artifacts.
    :type corpus: Corpus
    :param classifier_id: Classifier identifier.
    :type classifier_id: str
    :param item_id: Corpus item identifier.
    :type item_id: str
    :param review_threshold: Minimum score before review is recommended.
    :type review_threshold: float
    :param top_k: Maximum ranked candidates to include.
    :type top_k: int
    :param extraction_snapshot: Optional extraction snapshot override for the item text.
    :type extraction_snapshot: ExtractionSnapshotReference or None
    :param record: Whether to persist the prediction as an audit record.
    :type record: bool
    :return: Prediction output.
    :rtype: TopicClassifierPrediction
    """
    bundle = _load_model_bundle(corpus=corpus, classifier_id=classifier_id)
    snapshot = extraction_snapshot or ExtractionSnapshotReference.model_validate(
        bundle["model_manifest"]["extraction_snapshot"]
    )
    topic_model = _load_bertopic_model(bundle["run_dir"] / "model")
    prediction = _classify_item_with_bundle(
        corpus=corpus,
        bundle=bundle,
        topic_model=topic_model,
        item_id=item_id,
        extraction_snapshot=snapshot,
        review_threshold=review_threshold,
        top_k=top_k,
        recorded=False,
    )
    if record:
        _record_prediction(corpus=corpus, classifier_id=classifier_id, prediction=prediction)
        prediction = prediction.model_copy(update={"recorded": True})
    return prediction


def classify_topic_classifier_text(
    *,
    corpus: Corpus,
    classifier_id: str,
    text: str,
    item_id: str,
    review_threshold: float = 0.35,
    top_k: int = 5,
) -> TopicClassifierPrediction:
    """
    Classify a standalone text payload with the latest classifier model version.

    :param corpus: Corpus containing model artifacts.
    :type corpus: Corpus
    :param classifier_id: Classifier identifier.
    :type classifier_id: str
    :param text: Candidate text to classify.
    :type text: str
    :param item_id: Stable identifier to use in the prediction output.
    :type item_id: str
    :param review_threshold: Minimum score before review is recommended.
    :type review_threshold: float
    :param top_k: Maximum ranked candidates to include.
    :type top_k: int
    :return: Prediction output.
    :rtype: TopicClassifierPrediction
    """
    bundle = _load_model_bundle(corpus=corpus, classifier_id=classifier_id)
    topic_model = _load_bertopic_model(bundle["run_dir"] / "model")
    return _classify_text_with_bundle(
        bundle=bundle,
        topic_model=topic_model,
        item_id=item_id,
        text=text,
        review_threshold=review_threshold,
        top_k=top_k,
        recorded=False,
    )


def project_topic_classifier_items(
    *,
    classifier_corpus: Corpus,
    target_corpus: Corpus,
    classifier_id: str,
    extraction_snapshot: ExtractionSnapshotReference,
    project_all: bool = False,
    item_ids: Sequence[str] = (),
    review_threshold: float = 0.35,
    top_k: int = 5,
    record: bool = False,
) -> TopicClassifierProjectionOutput:
    """
    Project a classifier trained in one corpus onto items in another corpus.

    :param classifier_corpus: Corpus containing the trained topic classifier artifacts.
    :type classifier_corpus: Corpus
    :param target_corpus: Corpus containing the items to classify.
    :type target_corpus: Corpus
    :param classifier_id: Topic classifier identifier.
    :type classifier_id: str
    :param extraction_snapshot: Target corpus extraction snapshot used for item text.
    :type extraction_snapshot: ExtractionSnapshotReference
    :param project_all: Whether to classify every target corpus item.
    :type project_all: bool
    :param item_ids: Explicit target item identifiers to classify.
    :type item_ids: Sequence[str]
    :param review_threshold: Minimum score before review is recommended.
    :type review_threshold: float
    :param top_k: Maximum ranked candidates to include.
    :type top_k: int
    :param record: Whether to persist projections in the target corpus.
    :type record: bool
    :return: Projection output with classifier provenance.
    :rtype: TopicClassifierProjectionOutput
    :raises ValueError: If item selection is ambiguous or empty.
    :raises KeyError: If a target item identifier is unknown.
    :raises FileNotFoundError: If the target extraction snapshot is missing.
    """
    explicit_item_ids = [item_id.strip() for item_id in item_ids if item_id.strip()]
    if int(project_all) + int(bool(explicit_item_ids)) != 1:
        raise ValueError("Topic classifier projection requires exactly one of --all or --item-id")

    target_corpus.load_extraction_snapshot_manifest(
        extractor_id=extraction_snapshot.extractor_id,
        snapshot_id=extraction_snapshot.snapshot_id,
    )
    classifier_catalog = classifier_corpus.load_catalog()
    target_catalog = target_corpus.load_catalog()
    selected_item_ids = _selected_projection_item_ids(
        catalog_order=target_catalog.order,
        catalog_items=target_catalog.items,
        project_all=project_all,
        item_ids=explicit_item_ids,
    )

    bundle = _load_model_bundle(corpus=classifier_corpus, classifier_id=classifier_id)
    topic_model = _load_bertopic_model(bundle["run_dir"] / "model")
    classifier_corpus_uri = classifier_catalog.corpus_uri
    target_corpus_uri = target_catalog.corpus_uri
    model_version = str(bundle["model_manifest"]["model_version"])
    projection_items: List[TopicClassifierProjectionItem] = []
    skipped_items: List[TopicClassifierProjectionSkippedItem] = []

    for item_id in selected_item_ids:
        item = target_catalog.items[item_id]
        try:
            prediction = _classify_item_with_bundle(
                corpus=target_corpus,
                bundle=bundle,
                topic_model=topic_model,
                item_id=item_id,
                extraction_snapshot=extraction_snapshot,
                review_threshold=review_threshold,
                top_k=top_k,
                recorded=record,
            )
        except ValueError as exc:
            if not _is_projection_text_eligibility_error(exc):
                raise
            skipped_items.append(
                TopicClassifierProjectionSkippedItem(
                    item_id=item.id,
                    title=item.title,
                    source_uri=item.source_uri,
                    reason=str(exc),
                )
            )
            continue
        projection = TopicClassifierProjectionItem(
            classifier_id=prediction.classifier_id,
            item_id=prediction.item_id,
            title=item.title,
            source_uri=item.source_uri,
            model_version=prediction.model_version,
            classifier_corpus_uri=classifier_corpus_uri,
            target_corpus_uri=target_corpus_uri,
            extraction_snapshot=extraction_snapshot.model_dump(mode="json"),
            bertopic_topic_id=prediction.bertopic_topic_id,
            topic_uid=prediction.topic_uid,
            display_name=prediction.display_name,
            score=prediction.score,
            review_recommended=prediction.review_recommended,
            representative_evidence=prediction.representative_evidence,
            topic_candidates=prediction.topic_candidates,
            recorded=record,
        )
        if record:
            _record_projection(
                corpus=target_corpus,
                classifier_id=classifier_id,
                projection=projection,
            )
        projection_items.append(projection)

    return TopicClassifierProjectionOutput(
        classifier_id=classifier_id,
        model_version=model_version,
        classifier_corpus_uri=classifier_corpus_uri,
        target_corpus_uri=target_corpus_uri,
        extraction_snapshot=extraction_snapshot.model_dump(mode="json"),
        review_threshold=review_threshold,
        recorded=record,
        summary=_projection_summary(projection_items, skipped_items),
        items=projection_items,
        skipped_items=skipped_items,
    )


def ingest_and_classify_topic_classifier_item(
    *,
    corpus: Corpus,
    classifier_id: str,
    source: str,
    tags: Sequence[str] = (),
    review_threshold: float = 0.35,
    top_k: int = 5,
    record: bool = False,
) -> TopicClassifierPrediction:
    """
    Ingest one source, refresh extraction artifacts, and classify it with the latest model.

    :param corpus: Corpus receiving the new item.
    :type corpus: Corpus
    :param classifier_id: Classifier identifier.
    :type classifier_id: str
    :param source: Local path or uniform resource locator to ingest.
    :type source: str
    :param tags: Tags to apply to the ingested item.
    :type tags: Sequence[str]
    :param review_threshold: Minimum score before review is recommended.
    :type review_threshold: float
    :param top_k: Maximum ranked candidates to include.
    :type top_k: int
    :param record: Whether to persist the prediction as an audit record.
    :type record: bool
    :return: Prediction output.
    :rtype: TopicClassifierPrediction
    """
    ingest_result = corpus.ingest_source(source, tags=tags, allow_external=True)
    corpus.reindex()
    bundle = _load_model_bundle(corpus=corpus, classifier_id=classifier_id)
    extraction_snapshot = _build_extraction_snapshot_for_current_catalog(
        corpus=corpus,
        model_manifest=bundle["model_manifest"],
    )
    return classify_topic_classifier_item(
        corpus=corpus,
        classifier_id=classifier_id,
        item_id=ingest_result.item_id,
        review_threshold=review_threshold,
        top_k=top_k,
        extraction_snapshot=extraction_snapshot,
        record=record,
    )


def build_topic_classifier_batch_review(
    *,
    corpus: Corpus,
    classifier_id: str,
    extraction_snapshot: ExtractionSnapshotReference,
    topic_modeling_snapshot_id: str,
    candidate_tag: Optional[str] = None,
    proposed_topic_uid: Optional[str] = None,
    review_threshold: float = 0.35,
    record: bool = False,
) -> TopicClassifierBatchReviewOutput:
    """
    Build a blind candidate batch review table.

    :param corpus: Corpus containing candidate items and model artifacts.
    :type corpus: Corpus
    :param classifier_id: Topic classifier identifier.
    :type classifier_id: str
    :param extraction_snapshot: Extraction snapshot used for candidate text.
    :type extraction_snapshot: ExtractionSnapshotReference
    :param topic_modeling_snapshot_id: Exploratory topic modeling snapshot identifier.
    :type topic_modeling_snapshot_id: str
    :param candidate_tag: Optional tag required for candidate selection.
    :type candidate_tag: str or None
    :param proposed_topic_uid: Optional proposed topic identity required for selection.
    :type proposed_topic_uid: str or None
    :param review_threshold: Minimum confidence score before review is recommended.
    :type review_threshold: float
    :param record: Whether to persist classifier predictions as audit records.
    :type record: bool
    :return: Batch review output.
    :rtype: TopicClassifierBatchReviewOutput
    :raises ValueError: If no candidate selector is provided.
    """
    if not candidate_tag and not proposed_topic_uid:
        raise ValueError("Batch review requires --candidate-tag or --proposed-topic-uid")

    catalog = corpus.load_catalog()
    candidates = [
        item
        for item in catalog.items.values()
        if _catalog_item_matches_candidate_filters(
            item=item,
            candidate_tag=candidate_tag,
            proposed_topic_uid=proposed_topic_uid,
        )
    ]
    candidates.sort(key=lambda item: item.created_at)

    bundle = _load_model_bundle(corpus=corpus, classifier_id=classifier_id)
    topic_model = _load_bertopic_model(bundle["run_dir"] / "model")
    unsupervised_by_item = _load_unsupervised_topics_by_item(
        corpus=corpus,
        topic_modeling_snapshot_id=topic_modeling_snapshot_id,
    )

    rows: List[TopicClassifierBatchReviewItem] = []
    for item in candidates:
        prediction = _classify_item_with_bundle(
            corpus=corpus,
            bundle=bundle,
            topic_model=topic_model,
            item_id=item.id,
            extraction_snapshot=extraction_snapshot,
            review_threshold=review_threshold,
            top_k=5,
            recorded=False,
        )
        if record:
            _record_prediction(corpus=corpus, classifier_id=classifier_id, prediction=prediction)
            prediction = prediction.model_copy(update={"recorded": True})
        unsupervised = unsupervised_by_item.get(item.id, {})
        rows.append(
            TopicClassifierBatchReviewItem(
                item_id=item.id,
                title=item.title,
                source_uri=item.source_uri,
                proposed_topic_uid=_proposed_topic_uid(item.metadata),
                classifier_topic_uid=prediction.topic_uid,
                classifier_display_name=prediction.display_name,
                classifier_bertopic_topic_id=prediction.bertopic_topic_id,
                classifier_score=prediction.score,
                review_recommended=prediction.review_recommended,
                unsupervised_topic_id=unsupervised.get("topic_id"),
                unsupervised_keywords=unsupervised.get("keywords", []),
            )
        )

    summary = _batch_review_summary(rows)
    return TopicClassifierBatchReviewOutput(
        classifier_id=classifier_id,
        model_version=str(bundle["model_manifest"]["model_version"]),
        extraction_snapshot=extraction_snapshot.model_dump(mode="json"),
        topic_modeling_snapshot_id=topic_modeling_snapshot_id,
        filters={
            "candidate_tag": candidate_tag,
            "proposed_topic_uid": proposed_topic_uid,
            "review_threshold": review_threshold,
            "record": record,
        },
        summary=summary,
        items=rows,
    )


def draft_topic_classifier_manifest(
    *,
    base_manifest_path: Path,
    output_path: Path,
    classifier_id: Optional[str],
    display_name: Optional[str],
    description: Optional[str],
    topic_uid: str,
    topic_display_name: str,
    topic_description: str,
    seed_item_ids: Sequence[str],
    holdout_item_ids: Sequence[str],
) -> TopicClassifierDraftManifestOutput:
    """
    Draft a new seed manifest by adding one reviewed topic to an existing manifest.

    :param base_manifest_path: Existing seed manifest path.
    :type base_manifest_path: pathlib.Path
    :param output_path: Destination path for the drafted manifest.
    :type output_path: pathlib.Path
    :param classifier_id: Optional classifier identifier for the draft.
    :type classifier_id: str or None
    :param display_name: Optional display name for the draft classifier.
    :type display_name: str or None
    :param description: Optional description for the draft classifier.
    :type description: str or None
    :param topic_uid: Topic identity to add.
    :type topic_uid: str
    :param topic_display_name: Human-readable topic label.
    :type topic_display_name: str
    :param topic_description: Reviewed topic definition.
    :type topic_description: str
    :param seed_item_ids: Reviewed seed item identifiers.
    :type seed_item_ids: Sequence[str]
    :param holdout_item_ids: Reviewed holdout item identifiers.
    :type holdout_item_ids: Sequence[str]
    :return: Draft manifest output summary.
    :rtype: TopicClassifierDraftManifestOutput
    """
    base_manifest = load_topic_classifier_seed_manifest(base_manifest_path)
    payload = base_manifest.model_dump(mode="json")
    if classifier_id is not None:
        payload["classifier_id"] = classifier_id
    if display_name is not None:
        payload["display_name"] = display_name
    if description is not None:
        payload["description"] = description
    payload["topics"] = [
        *payload["topics"],
        {
            "topic_uid": topic_uid,
            "display_name": topic_display_name,
            "description": topic_description,
            "seed_item_ids": list(seed_item_ids),
            "holdout_item_ids": list(holdout_item_ids),
        },
    ]
    draft = TopicClassifierSeedManifest.model_validate(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output_path, draft.model_dump(mode="json"))
    return TopicClassifierDraftManifestOutput(
        classifier_id=draft.classifier_id,
        output_path=str(output_path),
        topic_count=len(draft.topics),
        added_topic_uid=topic_uid,
    )


def _validate_classifier_configuration(config: TopicModelingConfiguration) -> None:
    if (
        config.llm_extraction.enabled
        and config.llm_extraction.method != TopicModelingLlmExtractionMethod.SINGLE
    ):
        raise ValueError("Topic classifier training requires llm_extraction.method to be 'single'")
    if config.bertopic_analysis.representation_model is not None:
        raise ValueError("Topic classifier training does not support representation_model")


def _classify_item_with_bundle(
    *,
    corpus: Corpus,
    bundle: Dict[str, Any],
    topic_model: Any,
    item_id: str,
    extraction_snapshot: ExtractionSnapshotReference,
    review_threshold: float,
    top_k: int,
    recorded: bool,
) -> TopicClassifierPrediction:
    config = TopicModelingConfiguration.model_validate(bundle["model_manifest"]["configuration"])
    document = _prepare_single_document(
        corpus=corpus,
        item_id=item_id,
        extraction_snapshot=extraction_snapshot,
        config=config,
    )
    topics, probabilities = topic_model.transform([document.text])
    candidate_probabilities = _topic_candidate_probabilities(
        topic_model=topic_model,
        text=document.text,
    )
    topic_id = int(list(topics)[0])
    score = _probability_score(probabilities, index=0, topic_id=topic_id)
    return _prediction_from_topic(
        classifier_id=str(bundle["model_manifest"]["classifier_id"]),
        item_id=item_id,
        model_version=str(bundle["model_manifest"]["model_version"]),
        topic_id=topic_id,
        score=score,
        probabilities=candidate_probabilities,
        topic_map=bundle["topic_map"],
        review_threshold=review_threshold,
        top_k=top_k,
        recorded=recorded,
    )


def _classify_text_with_bundle(
    *,
    bundle: Dict[str, Any],
    topic_model: Any,
    item_id: str,
    text: str,
    review_threshold: float,
    top_k: int,
    recorded: bool,
) -> TopicClassifierPrediction:
    config = TopicModelingConfiguration.model_validate(bundle["model_manifest"]["configuration"])
    document = _prepare_text_document(item_id=item_id, text=text, config=config)
    topics, probabilities = topic_model.transform([document.text])
    candidate_probabilities = _topic_candidate_probabilities(
        topic_model=topic_model,
        text=document.text,
    )
    topic_id = int(list(topics)[0])
    score = _probability_score(probabilities, index=0, topic_id=topic_id)
    return _prediction_from_topic(
        classifier_id=str(bundle["model_manifest"]["classifier_id"]),
        item_id=item_id,
        model_version=str(bundle["model_manifest"]["model_version"]),
        topic_id=topic_id,
        score=score,
        probabilities=candidate_probabilities,
        topic_map=bundle["topic_map"],
        review_threshold=review_threshold,
        top_k=top_k,
        recorded=recorded,
    )


def _catalog_item_matches_candidate_filters(
    *,
    item: Any,
    candidate_tag: Optional[str],
    proposed_topic_uid: Optional[str],
) -> bool:
    if candidate_tag and candidate_tag not in item.tags:
        return False
    if proposed_topic_uid and _proposed_topic_uid(item.metadata) != proposed_topic_uid:
        return False
    return True


def _proposed_topic_uid(metadata: Dict[str, Any]) -> Optional[str]:
    curation = metadata.get("curation")
    if not isinstance(curation, dict):
        return None
    proposed = curation.get("proposed_topic_uid")
    if isinstance(proposed, str) and proposed.strip():
        return proposed.strip()
    return None


def _load_unsupervised_topics_by_item(
    *, corpus: Corpus, topic_modeling_snapshot_id: str
) -> Dict[str, Dict[str, Any]]:
    output_path = (
        corpus.analysis_dir / "topic-modeling" / topic_modeling_snapshot_id / "output.json"
    )
    if not output_path.is_file():
        raise FileNotFoundError(f"Missing topic modeling output: {output_path}")
    output = json.loads(output_path.read_text(encoding="utf-8"))
    topics = output.get("report", {}).get("topics", [])
    by_item: Dict[str, Dict[str, Any]] = {}
    for topic in topics:
        topic_id = int(topic["topic_id"])
        keywords = topic.get("keywords", [])
        for item_id in topic.get("document_ids", []):
            by_item[str(item_id)] = {
                "topic_id": topic_id,
                "keywords": keywords,
            }
    return by_item


def _batch_review_summary(rows: Sequence[TopicClassifierBatchReviewItem]) -> Dict[str, Any]:
    total = len(rows)
    review_count = len([row for row in rows if row.review_recommended])
    unmapped_count = len([row for row in rows if row.classifier_topic_uid is None])
    proposed_counts = Counter(row.proposed_topic_uid for row in rows if row.proposed_topic_uid)
    unsupervised_counts = Counter(
        row.unsupervised_topic_id for row in rows if row.unsupervised_topic_id is not None
    )
    review_rate = review_count / total if total else 0.0
    unmapped_rate = unmapped_count / total if total else 0.0
    flags = {
        "batch_review_required": total > 0,
        "classifier_unmapped_rate_exceeds_threshold": unmapped_rate > 0.15,
        "review_recommended_rate_exceeds_threshold": review_rate > 0.25,
        "candidate_topic_reached_review_size": any(
            count >= 5 for count in proposed_counts.values()
        ),
    }
    dominant_unsupervised_topic_id = None
    if unsupervised_counts:
        dominant_unsupervised_topic_id = sorted(
            unsupervised_counts.items(), key=lambda entry: (-entry[1], entry[0])
        )[0][0]
    return {
        "candidate_items": total,
        "review_recommended_items": review_count,
        "review_recommended_rate": review_rate,
        "classifier_unmapped_items": unmapped_count,
        "classifier_unmapped_rate": unmapped_rate,
        "proposed_topic_counts": dict(sorted(proposed_counts.items())),
        "unsupervised_topic_counts": {
            str(topic_id): count for topic_id, count in sorted(unsupervised_counts.items())
        },
        "dominant_unsupervised_topic_id": dominant_unsupervised_topic_id,
        "topic_management_flags": flags,
    }


def _validate_manifest_item_references(
    manifest: TopicClassifierSeedManifest, catalog_item_ids: Iterable[str]
) -> None:
    catalog_ids = set(catalog_item_ids)
    referenced = sorted(
        {
            item_id
            for topic in manifest.topics
            for item_id in [*topic.seed_item_ids, *topic.holdout_item_ids]
        }
    )
    missing = [item_id for item_id in referenced if item_id not in catalog_ids]
    if missing:
        raise ValueError(
            f"Topic classifier manifest references unknown item IDs: {', '.join(missing)}"
        )


def _validate_manifest_documents(
    manifest: TopicClassifierSeedManifest, documents: Sequence[TopicModelingDocument]
) -> None:
    document_item_ids = {document.source_item_id for document in documents}
    required = sorted(
        {
            item_id
            for topic in manifest.topics
            for item_id in [*topic.seed_item_ids, *topic.holdout_item_ids]
        }
    )
    missing = [item_id for item_id in required if item_id not in document_item_ids]
    if missing:
        raise ValueError(
            "Topic classifier training requires extracted text for manifest item IDs: "
            + ", ".join(missing)
        )


def _configuration_id(
    *,
    configuration_name: str,
    configuration: TopicModelingConfiguration,
    classifier_id: str,
) -> str:
    payload = json.dumps(
        {
            "analysis_id": TOPIC_CLASSIFIER_ANALYSIS_ID,
            "classifier_id": classifier_id,
            "name": configuration_name,
            "configuration": configuration.model_dump(mode="json"),
        },
        sort_keys=True,
    )
    return hash_text(payload)


def _model_version(
    *,
    classifier_id: str,
    configuration_id: str,
    manifest_path: Path,
    extraction_snapshot: ExtractionSnapshotReference,
    catalog_generated_at: str,
) -> str:
    manifest_hash = hash_text(manifest_path.read_text(encoding="utf-8"))
    payload = ":".join(
        [
            TOPIC_CLASSIFIER_ANALYSIS_ID,
            classifier_id,
            configuration_id,
            manifest_hash,
            extraction_snapshot.as_string(),
            catalog_generated_at,
        ]
    )
    return hash_text(payload)


def _training_labels_for_documents(
    manifest: TopicClassifierSeedManifest,
    documents: Sequence[TopicModelingDocument],
) -> List[int]:
    class_by_item_id: Dict[str, int] = {}
    for class_label, topic in enumerate(manifest.topics):
        for item_id in topic.seed_item_ids:
            class_by_item_id[item_id] = class_label
    return [
        class_by_item_id.get(document.source_item_id, UNLABELED_CLASS_LABEL)
        for document in documents
    ]


def _fit_bertopic_classifier(
    *,
    documents: List[TopicModelingDocument],
    labels: List[int],
    config: TopicModelingBerTopicConfig,
) -> Tuple[Any, List[int], Any, TopicModelingBerTopicReport, List[TopicModelingTopic]]:
    try:
        bertopic_module = importlib.import_module("bertopic")
        if not hasattr(bertopic_module, "BERTopic"):
            raise ImportError("BERTopic class is unavailable")
        BERTopic = bertopic_module.BERTopic
    except ImportError as import_error:
        raise ValueError(
            "Topic classifier training requires BERTopic. "
            'Install it with pip install "biblicus[topic-modeling]".'
        ) from import_error

    bertopic_kwargs = dict(config.parameters)
    is_fake = bool(getattr(bertopic_module, "__biblicus_fake__", False))
    if config.vectorizer is not None and "vectorizer_model" not in bertopic_kwargs:
        if is_fake:
            bertopic_kwargs["vectorizer_model"] = None
        else:
            try:
                from sklearn.feature_extraction.text import CountVectorizer
            except ImportError as import_error:
                raise ValueError(
                    "Vectorizer configuration requires scikit-learn. "
                    'Install with pip install "biblicus[topic-modeling]".'
                ) from import_error
            bertopic_kwargs["vectorizer_model"] = CountVectorizer(
                ngram_range=tuple(config.vectorizer.ngram_range),
                stop_words=config.vectorizer.stop_words,
            )

    topic_model = BERTopic(**bertopic_kwargs)
    texts = [document.text for document in documents]
    start_time = time.perf_counter()
    stop_event = threading.Event()

    def heartbeat() -> None:
        while not stop_event.wait(30):
            elapsed = time.perf_counter() - start_time
            print(
                f"[topic-classifier] bertopic fit_transform elapsed={elapsed:.1f}s",
                flush=True,
                file=sys.stderr,
            )

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    print(
        f"[topic-classifier] bertopic fit_transform documents={len(texts)}",
        flush=True,
        file=sys.stderr,
    )
    try:
        assignments, probabilities = topic_model.fit_transform(texts, y=labels)
    finally:
        stop_event.set()
        thread.join(timeout=1)
    elapsed = time.perf_counter() - start_time
    print(
        f"[topic-classifier] bertopic fit_transform complete elapsed={elapsed:.1f}s",
        flush=True,
        file=sys.stderr,
    )

    assignment_list = [int(topic_id) for topic_id in list(assignments)]
    topic_ids = sorted(set(assignment_list))
    topic_documents = _group_documents_by_topic(documents, assignment_list)
    topics: List[TopicModelingTopic] = []
    for topic_id in topic_ids:
        keywords = _resolve_topic_keywords(topic_model=topic_model, topic_id=topic_id)
        label = keywords[0].keyword if keywords else f"Topic {topic_id}"
        doc_entries = topic_documents.get(topic_id, [])
        topics.append(
            TopicModelingTopic(
                topic_id=topic_id,
                label=label,
                label_source=TopicModelingLabelSource.BERTOPIC,
                keywords=keywords,
                document_count=len(doc_entries),
                document_examples=[doc.text for doc in doc_entries[:3]],
                document_ids=[doc.document_id for doc in doc_entries],
            )
        )
    report = TopicModelingBerTopicReport(
        status=TopicModelingStageStatus.COMPLETE,
        topic_count=len(topics),
        document_count=len(documents),
        parameters=dict(config.parameters),
        vectorizer=config.vectorizer,
        warnings=[],
        errors=[],
    )
    return topic_model, assignment_list, probabilities, report, topics


def _build_topic_map(
    *,
    classifier_id: str,
    model_version: str,
    manifest: TopicClassifierSeedManifest,
    documents: Sequence[TopicModelingDocument],
    assignments: Sequence[int],
    topics: Sequence[TopicModelingTopic],
) -> Dict[str, Any]:
    topic_by_uid = {topic.topic_uid: topic for topic in manifest.topics}
    manifest_order = {topic.topic_uid: index for index, topic in enumerate(manifest.topics)}
    seed_topic_by_item_id = {
        item_id: topic.topic_uid for topic in manifest.topics for item_id in topic.seed_item_ids
    }
    votes_by_bertopic_topic: Dict[int, Counter[str]] = {}
    seed_items_by_bertopic_topic: Dict[int, List[str]] = {}
    documents_by_bertopic_topic: Dict[int, List[TopicModelingDocument]] = {}

    for document, topic_id in zip(documents, assignments):
        documents_by_bertopic_topic.setdefault(int(topic_id), []).append(document)
        topic_uid = seed_topic_by_item_id.get(document.source_item_id)
        if topic_uid is None:
            continue
        votes_by_bertopic_topic.setdefault(int(topic_id), Counter())[topic_uid] += 1
        seed_items_by_bertopic_topic.setdefault(int(topic_id), []).append(document.source_item_id)

    topic_records = {topic.topic_id: topic for topic in topics}
    mappings: List[Dict[str, Any]] = []
    discovered: List[Dict[str, Any]] = []
    topic_ids_by_uid: Dict[str, List[int]] = {topic.topic_uid: [] for topic in manifest.topics}

    for topic_id in sorted(documents_by_bertopic_topic):
        votes = votes_by_bertopic_topic.get(topic_id, Counter())
        topic_record = topic_records.get(topic_id)
        keywords = _keywords_payload(topic_record)
        document_ids = [document.document_id for document in documents_by_bertopic_topic[topic_id]]
        if votes:
            selected_topic_uid, vote_count = sorted(
                votes.items(),
                key=lambda entry: (-entry[1], manifest_order[entry[0]]),
            )[0]
            seed_topic = topic_by_uid[selected_topic_uid]
            mappings.append(
                {
                    "bertopic_topic_id": topic_id,
                    "topic_uid": selected_topic_uid,
                    "display_name": seed_topic.display_name,
                    "seed_votes": vote_count,
                    "seed_vote_counts": dict(sorted(votes.items())),
                    "seed_item_ids": seed_items_by_bertopic_topic.get(topic_id, []),
                    "document_count": len(document_ids),
                    "document_ids": document_ids,
                    "keywords": keywords,
                }
            )
            topic_ids_by_uid[selected_topic_uid].append(topic_id)
        else:
            discovered.append(
                {
                    "bertopic_topic_id": topic_id,
                    "document_count": len(document_ids),
                    "document_ids": document_ids,
                    "keywords": keywords,
                }
            )

    topic_summaries = []
    for topic in manifest.topics:
        topic_summaries.append(
            {
                "topic_uid": topic.topic_uid,
                "display_name": topic.display_name,
                "description": topic.description,
                "seed_item_ids": topic.seed_item_ids,
                "holdout_item_ids": topic.holdout_item_ids,
                "bertopic_topic_ids": sorted(topic_ids_by_uid[topic.topic_uid]),
            }
        )

    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "classifier_id": classifier_id,
        "model_version": model_version,
        "generated_at": utc_now_iso(),
        "topics": topic_summaries,
        "mappings": mappings,
        "discovered": discovered,
    }


def _build_holdout_evaluation(
    *,
    classifier_id: str,
    model_version: str,
    manifest: TopicClassifierSeedManifest,
    documents: Sequence[TopicModelingDocument],
    assignments: Sequence[int],
    probabilities: Any,
    topic_map: Dict[str, Any],
) -> Dict[str, Any]:
    assignment_by_item_id = {
        document.source_item_id: int(assignments[index]) for index, document in enumerate(documents)
    }
    index_by_item_id = {document.source_item_id: index for index, document in enumerate(documents)}
    mapping_by_topic_id = _mapping_by_bertopic_topic(topic_map)
    items: List[Dict[str, Any]] = []

    for topic in manifest.topics:
        for item_id in topic.holdout_item_ids:
            topic_id = assignment_by_item_id[item_id]
            mapping = mapping_by_topic_id.get(topic_id)
            predicted_topic_uid = mapping.get("topic_uid") if mapping else None
            score = _probability_score(
                probabilities,
                index=index_by_item_id[item_id],
                topic_id=topic_id,
            )
            review_recommended = predicted_topic_uid is None
            items.append(
                {
                    "item_id": item_id,
                    "expected_topic_uid": topic.topic_uid,
                    "bertopic_topic_id": topic_id,
                    "predicted_topic_uid": predicted_topic_uid,
                    "score": score,
                    "matched": predicted_topic_uid == topic.topic_uid,
                    "review_recommended": review_recommended,
                }
            )

    matched = len([item for item in items if item["matched"]])
    review_recommended = len([item for item in items if item["review_recommended"]])
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "classifier_id": classifier_id,
        "model_version": model_version,
        "generated_at": utc_now_iso(),
        "summary": {
            "holdout_items": _holdout_count(manifest),
            "evaluated_items": len(items),
            "matched_items": matched,
            "review_recommended_items": review_recommended,
        },
        "items": items,
    }


def _prepare_single_document(
    *,
    corpus: Corpus,
    item_id: str,
    extraction_snapshot: ExtractionSnapshotReference,
    config: TopicModelingConfiguration,
) -> TopicModelingDocument:
    raw_text = corpus.read_extracted_text(
        extractor_id=extraction_snapshot.extractor_id,
        snapshot_id=extraction_snapshot.snapshot_id,
        item_id=item_id,
    )
    if raw_text is None:
        raise ValueError(
            f"Missing extracted text for item {item_id} in snapshot {extraction_snapshot.as_string()}"
        )
    return _prepare_text_document(item_id=item_id, text=raw_text, config=config)


def _prepare_text_document(
    *,
    item_id: str,
    text: str,
    config: TopicModelingConfiguration,
) -> TopicModelingDocument:
    """
    Prepare a single text payload using the classifier preprocessing configuration.

    :param item_id: Identifier to assign to the prepared document.
    :type item_id: str
    :param text: Raw text payload.
    :type text: str
    :param config: Topic modeling configuration from the classifier model manifest.
    :type config: TopicModelingConfiguration
    :return: Prepared topic modeling document.
    :rtype: TopicModelingDocument
    """
    raw_text = text
    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError(f"Extracted text for item {item_id} is empty")
    min_characters = config.text_source.min_text_characters
    if min_characters is not None and len(cleaned) < min_characters:
        raise ValueError(
            f"Extracted text for item {item_id} is shorter than min_text_characters {min_characters}"
        )
    document = TopicModelingDocument(
        document_id=item_id,
        source_item_id=item_id,
        text=cleaned,
    )
    llm_report, llm_documents = _apply_llm_extraction(
        documents=[document],
        config=config.llm_extraction,
    )
    if llm_report.output_documents != 1:
        raise ValueError("Topic classifier classification requires exactly one processed document")
    entity_report, entity_documents = _apply_entity_removal(
        documents=llm_documents,
        config=config.entity_removal,
        cache_path=None,
    )
    if entity_report.output_documents != 1:
        raise ValueError(
            "Topic classifier classification requires exactly one entity-processed document"
        )
    lexical_report, lexical_documents = _apply_lexical_processing(
        documents=entity_documents,
        config=config.lexical_processing,
    )
    if lexical_report.output_documents != 1:
        raise ValueError("Topic classifier classification requires exactly one lexical document")
    return lexical_documents[0]


def _topic_candidate_probabilities(*, topic_model: Any, text: str) -> Any:
    approximation = getattr(topic_model, "approximate_distribution", None)
    if not callable(approximation):
        raise ValueError(
            "BERTopic model must support approximate_distribution for ranked topic candidates"
        )
    output = approximation([text])
    if isinstance(output, tuple):
        return output[0]
    return output


def _topic_candidates_from_probabilities(
    *,
    probabilities: Any,
    index: int,
    topic_map: Dict[str, Any],
    top_k: int,
) -> List[TopicClassifierTopicCandidate]:
    row = _probability_row(probabilities, index=index)
    if row is None:
        return []
    candidates: List[TopicClassifierTopicCandidate] = []
    for topic_id, score in row.items():
        candidate = _topic_candidate_for_topic(
            topic_id=topic_id,
            score=score,
            topic_map=topic_map,
            rank=1,
            mapped_only=True,
        )
        if candidate is not None:
            candidates.append(candidate)
    candidates.sort(
        key=lambda candidate: (
            candidate.score is None,
            -(candidate.score or 0.0),
            candidate.bertopic_topic_id,
        )
    )
    ranked = []
    for rank, candidate in enumerate(candidates[:top_k], start=1):
        ranked.append(candidate.model_copy(update={"rank": rank}))
    return ranked


def _topic_candidate_for_topic(
    *,
    topic_id: int,
    score: Optional[float],
    topic_map: Dict[str, Any],
    rank: int,
    mapped_only: bool,
) -> Optional[TopicClassifierTopicCandidate]:
    mapping = _mapping_by_bertopic_topic(topic_map).get(topic_id)
    discovered = _discovered_by_bertopic_topic(topic_map).get(topic_id)
    if mapped_only and mapping is None:
        return None
    evidence_source = mapping or discovered or {}
    return TopicClassifierTopicCandidate(
        rank=rank,
        bertopic_topic_id=topic_id,
        topic_uid=mapping.get("topic_uid") if mapping else None,
        display_name=mapping.get("display_name") if mapping else None,
        score=score,
        representative_evidence={
            "keywords": evidence_source.get("keywords", []),
            "document_ids": evidence_source.get("document_ids", []),
            "seed_item_ids": evidence_source.get("seed_item_ids", []),
            "discovered": mapping is None,
        },
    )


def _prediction_from_topic(
    *,
    classifier_id: str,
    item_id: str,
    model_version: str,
    topic_id: int,
    score: Optional[float],
    probabilities: Any,
    topic_map: Dict[str, Any],
    review_threshold: float,
    top_k: int,
    recorded: bool,
) -> TopicClassifierPrediction:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    topic_candidates = _topic_candidates_from_probabilities(
        probabilities=probabilities,
        index=0,
        topic_map=topic_map,
        top_k=top_k,
    )
    if not topic_candidates:
        assigned_candidate = _topic_candidate_for_topic(
            topic_id=topic_id,
            score=score,
            topic_map=topic_map,
            rank=1,
            mapped_only=False,
        )
        topic_candidates = [assigned_candidate] if assigned_candidate is not None else []
    primary_candidate = topic_candidates[0] if topic_candidates else None
    primary_score = primary_candidate.score if primary_candidate is not None else score
    primary_topic_uid = (
        primary_candidate.topic_uid
        if primary_candidate is not None
        and (primary_candidate.score is None or primary_candidate.score >= review_threshold)
        else None
    )
    primary_display_name = primary_candidate.display_name if primary_topic_uid is not None else None
    evidence_source = (
        primary_candidate.representative_evidence if primary_candidate is not None else {}
    )
    primary_topic_id = (
        primary_candidate.bertopic_topic_id if primary_candidate is not None else topic_id
    )
    review_recommended = primary_topic_uid is None or (
        primary_score is not None and primary_score < review_threshold
    )
    return TopicClassifierPrediction(
        classifier_id=classifier_id,
        item_id=item_id,
        model_version=model_version,
        bertopic_topic_id=primary_topic_id,
        topic_uid=primary_topic_uid,
        display_name=primary_display_name,
        score=primary_score,
        review_recommended=review_recommended,
        representative_evidence=evidence_source,
        topic_candidates=topic_candidates,
        recorded=recorded,
    )


def _save_bertopic_model(*, topic_model: Any, model_path: Path) -> None:
    model_path.mkdir(parents=True, exist_ok=True)
    if not hasattr(topic_model, "save"):
        raise ValueError("BERTopic model object does not support save")
    topic_model.save(str(model_path / "bertopic"))


def _load_bertopic_model(model_path: Path) -> Any:
    try:
        bertopic_module = importlib.import_module("bertopic")
        if not hasattr(bertopic_module, "BERTopic"):
            raise ImportError("BERTopic class is unavailable")
        BERTopic = bertopic_module.BERTopic
    except ImportError as import_error:
        raise ValueError(
            "Topic classifier classification requires BERTopic. "
            'Install it with pip install "biblicus[topic-modeling]".'
        ) from import_error
    if not hasattr(BERTopic, "load"):
        raise ValueError("BERTopic class does not support load")
    return BERTopic.load(str(model_path / "bertopic"))


def _load_model_bundle(*, corpus: Corpus, classifier_id: str) -> Dict[str, Any]:
    latest_path = (
        corpus.analysis_dir / TOPIC_CLASSIFIER_ANALYSIS_ID / f"{classifier_id}-latest.json"
    )
    if not latest_path.is_file():
        raise FileNotFoundError(f"Missing topic classifier latest pointer: {latest_path}")
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    model_version = str(latest["model_version"])
    run_dir = corpus.analysis_run_dir(
        analysis_id=TOPIC_CLASSIFIER_ANALYSIS_ID,
        snapshot_id=model_version,
    )
    model_manifest_path = run_dir / "model-manifest.json"
    topic_map_path = run_dir / "topic-map.json"
    if not model_manifest_path.is_file():
        raise FileNotFoundError(f"Missing topic classifier model manifest: {model_manifest_path}")
    if not topic_map_path.is_file():
        raise FileNotFoundError(f"Missing topic classifier topic map: {topic_map_path}")
    return {
        "run_dir": run_dir,
        "model_manifest": json.loads(model_manifest_path.read_text(encoding="utf-8")),
        "topic_map": json.loads(topic_map_path.read_text(encoding="utf-8")),
    }


def _build_extraction_snapshot_for_current_catalog(
    *, corpus: Corpus, model_manifest: Dict[str, Any]
) -> ExtractionSnapshotReference:
    snapshot_reference = ExtractionSnapshotReference.model_validate(
        model_manifest["extraction_snapshot"]
    )
    extraction_manifest = corpus.load_extraction_snapshot_manifest(
        extractor_id=snapshot_reference.extractor_id,
        snapshot_id=snapshot_reference.snapshot_id,
    )
    manifest = load_or_build_extraction_snapshot(
        corpus,
        extractor_id=extraction_manifest.configuration.extractor_id,
        configuration_name=extraction_manifest.configuration.name,
        configuration=dict(extraction_manifest.configuration.configuration),
        max_workers=1,
    )
    return ExtractionSnapshotReference(
        extractor_id=extraction_manifest.configuration.extractor_id,
        snapshot_id=manifest.snapshot_id,
    )


def _write_latest_pointer(*, corpus: Corpus, classifier_id: str, model_version: str) -> Path:
    latest_path = (
        corpus.analysis_dir / TOPIC_CLASSIFIER_ANALYSIS_ID / f"{classifier_id}-latest.json"
    )
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(latest_path, {"model_version": model_version, "created_at": utc_now_iso()})
    return latest_path


def _record_prediction(
    *,
    corpus: Corpus,
    classifier_id: str,
    prediction: TopicClassifierPrediction,
) -> None:
    path = corpus.meta_dir / "topic-classifiers" / classifier_id / "predictions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = prediction.model_dump(mode="json")
    payload["recorded_at"] = utc_now_iso()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _record_projection(
    *,
    corpus: Corpus,
    classifier_id: str,
    projection: TopicClassifierProjectionItem,
) -> None:
    path = corpus.meta_dir / "topic-classifiers" / classifier_id / "predictions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = projection.model_dump(mode="json")
    payload["recorded_at"] = utc_now_iso()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _selected_projection_item_ids(
    *,
    catalog_order: Sequence[str],
    catalog_items: Dict[str, Any],
    project_all: bool,
    item_ids: Sequence[str],
) -> List[str]:
    if project_all:
        ordered = list(catalog_order) if catalog_order else sorted(catalog_items)
        if not ordered:
            raise ValueError("Topic classifier projection target corpus has no items")
        return ordered

    missing = [item_id for item_id in item_ids if item_id not in catalog_items]
    if missing:
        raise KeyError(f"Unknown item id: {', '.join(missing)}")
    return list(item_ids)


def _is_projection_text_eligibility_error(error: ValueError) -> bool:
    message = str(error)
    return message.startswith("Missing extracted text for item ") or (
        message.startswith("Extracted text for item ")
        and (" is empty" in message or " is shorter than min_text_characters " in message)
    )


def _projection_summary(
    items: Sequence[TopicClassifierProjectionItem],
    skipped_items: Sequence[TopicClassifierProjectionSkippedItem],
) -> Dict[str, Any]:
    mapped_items = len([item for item in items if item.topic_uid is not None])
    review_recommended_items = len([item for item in items if item.review_recommended])
    return {
        "projected_items": len(items),
        "skipped_items": len(skipped_items),
        "mapped_items": mapped_items,
        "unmapped_items": len(items) - mapped_items,
        "review_recommended_items": review_recommended_items,
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _keywords_payload(topic: Optional[TopicModelingTopic]) -> List[Dict[str, Any]]:
    if topic is None:
        return []
    return [keyword.model_dump(mode="json") for keyword in topic.keywords]


def _mapping_by_bertopic_topic(topic_map: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {int(mapping["bertopic_topic_id"]): mapping for mapping in topic_map.get("mappings", [])}


def _discovered_by_bertopic_topic(topic_map: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {
        int(mapping["bertopic_topic_id"]): mapping for mapping in topic_map.get("discovered", [])
    }


def _probability_score(probabilities: Any, *, index: int, topic_id: int) -> Optional[float]:
    row = _probability_row(probabilities, index=index)
    if row is None:
        return None
    if topic_id in row:
        return row[topic_id]
    numeric_values = list(row.values())
    return max(numeric_values) if numeric_values else None


def _probability_row(probabilities: Any, *, index: int) -> Optional[Dict[int, float]]:
    if probabilities is None:
        return None
    value = probabilities.tolist() if hasattr(probabilities, "tolist") else probabilities
    try:
        row = value[index]
    except (TypeError, IndexError, KeyError):
        return None
    if isinstance(row, (int, float)):
        return {0: float(row)}
    if isinstance(row, dict):
        result: Dict[int, float] = {}
        for raw_topic_id, raw_score in row.items():
            if isinstance(raw_score, (int, float)):
                result[int(raw_topic_id)] = float(raw_score)
        return result
    if isinstance(row, SequenceCollection) and not isinstance(row, (str, bytes)):
        return {
            topic_id: float(entry)
            for topic_id, entry in enumerate(row)
            if isinstance(entry, (int, float))
        }
    return None


def _seed_count(manifest: TopicClassifierSeedManifest) -> int:
    return sum(len(topic.seed_item_ids) for topic in manifest.topics)


def _holdout_count(manifest: TopicClassifierSeedManifest) -> int:
    return sum(len(topic.holdout_item_ids) for topic in manifest.topics)
