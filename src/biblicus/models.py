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
    raw_dir: str = "raw"
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
    :ivar latest_run_id: Latest retrieval run identifier, if any.
    :vartype latest_run_id: str or None
    :ivar items: Mapping of item IDs to catalog entries.
    :vartype items: dict[str, CatalogItem]
    :ivar order: Display order of item IDs (most recent first).
    :vartype order: list[str]
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    generated_at: str
    corpus_uri: str
    raw_dir: str = "raw"
    latest_run_id: Optional[str] = None
    items: Dict[str, CatalogItem] = Field(default_factory=dict)
    order: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_schema_version(self) -> "CorpusCatalog":
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported catalog schema version: {self.schema_version}")
        return self


class ExtractionRunReference(BaseModel):
    """
    Reference to an extraction run.

    :ivar extractor_id: Extractor plugin identifier.
    :vartype extractor_id: str
    :ivar run_id: Extraction run identifier.
    :vartype run_id: str
    """

    model_config = ConfigDict(extra="forbid")

    extractor_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)

    def as_string(self) -> str:
        """
        Serialize the reference as a single string.

        :return: Reference in the form extractor_id:run_id.
        :rtype: str
        """
        return f"{self.extractor_id}:{self.run_id}"


def parse_extraction_run_reference(value: str) -> ExtractionRunReference:
    """
    Parse an extraction run reference in the form extractor_id:run_id.

    :param value: Raw reference string.
    :type value: str
    :return: Parsed extraction run reference.
    :rtype: ExtractionRunReference
    :raises ValueError: If the reference is not well formed.
    """
    if ":" not in value:
        raise ValueError("Extraction run reference must be extractor_id:run_id")
    extractor_id, run_id = value.split(":", 1)
    extractor_id = extractor_id.strip()
    run_id = run_id.strip()
    if not extractor_id or not run_id:
        raise ValueError(
            "Extraction run reference must be extractor_id:run_id with non-empty parts"
        )
    return ExtractionRunReference(extractor_id=extractor_id, run_id=run_id)


class ExtractionRunListEntry(BaseModel):
    """
    Summary entry for an extraction run stored in a corpus.

    :ivar extractor_id: Extractor plugin identifier.
    :vartype extractor_id: str
    :ivar run_id: Extraction run identifier.
    :vartype run_id: str
    :ivar recipe_id: Deterministic recipe identifier.
    :vartype recipe_id: str
    :ivar recipe_name: Human-readable recipe name.
    :vartype recipe_name: str
    :ivar catalog_generated_at: Catalog timestamp used for the run.
    :vartype catalog_generated_at: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for run creation.
    :vartype created_at: str
    :ivar stats: Run statistics.
    :vartype stats: dict[str, object]
    """

    model_config = ConfigDict(extra="forbid")

    extractor_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    recipe_id: str = Field(min_length=1)
    recipe_name: str = Field(min_length=1)
    catalog_generated_at: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    stats: Dict[str, object] = Field(default_factory=dict)


class QueryBudget(BaseModel):
    """
    Evidence selection budget for retrieval.

    :ivar max_total_items: Maximum number of evidence items to return.
    :vartype max_total_items: int
    :ivar max_total_characters: Optional maximum total characters across evidence text.
    :vartype max_total_characters: int or None
    :ivar max_items_per_source: Optional cap per source uniform resource identifier.
    :vartype max_items_per_source: int or None
    """

    model_config = ConfigDict(extra="forbid")

    max_total_items: int = Field(ge=1)
    max_total_characters: Optional[int] = Field(default=None, ge=1)
    max_items_per_source: Optional[int] = Field(default=None, ge=1)


