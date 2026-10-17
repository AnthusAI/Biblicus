"""
Research-agent intake triage workflows.
"""

from __future__ import annotations

import json
import math
import mimetypes
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml
from pydantic import Field, field_validator

from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION, SIDECAR_SUFFIX
from .corpus import Corpus
from .frontmatter import parse_front_matter, render_front_matter
from .models import CatalogItem
from .retrieval import hash_text
from .time import utc_now_iso
from .topic_classifier import TopicClassifierPrediction, classify_topic_classifier_text

ACCEPTED_STATUS = "accepted"
PENDING_REVIEW_STATUS = "pending_review"
REJECTED_STATUS = "rejected"
RESEARCH_INTAKE_STATUSES = {ACCEPTED_STATUS, PENDING_REVIEW_STATUS, REJECTED_STATUS}
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_+-]*")
SIMILARITY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


class ResearchIntakeConfiguration(AnalysisSchemaModel):
    """
    Configuration for research-agent intake triage.

    :ivar schema_version: Configuration schema version.
    :vartype schema_version: int
    :ivar required_fields: Metadata field paths required for assessment.
    :vartype required_fields: list[str]
    :ivar metadata_text_fields: Metadata field paths used as classifier text.
    :vartype metadata_text_fields: list[str]
    :ivar accept_classifier_score: Minimum classifier score for acceptance.
    :vartype accept_classifier_score: float
    :ivar accept_corpus_similarity: Minimum corpus similarity for acceptance.
    :vartype accept_corpus_similarity: float
    :ivar reject_classifier_score: Classifier score below which low similarity is rejected.
    :vartype reject_classifier_score: float
    :ivar reject_corpus_similarity: Corpus similarity below which low classifier score is rejected.
    :vartype reject_corpus_similarity: float
    :ivar nearest_evidence_count: Count of nearest catalog items to include.
    :vartype nearest_evidence_count: int
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    required_fields: List[str] = Field(default_factory=lambda: ["title", "abstract"])
    metadata_text_fields: List[str] = Field(default_factory=lambda: ["title", "abstract"])
    accept_classifier_score: float = Field(default=0.6, ge=0.0, le=1.0)
    accept_corpus_similarity: float = Field(default=0.08, ge=0.0, le=1.0)
    reject_classifier_score: float = Field(default=0.2, ge=0.0, le=1.0)
    reject_corpus_similarity: float = Field(default=0.08, ge=0.0, le=1.0)
    nearest_evidence_count: int = Field(default=3, ge=1)

    @field_validator("required_fields", "metadata_text_fields")
    @classmethod
    def _validate_field_paths(cls, value: List[str]) -> List[str]:
        cleaned = [entry.strip() for entry in value if entry.strip()]
        if len(cleaned) != len(value):
            raise ValueError("field paths must contain non-empty values")
        duplicates = sorted({entry for entry in cleaned if cleaned.count(entry) > 1})
        if duplicates:
            raise ValueError("field paths contain duplicate values: " + ", ".join(duplicates))
        return cleaned


class ResearchIntakeOutput(AnalysisSchemaModel):
    """
    Output for a research-agent intake assessment or ingest command.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar corpus_path: Corpus path used by the command.
    :vartype corpus_path: str
    :ivar source_path: Candidate local source path.
    :vartype source_path: str
    :ivar item_id: Ingested item identifier, when an item was stored.
    :vartype item_id: str or None
    :ivar relpath: Ingested raw item relative path, when an item was stored.
    :vartype relpath: str or None
    :ivar sha256: Ingested raw item digest, when an item was stored.
    :vartype sha256: str or None
    :ivar classifier_id: Topic classifier identifier.
    :vartype classifier_id: str
    :ivar model_version: Topic classifier model version.
    :vartype model_version: str
    :ivar decision: Intake decision.
    :vartype decision: str
    :ivar reason: Human-readable decision reason.
    :vartype reason: str
    :ivar bertopic_topic_id: BERTopic topic identifier from the classifier.
    :vartype bertopic_topic_id: int
    :ivar topic_uid: Stable topic identity from the classifier map.
    :vartype topic_uid: str or None
    :ivar display_name: Topic display name from the classifier map.
    :vartype display_name: str or None
    :ivar classifier_score: Classifier confidence score when available.
    :vartype classifier_score: float or None
    :ivar corpus_similarity: Nearest corpus similarity score.
    :vartype corpus_similarity: float
    :ivar nearest_evidence_item_ids: Nearest eligible catalog item identifiers.
    :vartype nearest_evidence_item_ids: list[str]
    :ivar review_recommended: Whether review is recommended.
    :vartype review_recommended: bool
    :ivar curation: Curation metadata to store with accepted or pending items.
    :vartype curation: dict[str, Any]
    :ivar generated_at: Generation timestamp.
    :vartype generated_at: str
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    corpus_path: str
    source_path: str
    item_id: Optional[str] = None
    relpath: Optional[str] = None
    sha256: Optional[str] = None
    classifier_id: str
    model_version: str
    decision: str
    reason: str
    bertopic_topic_id: int
    topic_uid: Optional[str] = None
    display_name: Optional[str] = None
    classifier_score: Optional[float] = None
    corpus_similarity: float = Field(ge=0.0)
    nearest_evidence_item_ids: List[str] = Field(default_factory=list)
    review_recommended: bool
    curation: Dict[str, Any] = Field(default_factory=dict)
    generated_at: str


