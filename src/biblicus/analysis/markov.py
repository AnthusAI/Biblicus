"""
Markov analysis backend for Biblicus.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel

from ..ai.embeddings import generate_embeddings_batch
from ..ai.llm import generate_completion
from ..context import (
    ContextPack,
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_token_budget,
)
from ..corpus import Corpus
from ..models import Evidence, ExtractionRunReference, QueryBudget, RetrievalResult
from ..retrieval import hash_text
from ..text.annotate import TextAnnotateRequest, apply_text_annotate
from ..text.extract import TextExtractRequest, apply_text_extract
from ..time import utc_now_iso
from .base import CorpusAnalysisBackend
from .models import (
    AnalysisRecipeManifest,
    AnalysisRunInput,
    AnalysisRunManifest,
    MarkovAnalysisArtifactsGraphVizConfig,
    MarkovAnalysisDecodedPath,
    MarkovAnalysisModelFamily,
    MarkovAnalysisObservation,
    MarkovAnalysisObservationsEncoder,
    MarkovAnalysisOutput,
    MarkovAnalysisRecipeConfig,
    MarkovAnalysisReport,
    MarkovAnalysisSegment,
    MarkovAnalysisSegmentationMethod,
    MarkovAnalysisStageStatus,
    MarkovAnalysisState,
    MarkovAnalysisTextCollectionReport,
    MarkovAnalysisTextSourceConfig,
    MarkovAnalysisTransition,
    TopicModelingReport,
)
from .topic_modeling import TopicModelingDocument, run_topic_modeling_for_documents


class MarkovStateName(BaseModel):
    """
    Structured response for a single state name.

    :ivar state_id: State identifier.
    :vartype state_id: int
    :ivar name: Short noun-phrase name for the state.
    :vartype name: str
    """

    state_id: int
    name: str


class MarkovStateNamingResponse(BaseModel):
    """
    Structured response for state naming.

    :ivar state_names: State name assignments.
    :vartype state_names: list[MarkovStateName]
    :ivar start_state_id: Optional state id representing the start state.
    :vartype start_state_id: int or None
    :ivar end_state_id: Optional state id representing the end state.
    :vartype end_state_id: int or None
    :ivar disconnection_state_id: Optional state id representing a disconnection state.
    :vartype disconnection_state_id: int or None
    """

    state_names: List[MarkovStateName]
    start_state_id: Optional[int] = None
    end_state_id: Optional[int] = None
    disconnection_state_id: Optional[int] = None


@dataclass
class _Document:
    item_id: str
    text: str


class MarkovBackend(CorpusAnalysisBackend):
    """
    Markov analysis backend.

    :ivar analysis_id: Backend identifier.
    :vartype analysis_id: str
    """

    analysis_id = "markov"

    def run_analysis(
        self,
        corpus: Corpus,
        *,
        recipe_name: str,
        config: Dict[str, object],
        extraction_run: ExtractionRunReference,
    ) -> BaseModel:
        """
        Run Markov analysis for a corpus.

        :param corpus: Corpus to analyze.
        :type corpus: Corpus
        :param recipe_name: Human-readable recipe name.
        :type recipe_name: str
        :param config: Analysis configuration values.
        :type config: dict[str, object]
        :param extraction_run: Extraction run reference for text inputs.
        :type extraction_run: biblicus.models.ExtractionRunReference
        :return: Markov analysis output model.
        :rtype: pydantic.BaseModel
        """
        parsed_config = (
            config
            if isinstance(config, MarkovAnalysisRecipeConfig)
            else MarkovAnalysisRecipeConfig.model_validate(config)
        )
        return _run_markov(
            corpus=corpus,
            recipe_name=recipe_name,
            config=parsed_config,
            extraction_run=extraction_run,
        )


def _run_markov(
    *,
    corpus: Corpus,
    recipe_name: str,
    config: MarkovAnalysisRecipeConfig,
    extraction_run: ExtractionRunReference,
) -> MarkovAnalysisOutput:
    recipe = _create_recipe_manifest(name=recipe_name, config=config)
    catalog = corpus.load_catalog()
    run_id = _analysis_run_id(
        recipe_id=recipe.recipe_id,
        extraction_run=extraction_run,
        catalog_generated_at=catalog.generated_at,
    )
    run_manifest = AnalysisRunManifest(
        run_id=run_id,
        recipe=recipe,
        corpus_uri=catalog.corpus_uri,
        catalog_generated_at=catalog.generated_at,
        created_at=utc_now_iso(),
        input=AnalysisRunInput(extraction_run=extraction_run),
        artifact_paths=[],
        stats={},
    )
    run_dir = corpus.analysis_run_dir(analysis_id=MarkovBackend.analysis_id, run_id=run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    documents, text_report = _collect_documents(
        corpus=corpus,
        extraction_run=extraction_run,
        config=config.text_source,
    )
    segments = _segment_documents(documents=documents, config=config)
    observations = _build_observations(segments=segments, config=config)
    observations, topic_report = _apply_topic_modeling(observations=observations, config=config)
    observation_matrix, lengths = _encode_observations(observations=observations, config=config)

    predicted_states, transitions, state_count = _fit_and_decode(
        observations=observation_matrix,
        lengths=lengths,
        config=config,
    )

    decoded_paths = _group_decoded_paths(segments=segments, predicted_states=predicted_states)
    states = _build_states(
        segments=segments,
        predicted_states=predicted_states,
        n_states=state_count,
        max_exemplars=config.report.max_state_exemplars,
    )
    states = _assign_state_names(
        states=states,
        decoded_paths=decoded_paths,
        config=config,
    )

    artifact_paths: List[str] = [
        "output.json",
        "segments.jsonl",
        "observations.jsonl",
        "transitions.json",
    ]
    _write_segments(run_dir=run_dir, segments=segments)
    _write_observations(run_dir=run_dir, observations=observations)
    _write_transitions_json(run_dir=run_dir, transitions=transitions)
    if topic_report is not None:
        _write_topic_modeling_report(run_dir=run_dir, report=topic_report)
        _write_topic_assignments(run_dir=run_dir, observations=observations)
        artifact_paths.extend(["topic_modeling.json", "topic_assignments.jsonl"])

    if config.artifacts.graphviz.enabled:
        _write_graphviz(
            run_dir=run_dir,
            transitions=transitions,
            graphviz=config.artifacts.graphviz,
            states=states,
            decoded_paths=decoded_paths,
        )
        artifact_paths.append("transitions.dot")

    warnings = list(text_report.warnings)
    errors = list(text_report.errors)
    if topic_report is not None:
        warnings.extend(topic_report.warnings)
        errors.extend(topic_report.errors)

    report = MarkovAnalysisReport(
        text_collection=text_report,
        status=MarkovAnalysisStageStatus.COMPLETE,
        states=states,
        transitions=transitions,
        decoded_paths=decoded_paths,
        topic_modeling=topic_report,
        warnings=warnings,
        errors=errors,
    )

    run_stats = {
        "items": len({doc.item_id for doc in documents}),
        "segments": len(segments),
        "states": len(states),
        "transitions": len(transitions),
    }
    if topic_report is not None:
        run_stats["topics"] = len(topic_report.topics)
    run_manifest = run_manifest.model_copy(
        update={"artifact_paths": artifact_paths, "stats": run_stats}
    )
    _write_analysis_run_manifest(run_dir=run_dir, manifest=run_manifest)

    output = MarkovAnalysisOutput(
        analysis_id=MarkovBackend.analysis_id,
        generated_at=utc_now_iso(),
        run=run_manifest,
        report=report,
    )
    (run_dir / "output.json").write_text(output.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output


def _create_recipe_manifest(
    *, name: str, config: MarkovAnalysisRecipeConfig
) -> AnalysisRecipeManifest:
    recipe_payload = json.dumps(
        {
            "analysis_id": MarkovBackend.analysis_id,
            "name": name,
            "config": config.model_dump(),
        },
        sort_keys=True,
    )
    recipe_id = hash_text(recipe_payload)
    return AnalysisRecipeManifest(
        recipe_id=recipe_id,
        analysis_id=MarkovBackend.analysis_id,
        name=name,
        created_at=utc_now_iso(),
        config=config.model_dump(),
    )


def _analysis_run_id(
    *, recipe_id: str, extraction_run: ExtractionRunReference, catalog_generated_at: str
) -> str:
    run_seed = f"{recipe_id}:{extraction_run.as_string()}:{catalog_generated_at}"
    return hash_text(run_seed)


def _collect_documents(
    *,
    corpus: Corpus,
    extraction_run: ExtractionRunReference,
    config: MarkovAnalysisTextSourceConfig,
) -> Tuple[List[_Document], MarkovAnalysisTextCollectionReport]:
    manifest = corpus.load_extraction_run_manifest(
        extractor_id=extraction_run.extractor_id,
        run_id=extraction_run.run_id,
    )
    warnings: List[str] = []
    errors: List[str] = []
    documents: List[_Document] = []
    skipped_items = 0
    empty_texts = 0

    run_root = corpus.extraction_run_dir(
        extractor_id=extraction_run.extractor_id,
        run_id=extraction_run.run_id,
    )
    for item_result in manifest.items:
        if item_result.status != "extracted" or item_result.final_text_relpath is None:
            skipped_items += 1
            continue
        text_path = run_root / item_result.final_text_relpath
        text_value = text_path.read_text(encoding="utf-8").strip()
        if not text_value:
            empty_texts += 1
            continue
        if config.min_text_characters is not None and len(text_value) < config.min_text_characters:
            skipped_items += 1
            continue
        documents.append(_Document(item_id=item_result.item_id, text=text_value))

    if config.sample_size is not None and len(documents) > config.sample_size:
        documents = documents[: config.sample_size]
        warnings.append("Text collection truncated to sample_size")

    report = MarkovAnalysisTextCollectionReport(
        status=MarkovAnalysisStageStatus.COMPLETE,
        source_items=len(manifest.items),
        documents=len(documents),
        sample_size=config.sample_size,
        min_text_characters=config.min_text_characters,
        empty_texts=empty_texts,
        skipped_items=skipped_items,
        warnings=warnings,
        errors=errors,
    )
    if not documents:
        report = report.model_copy(update={"status": MarkovAnalysisStageStatus.FAILED})
        raise ValueError("Markov analysis requires at least one extracted text document")
    return documents, report


def _segment_documents(
    *, documents: Sequence[_Document], config: MarkovAnalysisRecipeConfig
) -> List[MarkovAnalysisSegment]:
    segments: List[MarkovAnalysisSegment] = []
    method = config.segmentation.method
    for document in documents:
        if method == MarkovAnalysisSegmentationMethod.SENTENCE:
            segments.extend(_sentence_segments(item_id=document.item_id, text=document.text))
            continue
        if method == MarkovAnalysisSegmentationMethod.FIXED_WINDOW:
            segments.extend(
                _fixed_window_segments(
                    item_id=document.item_id,
                    text=document.text,
                    max_characters=config.segmentation.fixed_window.max_characters,
                    overlap_characters=config.segmentation.fixed_window.overlap_characters,
                )
            )
            continue
        if method == MarkovAnalysisSegmentationMethod.LLM:
            segments.extend(
                _llm_segments(item_id=document.item_id, text=document.text, config=config)
            )
            continue
        if method == MarkovAnalysisSegmentationMethod.SPAN_MARKUP:
            segments.extend(
                _span_markup_segments(item_id=document.item_id, text=document.text, config=config)
            )
            continue
        raise ValueError(f"Unsupported segmentation method: {method}")
    if not segments:
        raise ValueError("Markov analysis produced no segments")
    return _add_boundary_segments(segments=segments)


def _add_boundary_segments(
    *, segments: Sequence[MarkovAnalysisSegment]
) -> List[MarkovAnalysisSegment]:
    """
    Add synthetic START/END boundary segments for each item sequence.

    This is a deterministic, programmatic boundary signal that keeps the LLM
    segmentation focused only on natural text phases. We insert:
    - a leading START segment per item
    - a trailing END segment per item

    These boundaries are added after segmentation for all methods (sentence,
    fixed-window, llm, span-markup) so the model never has to edit or reason
    about them during extraction.

    :param segments: Ordered segments grouped by item_id.
    :type segments: Sequence[MarkovAnalysisSegment]
    :return: Segments with START/END boundaries per item.
    :rtype: list[MarkovAnalysisSegment]
    """
    if not segments:
        return []
    enriched: List[MarkovAnalysisSegment] = []
    current_item: Optional[str] = None
    buffer: List[MarkovAnalysisSegment] = []

    def flush() -> None:
        item_id = buffer[0].item_id
        index = 1
        enriched.append(MarkovAnalysisSegment(item_id=item_id, segment_index=index, text="START"))
        for segment in buffer:
            index += 1
            enriched.append(
                MarkovAnalysisSegment(item_id=item_id, segment_index=index, text=segment.text)
            )
        index += 1
        enriched.append(MarkovAnalysisSegment(item_id=item_id, segment_index=index, text="END"))

    for segment in segments:
        if current_item is None:
            current_item = segment.item_id
        if segment.item_id != current_item:
            flush()
            buffer = []
            current_item = segment.item_id
        buffer.append(segment)
    flush()
    return enriched


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentence_segments(*, item_id: str, text: str) -> List[MarkovAnalysisSegment]:
    tokens = [token.strip() for token in _SENTENCE_SPLIT.split(text) if token.strip()]
    segments: List[MarkovAnalysisSegment] = []
    for index, token in enumerate(tokens, start=1):
        segments.append(
            MarkovAnalysisSegment(
                item_id=item_id,
                segment_index=index,
                text=token,
            )
        )
    return segments


def _fixed_window_segments(
    *, item_id: str, text: str, max_characters: int, overlap_characters: int
) -> List[MarkovAnalysisSegment]:
    segments: List[MarkovAnalysisSegment] = []
    if max_characters <= 0:
        raise ValueError("fixed_window.max_characters must be positive")
    if overlap_characters < 0:
        raise ValueError("fixed_window.overlap_characters must be non-negative")
    if overlap_characters >= max_characters:
        raise ValueError("fixed_window.overlap_characters must be smaller than max_characters")

    start = 0
    index = 1
    while start < len(text):
        end = min(len(text), start + max_characters)
        chunk = text[start:end].strip()
        if chunk:
            segments.append(MarkovAnalysisSegment(item_id=item_id, segment_index=index, text=chunk))
            index += 1
        if end >= len(text):
            break
        start = max(0, end - overlap_characters)
    return segments


def _llm_segments(
    *, item_id: str, text: str, config: MarkovAnalysisRecipeConfig
) -> List[MarkovAnalysisSegment]:
    llm_config = config.segmentation.llm
    if llm_config is None:
        raise ValueError("segmentation.llm is required when segmentation.method is 'llm'")
    prompt = llm_config.prompt_template.format(text=text)
    response_text = generate_completion(
        client=llm_config.client,
        system_prompt=llm_config.system_prompt,
        user_prompt=prompt,
    ).strip()
    if llm_config.client.response_format == "json_object":
        payload = _parse_json_object(response_text, error_label="LLM segmentation")
        segments_payload = payload.get("segments")
        if not isinstance(segments_payload, list):
            raise ValueError("LLM segmentation must return a JSON object with a 'segments' list")
    else:
        segments_payload = _parse_json_list(response_text, error_label="LLM segmentation")
    segments: List[MarkovAnalysisSegment] = []
    for index, value in enumerate(segments_payload, start=1):
        segment_text = str(value).strip()
        if not segment_text:
            continue
        segments.append(
            MarkovAnalysisSegment(item_id=item_id, segment_index=index, text=segment_text)
        )
    return segments


def _span_markup_segments(
    *, item_id: str, text: str, config: MarkovAnalysisRecipeConfig
) -> List[MarkovAnalysisSegment]:
    markup_config = config.segmentation.span_markup
    if markup_config is None:
        raise ValueError(
            "segmentation.span_markup is required when segmentation.method is 'span_markup'"
        )
    label_attribute = markup_config.label_attribute
    prepend_label = markup_config.prepend_label
    if label_attribute is not None or prepend_label:
        request = TextAnnotateRequest(
            text=text,
            client=markup_config.client,
            prompt_template=markup_config.prompt_template,
            system_prompt=markup_config.system_prompt,
            allowed_attributes=[label_attribute] if label_attribute else None,
            max_rounds=markup_config.max_rounds,
            max_edits_per_round=markup_config.max_edits_per_round,
        )
        result = apply_text_annotate(request)
    else:
        request = TextExtractRequest(
            text=text,
            client=markup_config.client,
            prompt_template=markup_config.prompt_template,
            system_prompt=markup_config.system_prompt,
            max_rounds=markup_config.max_rounds,
            max_edits_per_round=markup_config.max_edits_per_round,
        )
        result = apply_text_extract(request)
    segment_payloads: List[Dict[str, object]] = []
    for index, span in enumerate(result.spans, start=1):
        segment_body = str(span.text).strip()
        if not segment_body:
            continue
        segment_text = segment_body
        if prepend_label:
            if label_attribute is None:
                raise ValueError(
                    "segmentation.span_markup.label_attribute is required when "
                    "segmentation.span_markup.prepend_label is true"
                )
            label_value = str(span.attributes.get(label_attribute, "")).strip()
            if not label_value:
                raise ValueError(f"Span {index} missing label attribute '{label_attribute}'")
            segment_text = f"{label_value}\n{segment_body}"
        segment_payloads.append(
            {"segment_index": index, "body": segment_body, "text": segment_text}
        )
    segments: List[MarkovAnalysisSegment] = []
    for payload in segment_payloads:
        segments.append(
            MarkovAnalysisSegment(
                item_id=item_id,
                segment_index=int(payload["segment_index"]),
                text=str(payload["text"]),
            )
        )
    return segments


def _verify_end_label(
    *, text: str, config: MarkovAnalysisRecipeConfig
) -> Optional[Dict[str, object]]:
    markup_config = config.segmentation.span_markup
    if markup_config is None or markup_config.end_label_verifier is None:
        return None
    verifier = markup_config.end_label_verifier
    system_prompt = verifier.system_prompt.replace("{text}", text)
    user_prompt = verifier.prompt_template.replace("{text}", text)
    response_text = generate_completion(
        client=verifier.client,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    ).strip()
    payload = _parse_json_object(response_text, error_label="End label verifier")
    return {
        "is_end": bool(payload.get("is_end")),
        "reason": payload.get("reason"),
    }


def _apply_start_end_labels(
    *,
    item_id: str,
    payloads: Sequence[Dict[str, object]],
    config: MarkovAnalysisRecipeConfig,
) -> List[MarkovAnalysisSegment]:
    markup_config = config.segmentation.span_markup
    if markup_config is None:
        raise ValueError("segmentation.span_markup is required for start/end labels")
    segments: List[MarkovAnalysisSegment] = []
    for payload in payloads:
        segment_text = str(payload.get("text") or payload.get("body") or "").strip()
        if not segment_text:
            continue
        segments.append(
            MarkovAnalysisSegment(
                item_id=item_id,
                segment_index=int(payload.get("segment_index") or len(segments) + 1),
                text=segment_text,
            )
        )
    if not segments:
        return segments
    if markup_config.start_label_value:
        segments[0] = segments[0].model_copy(
            update={"text": f"{markup_config.start_label_value}\n{segments[0].text}"}
        )
    if markup_config.end_label_value:
        decision = _verify_end_label(text=segments[-1].text, config=config)
        if decision and decision.get("is_end"):
            segments[-1] = segments[-1].model_copy(
                update={"text": f"{markup_config.end_label_value}\n{segments[-1].text}"}
            )
        elif decision and not decision.get("is_end") and markup_config.end_reject_label_value:
            reason = decision.get("reason")
            prefix = markup_config.end_reject_label_value
            if reason:
                prefix = f"{prefix}\n{markup_config.end_reject_reason_prefix}: {reason}"
            segments[-1] = segments[-1].model_copy(
                update={"text": f"{prefix}\n{segments[-1].text}"}
            )
    return segments


def _parse_json_list(raw: str, *, error_label: str) -> List[object]:
    cleaned = str(raw or "").strip()
    if not cleaned:
        raise ValueError(f"{error_label} returned empty output")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{error_label} returned invalid JSON") from exc
    if not isinstance(data, list):
        raise ValueError(f"{error_label} must return a JSON list")
    return list(data)


def _parse_json_object(raw: str, *, error_label: str) -> Dict[str, object]:
    cleaned = str(raw or "").strip()
    if not cleaned:
        raise ValueError(f"{error_label} returned empty output")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{error_label} returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{error_label} must return a JSON object")
    return dict(data)


def _sequence_lengths(segments: Sequence[MarkovAnalysisSegment]) -> List[int]:
    lengths: List[int] = []
    current_item: str = ""
    current_length = 0
    for segment in segments:
        if not current_item:
            current_item = segment.item_id
            current_length = 0
        elif segment.item_id != current_item:
            lengths.append(current_length)
            current_item = segment.item_id
            current_length = 0
        current_length += 1
    if current_item:
        lengths.append(current_length)
    return lengths


def _build_observations(
    *, segments: Sequence[MarkovAnalysisSegment], config: MarkovAnalysisRecipeConfig
) -> List[MarkovAnalysisObservation]:
    observations: List[MarkovAnalysisObservation] = []
    for segment in segments:
        observations.append(
            MarkovAnalysisObservation(
                item_id=segment.item_id,
                segment_index=segment.segment_index,
                segment_text=segment.text,
            )
        )

    if config.llm_observations.enabled:
        llm = config.llm_observations
        assert llm.client is not None and llm.prompt_template is not None
        for index, observation in enumerate(observations):
            if observation.segment_text in {"START", "END"}:
                observations[index] = observation.model_copy(
                    update={
                        "llm_label": observation.segment_text,
                        "llm_label_confidence": 1.0,
                        "llm_summary": observation.segment_text,
                    }
                )
                continue
            prompt = llm.prompt_template.format(segment=observation.segment_text)
            response_text = generate_completion(
                client=llm.client,
                system_prompt=llm.system_prompt,
                user_prompt=prompt,
            ).strip()
            payload = _parse_json_object(response_text, error_label="LLM observations")
            label = payload.get("label")
            confidence = payload.get("label_confidence")
            summary = payload.get("summary")
            observations[index] = observation.model_copy(
                update={
                    "llm_label": str(label).strip() if label is not None else None,
                    "llm_label_confidence": float(confidence) if confidence is not None else None,
                    "llm_summary": str(summary).strip() if summary is not None else None,
                }
            )

    if config.embeddings.enabled:
        embedding_config = config.embeddings
        assert embedding_config.client is not None
        embed_indices: List[int] = []
        embed_texts: List[str] = []
        for index, observation in enumerate(observations):
            if observation.segment_text in {"START", "END"}:
                continue
            embed_indices.append(index)
            if embedding_config.text_source == "segment_text":
                embed_texts.append(observation.segment_text)
            else:
                if not observation.llm_summary:
                    raise ValueError(
                        "embeddings.text_source is 'llm_summary' but llm_summary is missing"
                    )
                embed_texts.append(observation.llm_summary)

        if not embed_indices:
            raise ValueError("Embeddings require at least one non-boundary segment")

        vectors = generate_embeddings_batch(client=embedding_config.client, texts=embed_texts)
        if len(vectors) != len(embed_indices):
            raise ValueError(
                "Embedding provider returned unexpected vector count: "
                f"expected {len(embed_indices)} but got {len(vectors)}"
            )

        vector_by_observation_index: Dict[int, List[float]] = {}
        for observation_index, vector in zip(embed_indices, vectors):
            vector_by_observation_index[observation_index] = list(vector)

        embedding_dimension = len(next(iter(vector_by_observation_index.values())))
        boundary_embedding = [0.0 for _ in range(embedding_dimension)]
        updated: List[MarkovAnalysisObservation] = []
        for index, observation in enumerate(observations):
            vector = vector_by_observation_index.get(index)
            updated.append(
                observation.model_copy(update={"embedding": vector or boundary_embedding})
            )
        observations = updated

    return observations


def _topic_document_id(*, item_id: str, segment_index: int) -> str:
    return f"{item_id}:{segment_index}"


def _apply_topic_modeling(
    *,
    observations: Sequence[MarkovAnalysisObservation],
    config: MarkovAnalysisRecipeConfig,
) -> Tuple[List[MarkovAnalysisObservation], Optional[TopicModelingReport]]:
    topic_config = config.topic_modeling
    if not topic_config.enabled:
        return list(observations), None
    if topic_config.recipe is None:
        raise ValueError("topic_modeling.recipe is required when topic_modeling.enabled is true")

    documents: List[TopicModelingDocument] = []
    for observation in observations:
        if observation.segment_text in {"START", "END"}:
            continue
        documents.append(
            TopicModelingDocument(
                document_id=_topic_document_id(
                    item_id=observation.item_id,
                    segment_index=observation.segment_index,
                ),
                source_item_id=observation.item_id,
                text=observation.segment_text,
            )
        )

    if not documents:
        raise ValueError("Topic modeling requires at least one non-boundary segment")

    report = run_topic_modeling_for_documents(
        documents=documents,
        config=topic_config.recipe,
    )

    topic_lookup: Dict[str, Tuple[int, str]] = {}
    for topic in report.topics:
        label = str(topic.label or "").strip()
        for document_id in topic.document_ids:
            topic_lookup[str(document_id)] = (int(topic.topic_id), label)

    updated: List[MarkovAnalysisObservation] = []
    for observation in observations:
        if observation.segment_text in {"START", "END"}:
            updated.append(
                observation.model_copy(
                    update={
                        "topic_id": None,
                        "topic_label": observation.segment_text,
                    }
                )
            )
            continue
        document_id = _topic_document_id(
            item_id=observation.item_id, segment_index=observation.segment_index
        )
        assignment = topic_lookup.get(document_id)
        if assignment is None:
            raise ValueError(
                f"Topic modeling did not return an assignment for segment {document_id}"
            )
        topic_id, topic_label = assignment
        updated.append(
            observation.model_copy(update={"topic_id": topic_id, "topic_label": topic_label})
        )
    return updated, report


def _encode_observations(
    *, observations: Sequence[MarkovAnalysisObservation], config: MarkovAnalysisRecipeConfig
) -> Tuple[object, List[int]]:
    lengths = _sequence_lengths(
        [
            MarkovAnalysisSegment(
                item_id=observation.item_id,
                segment_index=observation.segment_index,
                text=observation.segment_text,
            )
            for observation in observations
        ]
    )

    if config.model.family == MarkovAnalysisModelFamily.CATEGORICAL:
        labels: List[str] = []
        for observation in observations:
            label = getattr(observation, config.observations.categorical_source, None)
            if label is None:
                raise ValueError(
                    "Categorical Markov models require categorical labels for all segments"
                )
            labels.append(str(label))
        vocabulary = {label: idx for idx, label in enumerate(sorted(set(labels)))}
        encoded = [vocabulary[label] for label in labels]
        return encoded, lengths

    encoder = config.observations.encoder
    if encoder == MarkovAnalysisObservationsEncoder.TFIDF:
        texts: List[str] = []
        for observation in observations:
            if config.observations.text_source == "segment_text":
                texts.append(observation.segment_text)
            else:
                texts.append(observation.llm_summary or "")
        return (
            _tfidf_encode(
                texts=texts,
                max_features=config.observations.tfidf.max_features,
                ngram_range=tuple(config.observations.tfidf.ngram_range),
            ),
            lengths,
        )
    if encoder == MarkovAnalysisObservationsEncoder.EMBEDDING:
        matrix: List[List[float]] = []
        for observation in observations:
            if observation.embedding is None:
                raise ValueError("Embedding observations require embeddings.enabled true")
            matrix.append([float(value) for value in observation.embedding])
        return matrix, lengths
    if encoder == MarkovAnalysisObservationsEncoder.HYBRID:
        labels = [
            str(getattr(observation, config.observations.categorical_source, "") or "")
            for observation in observations
        ]
        vocabulary = {label: idx for idx, label in enumerate(sorted(set(labels)))}
        one_hot_size = len(vocabulary)
        matrix: List[List[float]] = []
        for observation in observations:
            if observation.embedding is None:
                raise ValueError("Hybrid observations require embeddings.enabled true")
            vector: List[float] = [float(value) for value in observation.embedding]
            numeric_value = getattr(observation, config.observations.numeric_source, None)
            confidence = float(numeric_value) if numeric_value is not None else 0.0
            vector.append(confidence)
            one_hot = [0.0 for _ in range(one_hot_size)]
            label_value = str(
                getattr(observation, config.observations.categorical_source, "") or ""
            )
            idx = vocabulary[label_value]
            one_hot[idx] = 1.0
            vector.extend(one_hot)
            matrix.append(vector)
        return matrix, lengths
    raise ValueError(f"Unsupported observations encoder: {encoder}")


def _tokenize(text: str) -> List[str]:
    return [token for token in re.split(r"[^A-Za-z0-9]+", text.lower()) if token]


def _tfidf_encode(
    *, texts: Sequence[str], max_features: int, ngram_range: Tuple[int, int]
) -> List[List[float]]:
    if max_features <= 0:
        raise ValueError("tfidf.max_features must be positive")
    min_n, max_n = ngram_range
    if min_n <= 0 or max_n < min_n:
        raise ValueError("tfidf.ngram_range is invalid")

    documents: List[List[str]] = []
    for text in texts:
        tokens = _tokenize(text)
        ngrams: List[str] = []
        for n in range(min_n, max_n + 1):
            for idx in range(0, max(0, len(tokens) - n + 1)):
                ngrams.append(" ".join(tokens[idx : idx + n]))
        documents.append(ngrams)

    df: Dict[str, int] = {}
    for doc in documents:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1

    sorted_terms = sorted(df.items(), key=lambda item: (-item[1], item[0]))
    vocabulary = [term for term, _ in sorted_terms[:max_features]]
    index = {term: idx for idx, term in enumerate(vocabulary)}

    n_docs = max(1, len(documents))
    idf: List[float] = []
    for term in vocabulary:
        count = df.get(term, 0)
        idf.append(float((n_docs + 1) / (count + 1)))

    vectors: List[List[float]] = []
    for doc in documents:
        tf: Dict[int, int] = {}
        for term in doc:
            term_idx = index.get(term)
            if term_idx is None:
                continue
            tf[term_idx] = tf.get(term_idx, 0) + 1
        length = sum(tf.values()) or 1
        vector = [0.0 for _ in vocabulary]
        for term_idx, count in tf.items():
            vector[term_idx] = (float(count) / float(length)) * idf[term_idx]
        vectors.append(vector)
    return vectors


def _fit_and_decode(
    *, observations: object, lengths: List[int], config: MarkovAnalysisRecipeConfig
) -> Tuple[List[int], List[MarkovAnalysisTransition], int]:
    def normalize_startprob(values: Sequence[float]) -> List[float]:
        cleaned = [float(value) if math.isfinite(float(value)) else 0.0 for value in values]
        total = sum(cleaned)
        if total <= 0.0:
            return [1.0 / float(len(cleaned)) for _ in cleaned]
        return [value / total for value in cleaned]

    def normalize_transmat(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
        normalized: List[List[float]] = []
        size = len(matrix)
        for row in matrix:
            cleaned = [float(value) if math.isfinite(float(value)) else 0.0 for value in row]
            total = sum(cleaned)
            if total <= 0.0:
                normalized.append([1.0 / float(size) for _ in cleaned])
            else:
                normalized.append([value / total for value in cleaned])
        return normalized

    family = config.model.family
    try:
        from hmmlearn.hmm import CategoricalHMM, GaussianHMM
    except ImportError as import_error:
        raise ValueError(
            "Markov analysis requires an optional dependency. "
            'Install it with pip install "biblicus[markov-analysis]".'
        ) from import_error

    if family == MarkovAnalysisModelFamily.CATEGORICAL:
        encoded = list(observations)  # type: ignore[arg-type]
        X: object = [[int(value)] for value in encoded]
        try:
            import numpy as np

            X = np.asarray(X, dtype=int)
        except ImportError:
            pass
        model = CategoricalHMM(n_components=config.model.n_states)
        model.fit(X, lengths=lengths)
        if hasattr(model, "startprob_"):
            startprob = normalize_startprob(model.startprob_)
            try:
                import numpy as np

                model.startprob_ = np.asarray(startprob, dtype=float)
            except ImportError:
                model.startprob_ = startprob
        if hasattr(model, "transmat_"):
            transmat = normalize_transmat(model.transmat_)
            try:
                import numpy as np

                model.transmat_ = np.asarray(transmat, dtype=float)
            except ImportError:
                model.transmat_ = transmat
        predicted = list(model.predict(X, lengths=lengths))
    else:
        matrix = list(observations)  # type: ignore[arg-type]
        X = matrix
        try:
            import numpy as np

            X = np.asarray(matrix, dtype=float)
        except ImportError:
            pass
        model = GaussianHMM(n_components=config.model.n_states)
        model.fit(X, lengths=lengths)
        if hasattr(model, "startprob_"):
            startprob = normalize_startprob(model.startprob_)
            try:
                import numpy as np

                model.startprob_ = np.asarray(startprob, dtype=float)
            except ImportError:
                model.startprob_ = startprob
        if hasattr(model, "transmat_"):
            transmat = normalize_transmat(model.transmat_)
            try:
                import numpy as np

                model.transmat_ = np.asarray(transmat, dtype=float)
            except ImportError:
                model.transmat_ = transmat
        predicted = list(model.predict(X, lengths=lengths))

    transitions: List[MarkovAnalysisTransition] = []
    transmat = getattr(model, "transmat_", None)
    if transmat is not None:
        for from_state in range(len(transmat)):
            row = transmat[from_state]
            for to_state in range(len(row)):
                weight = float(row[to_state])
                if weight <= 0.0:
                    continue
                transitions.append(
                    MarkovAnalysisTransition(
                        from_state=from_state,
                        to_state=to_state,
                        weight=weight,
                    )
                )
    else:
        transitions = _transitions_from_sequence(predicted)

    return predicted, transitions, config.model.n_states


def _transitions_from_sequence(states: Sequence[int]) -> List[MarkovAnalysisTransition]:
    counts: Dict[Tuple[int, int], int] = {}
    totals: Dict[int, int] = {}
    for prev, nxt in zip(states, states[1:]):
        counts[(prev, nxt)] = counts.get((prev, nxt), 0) + 1
        totals[prev] = totals.get(prev, 0) + 1
    transitions: List[MarkovAnalysisTransition] = []
    for (prev, nxt), count in sorted(counts.items()):
        denom = max(1, totals.get(prev, 0))
        transitions.append(
            MarkovAnalysisTransition(
                from_state=prev, to_state=nxt, weight=float(count) / float(denom)
            )
        )
    return transitions


def _group_decoded_paths(
    *, segments: Sequence[MarkovAnalysisSegment], predicted_states: Sequence[int]
) -> List[MarkovAnalysisDecodedPath]:
    paths: Dict[str, List[int]] = {}
    for segment, state in zip(segments, predicted_states):
        paths.setdefault(segment.item_id, []).append(int(state))
    return [
        MarkovAnalysisDecodedPath(item_id=item_id, state_sequence=sequence)
        for item_id, sequence in sorted(paths.items())
    ]


def _build_states(
    *,
    segments: Sequence[MarkovAnalysisSegment],
    predicted_states: Sequence[int],
    n_states: int,
    max_exemplars: int,
) -> List[MarkovAnalysisState]:
    exemplars: Dict[int, List[str]] = {idx: [] for idx in range(n_states)}
    for segment, state in zip(segments, predicted_states):
        exemplar_list = exemplars.get(int(state))
        if exemplar_list is None:
            continue
        boundary_token = str(segment.text).strip().upper()
        if boundary_token in {"START", "END"} and boundary_token not in exemplar_list:
            if max_exemplars > 0 and len(exemplar_list) >= max_exemplars:
                exemplar_list[-1] = boundary_token
                continue
            exemplar_list.append(boundary_token)
            continue
        if len(exemplar_list) >= max_exemplars:
            continue
        exemplar_list.append(segment.text)
    states: List[MarkovAnalysisState] = []
    for state_id in range(n_states):
        states.append(
            MarkovAnalysisState(
                state_id=state_id,
                label=None,
                exemplars=exemplars.get(state_id, []),
            )
        )
    return states


def _state_naming_context_pack(
    *,
    states: Sequence[MarkovAnalysisState],
    config: MarkovAnalysisRecipeConfig,
    position_stats: Optional[Dict[int, Dict[str, float]]] = None,
) -> Tuple[ContextPack, ContextPackPolicy]:
    naming = config.report.state_naming
    if naming is None or not naming.enabled:
        return ContextPack(text="", evidence_count=0, blocks=[]), ContextPackPolicy()
    evidence: List[Evidence] = []
    rank = 1
    for state in states:
        stats = (position_stats or {}).get(state.state_id)
        if stats:
            after_start = stats.get("after_start_pct", 0.0) * 100.0
            before_end = stats.get("before_end_pct", 0.0) * 100.0
            avg_position = stats.get("avg_position_pct", 0.0) * 100.0
            hint_text = (
                "Position hints:\n"
                f"- After START: {after_start:.1f}% of transitions from START\n"
                f"- Before END: {before_end:.1f}% of transitions to END\n"
                f"- Average position: {avg_position:.1f}% of call length"
            )
            evidence.append(
                Evidence(
                    item_id=f"state-{state.state_id}",
                    source_uri=None,
                    media_type="text/plain",
                    score=1.0,
                    rank=rank,
                    text=f"State {state.state_id}:\n{hint_text}",
                    stage="state-naming",
                    stage_scores=None,
                    recipe_id="state-naming",
                    run_id="state-naming",
                    hash=None,
                )
            )
            rank += 1
        exemplars = list(state.exemplars)[: naming.max_exemplars_per_state]
        for index, exemplar in enumerate(exemplars, start=1):
            text = f"State {state.state_id} exemplar {index}:\n{exemplar}"
            evidence.append(
                Evidence(
                    item_id=f"state-{state.state_id}",
                    source_uri=None,
                    media_type="text/plain",
                    score=1.0,
                    rank=rank,
                    text=text,
                    stage="state-naming",
                    stage_scores=None,
                    recipe_id="state-naming",
                    run_id="state-naming",
                    hash=None,
                )
            )
            rank += 1
    retrieval_result = RetrievalResult(
        query_text="state-naming",
        budget=QueryBudget(max_total_items=max(len(evidence), 1)),
        run_id="state-naming",
        recipe_id="state-naming",
        backend_id="state-naming",
        generated_at=utc_now_iso(),
        evidence=evidence,
        stats={},
    )
    policy = ContextPackPolicy(join_with="\n\n", ordering="rank", include_metadata=False)
    context_pack = build_context_pack(retrieval_result, policy=policy)
    fitted_pack = fit_context_pack_to_token_budget(
        context_pack,
        policy=policy,
        token_budget=TokenBudget(max_tokens=naming.token_budget),
    )
    return fitted_pack, policy


def _validate_state_names(
    *,
    response: MarkovStateNamingResponse,
    state_ids: Sequence[int],
    max_name_words: int,
) -> Dict[int, str]:
    def require_short_noun_phrase(name: str, max_words: int) -> None:
        raw_name = str(name).strip()
        tokens = [token for token in raw_name.split() if token]
        word_count = len(tokens)
        if word_count == 0 or word_count > max_words:
            raise ValueError("State names must be short noun phrases")
        if any(symbol in raw_name for symbol in (".", "!", "?", ":", ";")):
            raise ValueError("State names must be short noun phrases without sentence punctuation")
        lower_tokens = [token.lower() for token in tokens]
        if lower_tokens[0] in ("to", "please"):
            raise ValueError("State names must be short noun phrases")
        forbidden_auxiliaries = {
            "am",
            "are",
            "be",
            "been",
            "being",
            "is",
            "was",
            "were",
            "can",
            "could",
            "do",
            "does",
            "did",
            "doing",
            "have",
            "has",
            "had",
            "having",
            "may",
            "might",
            "must",
            "shall",
            "should",
            "will",
            "would",
        }
        if any(token in forbidden_auxiliaries for token in lower_tokens):
            raise ValueError("State names must be short noun phrases without verbs")

    names: Dict[int, str] = {}
    seen_names: Dict[str, int] = {}
    for entry in response.state_names:
        raw_name = str(entry.name).strip()
        require_short_noun_phrase(raw_name, max_name_words)
        if entry.state_id in names:
            raise ValueError("State naming response contains duplicate state_id values")
        normalized = raw_name.lower()
        if normalized in seen_names:
            raise ValueError("State naming response contains duplicate state names")
        names[entry.state_id] = raw_name
        seen_names[normalized] = entry.state_id
    missing = [state_id for state_id in state_ids if state_id not in names]
    if missing:
        raise ValueError("State naming response missing required state_id values")
    return names


def _assign_state_names(
    *,
    states: Sequence[MarkovAnalysisState],
    decoded_paths: Sequence[MarkovAnalysisDecodedPath],
    config: MarkovAnalysisRecipeConfig,
) -> List[MarkovAnalysisState]:
    naming = config.report.state_naming
    if naming is None or not naming.enabled:
        return list(states)
    if naming.client is None:
        raise ValueError("report.state_naming.client is required when enabled")
    if not states:
        return list(states)
    start_state_id = _select_boundary_state_id(states=states, boundary_label="START")
    end_state_id = _select_boundary_state_id(states=states, boundary_label="END")
    sanitized_states = _strip_boundary_exemplars(
        states=states,
        boundary_label="START",
        allowed_state_id=start_state_id,
    )
    sanitized_states = _strip_boundary_exemplars(
        states=sanitized_states,
        boundary_label="END",
        allowed_state_id=end_state_id,
    )
    naming_states = [
        state for state in sanitized_states if state.state_id not in {start_state_id, end_state_id}
    ]
    if not naming_states:
        return _apply_boundary_labels(
            states=sanitized_states,
            start_state_id=start_state_id,
            end_state_id=end_state_id,
        )
    state_ids = [state.state_id for state in naming_states]
    position_stats = _compute_state_position_stats(
        decoded_paths=decoded_paths,
        start_state_id=start_state_id,
        end_state_id=end_state_id,
    )
    context_pack, _policy = _state_naming_context_pack(
        states=naming_states,
        config=config,
        position_stats=position_stats,
    )
    system_prompt = str(naming.system_prompt or "").format(context_pack=context_pack.text)
    user_prompt = str(naming.prompt_template or "").format(
        state_ids=", ".join(str(state_id) for state_id in state_ids),
        state_count=len(state_ids),
    )
    last_error: Optional[str] = None
    for attempt in range(naming.max_retries + 1):
        if last_error is not None:
            user_prompt = f"{user_prompt}\n\nPrevious response:\n{last_error}\n\nFix the issues and return only JSON."
        response_text = generate_completion(
            client=naming.client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ).strip()
        payload = _parse_json_object(response_text, error_label="Markov state naming")
        response = MarkovStateNamingResponse.model_validate(payload)
        try:
            names = _validate_state_names(
                response=response,
                state_ids=state_ids,
                max_name_words=naming.max_name_words,
            )
        except ValueError as exc:
            last_error = f"{response_text}\n\nError: {exc}"
            continue
        updated_states: List[MarkovAnalysisState] = []
        for state in sanitized_states:
            if start_state_id is not None and state.state_id == start_state_id:
                updated_states.append(state.model_copy(update={"label": "START"}))
                continue
            if end_state_id is not None and state.state_id == end_state_id:
                updated_states.append(state.model_copy(update={"label": "END"}))
                continue
            base_label = names.get(state.state_id)
            if base_label is None:
                updated_states.append(state)
                continue
            updated_states.append(state.model_copy(update={"label": base_label}))
        return updated_states
    error_text = last_error or "unknown error"
    raise ValueError(f"Markov state naming failed after retries: {error_text}")


def _select_boundary_state_id(
    *, states: Sequence[MarkovAnalysisState], boundary_label: str
) -> Optional[int]:
    candidates: List[Tuple[int, int, int]] = []
    normalized_label = boundary_label.strip().upper()
    for state in states:
        exemplars = [str(exemplar).strip().upper() for exemplar in (state.exemplars or [])]
        match_count = sum(1 for exemplar in exemplars if exemplar == normalized_label)
        if match_count:
            candidates.append((match_count, len(exemplars), state.state_id))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def _strip_boundary_exemplars(
    *,
    states: Sequence[MarkovAnalysisState],
    boundary_label: str,
    allowed_state_id: Optional[int],
) -> List[MarkovAnalysisState]:
    normalized_label = boundary_label.strip().upper()
    updated_states: List[MarkovAnalysisState] = []
    for state in states:
        exemplars = list(state.exemplars or [])
        if allowed_state_id is None or state.state_id != allowed_state_id:
            exemplars = [
                exemplar
                for exemplar in exemplars
                if str(exemplar).strip().upper() != normalized_label
            ]
        updated_states.append(state.model_copy(update={"exemplars": exemplars}))
    return updated_states


def _apply_boundary_labels(
    *,
    states: Sequence[MarkovAnalysisState],
    start_state_id: Optional[int],
    end_state_id: Optional[int],
) -> List[MarkovAnalysisState]:
    updated_states: List[MarkovAnalysisState] = []
    for state in states:
        if start_state_id is not None and state.state_id == start_state_id:
            updated_states.append(state.model_copy(update={"label": "START"}))
            continue
        if end_state_id is not None and state.state_id == end_state_id:
            updated_states.append(state.model_copy(update={"label": "END"}))
            continue
        updated_states.append(state)
    return updated_states


def _compute_state_position_stats(
    *,
    decoded_paths: Sequence[MarkovAnalysisDecodedPath],
    start_state_id: Optional[int],
    end_state_id: Optional[int],
) -> Dict[int, Dict[str, float]]:
    after_start_counts: Dict[int, int] = {}
    before_end_counts: Dict[int, int] = {}
    avg_position_sums: Dict[int, float] = {}
    avg_position_counts: Dict[int, int] = {}
    total_after_start = 0
    total_before_end = 0

    for path in decoded_paths:
        sequence = list(path.state_sequence)
        if len(sequence) < 2:
            continue
        last_index = max(1, len(sequence) - 1)
        for index, state_id in enumerate(sequence):
            if state_id in {start_state_id, end_state_id}:
                continue
            avg_position_sums[state_id] = avg_position_sums.get(state_id, 0.0) + (
                float(index) / float(last_index)
            )
            avg_position_counts[state_id] = avg_position_counts.get(state_id, 0) + 1
        for from_state, to_state in zip(sequence, sequence[1:]):
            if start_state_id is not None and from_state == start_state_id:
                total_after_start += 1
                after_start_counts[to_state] = after_start_counts.get(to_state, 0) + 1
            if end_state_id is not None and to_state == end_state_id:
                total_before_end += 1
                before_end_counts[from_state] = before_end_counts.get(from_state, 0) + 1

    stats: Dict[int, Dict[str, float]] = {}
    state_ids = set(avg_position_counts) | set(after_start_counts) | set(before_end_counts)
    for state_id in state_ids:
        avg_count = avg_position_counts.get(state_id, 0)
        stats[state_id] = {
            "after_start_pct": (
                after_start_counts.get(state_id, 0) / total_after_start
                if total_after_start
                else 0.0
            ),
            "before_end_pct": (
                before_end_counts.get(state_id, 0) / total_before_end if total_before_end else 0.0
            ),
            "avg_position_pct": (
                avg_position_sums.get(state_id, 0.0) / avg_count if avg_count else 0.0
            ),
        }
    return stats


def _write_analysis_run_manifest(*, run_dir: Path, manifest: AnalysisRunManifest) -> None:
    (run_dir / "manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


def _write_segments(*, run_dir: Path, segments: Sequence[MarkovAnalysisSegment]) -> None:
    lines = [segment.model_dump_json() for segment in segments]
    (run_dir / "segments.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_observations(
    *, run_dir: Path, observations: Sequence[MarkovAnalysisObservation]
) -> None:
    lines = [observation.model_dump_json() for observation in observations]
    (run_dir / "observations.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_transitions_json(
    *, run_dir: Path, transitions: Sequence[MarkovAnalysisTransition]
) -> None:
    payload = [transition.model_dump() for transition in transitions]
    (run_dir / "transitions.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _write_topic_modeling_report(*, run_dir: Path, report: TopicModelingReport) -> None:
    (run_dir / "topic_modeling.json").write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


def _write_topic_assignments(
    *,
    run_dir: Path,
    observations: Sequence[MarkovAnalysisObservation],
) -> None:
    lines: List[str] = []
    for observation in observations:
        payload = {
            "item_id": observation.item_id,
            "segment_index": observation.segment_index,
            "segment_text": observation.segment_text,
            "topic_id": observation.topic_id,
            "topic_label": observation.topic_label,
        }
        lines.append(json.dumps(payload, ensure_ascii=True))
    (run_dir / "topic_assignments.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_graphviz(
    *,
    run_dir: Path,
    transitions: Sequence[MarkovAnalysisTransition],
    graphviz: MarkovAnalysisArtifactsGraphVizConfig,
    states: Sequence[MarkovAnalysisState],
    decoded_paths: Sequence[MarkovAnalysisDecodedPath],
) -> None:
    """
    Write GraphViz transition output for Markov analysis.

    The exported edge labels are meant for humans, so they include two values
    when decoded paths are available:

    1) The empirical transition percentage derived from decoded paths, rendered
       as ``X.Y% (a/b)``, where ``a`` is the observed transition count and ``b``
       is the total number of transitions across all decoded sequences.
    2) The model transition probability, rendered as ``model Z.W%``. This is
       the HMM transition weight for the same edge.

    The empirical value makes it clear how many transitions were actually observed,
    while the model value shows what the fitted HMM believes. When no decoded paths
    are available, the label falls back to the model percentage only.

    Edges are filtered by ``graphviz.min_edge_weight`` using the empirical weight
    when possible; otherwise the model weight is used. This keeps the visualization
    faithful to observed sequences instead of solely model priors.

    :param run_dir: Directory where the ``transitions.dot`` file is written.
    :type run_dir: pathlib.Path
    :param transitions: Markov transition edges with model weights.
    :type transitions: Sequence[MarkovAnalysisTransition]
    :param graphviz: GraphViz export configuration.
    :type graphviz: MarkovAnalysisArtifactsGraphVizConfig
    :param states: Markov states with labels and exemplars.
    :type states: Sequence[MarkovAnalysisState]
    :param decoded_paths: Per-item decoded state sequences.
    :type decoded_paths: Sequence[MarkovAnalysisDecodedPath]
    :return: None. Writes ``transitions.dot`` to ``run_dir``.
    :rtype: None
    """

    def infer_state_id_by_label(
        labels: Dict[int, str],
        keywords: Tuple[str, ...],
        exemplars_by_state: Dict[int, int],
    ) -> Optional[int]:
        matches: List[int] = []
        for state_id, label in labels.items():
            normalized = label.lower()
            if any(keyword in normalized for keyword in keywords):
                matches.append(state_id)
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        return max(matches, key=lambda state_id: exemplars_by_state.get(state_id, 0))

    lines: List[str] = []
    lines.append("digraph markov {")
    rankdir = str(graphviz.rankdir or "LR").upper()
    lines.append(f'  rankdir="{rankdir}";')
    label_by_state: Dict[int, str] = {}
    exemplars_by_state: Dict[int, int] = {}
    exemplar_start: Dict[int, bool] = {}
    exemplar_end: Dict[int, bool] = {}
    for state in states:
        label_by_state[state.state_id] = str(state.label or "")
        exemplars_by_state[state.state_id] = len(state.exemplars or [])
        base_label = str(state.label or str(state.state_id))
        exemplar_start[state.state_id] = any(
            str(exemplar).strip().upper() == "START" for exemplar in (state.exemplars or [])
        )
        exemplar_end[state.state_id] = any(
            str(exemplar).strip().upper() == "END" for exemplar in (state.exemplars or [])
        )
        label = base_label
        safe_label = label.replace('"', '\\"')
        lines.append(f'  {state.state_id} [label="{safe_label}"];')
    start_state_id = graphviz.start_state_id
    end_state_id = graphviz.end_state_id
    if start_state_id is None:
        matching = [state_id for state_id, has in exemplar_start.items() if has]
        if matching:
            start_state_id = max(matching, key=lambda state_id: exemplars_by_state.get(state_id, 0))
        else:
            start_state_id = infer_state_id_by_label(
                label_by_state,
                ("start", "greeting", "opening"),
                exemplars_by_state,
            )
    if end_state_id is None:
        matching = [state_id for state_id, has in exemplar_end.items() if has]
        if matching:
            end_state_id = max(matching, key=lambda state_id: exemplars_by_state.get(state_id, 0))
        else:
            end_state_id = infer_state_id_by_label(
                label_by_state,
                ("end", "closing", "goodbye", "wrap-up"),
                exemplars_by_state,
            )
    if start_state_id is not None:
        lines.append(f"  {{ rank=min; {start_state_id}; }}")
        lines.append(
            f'  {start_state_id} [shape="ellipse", peripheries=2, style="bold", color="#2b8a3e"];'
        )
    if end_state_id is not None:
        lines.append(f"  {{ rank=max; {end_state_id}; }}")
        lines.append(f'  {end_state_id} [shape="ellipse", peripheries=2, color="#b42318"];')
    observed_counts: Dict[Tuple[int, int], int] = {}
    observed_totals_by_state: Dict[int, int] = {}
    for path in decoded_paths:
        sequence = list(path.state_sequence)
        for from_state, to_state in zip(sequence, sequence[1:]):
            observed_counts[(from_state, to_state)] = (
                observed_counts.get((from_state, to_state), 0) + 1
            )
            observed_totals_by_state[from_state] = observed_totals_by_state.get(from_state, 0) + 1

    for transition in transitions:
        if end_state_id is not None and transition.from_state == end_state_id:
            continue
        observed_count = observed_counts.get((transition.from_state, transition.to_state), 0)
        observed_total = observed_totals_by_state.get(transition.from_state, 0)
        observed_weight = observed_count / observed_total if observed_total else transition.weight
        if observed_total and observed_count == 0:
            continue
        if observed_weight < graphviz.min_edge_weight:
            continue
        label = f"{observed_weight * 100.0:.1f}%"
        lines.append(f'  {transition.from_state} -> {transition.to_state} [label="{label}"];')
    lines.append("}")
    (run_dir / "transitions.dot").write_text("\n".join(lines) + "\n", encoding="utf-8")
