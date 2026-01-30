"""
Text extraction runs for Biblicus.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .corpus import Corpus
from .errors import ExtractionRunFatalError
from .extractors import get_extractor
from .extractors.base import TextExtractor
from .extractors.pipeline import PipelineExtractorConfig, PipelineStepSpec
from .models import CatalogItem, ExtractionStepOutput
from .retrieval import hash_text
from .time import utc_now_iso


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


class ExtractionStepResult(BaseModel):
    """
    Per-item result record for a single pipeline step.

    :ivar step_index: One-based pipeline step index.
    :vartype step_index: int
    :ivar extractor_id: Extractor identifier for the step.
    :vartype extractor_id: str
    :ivar status: Step status, extracted, skipped, or errored.
    :vartype status: str
    :ivar text_relpath: Relative path to the step text artifact, when extracted.
    :vartype text_relpath: str or None
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
    text_relpath: Optional[str] = None
    text_characters: int = Field(default=0, ge=0)
    producer_extractor_id: Optional[str] = None
    source_step_index: Optional[int] = Field(default=None, ge=1)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class ExtractionItemResult(BaseModel):
    """
    Per-item result record for an extraction run.

    :ivar item_id: Item identifier.
    :vartype item_id: str
    :ivar status: Final result status, extracted, skipped, or errored.
    :vartype status: str
    :ivar final_text_relpath: Relative path to the final extracted text artifact, when extracted.
    :vartype final_text_relpath: str or None
    :ivar final_step_index: Pipeline step index that produced the final text.
    :vartype final_step_index: int or None
    :ivar final_step_extractor_id: Extractor identifier of the step that produced the final text.
    :vartype final_step_extractor_id: str or None
    :ivar final_producer_extractor_id: Extractor identifier that produced the final text content.
    :vartype final_producer_extractor_id: str or None
    :ivar final_source_step_index: Optional step index that supplied the final text for selection-style extractors.
    :vartype final_source_step_index: int or None
    :ivar error_type: Optional error type name when no extracted text was produced.
    :vartype error_type: str or None
    :ivar error_message: Optional error message when no extracted text was produced.
    :vartype error_message: str or None
    :ivar step_results: Per-step results recorded for this item.
    :vartype step_results: list[ExtractionStepResult]
    """

    model_config = ConfigDict(extra="forbid")

    item_id: str
    status: str
    final_text_relpath: Optional[str] = None
    final_step_index: Optional[int] = Field(default=None, ge=1)
    final_step_extractor_id: Optional[str] = None
    final_producer_extractor_id: Optional[str] = None
    final_source_step_index: Optional[int] = Field(default=None, ge=1)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    step_results: List[ExtractionStepResult] = Field(default_factory=list)


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


def create_extraction_recipe_manifest(
    *, extractor_id: str, name: str, config: Dict[str, Any]
) -> ExtractionRecipeManifest:
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
    recipe_payload = json.dumps(
        {"extractor_id": extractor_id, "name": name, "config": config}, sort_keys=True
    )
    recipe_id = hash_text(recipe_payload)
    return ExtractionRecipeManifest(
        recipe_id=recipe_id,
        extractor_id=extractor_id,
        name=name,
        created_at=utc_now_iso(),
        config=config,
    )


