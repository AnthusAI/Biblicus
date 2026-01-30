"""
Pydantic models for analysis pipelines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from ..constants import ANALYSIS_SCHEMA_VERSION
from ..models import ExtractionRunReference
from .llm import LlmClientConfig
from .schema import AnalysisSchemaModel


class AnalysisRecipeManifest(AnalysisSchemaModel):
    """
    Reproducible configuration for an analysis pipeline.

    :ivar recipe_id: Deterministic recipe identifier.
    :vartype recipe_id: str
    :ivar analysis_id: Analysis backend identifier.
    :vartype analysis_id: str
    :ivar name: Human-readable recipe name.
    :vartype name: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for recipe creation.
    :vartype created_at: str
    :ivar config: Analysis-specific configuration values.
    :vartype config: dict[str, Any]
    :ivar description: Optional human description.
    :vartype description: str or None
    """

    recipe_id: str
    analysis_id: str
    name: str
    created_at: str
    config: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class AnalysisRunInput(AnalysisSchemaModel):
    """
    Inputs required to execute an analysis run.

    :ivar extraction_run: Extraction run reference for analysis inputs.
    :vartype extraction_run: biblicus.models.ExtractionRunReference
    """

    extraction_run: ExtractionRunReference


class AnalysisRunManifest(AnalysisSchemaModel):
    """
    Immutable record of an analysis run.

    :ivar run_id: Unique run identifier.
    :vartype run_id: str
    :ivar recipe: Recipe manifest for this run.
    :vartype recipe: AnalysisRecipeManifest
    :ivar corpus_uri: Canonical uniform resource identifier for the corpus root.
    :vartype corpus_uri: str
    :ivar catalog_generated_at: Catalog timestamp used for the run.
    :vartype catalog_generated_at: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for run creation.
    :vartype created_at: str
    :ivar input: Inputs used for this analysis run.
    :vartype input: AnalysisRunInput
    :ivar artifact_paths: Relative paths to materialized artifacts.
    :vartype artifact_paths: list[str]
    :ivar stats: Analysis-specific run statistics.
    :vartype stats: dict[str, Any]
    """

    run_id: str
    recipe: AnalysisRecipeManifest
    corpus_uri: str
    catalog_generated_at: str
    created_at: str
    input: AnalysisRunInput
    artifact_paths: List[str] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


class TopicModelingTextSourceConfig(AnalysisSchemaModel):
    """
    Configuration for text collection within topic modeling.

    :ivar sample_size: Optional sample size for text collection.
    :vartype sample_size: int or None
    :ivar min_text_characters: Optional minimum character count for text inclusion.
    :vartype min_text_characters: int or None
    """

    sample_size: Optional[int] = Field(default=None, ge=1)
    min_text_characters: Optional[int] = Field(default=None, ge=1)


class TopicModelingLlmExtractionMethod(str, Enum):
    """
    LLM extraction method identifiers.
    """

    SINGLE = "single"
    ITEMIZE = "itemize"


class TopicModelingLlmExtractionConfig(AnalysisSchemaModel):
    """
    Configuration for LLM-based extraction within topic modeling.

    :ivar enabled: Whether LLM extraction is enabled.
    :vartype enabled: bool
    :ivar method: Extraction method, single or itemize.
    :vartype method: TopicModelingLlmExtractionMethod
    :ivar client: LLM client configuration.
    :vartype client: LlmClientConfig or None
    :ivar prompt_template: Prompt template containing the {text} placeholder.
    :vartype prompt_template: str or None
    :ivar system_prompt: Optional system prompt.
    :vartype system_prompt: str or None
    """

    enabled: bool = Field(default=False)
    method: TopicModelingLlmExtractionMethod = Field(default=TopicModelingLlmExtractionMethod.SINGLE)
    client: Optional[LlmClientConfig] = None
    prompt_template: Optional[str] = None
    system_prompt: Optional[str] = None

    @field_validator("method", mode="before")
    @classmethod
    def _parse_method(cls, value: object) -> TopicModelingLlmExtractionMethod:
        if isinstance(value, TopicModelingLlmExtractionMethod):
            return value
        if isinstance(value, str):
            return TopicModelingLlmExtractionMethod(value)
        raise ValueError("llm_extraction.method must be a string or TopicModelingLlmExtractionMethod")

    @model_validator(mode="after")
    def _validate_requirements(self) -> "TopicModelingLlmExtractionConfig":
        if not self.enabled:
            return self
        if self.client is None:
            raise ValueError("llm_extraction.client is required when enabled")
        if self.prompt_template is None:
            raise ValueError("llm_extraction.prompt_template is required when enabled")
        if "{text}" not in self.prompt_template:
            raise ValueError("llm_extraction.prompt_template must include {text}")
        return self


class TopicModelingLexicalProcessingConfig(AnalysisSchemaModel):
    """
    Configuration for lexical processing within topic modeling.

    :ivar enabled: Whether lexical processing is enabled.
    :vartype enabled: bool
    :ivar lowercase: Whether to lowercase text.
    :vartype lowercase: bool
    :ivar strip_punctuation: Whether to remove punctuation.
    :vartype strip_punctuation: bool
    :ivar collapse_whitespace: Whether to normalize whitespace.
    :vartype collapse_whitespace: bool
    """

    enabled: bool = Field(default=False)
    lowercase: bool = Field(default=True)
    strip_punctuation: bool = Field(default=False)
    collapse_whitespace: bool = Field(default=True)


class TopicModelingBerTopicConfig(AnalysisSchemaModel):
    """
    Configuration for BERTopic analysis.

    :ivar parameters: Parameters forwarded to the BERTopic constructor.
    :vartype parameters: dict[str, Any]
    """

    parameters: Dict[str, Any] = Field(default_factory=dict)


class TopicModelingLlmFineTuningConfig(AnalysisSchemaModel):
    """
    Configuration for LLM-based topic labeling.

    :ivar enabled: Whether LLM topic labeling is enabled.
    :vartype enabled: bool
    :ivar client: LLM client configuration.
    :vartype client: LlmClientConfig or None
    :ivar prompt_template: Prompt template containing {keywords} and {documents} placeholders.
    :vartype prompt_template: str or None
    :ivar system_prompt: Optional system prompt.
    :vartype system_prompt: str or None
    :ivar max_keywords: Maximum number of keywords to include in prompts.
    :vartype max_keywords: int
    :ivar max_documents: Maximum number of documents to include in prompts.
    :vartype max_documents: int
    """

    enabled: bool = Field(default=False)
    client: Optional[LlmClientConfig] = None
    prompt_template: Optional[str] = None
    system_prompt: Optional[str] = None
    max_keywords: int = Field(default=8, ge=1)
    max_documents: int = Field(default=5, ge=1)

    @model_validator(mode="after")
    def _validate_requirements(self) -> "TopicModelingLlmFineTuningConfig":
        if not self.enabled:
            return self
        if self.client is None:
            raise ValueError("llm_fine_tuning.client is required when enabled")
        if self.prompt_template is None:
            raise ValueError("llm_fine_tuning.prompt_template is required when enabled")
        if "{keywords}" not in self.prompt_template or "{documents}" not in self.prompt_template:
            raise ValueError(
                "llm_fine_tuning.prompt_template must include {keywords} and {documents}"
            )
        return self


class TopicModelingRecipeConfig(AnalysisSchemaModel):
    """
    Recipe configuration for topic modeling analysis.

    :ivar schema_version: Analysis schema version.
    :vartype schema_version: int
    :ivar text_source: Text collection configuration.
    :vartype text_source: TopicModelingTextSourceConfig
    :ivar llm_extraction: LLM extraction configuration.
    :vartype llm_extraction: TopicModelingLlmExtractionConfig
    :ivar lexical_processing: Lexical processing configuration.
    :vartype lexical_processing: TopicModelingLexicalProcessingConfig
    :ivar bertopic_analysis: BERTopic configuration.
    :vartype bertopic_analysis: TopicModelingBerTopicConfig
    :ivar llm_fine_tuning: LLM fine-tuning configuration.
    :vartype llm_fine_tuning: TopicModelingLlmFineTuningConfig
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    text_source: TopicModelingTextSourceConfig = Field(default_factory=TopicModelingTextSourceConfig)
    llm_extraction: TopicModelingLlmExtractionConfig = Field(
        default_factory=TopicModelingLlmExtractionConfig
    )
    lexical_processing: TopicModelingLexicalProcessingConfig = Field(
        default_factory=TopicModelingLexicalProcessingConfig
    )
    bertopic_analysis: TopicModelingBerTopicConfig = Field(
        default_factory=TopicModelingBerTopicConfig
    )
    llm_fine_tuning: TopicModelingLlmFineTuningConfig = Field(
        default_factory=TopicModelingLlmFineTuningConfig
    )

    @model_validator(mode="after")
    def _validate_schema_version(self) -> "TopicModelingRecipeConfig":
        if self.schema_version != ANALYSIS_SCHEMA_VERSION:
            raise ValueError(f"Unsupported analysis schema version: {self.schema_version}")
        return self


