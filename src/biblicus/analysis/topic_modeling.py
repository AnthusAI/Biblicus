"""
Topic modeling analysis backend for Biblicus.
"""

from __future__ import annotations

import json
import re
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from ..corpus import Corpus
from ..models import ExtractionRunReference
from ..retrieval import hash_text
from ..time import utc_now_iso
from .base import CorpusAnalysisBackend
from .llm import generate_completion
from .models import (
    AnalysisRecipeManifest,
    AnalysisRunInput,
    AnalysisRunManifest,
    TopicModelingBerTopicConfig,
    TopicModelingBerTopicReport,
    TopicModelingKeyword,
    TopicModelingLabelSource,
    TopicModelingLexicalProcessingConfig,
    TopicModelingLexicalProcessingReport,
    TopicModelingLlmExtractionConfig,
    TopicModelingLlmExtractionMethod,
    TopicModelingLlmExtractionReport,
    TopicModelingLlmFineTuningConfig,
    TopicModelingLlmFineTuningReport,
    TopicModelingOutput,
    TopicModelingRecipeConfig,
    TopicModelingReport,
    TopicModelingStageStatus,
    TopicModelingTextCollectionReport,
    TopicModelingTextSourceConfig,
    TopicModelingTopic,
)


@dataclass
class _TopicDocument:
    document_id: str
    source_item_id: str
    text: str


class TopicModelingBackend(CorpusAnalysisBackend):
    """
    Topic modeling analysis backend backed by BERTopic.

    :ivar analysis_id: Backend identifier.
    :vartype analysis_id: str
    """

    analysis_id = "topic-modeling"

    def run_analysis(
        self,
        corpus: Corpus,
        *,
        recipe_name: str,
        config: Dict[str, object],
        extraction_run: ExtractionRunReference,
    ) -> BaseModel:
        """
        Run the topic modeling analysis pipeline.

        :param corpus: Corpus to analyze.
        :type corpus: Corpus
        :param recipe_name: Human-readable recipe name.
        :type recipe_name: str
        :param config: Analysis configuration values.
        :type config: dict[str, object]
        :param extraction_run: Extraction run reference for text inputs.
        :type extraction_run: biblicus.models.ExtractionRunReference
        :return: Topic modeling output model.
        :rtype: pydantic.BaseModel
        """
        parsed_config = (
            config
            if isinstance(config, TopicModelingRecipeConfig)
            else TopicModelingRecipeConfig.model_validate(config)
        )
        return _run_topic_modeling(
            corpus=corpus,
            recipe_name=recipe_name,
            config=parsed_config,
            extraction_run=extraction_run,
        )


def _run_topic_modeling(
    *,
    corpus: Corpus,
    recipe_name: str,
    config: TopicModelingRecipeConfig,
    extraction_run: ExtractionRunReference,
) -> TopicModelingOutput:
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
    run_dir = corpus.analysis_run_dir(analysis_id=TopicModelingBackend.analysis_id, run_id=run_id)
    output_path = run_dir / "output.json"

    run_dir.mkdir(parents=True, exist_ok=True)

    documents, text_report = _collect_documents(
        corpus=corpus,
        extraction_run=extraction_run,
        config=config.text_source,
    )

    llm_extraction_report, extracted_documents = _apply_llm_extraction(
        documents=documents,
        config=config.llm_extraction,
    )

    lexical_report, lexical_documents = _apply_lexical_processing(
        documents=extracted_documents,
        config=config.lexical_processing,
    )

    bertopic_report, topics = _run_bertopic(
        documents=lexical_documents,
        config=config.bertopic_analysis,
    )

    fine_tuning_report, labeled_topics = _apply_llm_fine_tuning(
        topics=topics,
        documents=lexical_documents,
        config=config.llm_fine_tuning,
    )

    report = TopicModelingReport(
        text_collection=text_report,
        llm_extraction=llm_extraction_report,
        lexical_processing=lexical_report,
        bertopic_analysis=bertopic_report,
        llm_fine_tuning=fine_tuning_report,
        topics=labeled_topics,
        warnings=(
            text_report.warnings
            + llm_extraction_report.warnings
            + bertopic_report.warnings
            + fine_tuning_report.warnings
        ),
        errors=text_report.errors
        + llm_extraction_report.errors
        + bertopic_report.errors
        + fine_tuning_report.errors,
    )

    run_stats = {
        "documents": bertopic_report.document_count,
        "topics": bertopic_report.topic_count,
    }
    run_manifest = run_manifest.model_copy(
        update={"artifact_paths": ["output.json"], "stats": run_stats}
    )
    _write_analysis_run_manifest(run_dir=run_dir, manifest=run_manifest)

    output = TopicModelingOutput(
        analysis_id=TopicModelingBackend.analysis_id,
        generated_at=utc_now_iso(),
        run=run_manifest,
        report=report,
    )
    _write_topic_modeling_output(path=output_path, output=output)
    return output


