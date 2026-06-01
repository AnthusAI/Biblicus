"""
Portable Document Format text extractor backed by GROBID.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models import CatalogItem, ExtractedText, ExtractionStageOutput
from ..url_text import UrlTextExtractionError, _convert_pdf_with_grobid
from .base import TextExtractor
from .pdf_text import PortableDocumentFormatTextExtractor, PortableDocumentFormatTextExtractorConfig


class GrobidPortableDocumentFormatTextExtractorConfig(BaseModel):
    """
    Configuration for GROBID-backed PDF text extraction.

    :ivar max_pages: Optional maximum number of pages (reserved for future use).
    :vartype max_pages: int or None
    :ivar fallback_to_pypdf: Use pypdf when GROBID is unavailable.
    :vartype fallback_to_pypdf: bool
    """

    model_config = ConfigDict(extra="forbid")

    max_pages: Optional[int] = Field(default=None, ge=1)
    fallback_to_pypdf: bool = Field(default=True)


class GrobidPortableDocumentFormatTextExtractor(TextExtractor):
    """
    Extract PDF text and structured metadata using GROBID when configured.
    """

    extractor_id = "grobid-pdf-text"

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        """
        Validate extractor configuration.

        :param config: Configuration mapping.
        :type config: dict[str, Any]
        :return: Parsed configuration.
        :rtype: GrobidPortableDocumentFormatTextExtractorConfig
        """
        return GrobidPortableDocumentFormatTextExtractorConfig.model_validate(config)

    def extract_text(
        self,
        *,
        corpus,
        item: CatalogItem,
        config: BaseModel,
        previous_extractions: List[ExtractionStageOutput],
    ) -> Optional[ExtractedText]:
        """
        Extract text for a PDF using GROBID, with optional pypdf fallback.

        :param corpus: Corpus containing the item bytes.
        :type corpus: Corpus
        :param item: Catalog item being processed.
        :type item: CatalogItem
        :param config: Parsed configuration model.
        :type config: BaseModel
        :param previous_extractions: Prior stage outputs (ignored).
        :type previous_extractions: list[ExtractionStageOutput]
        :return: Extracted text payload, or None when the item is not a PDF.
        :rtype: ExtractedText or None
        """
        _ = previous_extractions
        if item.media_type != "application/pdf":
            return None
        parsed = (
            config
            if isinstance(config, GrobidPortableDocumentFormatTextExtractorConfig)
            else GrobidPortableDocumentFormatTextExtractorConfig.model_validate(config)
        )
        pdf_path = corpus.root / item.relpath
        pdf_bytes = pdf_path.read_bytes()
        try:
            converted = _convert_pdf_with_grobid(
                data=pdf_bytes,
                source_uri=str(pdf_path),
                content_type=item.media_type,
            )
        except UrlTextExtractionError:
            if not parsed.fallback_to_pypdf:
                raise
            fallback = PortableDocumentFormatTextExtractor()
            fallback_result = fallback.extract_text(
                corpus=corpus,
                item=item,
                config=PortableDocumentFormatTextExtractorConfig(max_pages=parsed.max_pages),
                previous_extractions=[],
            )
            return fallback_result

        structured = converted.get("structured") if isinstance(converted.get("structured"), dict) else {}
        text = str(converted.get("text") or "").strip()
        if not text:
            return None
        return ExtractedText(
            text=text,
            producer_extractor_id=self.extractor_id,
            metadata={
                "method": "grobid",
                "grobid": converted.get("grobid") if isinstance(converted.get("grobid"), dict) else {},
                "structured": structured,
                "title": converted.get("title"),
            },
        )