class TopicModelingStageStatus(str, Enum):
    """
    Stage status values for topic modeling.
    """

    COMPLETE = "complete"
    SKIPPED = "skipped"
    FAILED = "failed"


class TopicModelingTextCollectionReport(AnalysisSchemaModel):
    """
    Report for the text collection stage.

    :ivar status: Stage status.
    :vartype status: TopicModelingStageStatus
    :ivar source_items: Count of source items inspected.
    :vartype source_items: int
    :ivar documents: Count of documents produced.
    :vartype documents: int
    :ivar sample_size: Optional sample size.
    :vartype sample_size: int or None
    :ivar min_text_characters: Optional minimum character threshold.
    :vartype min_text_characters: int or None
    :ivar empty_texts: Count of empty text inputs.
    :vartype empty_texts: int
    :ivar skipped_items: Count of skipped items.
    :vartype skipped_items: int
    :ivar warnings: Warning messages.
    :vartype warnings: list[str]
    :ivar errors: Error messages.
    :vartype errors: list[str]
    """

    status: TopicModelingStageStatus
    source_items: int = Field(ge=0)
    documents: int = Field(ge=0)
    sample_size: Optional[int] = None
    min_text_characters: Optional[int] = None
    empty_texts: int = Field(ge=0)
    skipped_items: int = Field(ge=0)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class TopicModelingLlmExtractionReport(AnalysisSchemaModel):
    """
    Report for the LLM extraction stage.

    :ivar status: Stage status.
    :vartype status: TopicModelingStageStatus
    :ivar method: Extraction method used.
    :vartype method: TopicModelingLlmExtractionMethod
    :ivar input_documents: Count of input documents.
    :vartype input_documents: int
    :ivar output_documents: Count of output documents.
    :vartype output_documents: int
    :ivar warnings: Warning messages.
    :vartype warnings: list[str]
    :ivar errors: Error messages.
    :vartype errors: list[str]
    """

    status: TopicModelingStageStatus
    method: TopicModelingLlmExtractionMethod
    input_documents: int = Field(ge=0)
    output_documents: int = Field(ge=0)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class TopicModelingLexicalProcessingReport(AnalysisSchemaModel):
    """
    Report for the lexical processing stage.

    :ivar status: Stage status.
    :vartype status: TopicModelingStageStatus
    :ivar input_documents: Count of input documents.
    :vartype input_documents: int
    :ivar output_documents: Count of output documents.
    :vartype output_documents: int
    :ivar lowercase: Whether lowercase normalization was applied.
    :vartype lowercase: bool
    :ivar strip_punctuation: Whether punctuation was removed.
    :vartype strip_punctuation: bool
    :ivar collapse_whitespace: Whether whitespace was normalized.
    :vartype collapse_whitespace: bool
    """

    status: TopicModelingStageStatus
    input_documents: int = Field(ge=0)
    output_documents: int = Field(ge=0)
    lowercase: bool
    strip_punctuation: bool
    collapse_whitespace: bool