def _create_recipe_manifest(
    *, name: str, config: TopicModelingRecipeConfig
) -> AnalysisRecipeManifest:
    recipe_payload = json.dumps(
        {
            "analysis_id": TopicModelingBackend.analysis_id,
            "name": name,
            "config": config.model_dump(),
        },
        sort_keys=True,
    )
    recipe_id = hash_text(recipe_payload)
    return AnalysisRecipeManifest(
        recipe_id=recipe_id,
        analysis_id=TopicModelingBackend.analysis_id,
        name=name,
        created_at=utc_now_iso(),
        config=config.model_dump(),
    )


def _analysis_run_id(
    *,
    recipe_id: str,
    extraction_run: ExtractionRunReference,
    catalog_generated_at: str,
) -> str:
    run_seed = f"{recipe_id}:{extraction_run.as_string()}:{catalog_generated_at}"
    return hash_text(run_seed)


def _collect_documents(
    *,
    corpus: Corpus,
    extraction_run: ExtractionRunReference,
    config: TopicModelingTextSourceConfig,
) -> Tuple[List[_TopicDocument], TopicModelingTextCollectionReport]:
    manifest = corpus.load_extraction_run_manifest(
        extractor_id=extraction_run.extractor_id,
        run_id=extraction_run.run_id,
    )
    warnings: List[str] = []
    errors: List[str] = []
    documents: List[_TopicDocument] = []
    skipped_items = 0
    empty_texts = 0

    for item_result in manifest.items:
        if item_result.status != "extracted" or item_result.final_text_relpath is None:
            skipped_items += 1
            continue
        text_path = (
            corpus.extraction_run_dir(
                extractor_id=extraction_run.extractor_id,
                run_id=extraction_run.run_id,
            )
            / item_result.final_text_relpath
        )
        text_value = text_path.read_text(encoding="utf-8").strip()
        if not text_value:
            empty_texts += 1
            continue
        if config.min_text_characters is not None and len(text_value) < config.min_text_characters:
            skipped_items += 1
            continue
        documents.append(
            _TopicDocument(
                document_id=item_result.item_id,
                source_item_id=item_result.item_id,
                text=text_value,
            )
        )

    if config.sample_size is not None and len(documents) > config.sample_size:
        documents = documents[: config.sample_size]
        warnings.append("Text collection truncated to sample_size")

    report = TopicModelingTextCollectionReport(
        status=TopicModelingStageStatus.COMPLETE,
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
        report = report.model_copy(update={"status": TopicModelingStageStatus.FAILED})
        raise ValueError("Topic modeling requires at least one extracted text document")
    return documents, report


def _apply_llm_extraction(
    *,
    documents: List[_TopicDocument],
    config: TopicModelingLlmExtractionConfig,
) -> Tuple[TopicModelingLlmExtractionReport, List[_TopicDocument]]:
    if not config.enabled:
        report = TopicModelingLlmExtractionReport(
            status=TopicModelingStageStatus.SKIPPED,
            method=config.method,
            input_documents=len(documents),
            output_documents=len(documents),
            warnings=[],
            errors=[],
        )
        return report, list(documents)

    extracted_documents: List[_TopicDocument] = []
    errors: List[str] = []

    for document in documents:
        prompt = config.prompt_template.format(text=document.text)
        response_text = generate_completion(
            client=config.client,
            system_prompt=config.system_prompt,
            user_prompt=prompt,
        ).strip()
        if config.method == TopicModelingLlmExtractionMethod.SINGLE:
            if not response_text:
                errors.append(f"LLM extraction returned empty output for {document.document_id}")
                continue
            extracted_documents.append(
                _TopicDocument(
                    document_id=document.document_id,
                    source_item_id=document.source_item_id,
                    text=response_text,
                )
            )
            continue
        items = _parse_itemized_response(response_text)
        if not items:
            errors.append(f"LLM itemization returned no items for {document.document_id}")
            continue
        for index, item_text in enumerate(items, start=1):
            extracted_documents.append(
                _TopicDocument(
                    document_id=f"{document.document_id}:{index}",
                    source_item_id=document.source_item_id,
                    text=item_text,
                )
            )

    report = TopicModelingLlmExtractionReport(
        status=TopicModelingStageStatus.COMPLETE,
        method=config.method,
        input_documents=len(documents),
        output_documents=len(extracted_documents),
        warnings=[],
        errors=errors,
    )
    if not extracted_documents:
        report = report.model_copy(update={"status": TopicModelingStageStatus.FAILED})
        raise ValueError("LLM extraction produced no usable documents")
    return report, extracted_documents


def _parse_itemized_response(response_text: str) -> List[str]:
    cleaned = response_text.strip()
    if not cleaned:
        return []
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        unescaped = cleaned.replace('\\"', '"')
        try:
            data = json.loads(unescaped)
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return []
        else:
            return []
    items: List[str] = []
    for entry in data:
        if not isinstance(entry, str):
            continue
        cleaned = entry.strip()
        if cleaned:
            items.append(cleaned)
    return items


def _apply_lexical_processing(
    *,
    documents: List[_TopicDocument],
    config: TopicModelingLexicalProcessingConfig,
) -> Tuple[TopicModelingLexicalProcessingReport, List[_TopicDocument]]:
    if not config.enabled:
        report = TopicModelingLexicalProcessingReport(
            status=TopicModelingStageStatus.SKIPPED,
            input_documents=len(documents),
            output_documents=len(documents),
            lowercase=config.lowercase,
            strip_punctuation=config.strip_punctuation,
            collapse_whitespace=config.collapse_whitespace,
        )
        return report, list(documents)

    processed: List[_TopicDocument] = []
    for document in documents:
        text_value = document.text
        if config.lowercase:
            text_value = text_value.lower()
        if config.strip_punctuation:
            text_value = text_value.translate(str.maketrans("", "", string.punctuation))
        if config.collapse_whitespace:
            text_value = re.sub(r"\s+", " ", text_value).strip()
        processed.append(
            _TopicDocument(
                document_id=document.document_id,
                source_item_id=document.source_item_id,
                text=text_value,
            )
        )

    report = TopicModelingLexicalProcessingReport(
        status=TopicModelingStageStatus.COMPLETE,
        input_documents=len(documents),
        output_documents=len(processed),
        lowercase=config.lowercase,
        strip_punctuation=config.strip_punctuation,
        collapse_whitespace=config.collapse_whitespace,
    )
    return report, processed


def _run_bertopic(
    *,
    documents: List[_TopicDocument],
    config: TopicModelingBerTopicConfig,
) -> Tuple[TopicModelingBerTopicReport, List[TopicModelingTopic]]:
    try:
        import importlib

        bertopic_module = importlib.import_module("bertopic")
        if not hasattr(bertopic_module, "BERTopic"):
            raise ImportError("BERTopic class is unavailable")
        BERTopic = bertopic_module.BERTopic
    except ImportError as import_error:
        raise ValueError(
            "BERTopic analysis requires an optional dependency. "
            'Install it with pip install "biblicus[topic-modeling]".'
        ) from import_error

    bertopic_kwargs = dict(config.parameters)
    is_fake = bool(getattr(bertopic_module, "__biblicus_fake__", False))
    if config.vectorizer is not None and "vectorizer_model" not in bertopic_kwargs:
        if is_fake:
            bertopic_kwargs["vectorizer_model"] = None
        else:
            try:
                from sklearn.feature_extraction.text import CountVectorizer
            except ImportError as import_error:
                raise ValueError(
                    "Vectorizer configuration requires scikit-learn. "
                    "Install with pip install \"biblicus[topic-modeling]\"."
                ) from import_error
            bertopic_kwargs["vectorizer_model"] = CountVectorizer(
                ngram_range=tuple(config.vectorizer.ngram_range),
                stop_words=config.vectorizer.stop_words,
            )

    topic_model = BERTopic(**bertopic_kwargs)
    texts = [document.text for document in documents]
    assignments, _ = topic_model.fit_transform(texts)
    assignment_list = list(assignments)
    topic_ids = sorted({int(topic_id) for topic_id in assignment_list})
    topics: List[TopicModelingTopic] = []
    topic_documents = _group_documents_by_topic(documents, assignment_list)

    for topic_id in topic_ids:
        keywords = _resolve_topic_keywords(topic_model=topic_model, topic_id=topic_id)
        label = keywords[0].keyword if keywords else f"Topic {topic_id}"
        doc_entries = topic_documents.get(topic_id, [])
        topics.append(
            TopicModelingTopic(
                topic_id=topic_id,
                label=label,
                label_source=TopicModelingLabelSource.BERTOPIC,
                keywords=keywords,
                document_count=len(doc_entries),
                document_examples=[doc.text for doc in doc_entries[:3]],
                document_ids=[doc.document_id for doc in doc_entries],
            )
        )

    report = TopicModelingBerTopicReport(
        status=TopicModelingStageStatus.COMPLETE,
        topic_count=len(topics),
        document_count=len(documents),
        parameters=dict(config.parameters),
        vectorizer=config.vectorizer,
        warnings=[],
        errors=[],
    )
    return report, topics


def _group_documents_by_topic(
    documents: List[_TopicDocument], assignments: List[int]
) -> Dict[int, List[_TopicDocument]]:
    grouped: Dict[int, List[_TopicDocument]] = {}
    for index, topic_id in enumerate(assignments):
        grouped.setdefault(int(topic_id), []).append(documents[index])
    return grouped


def _resolve_topic_keywords(
    *, topic_model: Any, topic_id: int
) -> List[TopicModelingKeyword]:
    raw_keywords = topic_model.get_topic(topic_id) or []
    return [
        TopicModelingKeyword(keyword=str(entry[0]), score=float(entry[1]))
        for entry in raw_keywords
    ]


def _apply_llm_fine_tuning(
    *,
    topics: List[TopicModelingTopic],
    documents: List[_TopicDocument],
    config: TopicModelingLlmFineTuningConfig,
) -> Tuple[TopicModelingLlmFineTuningReport, List[TopicModelingTopic]]:
    if not config.enabled:
        report = TopicModelingLlmFineTuningReport(
            status=TopicModelingStageStatus.SKIPPED,
            topics_labeled=0,
            warnings=[],
            errors=[],
        )
        return report, topics

    labeled_topics: List[TopicModelingTopic] = []
    errors: List[str] = []
    labeled_count = 0
    topic_documents = {doc.document_id: doc for doc in documents}

    for topic in topics:
        keyword_text = ", ".join(
            [keyword.keyword for keyword in topic.keywords[: config.max_keywords]]
        )
        selected_documents = []
        for doc_id in topic.document_ids[: config.max_documents]:
            doc = topic_documents.get(doc_id)
            if doc is not None:
                selected_documents.append(doc.text)
        documents_text = "\n".join(selected_documents)
        prompt = config.prompt_template.format(
            keywords=keyword_text,
            documents=documents_text,
        )
        label_text = generate_completion(
            client=config.client,
            system_prompt=config.system_prompt,
            user_prompt=prompt,
        ).strip()
        if label_text:
            labeled_topics.append(
                topic.model_copy(
                    update={
                        "label": label_text,
                        "label_source": TopicModelingLabelSource.LLM,
                    }
                )
            )
            labeled_count += 1
        else:
            errors.append(f"LLM fine-tuning returned empty label for topic {topic.topic_id}")
            labeled_topics.append(topic)

    report = TopicModelingLlmFineTuningReport(
        status=TopicModelingStageStatus.COMPLETE,
        topics_labeled=labeled_count,
        warnings=[],
        errors=errors,
    )
    return report, labeled_topics


def _write_analysis_run_manifest(*, run_dir: Path, manifest: AnalysisRunManifest) -> None:
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_topic_modeling_output(*, path: Path, output: TopicModelingOutput) -> None:
    path.write_text(output.model_dump_json(indent=2) + "\n", encoding="utf-8")