def create_extraction_run_manifest(
    corpus: Corpus, *, recipe: ExtractionRecipeManifest
) -> ExtractionRunManifest:
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
    run_id = hash_text(f"{recipe.recipe_id}:{catalog.generated_at}")
    return ExtractionRunManifest(
        run_id=run_id,
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


def _pipeline_step_dir_name(*, step_index: int, extractor_id: str) -> str:
    """
    Build a stable directory name for a pipeline step.

    :param step_index: One-based pipeline step index.
    :type step_index: int
    :param extractor_id: Extractor identifier for the step.
    :type extractor_id: str
    :return: Directory name for the step.
    :rtype: str
    """
    return f"{step_index:02d}-{extractor_id}"


def write_pipeline_step_text_artifact(
    *,
    run_dir: Path,
    step_index: int,
    extractor_id: str,
    item: CatalogItem,
    text: str,
) -> str:
    """
    Write a pipeline step text artifact for an item.

    :param run_dir: Extraction run directory.
    :type run_dir: Path
    :param step_index: One-based pipeline step index.
    :type step_index: int
    :param extractor_id: Extractor identifier for the step.
    :type extractor_id: str
    :param item: Catalog item being extracted.
    :type item: CatalogItem
    :param text: Extracted text content.
    :type text: str
    :return: Relative path to the stored step text artifact.
    :rtype: str
    """
    step_dir_name = _pipeline_step_dir_name(step_index=step_index, extractor_id=extractor_id)
    text_dir = run_dir / "steps" / step_dir_name / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    relpath = str(Path("steps") / step_dir_name / "text" / f"{item.id}.txt")
    (run_dir / relpath).write_text(text, encoding="utf-8")
    return relpath


def _final_output_from_steps(
    step_outputs: List[ExtractionStepOutput],
) -> Optional[ExtractionStepOutput]:
    """
    Select the final pipeline output for an item.

    The final output is the last extracted step output in pipeline order.

    :param step_outputs: Extracted outputs produced by pipeline steps.
    :type step_outputs: list[biblicus.models.ExtractionStepOutput]
    :return: Final step output or None when no steps produced extracted text.
    :rtype: biblicus.models.ExtractionStepOutput or None
    """
    if not step_outputs:
        return None
    return step_outputs[-1]


def build_extraction_run(
    corpus: Corpus,
    *,
    extractor_id: str,
    recipe_name: str,
    config: Dict[str, Any],
) -> ExtractionRunManifest:
    """
    Build an extraction run for a corpus using the pipeline extractor.

    :param corpus: Corpus to extract from.
    :type corpus: Corpus
    :param extractor_id: Extractor plugin identifier (must be ``pipeline``).
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
    :raises ExtractionRunFatalError: If the extractor is not the pipeline.
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
    if run_dir.exists():
        return corpus.load_extraction_run_manifest(
            extractor_id=extractor_id, run_id=manifest.run_id
        )
    run_dir.mkdir(parents=True, exist_ok=False)

    catalog = corpus.load_catalog()
    if extractor_id != "pipeline":
        raise ExtractionRunFatalError("Extraction runs must use the pipeline extractor")

    pipeline_config = (
        parsed_config
        if isinstance(parsed_config, PipelineExtractorConfig)
        else PipelineExtractorConfig.model_validate(parsed_config)
    )

    validated_steps: List[Tuple[PipelineStepSpec, TextExtractor, BaseModel]] = []
    for step in pipeline_config.steps:
        step_extractor = get_extractor(step.extractor_id)
        parsed_step_config = step_extractor.validate_config(step.config)
        validated_steps.append((step, step_extractor, parsed_step_config))

    extracted_items: List[ExtractionItemResult] = []
    extracted_count = 0
    skipped_count = 0
    errored_count = 0
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

        step_results: List[ExtractionStepResult] = []
        step_outputs: List[ExtractionStepOutput] = []
        last_error_type: Optional[str] = None
        last_error_message: Optional[str] = None

        for step_index, (step, step_extractor, parsed_step_config) in enumerate(
            validated_steps, start=1
        ):
            try:
                extracted_text = step_extractor.extract_text(
                    corpus=corpus,
                    item=item,
                    config=parsed_step_config,
                    previous_extractions=step_outputs,
                )
            except Exception as extraction_error:
                if isinstance(extraction_error, ExtractionRunFatalError):
                    raise
                last_error_type = extraction_error.__class__.__name__
                last_error_message = str(extraction_error)
                step_results.append(
                    ExtractionStepResult(
                        step_index=step_index,
                        extractor_id=step.extractor_id,
                        status="errored",
                        text_relpath=None,
                        text_characters=0,
                        producer_extractor_id=None,
                        source_step_index=None,
                        error_type=last_error_type,
                        error_message=last_error_message,
                    )
                )
                continue

            if extracted_text is None:
                step_results.append(
                    ExtractionStepResult(
                        step_index=step_index,
                        extractor_id=step.extractor_id,
                        status="skipped",
                        text_relpath=None,
                        text_characters=0,
                        producer_extractor_id=None,
                        source_step_index=None,
                        error_type=None,
                        error_message=None,
                    )
                )
                continue

            relpath = write_pipeline_step_text_artifact(
                run_dir=run_dir,
                step_index=step_index,
                extractor_id=step.extractor_id,
                item=item,
                text=extracted_text.text,
            )
            text_characters = len(extracted_text.text)
            step_results.append(
                ExtractionStepResult(
                    step_index=step_index,
                    extractor_id=step.extractor_id,
                    status="extracted",
                    text_relpath=relpath,
                    text_characters=text_characters,
                    producer_extractor_id=extracted_text.producer_extractor_id,
                    source_step_index=extracted_text.source_step_index,
                    confidence=extracted_text.confidence,
                    error_type=None,
                    error_message=None,
                )
            )
            step_outputs.append(
                ExtractionStepOutput(
                    step_index=step_index,
                    extractor_id=step.extractor_id,
                    status="extracted",
                    text=extracted_text.text,
                    text_characters=text_characters,
                    producer_extractor_id=extracted_text.producer_extractor_id,
                    source_step_index=extracted_text.source_step_index,
                    confidence=extracted_text.confidence,
                    error_type=None,
                    error_message=None,
                )
            )

        final_output = _final_output_from_steps(step_outputs)
        if final_output is None:
            status = "errored" if last_error_type else "skipped"
            if status == "errored":
                errored_count += 1
            else:
                skipped_count += 1
            extracted_items.append(
                ExtractionItemResult(
                    item_id=item.id,
                    status=status,
                    final_text_relpath=None,
                    final_step_index=None,
                    final_step_extractor_id=None,
                    final_producer_extractor_id=None,
                    final_source_step_index=None,
                    error_type=last_error_type if status == "errored" else None,
                    error_message=last_error_message if status == "errored" else None,
                    step_results=step_results,
                )
            )
            continue

        final_text = final_output.text or ""
        final_text_relpath = write_extracted_text_artifact(
            run_dir=run_dir, item=item, text=final_text
        )
        extracted_count += 1
        if final_text.strip():
            extracted_nonempty_count += 1
            if not item_is_text:
                converted_item_count += 1
        else:
            extracted_empty_count += 1

        extracted_items.append(
            ExtractionItemResult(
                item_id=item.id,
                status="extracted",
                final_text_relpath=final_text_relpath,
                final_step_index=final_output.step_index,
                final_step_extractor_id=final_output.extractor_id,
                final_producer_extractor_id=final_output.producer_extractor_id,
                final_source_step_index=final_output.source_step_index,
                error_type=None,
                error_message=None,
                step_results=step_results,
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
        "errored_items": errored_count,
        "converted_items": converted_item_count,
    }
    manifest = manifest.model_copy(update={"items": extracted_items, "stats": stats})
    write_extraction_run_manifest(run_dir=run_dir, manifest=manifest)
    return manifest