class TopicModelingBerTopicReport(AnalysisSchemaModel):
    """
    Report for the BERTopic analysis stage.

    :ivar status: Stage status.
    :vartype status: TopicModelingStageStatus
    :ivar topic_count: Count of topics discovered.
    :vartype topic_count: int
    :ivar document_count: Count of documents analyzed.
    :vartype document_count: int
    :ivar parameters: BERTopic configuration parameters.
    :vartype parameters: dict[str, Any]
    :ivar warnings: Warning messages.
    :vartype warnings: list[str]
    :ivar errors: Error messages.
    :vartype errors: list[str]
    """

    status: TopicModelingStageStatus
    topic_count: int = Field(ge=0)
    document_count: int = Field(ge=0)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class TopicModelingLlmFineTuningReport(AnalysisSchemaModel):
    """
    Report for the LLM fine-tuning stage.

    :ivar status: Stage status.
    :vartype status: TopicModelingStageStatus
    :ivar topics_labeled: Count of topics labeled.
    :vartype topics_labeled: int
    :ivar warnings: Warning messages.
    :vartype warnings: list[str]
    :ivar errors: Error messages.
    :vartype errors: list[str]
    """

    status: TopicModelingStageStatus
    topics_labeled: int = Field(ge=0)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class TopicModelingLabelSource(str, Enum):
    """
    Source identifiers for topic labels.
    """

    BERTOPIC = "bertopic"
    LLM = "llm"


