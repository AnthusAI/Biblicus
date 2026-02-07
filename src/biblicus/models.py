"""
Pydantic models for Biblicus domain concepts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .constants import SCHEMA_VERSION
from .hooks import HookSpec


class CorpusConfig(BaseModel):
    """
    Canonical on-disk config for a local Biblicus corpus.

    :ivar schema_version: Version of the corpus config schema.
    :vartype schema_version: int
    :ivar created_at: International Organization for Standardization 8601 timestamp for corpus creation.
    :vartype created_at: str
    :ivar corpus_uri: Canonical uniform resource identifier for the corpus root.
    :vartype corpus_uri: str
    :ivar raw_dir: Relative path to the raw items folder.
    :vartype raw_dir: str
    :ivar notes: Optional free-form notes for operators.
    :vartype notes: dict[str, Any] or None
    :ivar hooks: Optional hook specifications for corpus lifecycle events.
    :vartype hooks: list[HookSpec] or None
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    created_at: str
    corpus_uri: str
    raw_dir: str = "."
    notes: Optional[Dict[str, Any]] = None
    hooks: Optional[List[HookSpec]] = None

    @model_validator(mode="after")
    def _enforce_schema_version(self) -> "CorpusConfig":
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported corpus config schema version: {self.schema_version}")
        return self


class IngestResult(BaseModel):
    """
    Minimal summary for an ingestion event.

    :ivar item_id: Universally unique identifier assigned to the ingested item.
    :vartype item_id: str
    :ivar relpath: Relative path to the raw item file.
    :vartype relpath: str
    :ivar sha256: Secure Hash Algorithm 256 digest of the stored bytes.
    :vartype sha256: str
    """

    model_config = ConfigDict(extra="forbid")

    item_id: str
    relpath: str
    sha256: str


class CatalogItem(BaseModel):
    """
    Catalog entry derived from a raw corpus item.

    :ivar id: Universally unique identifier of the item.
    :vartype id: str
    :ivar relpath: Relative path to the raw item file.
    :vartype relpath: str
    :ivar sha256: Secure Hash Algorithm 256 digest of the stored bytes.
    :vartype sha256: str
    :ivar bytes: Size of the raw item in bytes.
    :vartype bytes: int
    :ivar media_type: Internet Assigned Numbers Authority media type for the item.
    :vartype media_type: str
    :ivar title: Optional human title extracted from metadata.
    :vartype title: str or None
    :ivar tags: Tags extracted or supplied for the item.
    :vartype tags: list[str]
    :ivar metadata: Merged front matter or sidecar metadata.
    :vartype metadata: dict[str, Any]
    :ivar created_at: International Organization for Standardization 8601 timestamp when the item was first indexed.
    :vartype created_at: str
    :ivar source_uri: Optional source uniform resource identifier used at ingestion time.
    :vartype source_uri: str or None
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    relpath: str
    sha256: str
    bytes: int = Field(ge=0)
    media_type: str
    title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    source_uri: Optional[str] = None


class CorpusCatalog(BaseModel):
    """
    Snapshot of the derived corpus catalog.

    :ivar schema_version: Version of the catalog schema.
    :vartype schema_version: int
    :ivar generated_at: International Organization for Standardization 8601 timestamp of catalog generation.
    :vartype generated_at: str
    :ivar corpus_uri: Canonical uniform resource identifier for the corpus root.
    :vartype corpus_uri: str
    :ivar raw_dir: Relative path to the raw items folder.
    :vartype raw_dir: str
    :ivar latest_run_id: Latest extraction run identifier, if any.
    :vartype latest_run_id: str or None
    :ivar latest_snapshot_id: Latest retrieval snapshot identifier, if any.
    :vartype latest_snapshot_id: str or None
    :ivar items: Mapping of item IDs to catalog entries.
    :vartype items: dict[str, CatalogItem]
    :ivar order: Display order of item IDs (most recent first).
    :vartype order: list[str]
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    generated_at: str
    corpus_uri: str
    raw_dir: str = "."
    latest_run_id: Optional[str] = None
    latest_snapshot_id: Optional[str] = None
    items: Dict[str, CatalogItem] = Field(default_factory=dict)
    order: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_schema_version(self) -> "CorpusCatalog":
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported catalog schema version: {self.schema_version}")
        return self


class ExtractionSnapshotReference(BaseModel):
    """
    Reference to an extraction snapshot.

    :ivar extractor_id: Extractor plugin identifier.
    :vartype extractor_id: str
    :ivar snapshot_id: Extraction snapshot identifier.
    :vartype snapshot_id: str
    """

    model_config = ConfigDict(extra="forbid")

    extractor_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)

    def as_string(self) -> str:
        """
        Serialize the reference as a single string.

        :return: Reference in the form extractor_id:snapshot_id.
        :rtype: str
        """
        return f"{self.extractor_id}:{self.snapshot_id}"


