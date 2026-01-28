"""
Cascade extractor plugin that composes multiple extractors.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..corpus import Corpus
from ..models import CatalogItem, ExtractedText
from .base import TextExtractor


class CascadeStepSpec(BaseModel):
    """
    Single extractor step within a cascade pipeline.

    :ivar extractor_id: Extractor plugin identifier.
    :vartype extractor_id: str
    :ivar config: Extractor configuration mapping.
    :vartype config: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    extractor_id: str = Field(min_length=1)
    config: Dict[str, Any] = Field(default_factory=dict)


class CascadeExtractorConfig(BaseModel):
    """
    Configuration for the cascade extractor.

    :ivar steps: Ordered list of extractor steps to try.
    :vartype steps: list[CascadeStepSpec]
    """

    model_config = ConfigDict(extra="forbid")

    steps: List[CascadeStepSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _forbid_self_reference(self) -> "CascadeExtractorConfig":
        if any(step.extractor_id == "cascade" for step in self.steps):
            raise ValueError("Cascade extractor cannot include itself as a step")
        return self


class CascadeExtractor(TextExtractor):
    """
    Extractor that tries a sequence of extractors and uses the first usable text result.

    A result is considered usable when its text is non-empty after stripping whitespace.

    :ivar extractor_id: Extractor identifier.
    :vartype extractor_id: str
    """

    extractor_id = "cascade"

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        """
        Validate cascade extractor configuration.

        :param config: Configuration mapping.
        :type config: dict[str, Any]
        :return: Parsed config.
        :rtype: CascadeExtractorConfig
        """

        return CascadeExtractorConfig.model_validate(config)

    def extract_text(self, *, corpus: Corpus, item: CatalogItem, config: BaseModel) -> Optional[ExtractedText]:
        """
        Run each configured extractor step until usable text is produced.

        :param corpus: Corpus containing the item bytes.
        :type corpus: Corpus
        :param item: Catalog item being processed.
        :type item: CatalogItem
        :param config: Parsed configuration model.
        :type config: CascadeExtractorConfig
        :return: Extracted text payload or None.
        :rtype: ExtractedText or None
        """

        cascade_config = config if isinstance(config, CascadeExtractorConfig) else CascadeExtractorConfig.model_validate(config)
        for step in cascade_config.steps:
            from . import get_extractor

            extractor = get_extractor(step.extractor_id)
            parsed_step_config = extractor.validate_config(step.config)
            result = extractor.extract_text(corpus=corpus, item=item, config=parsed_step_config)
            if result is None:
                continue
            if not result.text.strip():
                continue
            return result
        return None