class ResearchIntakePendingItem(AnalysisSchemaModel):
    """
    Pending review item row.

    :ivar item_id: Corpus item identifier.
    :vartype item_id: str
    :ivar title: Item title.
    :vartype title: str or None
    :ivar source_uri: Item source uniform resource identifier.
    :vartype source_uri: str or None
    :ivar topic_uid: Predicted topic identity, when available.
    :vartype topic_uid: str or None
    :ivar display_name: Predicted topic display name, when available.
    :vartype display_name: str or None
    :ivar classifier_score: Classifier score, when available.
    :vartype classifier_score: float or None
    :ivar corpus_similarity: Nearest corpus similarity score.
    :vartype corpus_similarity: float or None
    :ivar created_at: Catalog creation timestamp.
    :vartype created_at: str
    """

    item_id: str
    title: Optional[str] = None
    source_uri: Optional[str] = None
    topic_uid: Optional[str] = None
    display_name: Optional[str] = None
    classifier_score: Optional[float] = None
    corpus_similarity: Optional[float] = None
    created_at: str


class ResearchIntakePendingOutput(AnalysisSchemaModel):
    """
    Output for the pending research intake list.

    :ivar schema_version: Output schema version.
    :vartype schema_version: int
    :ivar corpus_path: Corpus path used by the command.
    :vartype corpus_path: str
    :ivar generated_at: Generation timestamp.
    :vartype generated_at: str
    :ivar items: Pending review items.
    :vartype items: list[ResearchIntakePendingItem]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    corpus_path: str
    generated_at: str
    items: List[ResearchIntakePendingItem] = Field(default_factory=list)


def assess_research_intake_candidate(
    *,
    corpus: Corpus,
    classifier_id: str,
    source_path: Path,
    metadata: Dict[str, Any],
    configuration: ResearchIntakeConfiguration,
) -> ResearchIntakeOutput:
    """
    Assess a local candidate item without storing it in the corpus.

    :param corpus: Corpus whose classifier and catalog define relevance.
    :type corpus: Corpus
    :param classifier_id: Topic classifier identifier.
    :type classifier_id: str
    :param source_path: Local candidate file path.
    :type source_path: pathlib.Path
    :param metadata: Candidate metadata mapping.
    :type metadata: dict[str, Any]
    :param configuration: Research intake configuration.
    :type configuration: ResearchIntakeConfiguration
    :return: Intake assessment output.
    :rtype: ResearchIntakeOutput
    """
    resolved_source_path = _validate_local_source_path(source_path)
    _validate_candidate_metadata(metadata=metadata, configuration=configuration)
    candidate_text = metadata_text(metadata=metadata, fields=configuration.metadata_text_fields)
    candidate_identifier = "candidate-" + hash_text(candidate_text)[:16]
    prediction = classify_topic_classifier_text(
        corpus=corpus,
        classifier_id=classifier_id,
        text=candidate_text,
        item_id=candidate_identifier,
        review_threshold=configuration.reject_classifier_score,
    )
    nearest = nearest_corpus_evidence(
        corpus=corpus,
        candidate_text=candidate_text,
        limit=configuration.nearest_evidence_count,
    )
    corpus_similarity = nearest[0][1] if nearest else 0.0
    decision, reason = decide_research_intake(
        prediction=prediction,
        corpus_similarity=corpus_similarity,
        configuration=configuration,
    )
    generated_at = utc_now_iso()
    curation = _curation_for_assessment(
        decision=decision,
        reason=reason,
        prediction=prediction,
        corpus_similarity=corpus_similarity,
        nearest_evidence_item_ids=[item_id for item_id, _score in nearest],
        generated_at=generated_at,
    )
    return ResearchIntakeOutput(
        corpus_path=str(corpus.root),
        source_path=str(resolved_source_path),
        classifier_id=classifier_id,
        model_version=prediction.model_version,
        decision=decision,
        reason=reason,
        bertopic_topic_id=prediction.bertopic_topic_id,
        topic_uid=prediction.topic_uid,
        display_name=prediction.display_name,
        classifier_score=prediction.score,
        corpus_similarity=round(corpus_similarity, 6),
        nearest_evidence_item_ids=[item_id for item_id, _score in nearest],
        review_recommended=decision != ACCEPTED_STATUS or prediction.review_recommended,
        curation=curation,
        generated_at=generated_at,
    )


def ingest_research_intake_candidate(
    *,
    corpus: Corpus,
    classifier_id: str,
    source_path: Path,
    metadata: Dict[str, Any],
    configuration: ResearchIntakeConfiguration,
    source_uri: Optional[str],
    media_type: Optional[str],
    tags: Sequence[str],
) -> ResearchIntakeOutput:
    """
    Assess a candidate and ingest it when the decision permits storage.

    :param corpus: Corpus receiving accepted or pending items.
    :type corpus: Corpus
    :param classifier_id: Topic classifier identifier.
    :type classifier_id: str
    :param source_path: Local candidate file path.
    :type source_path: pathlib.Path
    :param metadata: Candidate metadata mapping.
    :type metadata: dict[str, Any]
    :param configuration: Research intake configuration.
    :type configuration: ResearchIntakeConfiguration
    :param source_uri: Optional provenance uniform resource identifier.
    :type source_uri: str or None
    :param media_type: Optional media type override.
    :type media_type: str or None
    :param tags: Additional tags to apply.
    :type tags: sequence[str]
    :return: Intake output, including item fields when stored.
    :rtype: ResearchIntakeOutput
    """
    assessment = assess_research_intake_candidate(
        corpus=corpus,
        classifier_id=classifier_id,
        source_path=source_path,
        metadata=metadata,
        configuration=configuration,
    )
    if assessment.decision == REJECTED_STATUS:
        return assessment

    resolved_source_path = Path(assessment.source_path)
    metadata_for_ingest = _metadata_with_curation(
        metadata=metadata,
        curation=assessment.curation,
    )
    ingest_result = corpus.ingest_item(
        resolved_source_path.read_bytes(),
        filename=resolved_source_path.name,
        media_type=_resolved_media_type(
            source_path=resolved_source_path,
            metadata=metadata_for_ingest,
            media_type=media_type,
        ),
        title=_metadata_string(metadata_for_ingest, "title"),
        tags=_dedupe([*tags, *_metadata_tags(metadata_for_ingest)]),
        metadata=metadata_for_ingest,
        source_uri=source_uri or resolved_source_path.as_uri(),
    )
    corpus.reindex()
    return assessment.model_copy(
        update={
            "item_id": ingest_result.item_id,
            "relpath": ingest_result.relpath,
            "sha256": ingest_result.sha256,
        }
    )


def decide_research_intake_item(
    *,
    corpus: Corpus,
    item_id: str,
    decision: str,
    topic_uid: Optional[str],
    tags_add: Sequence[str] = (),
    tags_remove: Sequence[str] = (),
    delete: bool = False,
) -> ResearchIntakeOutput:
    """
    Apply a human intake decision to an existing corpus item.

    :param corpus: Corpus containing the item.
    :type corpus: Corpus
    :param item_id: Item identifier to update.
    :type item_id: str
    :param decision: Human decision, ``accept`` or ``reject``.
    :type decision: str
    :param topic_uid: Optional reviewed topic identity.
    :type topic_uid: str or None
    :return: Updated intake output.
    :rtype: ResearchIntakeOutput
    """
    status = _status_from_human_decision(decision)
    item = corpus.get_item(item_id)

    if delete and status != REJECTED_STATUS:
        raise ValueError("--delete is only supported when rejecting an item")

    if delete:
        corpus.delete_item(item_id)
        corpus.reindex()
        return ResearchIntakeOutput(
            corpus_path=str(corpus.root),
            source_path="",
            item_id=item_id,
            relpath=None,
            sha256=None,
            classifier_id="",
            model_version="",
            decision=REJECTED_STATUS,
            reason="Human decision: rejected (deleted).",
            bertopic_topic_id=-1,
            topic_uid=None,
            display_name=None,
            classifier_score=None,
            corpus_similarity=0.0,
            nearest_evidence_item_ids=[],
            review_recommended=True,
            curation={},
            generated_at=utc_now_iso(),
        )

    metadata = _update_item_curation(
        corpus=corpus,
        item=item,
        status=status,
        topic_uid=topic_uid,
        tags_add=tags_add,
        tags_remove=tags_remove,
    )
    corpus.reindex()
    updated_item = corpus.get_item(item_id)
    assessment = metadata.get("curation", {}).get("intake_assessment", {})
    return ResearchIntakeOutput(
        corpus_path=str(corpus.root),
        source_path=str(corpus.root / updated_item.relpath),
        item_id=updated_item.id,
        relpath=updated_item.relpath,
        sha256=updated_item.sha256,
        classifier_id=str(assessment.get("classifier_id") or ""),
        model_version=str(assessment.get("model_version") or ""),
        decision=status,
        reason=str(assessment.get("reason") or f"Human decision: {status}"),
        bertopic_topic_id=int(assessment.get("bertopic_topic_id") or -1),
        topic_uid=topic_uid or _optional_string(assessment.get("topic_uid")),
        display_name=_optional_string(assessment.get("display_name")),
        classifier_score=_optional_float(assessment.get("classifier_score")),
        corpus_similarity=float(assessment.get("corpus_similarity") or 0.0),
        nearest_evidence_item_ids=[
            str(value) for value in assessment.get("nearest_evidence_item_ids", [])
        ],
        review_recommended=status != ACCEPTED_STATUS,
        curation=metadata.get("curation", {}),
        generated_at=utc_now_iso(),
    )


def list_pending_research_intake_items(*, corpus: Corpus) -> ResearchIntakePendingOutput:
    """
    List corpus items awaiting research intake review.

    :param corpus: Corpus to inspect.
    :type corpus: Corpus
    :return: Pending review output.
    :rtype: ResearchIntakePendingOutput
    """
    catalog = corpus.load_catalog()
    items: List[ResearchIntakePendingItem] = []
    for item in catalog.items.values():
        if _intake_status(item.metadata) != PENDING_REVIEW_STATUS:
            continue
        assessment = _intake_assessment(item.metadata)
        items.append(
            ResearchIntakePendingItem(
                item_id=item.id,
                title=item.title,
                source_uri=item.source_uri,
                topic_uid=_optional_string(assessment.get("topic_uid")),
                display_name=_optional_string(assessment.get("display_name")),
                classifier_score=_optional_float(assessment.get("classifier_score")),
                corpus_similarity=_optional_float(assessment.get("corpus_similarity")),
                created_at=item.created_at,
            )
        )
    items.sort(key=lambda entry: (entry.created_at, entry.item_id))
    return ResearchIntakePendingOutput(
        corpus_path=str(corpus.root),
        generated_at=utc_now_iso(),
        items=items,
    )


def research_intake_pending_markdown(output: ResearchIntakePendingOutput) -> str:
    """
    Render pending research intake items as Markdown.

    :param output: Pending list output.
    :type output: ResearchIntakePendingOutput
    :return: Markdown report.
    :rtype: str
    """
    lines = ["# Research Intake Pending Review", ""]
    if not output.items:
        lines.append("No pending review items.")
        return "\n".join(lines)
    lines.append("| Title | Item ID | Topic | Score | Similarity | Source |")
    lines.append("| --- | --- | --- | ---: | ---: | --- |")
    for item in output.items:
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(item.title or ""),
                    item.item_id,
                    _markdown_cell(item.display_name or item.topic_uid or ""),
                    _format_optional_float(item.classifier_score),
                    _format_optional_float(item.corpus_similarity),
                    _markdown_cell(item.source_uri or ""),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def metadata_text(*, metadata: Dict[str, Any], fields: Sequence[str]) -> str:
    """
    Build deterministic assessment text from selected metadata fields.

    :param metadata: Candidate metadata mapping.
    :type metadata: dict[str, Any]
    :param fields: Metadata field paths to include.
    :type fields: sequence[str]
    :return: Plain text assessment payload.
    :rtype: str
    """
    lines: List[str] = []
    for field_path in fields:
        value = _field_value(metadata, field_path)
        text = _field_value_text(value)
        if text:
            lines.append(text)
    return "\n".join(lines)


def decide_research_intake(
    *,
    prediction: TopicClassifierPrediction,
    corpus_similarity: float,
    configuration: ResearchIntakeConfiguration,
) -> Tuple[str, str]:
    """
    Decide the intake status from classifier and corpus-similarity signals.

    :param prediction: Topic classifier prediction.
    :type prediction: TopicClassifierPrediction
    :param corpus_similarity: Nearest eligible corpus similarity.
    :type corpus_similarity: float
    :param configuration: Intake threshold configuration.
    :type configuration: ResearchIntakeConfiguration
    :return: Decision and reason.
    :rtype: tuple[str, str]
    """
    score = prediction.score
    mapped = prediction.topic_uid is not None
    if (
        mapped
        and score is not None
        and score >= configuration.accept_classifier_score
        and corpus_similarity >= configuration.accept_corpus_similarity
    ):
        return (
            ACCEPTED_STATUS,
            "Classifier and corpus similarity passed acceptance thresholds.",
        )
    if corpus_similarity < configuration.reject_corpus_similarity and (
        score is None or not mapped or score < configuration.reject_classifier_score
    ):
        return REJECTED_STATUS, "Classifier and corpus similarity are below rejection thresholds."
    return (
        PENDING_REVIEW_STATUS,
        "Candidate requires human review before topic workflow eligibility.",
    )


def nearest_corpus_evidence(
    *, corpus: Corpus, candidate_text: str, limit: int
) -> List[Tuple[str, float]]:
    """
    Rank eligible corpus items by similarity to candidate metadata text.

    :param corpus: Corpus providing eligible catalog items.
    :type corpus: Corpus
    :param candidate_text: Candidate assessment text.
    :type candidate_text: str
    :param limit: Maximum number of evidence items.
    :type limit: int
    :return: Item identifier and similarity pairs.
    :rtype: list[tuple[str, float]]
    """
    candidate_vector = _term_counts(candidate_text)
    if not candidate_vector:
        return []
    scored: List[Tuple[str, float]] = []
    for item in corpus.load_catalog().items.values():
        if _intake_status(item.metadata) in {PENDING_REVIEW_STATUS, REJECTED_STATUS}:
            continue
        item_text = _catalog_similarity_text(item)
        score = _cosine_similarity(candidate_vector, _term_counts(item_text))
        scored.append((item.id, round(score, 6)))
    scored.sort(key=lambda entry: (-entry[1], entry[0]))
    return scored[:limit]


def _validate_local_source_path(path: Path) -> Path:
    path_text = str(path)
    path_posix = path.as_posix()
    if "://" in path_text or path_posix.startswith(("http:/", "https:/")):
        raise ValueError("Research intake requires a local file path")
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Research intake source file not found: {resolved}")
    return resolved


def _validate_candidate_metadata(
    *, metadata: Dict[str, Any], configuration: ResearchIntakeConfiguration
) -> None:
    for field_path in configuration.required_fields:
        value = _field_value(metadata, field_path)
        if not _field_value_text(value):
            raise ValueError(f"Research intake metadata requires field: {field_path}")
    text = metadata_text(metadata=metadata, fields=configuration.metadata_text_fields)
    if not text.strip():
        raise ValueError("Research intake metadata produced empty assessment text")


def _curation_for_assessment(
    *,
    decision: str,
    reason: str,
    prediction: TopicClassifierPrediction,
    corpus_similarity: float,
    nearest_evidence_item_ids: Sequence[str],
    generated_at: str,
) -> Dict[str, Any]:
    return {
        "intake_status": decision,
        "intake_assessment": {
            "decision": decision,
            "reason": reason,
            "classifier_id": prediction.classifier_id,
            "model_version": prediction.model_version,
            "bertopic_topic_id": prediction.bertopic_topic_id,
            "topic_uid": prediction.topic_uid,
            "display_name": prediction.display_name,
            "classifier_score": prediction.score,
            "corpus_similarity": round(corpus_similarity, 6),
            "nearest_evidence_item_ids": list(nearest_evidence_item_ids),
            "assessed_at": generated_at,
        },
    }


def _metadata_with_curation(
    *, metadata: Dict[str, Any], curation: Dict[str, Any]
) -> Dict[str, Any]:
    updated = dict(metadata)
    existing_curation = updated.get("curation")
    merged_curation = dict(existing_curation) if isinstance(existing_curation, dict) else {}
    merged_curation.update(curation)
    updated["curation"] = merged_curation
    return updated


def _resolved_media_type(
    *, source_path: Path, metadata: Dict[str, Any], media_type: Optional[str]
) -> str:
    if media_type is not None and media_type.strip():
        return media_type.strip()
    metadata_media_type = _metadata_string(metadata, "media_type")
    if metadata_media_type:
        return metadata_media_type
    guessed, _ = mimetypes.guess_type(source_path.name)
    return guessed or "application/octet-stream"


def _metadata_tags(metadata: Dict[str, Any]) -> List[str]:
    raw = metadata.get("tags")
    if raw is None:
        return []
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    if isinstance(raw, list):
        return [entry.strip() for entry in raw if isinstance(entry, str) and entry.strip()]
    raise ValueError("Research intake metadata tags must be a string or list of strings")


def _dedupe(values: Sequence[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            output.append(cleaned)
    return output


def _metadata_string(metadata: Dict[str, Any], key: str) -> Optional[str]:
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _status_from_human_decision(decision: str) -> str:
    normalized = decision.strip().lower()
    if normalized == "accept":
        return ACCEPTED_STATUS
    if normalized == "reject":
        return REJECTED_STATUS
    raise ValueError("Research intake decision must be accept or reject")


def _update_item_curation(
    *,
    corpus: Corpus,
    item: CatalogItem,
    status: str,
    topic_uid: Optional[str],
    tags_add: Sequence[str],
    tags_remove: Sequence[str],
) -> Dict[str, Any]:
    metadata, writer = _load_mutable_item_metadata(corpus=corpus, item=item)
    curation = metadata.get("curation")
    curation_payload = dict(curation) if isinstance(curation, dict) else {}
    assessment = curation_payload.get("intake_assessment")
    assessment_payload = dict(assessment) if isinstance(assessment, dict) else {}
    assessment_payload["human_decision"] = status
    assessment_payload["human_decided_at"] = utc_now_iso()
    if topic_uid:
        assessment_payload["reviewed_topic_uid"] = topic_uid
        curation_payload["reviewed_topic_uid"] = topic_uid
    curation_payload["intake_status"] = status
    curation_payload["intake_assessment"] = assessment_payload
    metadata["curation"] = curation_payload

    if tags_add or tags_remove:
        updated_tags = _update_tags(
            existing=_metadata_tags(metadata),
            tags_add=tags_add,
            tags_remove=tags_remove,
        )
        if updated_tags:
            metadata["tags"] = updated_tags
        elif "tags" in metadata:
            metadata.pop("tags", None)

    writer(metadata)
    return metadata


def _update_tags(
    *, existing: Sequence[str], tags_add: Sequence[str], tags_remove: Sequence[str]
) -> List[str]:
    cleaned_add = [tag.strip() for tag in tags_add if isinstance(tag, str) and tag.strip()]
    cleaned_remove = {tag.strip() for tag in tags_remove if isinstance(tag, str) and tag.strip()}
    tags = [tag for tag in existing if tag and tag not in cleaned_remove]
    for tag in cleaned_add:
        if tag not in tags:
            tags.append(tag)
    return _dedupe(tags)


def _load_mutable_item_metadata(*, corpus: Corpus, item: CatalogItem) -> Tuple[Dict[str, Any], Any]:
    content_path = corpus.root / item.relpath
    if item.media_type == "text/markdown":
        document = parse_front_matter(content_path.read_text(encoding="utf-8"))
        metadata = dict(document.metadata)

        def write_markdown(updated: Dict[str, Any]) -> None:
            content_path.write_text(
                render_front_matter(updated, document.body),
                encoding="utf-8",
            )

        return metadata, write_markdown

    sidecar_path = content_path.with_name(content_path.name + SIDECAR_SUFFIX)
    if sidecar_path.is_file():
        payload = yaml.safe_load(sidecar_path.read_text(encoding="utf-8")) or {}
    else:
        payload = dict(item.metadata)
    if not isinstance(payload, dict):
        raise ValueError(f"Sidecar metadata must be a mapping/object: {sidecar_path}")
    metadata = dict(payload)

    def write_sidecar(updated: Dict[str, Any]) -> None:
        sidecar_path.write_text(
            yaml.safe_dump(
                updated,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    return metadata, write_sidecar


def _field_value(metadata: Dict[str, Any], field_path: str) -> object:
    current: object = metadata
    for part in field_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _field_value_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        cleaned = [str(entry).strip() for entry in value if str(entry).strip()]
        return ", ".join(cleaned)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    if value is None:
        return ""
    return str(value).strip()


def _catalog_similarity_text(item: CatalogItem) -> str:
    parts = [
        item.title or "",
        _field_value_text(item.metadata.get("abstract")),
        _field_value_text(item.metadata.get("summary")),
        _field_value_text(item.metadata.get("description")),
    ]
    return "\n".join(part for part in parts if part)


def _term_counts(text: str) -> Counter[str]:
    return Counter(
        token for token in TOKEN_PATTERN.findall(text.lower()) if token not in SIMILARITY_STOPWORDS
    )


def _cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left).intersection(right)
    numerator = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _intake_status(metadata: Dict[str, Any]) -> Optional[str]:
    curation = metadata.get("curation")
    if not isinstance(curation, dict):
        return None
    status = curation.get("intake_status")
    if isinstance(status, str) and status.strip():
        return status.strip()
    return None


def _intake_assessment(metadata: Dict[str, Any]) -> Dict[str, Any]:
    curation = metadata.get("curation")
    if not isinstance(curation, dict):
        return {}
    assessment = curation.get("intake_assessment")
    return dict(assessment) if isinstance(assessment, dict) else {}


def _optional_string(value: object) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _optional_float(value: object) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _format_optional_float(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.3f}"


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