def parse_extraction_snapshot_reference(value: str) -> ExtractionSnapshotReference:
    """
    Parse an extraction snapshot reference in the form extractor_id:snapshot_id.

    :param value: Raw reference string.
    :type value: str
    :return: Parsed extraction snapshot reference.
    :rtype: ExtractionSnapshotReference
    :raises ValueError: If the reference is not well formed.
    """
    if ":" not in value:
        raise ValueError("Extraction snapshot reference must be extractor_id:snapshot_id")
    extractor_id, snapshot_id = value.split(":", 1)
    extractor_id = extractor_id.strip()
    snapshot_id = snapshot_id.strip()
    if not extractor_id or not snapshot_id:
        raise ValueError(
            "Extraction snapshot reference must be extractor_id:snapshot_id with non-empty parts"
        )
    return ExtractionSnapshotReference(extractor_id=extractor_id, snapshot_id=snapshot_id)


class ExtractionSnapshotListEntry(BaseModel):
    """
    Summary entry for an extraction snapshot stored in a corpus.

    :ivar extractor_id: Extractor plugin identifier.
    :vartype extractor_id: str
    :ivar snapshot_id: Extraction snapshot identifier.
    :vartype snapshot_id: str
    :ivar configuration_id: Deterministic configuration identifier.
    :vartype configuration_id: str
    :ivar configuration_name: Human-readable configuration name.
    :vartype configuration_name: str
    :ivar catalog_generated_at: Catalog timestamp used for the snapshot.
    :vartype catalog_generated_at: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for snapshot creation.
    :vartype created_at: str
    :ivar stats: Snapshot statistics.
    :vartype stats: dict[str, object]
    """

    model_config = ConfigDict(extra="forbid")

    extractor_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    configuration_id: str = Field(min_length=1)
    configuration_name: str = Field(min_length=1)
    catalog_generated_at: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    stats: Dict[str, object] = Field(default_factory=dict)


class QueryBudget(BaseModel):
    """
    Evidence selection budget for retrieval.

    The budget constrains the *returned* evidence. It intentionally does not
    change how a backend scores candidates, only how many evidence items are
    selected and how much text is allowed through.

    :ivar max_total_items: Maximum number of evidence items to return.
    :vartype max_total_items: int
    :ivar offset: Number of ranked candidates to skip before selecting evidence.
        This enables simple pagination by re-running the same query with a
        higher offset.
    :vartype offset: int
    :ivar maximum_total_characters: Optional maximum total characters across evidence text.
    :vartype maximum_total_characters: int or None
    :ivar max_items_per_source: Optional cap per source uniform resource identifier.
    :vartype max_items_per_source: int or None
    """

    model_config = ConfigDict(extra="forbid")

    max_total_items: int = Field(ge=1)
    offset: int = Field(default=0, ge=0)
    maximum_total_characters: Optional[int] = Field(default=None, ge=1)
    max_items_per_source: Optional[int] = Field(default=None, ge=1)


class Evidence(BaseModel):
    """
    Structured retrieval evidence returned from a retriever.

    :ivar item_id: Item identifier that produced the evidence.
    :vartype item_id: str
    :ivar source_uri: Source uniform resource identifier from ingestion metadata.
    :vartype source_uri: str or None
    :ivar media_type: Media type for the evidence item.
    :vartype media_type: str
    :ivar score: Retrieval score (higher is better).
    :vartype score: float
    :ivar rank: Rank within the final evidence list (1-based).
    :vartype rank: int
    :ivar text: Optional text payload for the evidence.
    :vartype text: str or None
    :ivar content_ref: Optional reference for non-text content.
    :vartype content_ref: str or None
    :ivar span_start: Optional start offset in the source text.
    :vartype span_start: int or None
    :ivar span_end: Optional end offset in the source text.
    :vartype span_end: int or None
    :ivar stage: Retrieval stage label (for example, scan, full-text search, rerank).
    :vartype stage: str
    :ivar stage_scores: Optional per-stage scores for multi-stage retrieval.
    :vartype stage_scores: dict[str, float] or None
    :ivar configuration_id: Configuration identifier used to create the snapshot.
    :vartype configuration_id: str
    :ivar snapshot_id: Retrieval snapshot identifier.
    :vartype snapshot_id: str
    :ivar metadata: Optional metadata payload from the catalog item.
    :vartype metadata: dict[str, Any]
    :ivar hash: Optional content hash for provenance.
    :vartype hash: str or None
    """

    model_config = ConfigDict(extra="forbid")

    item_id: str
    source_uri: Optional[str] = None
    media_type: str
    score: float
    rank: int = Field(ge=1)
    text: Optional[str] = None
    content_ref: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    stage: str
    stage_scores: Optional[Dict[str, float]] = None
    configuration_id: str
    snapshot_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    hash: Optional[str] = None

    @model_validator(mode="after")
    def _require_text_or_reference(self) -> "Evidence":
        has_text = isinstance(self.text, str) and self.text.strip()
        has_ref = isinstance(self.content_ref, str) and self.content_ref.strip()
        if not has_text and not has_ref:
            raise ValueError("Evidence must include either text or content_ref")
        return self


