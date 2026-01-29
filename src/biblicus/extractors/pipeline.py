"""
Pipeline extractor configuration and validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..corpus import Corpus
from ..errors import ExtractionRunFatalError
from ..models import CatalogItem, ExtractedText, ExtractionStepOutput
from .base import TextExtractor


class PipelineStepSpec(BaseModel):
    """
    Single extractor step within a pipeline.

    :ivar extractor_id: Extractor plugin identifier.
    :vartype extractor_id: str
    :ivar config: Extractor configuration mapping.
    :vartype config: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    extractor_id: str = Field(min_length=1)
    config: Dict[str, Any] = Field(default_factory=dict)


class PipelineExtractorConfig(BaseModel):
    """
    Configuration for the pipeline extractor.

    :ivar steps: Ordered list of extractor steps to run.
    :vartype steps: list[PipelineStepSpec]
    """

    model_config = ConfigDict(extra="forbid")

    steps: List[PipelineStepSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _forbid_pipeline_step(self) -> "PipelineExtractorConfig":
        if any(step.extractor_id == "pipeline" for step in self.steps):
            raise ValueError("Pipeline steps cannot include the pipeline extractor itself")
        return self


class PipelineExtractor(TextExtractor):
    """
    Pipeline extractor configuration shim.

    The pipeline extractor is executed by the extraction engine so it can persist
    per-step artifacts. This class only validates configuration.

    :ivar extractor_id: Extractor identifier.
    :vartype extractor_id: str
    """

    extractor_id = "pipeline"

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        """
        Validate pipeline configuration.

        :param config: Configuration mapping.
        :type config: dict[str, Any]
        :return: Parsed configuration.
        :rtype: PipelineExtractorConfig
        """
        return PipelineExtractorConfig.model_validate(config)

    def extract_text(
        self,
        *,
        corpus: Corpus,
        item: CatalogItem,
        config: BaseModel,
        previous_extractions: List[ExtractionStepOutput],
    ) -> Optional[ExtractedText]:
        """
        Reject direct execution of the pipeline extractor.

        :param corpus: Corpus containing the item bytes.
        :type corpus: Corpus
        :param item: Catalog item being processed.
        :type item: CatalogItem
        :param config: Parsed configuration model.
        :type config: PipelineExtractorConfig
        :param previous_extractions: Prior step outputs for this item within the pipeline.
        :type previous_extractions: list[biblicus.models.ExtractionStepOutput]
        :raises ExtractionRunFatalError: Always, because the pipeline is executed by the runner.
        :return: None.
        :rtype: None
        """
        _ = corpus
        _ = item
        _ = config
        _ = previous_extractions
        raise ExtractionRunFatalError(
            "Pipeline extractor must be executed by the extraction runner."
        )
