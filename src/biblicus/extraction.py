"""
Text extraction runs for Biblicus.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .corpus import Corpus
from .extractors import get_extractor
from .models import CatalogItem
from .retrieval import hash_text
from .time import utc_now_iso


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
        raise ValueError("Extraction run reference must be extractor_id:run_id with non-empty parts")
    return ExtractionRunReference(extractor_id=extractor_id, run_id=run_id)


class ExtractionRecipeManifest(BaseModel):
    """
    Reproducible configuration for an extraction plugin run.

    :ivar recipe_id: Deterministic recipe identifier.
    :vartype recipe_id: str
    :ivar extractor_id: Extractor plugin identifier.
    :vartype extractor_id: str
    :ivar name: Human-readable recipe name.
    :vartype name: str
    :ivar created_at: International Organization for Standardization 8601 timestamp.
    :vartype created_at: str
    :ivar config: Extractor-specific configuration values.
    :vartype config: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    recipe_id: str
    extractor_id: str
    name: str
    created_at: str
    config: Dict[str, Any] = Field(default_factory=dict)


class ExtractionItemResult(BaseModel):
    """
    Per-item result record for an extraction run.

    :ivar item_id: Item identifier.
    :vartype item_id: str
    :ivar status: Result status, extracted or skipped.
    :vartype status: str
    :ivar text_relpath: Relative path to the extracted text artifact, when extracted.
    :vartype text_relpath: str or None
    :ivar producer_extractor_id: Extractor identifier that produced the extracted text.
    :vartype producer_extractor_id: str or None
    """

    model_config = ConfigDict(extra="forbid")

    item_id: str
    status: str
    text_relpath: Optional[str] = None
    producer_extractor_id: Optional[str] = None