class Evidence(BaseModel):
    """
    Structured retrieval evidence returned from a backend.

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
    :ivar recipe_id: Recipe identifier used to create the run.
    :vartype recipe_id: str
    :ivar run_id: Retrieval run identifier.
    :vartype run_id: str
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
    recipe_id: str
    run_id: str
    hash: Optional[str] = None

    @model_validator(mode="after")
    def _require_text_or_reference(self) -> "Evidence":
        has_text = isinstance(self.text, str) and self.text.strip()
        has_ref = isinstance(self.content_ref, str) and self.content_ref.strip()
        if not has_text and not has_ref:
            raise ValueError("Evidence must include either text or content_ref")
        return self


class RecipeManifest(BaseModel):
    """
    Reproducible configuration for a retrieval backend.

    :ivar recipe_id: Deterministic recipe identifier.
    :vartype recipe_id: str
    :ivar backend_id: Backend identifier for the recipe.
    :vartype backend_id: str
    :ivar name: Human-readable name for the recipe.
    :vartype name: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for recipe creation.
    :vartype created_at: str
    :ivar config: Backend-specific configuration values.
    :vartype config: dict[str, Any]
    :ivar description: Optional human description.
    :vartype description: str or None
    """

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    backend_id: str
    name: str
    created_at: str
    config: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class RetrievalRun(BaseModel):
    """
    Immutable record of a retrieval materialization or on-demand run.

    :ivar run_id: Unique run identifier.
    :vartype run_id: str
    :ivar recipe: Recipe manifest for this run.
    :vartype recipe: RecipeManifest
    :ivar corpus_uri: Canonical uniform resource identifier for the corpus root.
    :vartype corpus_uri: str
    :ivar catalog_generated_at: Catalog timestamp used for the run.
    :vartype catalog_generated_at: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for run creation.
    :vartype created_at: str
    :ivar artifact_paths: Relative paths to materialized artifacts.
    :vartype artifact_paths: list[str]
    :ivar stats: Backend-specific run statistics.
    :vartype stats: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str
    recipe: RecipeManifest
    corpus_uri: str
    catalog_generated_at: str
    created_at: str
    artifact_paths: List[str] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """
    Retrieval result bundle returned from a backend query.

    :ivar query_text: Query text issued against the backend.
    :vartype query_text: str
    :ivar budget: Evidence selection budget applied to results.
    :vartype budget: QueryBudget
    :ivar run_id: Retrieval run identifier.
    :vartype run_id: str
    :ivar recipe_id: Recipe identifier used for this query.
    :vartype recipe_id: str
    :ivar backend_id: Backend identifier used for this query.
    :vartype backend_id: str
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
    run_id: str
    recipe_id: str
    backend_id: str
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
    :ivar source_step_index: Optional pipeline step index where this text originated.
    :vartype source_step_index: int or None
    :ivar confidence: Optional confidence score from 0.0 to 1.0.
    :vartype confidence: float or None
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    producer_extractor_id: str = Field(min_length=1)
    source_step_index: Optional[int] = Field(default=None, ge=1)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ExtractionStepOutput(BaseModel):
    """
    In-memory representation of a pipeline step output for a single item.

    :ivar step_index: One-based pipeline step index.
    :vartype step_index: int
    :ivar extractor_id: Extractor identifier for the step.
    :vartype extractor_id: str
    :ivar status: Step status, extracted, skipped, or errored.
    :vartype status: str
    :ivar text: Extracted text content, when produced.
    :vartype text: str or None
    :ivar text_characters: Character count of the extracted text.
    :vartype text_characters: int
    :ivar producer_extractor_id: Extractor identifier that produced the text content.
    :vartype producer_extractor_id: str or None
    :ivar source_step_index: Optional step index that supplied the text for selection-style extractors.
    :vartype source_step_index: int or None
    :ivar confidence: Optional confidence score from 0.0 to 1.0.
    :vartype confidence: float or None
    :ivar error_type: Optional error type name for errored steps.
    :vartype error_type: str or None
    :ivar error_message: Optional error message for errored steps.
    :vartype error_message: str or None
    """

    model_config = ConfigDict(extra="forbid")

    step_index: int = Field(ge=1)
    extractor_id: str
    status: str
    text: Optional[str] = None
    text_characters: int = Field(default=0, ge=0)
    producer_extractor_id: Optional[str] = None
    source_step_index: Optional[int] = Field(default=None, ge=1)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
