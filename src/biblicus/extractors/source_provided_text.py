"""
Source-provided text extractor plugin.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict

from ..models import CatalogItem, ExtractedText, ExtractionStageOutput
from .base import TextExtractor


class SourceProvidedTextExtractorConfig(BaseModel):
    """
    Configuration for source-provided text extraction.
    """

    model_config = ConfigDict(extra="forbid")


class SourceProvidedTextExtractor(TextExtractor):
    """
    Extractor plugin that uses text supplied by the original source platform.

    :ivar extractor_id: Extractor identifier.
    :vartype extractor_id: str
    """

    extractor_id = "source-provided-text"

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        """
        Validate extractor configuration.

        :param config: Configuration mapping.
        :type config: dict[str, Any]
        :return: Parsed configuration.
        :rtype: SourceProvidedTextExtractorConfig
        """
        return SourceProvidedTextExtractorConfig.model_validate(config)

    def extract_text(
        self,
        *,
        corpus,
        item: CatalogItem,
        config: BaseModel,
        previous_extractions: List[ExtractionStageOutput],
    ) -> Optional[ExtractedText]:
        """
        Extract text from source-provided derived asset metadata.

        :param corpus: Corpus containing the item bytes.
        :type corpus: Corpus
        :param item: Catalog item being processed.
        :type item: CatalogItem
        :param config: Parsed configuration model.
        :type config: SourceProvidedTextExtractorConfig
        :param previous_extractions: Prior stage outputs for this item within the pipeline.
        :type previous_extractions: list[biblicus.models.ExtractionStageOutput]
        :return: Extracted text payload, or None when no source text URI exists.
        :rtype: ExtractedText or None
        """
        _ = corpus
        _ = config
        _ = previous_extractions
        full_text_uri = _source_provided_text_uri(item.metadata)
        if full_text_uri is None:
            return None
        request = Request(full_text_uri, headers={"User-Agent": "biblicus/0"})
        with urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
        return ExtractedText(
            text=text,
            producer_extractor_id=self.extractor_id,
            metadata={"source_provided_text_uri": full_text_uri},
        )


def _source_provided_text_uri(metadata: Dict[str, Any]) -> Optional[str]:
    source_resolution = metadata.get("source_resolution")
    if not isinstance(source_resolution, dict):
        return None
    derived_assets = source_resolution.get("derived_assets")
    if not isinstance(derived_assets, dict):
        return None
    full_text_uri = derived_assets.get("full_text_uri")
    if isinstance(full_text_uri, str) and full_text_uri.strip():
        return full_text_uri.strip()
    return None