class ExtractionRunManifest(BaseModel):
    """
    Immutable record describing an extraction run.

    :ivar run_id: Unique run identifier.
    :vartype run_id: str
    :ivar recipe: Recipe manifest for this run.
    :vartype recipe: ExtractionRecipeManifest
    :ivar corpus_uri: Canonical uniform resource identifier for the corpus root.
    :vartype corpus_uri: str
    :ivar catalog_generated_at: Catalog timestamp used for the run.
    :vartype catalog_generated_at: str
    :ivar created_at: International Organization for Standardization 8601 timestamp for run creation.
    :vartype created_at: str
    :ivar items: Per-item results.
    :vartype items: list[ExtractionItemResult]
    :ivar stats: Run statistics.
    :vartype stats: dict[str, Any]
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str
    recipe: ExtractionRecipeManifest
    corpus_uri: str
    catalog_generated_at: str
    created_at: str
    items: List[ExtractionItemResult] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)


def create_extraction_recipe_manifest(*, extractor_id: str, name: str, config: Dict[str, Any]) -> ExtractionRecipeManifest:
    """
    Create a deterministic extraction recipe manifest.

    :param extractor_id: Extractor plugin identifier.
    :type extractor_id: str
    :param name: Human recipe name.
    :type name: str
    :param config: Extractor configuration.
    :type config: dict[str, Any]
    :return: Recipe manifest.
    :rtype: ExtractionRecipeManifest
    """

    recipe_payload = json.dumps({"extractor_id": extractor_id, "name": name, "config": config}, sort_keys=True)
    recipe_id = hash_text(recipe_payload)
    return ExtractionRecipeManifest(
        recipe_id=recipe_id,
        extractor_id=extractor_id,
        name=name,
        created_at=utc_now_iso(),
        config=config,
    )


def create_extraction_run_manifest(corpus: Corpus, *, recipe: ExtractionRecipeManifest) -> ExtractionRunManifest:
    """
    Create a new extraction run manifest for a corpus.

    :param corpus: Corpus associated with the run.
    :type corpus: Corpus
    :param recipe: Recipe manifest.
    :type recipe: ExtractionRecipeManifest
    :return: Run manifest.
    :rtype: ExtractionRunManifest
    """

    catalog = corpus.load_catalog()
    return ExtractionRunManifest(
        run_id=str(uuid4()),
        recipe=recipe,
        corpus_uri=corpus.uri,
        catalog_generated_at=catalog.generated_at,
        created_at=utc_now_iso(),
        items=[],
        stats={},
    )


def write_extraction_run_manifest(*, run_dir: Path, manifest: ExtractionRunManifest) -> None:
    """
    Persist an extraction run manifest to a run directory.

    :param run_dir: Extraction run directory.
    :type run_dir: Path
    :param manifest: Run manifest to write.
    :type manifest: ExtractionRunManifest
    :return: None.
    :rtype: None
    """

    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")


def write_extracted_text_artifact(*, run_dir: Path, item: CatalogItem, text: str) -> str:
    """
    Write an extracted text artifact for an item into the run directory.

    :param run_dir: Extraction run directory.
    :type run_dir: Path
    :param item: Catalog item being extracted.
    :type item: CatalogItem
    :param text: Extracted text.
    :type text: str
    :return: Relative path to the stored text artifact.
    :rtype: str
    """

    text_dir = run_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    relpath = str(Path("text") / f"{item.id}.txt")
    path = run_dir / relpath
    path.write_text(text, encoding="utf-8")
    return relpath


def build_extraction_run(
    corpus: Corpus,
    *,
    extractor_id: str,
    recipe_name: str,
    config: Dict[str, Any],
) -> ExtractionRunManifest:
    """
    Build an extraction run for a corpus using a named extractor plugin.

    :param corpus: Corpus to extract from.
    :type corpus: Corpus
    :param extractor_id: Extractor plugin identifier.
    :type extractor_id: str
    :param recipe_name: Human-readable recipe name.
    :type recipe_name: str
    :param config: Extractor configuration mapping.
    :type config: dict[str, Any]
    :return: Extraction run manifest describing the build.
    :rtype: ExtractionRunManifest
    :raises KeyError: If the extractor identifier is unknown.
    :raises ValueError: If the extractor configuration is invalid.
    :raises OSError: If the run directory or artifacts cannot be written.
    """

    extractor = get_extractor(extractor_id)
    parsed_config = extractor.validate_config(config)
    recipe = create_extraction_recipe_manifest(
        extractor_id=extractor_id,
        name=recipe_name,
        config=parsed_config.model_dump(),
    )
    manifest = create_extraction_run_manifest(corpus, recipe=recipe)
    run_dir = corpus.extraction_run_dir(extractor_id=extractor_id, run_id=manifest.run_id)
    run_dir.mkdir(parents=True, exist_ok=False)

    catalog = corpus.load_catalog()
    extracted_items: List[ExtractionItemResult] = []
    extracted_count = 0
    skipped_count = 0
    extracted_nonempty_count = 0
    extracted_empty_count = 0
    already_text_item_count = 0
    needs_extraction_item_count = 0
    converted_item_count = 0
    for item in catalog.items.values():
        media_type = item.media_type
        item_is_text = media_type == "text/markdown" or media_type.startswith("text/")
        if item_is_text:
            already_text_item_count += 1
        else:
            needs_extraction_item_count += 1

        extracted_text = extractor.extract_text(corpus=corpus, item=item, config=parsed_config)
        if extracted_text is None:
            skipped_count += 1
            extracted_items.append(
                ExtractionItemResult(
                    item_id=item.id,
                    status="skipped",
                    text_relpath=None,
                    producer_extractor_id=None,
                )
            )
            continue

        extracted_count += 1
        stripped_text = extracted_text.text.strip()
        if stripped_text:
            extracted_nonempty_count += 1
            if not item_is_text:
                converted_item_count += 1
        else:
            extracted_empty_count += 1

        relpath = write_extracted_text_artifact(run_dir=run_dir, item=item, text=extracted_text.text)
        extracted_items.append(
            ExtractionItemResult(
                item_id=item.id,
                status="extracted",
                text_relpath=relpath,
                producer_extractor_id=extracted_text.producer_extractor_id,
            )
        )

    stats = {
        "total_items": len(catalog.items),
        "already_text_items": already_text_item_count,
        "needs_extraction_items": needs_extraction_item_count,
        "extracted_items": extracted_count,
        "extracted_nonempty_items": extracted_nonempty_count,
        "extracted_empty_items": extracted_empty_count,
        "skipped_items": skipped_count,
        "converted_items": converted_item_count,
    }
    manifest = manifest.model_copy(update={"items": extracted_items, "stats": stats})
    write_extraction_run_manifest(run_dir=run_dir, manifest=manifest)
    return manifest
