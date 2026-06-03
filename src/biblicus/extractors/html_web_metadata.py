"""
Attach BeautifulSoup web metadata to HTML corpus items during text extraction.

Runs after markitdown (or similar) so final pipeline text is unchanged while
``metadata/{item_id}.json`` carries ``method`` and ``structured`` for graph NER dedup.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..corpus import Corpus
from ..models import CatalogItem, ExtractedText, ExtractionStageOutput
from ..web_reference_metadata import (
    LOCAL_HTML_SOURCE_URI,
    extract_web_reference_metadata_from_html,
    extraction_metadata_from_web_payload,
)
from .base import TextExtractor

_DEFAULT_HTML_MEDIA_PATTERNS = (
    "text/html",
    "application/xhtml+xml",
    "application/xhtml*",
)


class HtmlWebMetadataExtractorConfig(BaseModel):
    """
    Configuration for HTML web metadata attachment.

    :ivar media_type_patterns: Media types that receive heuristic metadata extraction.
    :vartype media_type_patterns: list[str]
    :ivar use_llm_fallback: Whether to run LLM structured enrichment when heuristics are sparse.
    :vartype use_llm_fallback: bool
    """

    model_config = ConfigDict(extra="forbid")

    media_type_patterns: List[str] = Field(default_factory=lambda: list(_DEFAULT_HTML_MEDIA_PATTERNS))
    use_llm_fallback: bool = Field(default=False)


class HtmlWebMetadataExtractor(TextExtractor):
    """
    Pipeline stage that enriches HTML items with shared web heuristic metadata.
    """

    extractor_id = "html-web-metadata"

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        """
        Validate extractor configuration.

        :param config: Configuration mapping.
        :type config: dict[str, Any]
        :return: Parsed configuration.
        :rtype: HtmlWebMetadataExtractorConfig
        """
        return HtmlWebMetadataExtractorConfig.model_validate(config)

    def extract_text(
        self,
        *,
        corpus: Corpus,
        item: CatalogItem,
        config: BaseModel,
        previous_extractions: List[ExtractionStageOutput],
    ) -> Optional[ExtractedText]:
        """
        Pass through prior stage text and attach web heuristic metadata for HTML items.

        :param corpus: Corpus containing the item bytes.
        :type corpus: Corpus
        :param item: Catalog item being processed.
        :type item: CatalogItem
        :param config: Parsed configuration model.
        :type config: HtmlWebMetadataExtractorConfig
        :param previous_extractions: Prior stage outputs for this item within the pipeline.
        :type previous_extractions: list[ExtractionStageOutput]
        :return: Text plus metadata when HTML matches; otherwise None.
        :rtype: ExtractedText or None
        """
        parsed = (
            config
            if isinstance(config, HtmlWebMetadataExtractorConfig)
            else HtmlWebMetadataExtractorConfig.model_validate(config)
        )
        if not _matches_html_media_type(item.media_type, parsed.media_type_patterns):
            return None

        prior_text = _latest_prior_text(previous_extractions)
        if prior_text is None:
            return None

        source_path = corpus.root / item.relpath
        try:
            html_body = source_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ExtractedText(
                text=prior_text,
                producer_extractor_id=self.extractor_id,
                metadata={
                    "method": "html_heuristics_unavailable",
                    "structured": {
                        "authors": [],
                        "citations": [],
                        "warnings": [
                            {
                                "code": "html_read_failed",
                                "message": f"Could not read HTML file at {item.relpath}.",
                            }
                        ],
                    },
                },
            )

        source_uri = _resolve_source_uri(item, source_path)
        payload = extract_web_reference_metadata_from_html(
            html_body,
            source_uri=source_uri,
            reference_title=str(item.title or ""),
            use_llm_fallback=parsed.use_llm_fallback,
        )
        metadata = extraction_metadata_from_web_payload(payload)
        producer = _latest_prior_producer(previous_extractions) or self.extractor_id
        return ExtractedText(
            text=prior_text,
            producer_extractor_id=producer,
            metadata=metadata,
        )


def _matches_html_media_type(media_type: str, patterns: List[str]) -> bool:
    normalized = str(media_type or "").strip().lower()
    if not normalized:
        return False
    return any(fnmatch.fnmatch(normalized, pattern.lower()) for pattern in patterns)


def _latest_prior_text(previous_extractions: List[ExtractionStageOutput]) -> Optional[str]:
    for stage in reversed(previous_extractions):
        text = str(stage.text or "").strip()
        if text:
            return stage.text or ""
    return None


def _latest_prior_producer(previous_extractions: List[ExtractionStageOutput]) -> Optional[str]:
    for stage in reversed(previous_extractions):
        if str(stage.text or "").strip():
            return stage.producer_extractor_id or stage.extractor_id
    return None


def _resolve_source_uri(item: CatalogItem, source_path: Path) -> str:
    explicit = str(item.source_uri or "").strip()
    if explicit:
        return explicit
    metadata = item.metadata if isinstance(item.metadata, dict) else {}
    for key in ("source_uri", "sourceUri", "url", "canonical_uri", "canonicalUri"):
        value = str(metadata.get(key) or "").strip()
        if value:
            return value
    return f"{LOCAL_HTML_SOURCE_URI.rstrip('/')}/{source_path.name}"