class TopicModelingKeyword(AnalysisSchemaModel):
    """
    Keyword entry for a topic.

    :ivar keyword: Keyword or phrase.
    :vartype keyword: str
    :ivar score: Keyword relevance score.
    :vartype score: float
    """

    keyword: str
    score: float


class TopicModelingTopic(AnalysisSchemaModel):
    """
    Topic output record.

    :ivar topic_id: Topic identifier.
    :vartype topic_id: int
    :ivar label: Human-readable topic label.
    :vartype label: str
    :ivar label_source: Source for the label.
    :vartype label_source: TopicModelingLabelSource
    :ivar keywords: Topic keywords with scores.
    :vartype keywords: list[TopicModelingKeyword]
    :ivar document_count: Number of documents in the topic.
    :vartype document_count: int
    :ivar document_examples: Example document texts.
    :vartype document_examples: list[str]
    :ivar document_ids: Document identifiers for the topic.
    :vartype document_ids: list[str]
    """

    topic_id: int
    label: str
    label_source: TopicModelingLabelSource
    keywords: List[TopicModelingKeyword] = Field(default_factory=list)
    document_count: int = Field(ge=0)
    document_examples: List[str] = Field(default_factory=list)
    document_ids: List[str] = Field(default_factory=list)


class TopicModelingReport(AnalysisSchemaModel):
    """
    Report for topic modeling analysis.

    :ivar text_collection: Text collection report.
    :vartype text_collection: TopicModelingTextCollectionReport
    :ivar llm_extraction: LLM extraction report.
    :vartype llm_extraction: TopicModelingLlmExtractionReport
    :ivar lexical_processing: Lexical processing report.
    :vartype lexical_processing: TopicModelingLexicalProcessingReport
    :ivar bertopic_analysis: BERTopic analysis report.
    :vartype bertopic_analysis: TopicModelingBerTopicReport
    :ivar llm_fine_tuning: LLM fine-tuning report.
    :vartype llm_fine_tuning: TopicModelingLlmFineTuningReport
    :ivar topics: Topic output list.
    :vartype topics: list[TopicModelingTopic]
    :ivar warnings: Warning messages.
    :vartype warnings: list[str]
    :ivar errors: Error messages.
    :vartype errors: list[str]
    """

    text_collection: TopicModelingTextCollectionReport
    llm_extraction: TopicModelingLlmExtractionReport
    lexical_processing: TopicModelingLexicalProcessingReport
    bertopic_analysis: TopicModelingBerTopicReport
    llm_fine_tuning: TopicModelingLlmFineTuningReport
    topics: List[TopicModelingTopic] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class TopicModelingOutput(AnalysisSchemaModel):
    """
    Output bundle for topic modeling analysis.

    :ivar schema_version: Analysis schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis backend identifier.
    :vartype analysis_id: str
    :ivar generated_at: International Organization for Standardization 8601 timestamp for output creation.
    :vartype generated_at: str
    :ivar run: Analysis run manifest.
    :vartype run: AnalysisRunManifest
    :ivar report: Topic modeling report data.
    :vartype report: TopicModelingReport
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str
    generated_at: str
    run: AnalysisRunManifest
    report: TopicModelingReport