class ConfigurationManifest(BaseModel):
    """
    Reproducible configuration for a retriever.

    :ivar configuration_id: Deterministic configuration identifier.
    :vartype configuration_id: str
    :ivar retriever_id: Retriever identifier for the configuration.
    :vartype retriever_id: str
    :ivar name: Human-readable name for the configuration.
    :vartype name: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for configuration creation.
    :vartype created_at: str
    :ivar configuration: Retriever-specific configuration values.
    :vartype configuration: dict[str, Any]
    :ivar description: Optional human description.
    :vartype description: str or None
    """

    model_config = ConfigDict(extra="forbid")

    configuration_id: str
    retriever_id: str
    name: str
    created_at: str
    configuration: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class RetrievalSnapshot(BaseModel):
    """
    Immutable record of a retrieval snapshot.

    :ivar snapshot_id: Unique snapshot identifier.
    :vartype snapshot_id: str
    :ivar configuration: Configuration manifest for this snapshot.
    :vartype configuration: ConfigurationManifest
    :ivar corpus_uri: Canonical uniform resource identifier for the corpus root.
    :vartype corpus_uri: str
    :ivar catalog_generated_at: Catalog timestamp used for the snapshot.
    :vartype catalog_generated_at: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for snapshot creation.
    :vartype created_at: str
    :ivar snapshot_artifacts: Relative paths to materialized artifacts.
    :vartype snapshot_artifacts: list[str]
    :ivar stats: Retriever-specific snapshot statistics.
    :vartype stats: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    configuration: ConfigurationManifest
    corpus_uri: str
    catalog_generated_at: str
    created_at: str
    snapshot_artifacts: List[str] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """
    Retrieval result bundle returned from a retriever query.

    :ivar query_text: Query text issued against the backend.
    :vartype query_text: str
    :ivar budget: Evidence selection budget applied to results.
    :vartype budget: QueryBudget
    :ivar snapshot_id: Retrieval snapshot identifier.
    :vartype snapshot_id: str
    :ivar configuration_id: Configuration identifier used for this query.
    :vartype configuration_id: str
    :ivar retriever_id: Retriever identifier used for this query.
    :vartype retriever_id: str
    :ivar generated_at: International Organization for Standardization 8601 timestamp for the query result.
    :vartype generated_at: str
    :ivar evidence: Evidence objects selected under the budget.
    :vartype evidence: list[Evidence]
    :ivar stats: Backend-specific query statistics.
    :vartype stats: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    query_text: str
    budget: QueryBudget
    snapshot_id: str
    configuration_id: str
    retriever_id: str
    generated_at: str
    evidence: List[Evidence] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


class ExtractedText(BaseModel):
    """
    Text payload produced by an extractor plugin.

    :ivar text: Extracted text content.
    :vartype text: str
    :ivar producer_extractor_id: Extractor identifier that produced this text.
    :vartype producer_extractor_id: str
    :ivar source_stage_index: Optional pipeline stage index where this text originated.
    :vartype source_stage_index: int or None
    :ivar confidence: Optional confidence score from 0.0 to 1.0.
    :vartype confidence: float or None
    :ivar metadata: Optional structured metadata for passing data between pipeline stages.
    :vartype metadata: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    producer_extractor_id: str = Field(min_length=1)
    source_stage_index: Optional[int] = Field(default=None, ge=1)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractionStageOutput(BaseModel):
    """
    In-memory representation of a pipeline stage output for a single item.

    :ivar stage_index: One-based pipeline stage index.
    :vartype stage_index: int
    :ivar extractor_id: Extractor identifier for the stage.
    :vartype extractor_id: str
    :ivar status: Stage status, extracted, skipped, or errored.
    :vartype status: str
    :ivar text: Extracted text content, when produced.
    :vartype text: str or None
    :ivar text_characters: Character count of the extracted text.
    :vartype text_characters: int
    :ivar producer_extractor_id: Extractor identifier that produced the text content.
    :vartype producer_extractor_id: str or None
    :ivar source_stage_index: Optional stage index that supplied the text for selection-style extractors.
    :vartype source_stage_index: int or None
    :ivar confidence: Optional confidence score from 0.0 to 1.0.
    :vartype confidence: float or None
    :ivar metadata: Optional structured metadata for passing data between pipeline stages.
    :vartype metadata: dict[str, Any]
    :ivar error_type: Optional error type name for errored stages.
    :vartype error_type: str or None
    :ivar error_message: Optional error message for errored stages.
    :vartype error_message: str or None
    """

    model_config = ConfigDict(extra="forbid")

    stage_index: int = Field(ge=1)
    extractor_id: str
    status: str
    text: Optional[str] = None
    text_characters: int = Field(default=0, ge=0)
    producer_extractor_id: Optional[str] = None
    source_stage_index: Optional[int] = Field(default=None, ge=1)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
