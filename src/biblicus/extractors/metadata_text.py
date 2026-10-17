"""
Metadata-based text extractor plugin.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models import CatalogItem, ExtractedText, ExtractionStageOutput
from .base import TextExtractor


class MetadataTextExtractorConfig(BaseModel):
    """
    Configuration for the metadata text extractor.

    The metadata text extractor is intentionally minimal and deterministic.
    It emits a plain text representation derived only from an item's catalog metadata.

    :ivar include_title: Whether to include the item title as the first line, if present.
    :vartype include_title: bool
    :ivar include_tags: Whether to include a ``tags: ...`` line, if tags are present.
    :vartype include_tags: bool
    :ivar fields: Explicit catalog or metadata field paths to emit.
    :vartype fields: list[str]
    """

    model_config = ConfigDict(extra="forbid")

    include_title: bool = Field(default=True)
    include_tags: bool = Field(default=True)
    fields: List[str] = Field(default_factory=list)

    @field_validator("fields", mode="before")
    @classmethod
    def _parse_fields(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("fields must be a list of field paths") from exc
            return parsed
        return value

    @field_validator("fields", mode="after")
    @classmethod
    def _validate_fields(cls, value: List[str]) -> List[str]:
        cleaned = [entry.strip() for entry in value if entry.strip()]
        if len(cleaned) != len(value):
            raise ValueError("fields must contain non-empty field paths")
        for field_path in cleaned:
            if field_path not in {"title", "tags"} and not field_path.startswith("metadata."):
                raise ValueError("fields must be title, tags, or metadata.<key>")
        return cleaned


class MetadataTextExtractor(TextExtractor):
    """
    Extractor plugin that emits a small, searchable text representation of item metadata.

    The output is intended to be stable and human-readable:

    - If a title exists, the first line is the title.
    - If tags exist, the next line is ``tags: <comma separated tags>``.

    This extractor is useful for:

    - Retrieval over non-text items that carry meaningful metadata.
    - Comparing downstream retrieval backends while holding extraction stable.

    :ivar extractor_id: Extractor identifier.
    :vartype extractor_id: str
    """

    extractor_id = "metadata-text"

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        """
        Validate extractor configuration.

        :param config: Configuration mapping.
        :type config: dict[str, Any]
        :return: Parsed config.
        :rtype: MetadataTextExtractorConfig
        """
        return MetadataTextExtractorConfig.model_validate(config)

    def extract_text(
        self,
        *,
        corpus,
        item: CatalogItem,
        config: BaseModel,
        previous_extractions: List[ExtractionStageOutput],
    ) -> Optional[ExtractedText]:
        """
        Extract a metadata-based text payload for the item.

        :param corpus: Corpus containing the item bytes.
        :type corpus: Corpus
        :param item: Catalog item being processed.
        :type item: CatalogItem
        :param config: Parsed configuration model.
        :type config: MetadataTextExtractorConfig
        :param previous_extractions: Prior stage outputs for this item within the pipeline.
        :type previous_extractions: list[biblicus.models.ExtractionStageOutput]
        :return: Extracted text payload, or ``None`` if no metadata is available.
        :rtype: ExtractedText or None
        """
        parsed_config = (
            config
            if isinstance(config, MetadataTextExtractorConfig)
            else MetadataTextExtractorConfig.model_validate(config)
        )
        _ = corpus
        _ = previous_extractions
        lines: list[str] = []

        if parsed_config.fields:
            lines.extend(_selected_field_lines(item=item, fields=parsed_config.fields))
        else:
            if parsed_config.include_title and isinstance(item.title, str) and item.title.strip():
                lines.append(item.title.strip())

            tags = [tag.strip() for tag in item.tags if isinstance(tag, str) and tag.strip()]
            if parsed_config.include_tags and tags:
                lines.append(f"tags: {', '.join(tags)}")

        if not lines:
            return None

        return ExtractedText(text="\n".join(lines), producer_extractor_id=self.extractor_id)


def _selected_field_lines(*, item: CatalogItem, fields: List[str]) -> List[str]:
    lines: List[str] = []
    for field_path in fields:
        value = _selected_field_value(item=item, field_path=field_path)
        if value is None:
            continue
        line = _field_value_to_text(value)
        if line:
            lines.append(line)
    return lines


def _selected_field_value(*, item: CatalogItem, field_path: str) -> object:
    if field_path == "title":
        return item.title
    if field_path == "tags":
        return item.tags
    if field_path.startswith("metadata."):
        key = field_path.removeprefix("metadata.")
        return item.metadata.get(key)
    return None


def _field_value_to_text(value: object) -> str:
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
