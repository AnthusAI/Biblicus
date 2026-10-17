"""
Research-agent topic context reports.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from pydantic import Field, field_validator

from .ai.models import LlmClientConfig
from .analysis.models import TopicModelingOutput, TopicModelingTopic
from .analysis.schema import AnalysisSchemaModel
from .constants import ANALYSIS_SCHEMA_VERSION
from .corpus import Corpus
from .models import CatalogItem, ExtractionSnapshotReference
from .retrieval import hash_text
from .time import utc_now_iso

TOPIC_CONTEXT_ANALYSIS_ID = "topic-context"
MAX_EXAMPLE_CHARACTERS = 1200
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_+-]*")
CENTRALITY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


class TopicContextExample(AnalysisSchemaModel):
    """
    Representative document example for a topic context report.

    :ivar item_id: Corpus item identifier.
    :vartype item_id: str
    :ivar title: Human-readable item title.
    :vartype title: str
    :ivar subtitle: Optional subtitle from curated metadata.
    :vartype subtitle: str or None
    :ivar source_uri: Optional source uniform resource identifier.
    :vartype source_uri: str or None
    :ivar published_at: Optional canonical publication date.
    :vartype published_at: str or None
    :ivar text_source: Source of the example text.
    :vartype text_source: str
    :ivar text: Abstract, summary, or extracted text shown for the example.
    :vartype text: str
    :ivar centrality_score: Similarity score used to rank examples inside the topic.
    :vartype centrality_score: float
    """

    item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    subtitle: Optional[str] = None
    source_uri: Optional[str] = None
    published_at: Optional[str] = None
    text_source: str = Field(min_length=1)
    text: str = Field(min_length=1)
    centrality_score: float = Field(ge=0)


class TopicContextTopic(AnalysisSchemaModel):
    """
    Topic row in a research-agent context report.

    :ivar rank: Rank in the context report.
    :vartype rank: int
    :ivar topic_id: BERTopic topic identifier.
    :vartype topic_id: int
    :ivar label: Human-readable topic label from the topic-modeling snapshot.
    :vartype label: str
    :ivar label_source: Source identifier for the topic label.
    :vartype label_source: str
    :ivar document_count: Number of documents assigned to the topic.
    :vartype document_count: int
    :ivar keywords: Topic keywords.
    :vartype keywords: list[str]
    :ivar guidance: Optional LLM-generated research-agent guidance.
    :vartype guidance: str or None
    :ivar examples: Representative examples.
    :vartype examples: list[TopicContextExample]
    """

    rank: int = Field(ge=1)
    topic_id: int
    label: str = Field(min_length=1)
    label_source: str = Field(min_length=1)
    document_count: int = Field(ge=0)
    keywords: List[str] = Field(default_factory=list)
    guidance: Optional[str] = None
    examples: List[TopicContextExample] = Field(default_factory=list)


class TopicContextOutput(AnalysisSchemaModel):
    """
    Output for a research-agent topic context report.

    :ivar schema_version: Schema version.
    :vartype schema_version: int
    :ivar analysis_id: Analysis identifier.
    :vartype analysis_id: str
    :ivar snapshot_id: Topic context snapshot identifier.
    :vartype snapshot_id: str
    :ivar generated_at: Generation timestamp.
    :vartype generated_at: str
    :ivar inputs: Reproducibility inputs.
    :vartype inputs: dict[str, Any]
    :ivar source_topic_modeling_snapshot_id: Topic-modeling snapshot summarized by the report.
    :vartype source_topic_modeling_snapshot_id: str
    :ivar extraction_snapshot: Extraction snapshot used by the source topic-modeling snapshot.
    :vartype extraction_snapshot: str
    :ivar max_topics: Maximum topics included.
    :vartype max_topics: int
    :ivar examples_per_topic: Maximum representative examples per topic.
    :vartype examples_per_topic: int
    :ivar topics: Topic context rows.
    :vartype topics: list[TopicContextTopic]
    :ivar warnings: Warning messages.
    :vartype warnings: list[str]
    :ivar artifact_paths: Written artifact paths.
    :vartype artifact_paths: dict[str, str]
    """

    schema_version: int = Field(default=ANALYSIS_SCHEMA_VERSION, ge=1)
    analysis_id: str = Field(default=TOPIC_CONTEXT_ANALYSIS_ID)
    snapshot_id: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    source_topic_modeling_snapshot_id: str = Field(min_length=1)
    extraction_snapshot: str = Field(min_length=1)
    max_topics: int = Field(ge=1)
    examples_per_topic: int = Field(ge=1)
    topics: List[TopicContextTopic] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    artifact_paths: Dict[str, str] = Field(default_factory=dict)

    @field_validator("analysis_id")
    @classmethod
    def _validate_analysis_id(cls, value: str) -> str:
        if value != TOPIC_CONTEXT_ANALYSIS_ID:
            raise ValueError(f"analysis_id must be {TOPIC_CONTEXT_ANALYSIS_ID}")
        return value


def build_topic_context(
    *,
    corpus: Corpus,
    topic_modeling_snapshot_id: str,
    max_topics: int,
    examples_per_topic: int,
    summary_model: Optional[str],
    include_outlier: bool,
) -> TopicContextOutput:
    """
    Build and persist a research-agent topic context report.

    :param corpus: Corpus containing catalog, extraction, and topic-modeling artifacts.
    :type corpus: biblicus.corpus.Corpus
    :param topic_modeling_snapshot_id: Topic-modeling snapshot identifier to summarize.
    :type topic_modeling_snapshot_id: str
    :param max_topics: Maximum number of topic buckets to include.
    :type max_topics: int
    :param examples_per_topic: Maximum representative examples per topic.
    :type examples_per_topic: int
    :param summary_model: Optional OpenAI model for topic guidance and missing example summaries.
    :type summary_model: str or None
    :param include_outlier: Whether to include BERTopic topic ``-1``.
    :type include_outlier: bool
    :return: Topic context report output.
    :rtype: TopicContextOutput
    """
    if max_topics < 1:
        raise ValueError("max_topics must be at least 1")
    if examples_per_topic < 1:
        raise ValueError("examples_per_topic must be at least 1")

    catalog = corpus.load_catalog()
    topic_modeling_output = _load_topic_modeling_output(
        corpus=corpus,
        snapshot_id=topic_modeling_snapshot_id,
    )
    extraction_snapshot = ExtractionSnapshotReference.model_validate(
        topic_modeling_output.snapshot.input.extraction_snapshot.model_dump(mode="json")
    )
    topic_candidates = _rank_topic_candidates(
        topics=topic_modeling_output.report.topics,
        include_outlier=include_outlier,
    )[:max_topics]
    warnings: List[str] = []
    topic_rows: List[TopicContextTopic] = []
    for rank, topic in enumerate(topic_candidates, start=1):
        examples = _representative_examples(
            corpus=corpus,
            catalog_items=catalog.items,
            extraction_snapshot=extraction_snapshot,
            topic=topic,
            examples_per_topic=examples_per_topic,
            summary_model=summary_model,
            warnings=warnings,
        )
        guidance = _topic_guidance(
            topic=topic,
            examples=examples,
            summary_model=summary_model,
            warnings=warnings,
        )
        topic_rows.append(
            TopicContextTopic(
                rank=rank,
                topic_id=topic.topic_id,
                label=topic.label,
                label_source=str(topic.label_source.value),
                document_count=topic.document_count,
                keywords=[keyword.keyword for keyword in topic.keywords],
                guidance=guidance,
                examples=examples,
            )
        )

    inputs = {
        "topic_modeling_snapshot_id": topic_modeling_snapshot_id,
        "extraction_snapshot": extraction_snapshot.as_string(),
        "max_topics": max_topics,
        "examples_per_topic": examples_per_topic,
        "summary_model": summary_model,
        "include_outlier": include_outlier,
        "selected_topic_ids": [topic.topic_id for topic in topic_candidates],
    }
    snapshot_id = _topic_context_snapshot_id(inputs=inputs)
    output = TopicContextOutput(
        snapshot_id=snapshot_id,
        generated_at=utc_now_iso(),
        inputs=inputs,
        source_topic_modeling_snapshot_id=topic_modeling_snapshot_id,
        extraction_snapshot=extraction_snapshot.as_string(),
        max_topics=max_topics,
        examples_per_topic=examples_per_topic,
        topics=topic_rows,
        warnings=warnings,
        artifact_paths={},
    )
    artifact_paths = _write_topic_context_artifacts(corpus=corpus, output=output)
    return output.model_copy(update={"artifact_paths": artifact_paths})


def topic_context_markdown(output: TopicContextOutput) -> str:
    """
    Render a topic context report as Markdown.

    :param output: Topic context output.
    :type output: TopicContextOutput
    :return: Markdown report suitable for research-agent context.
    :rtype: str
    """
    lines = [
        "# Research Agent Topic Context",
        "",
        f"- Snapshot: `{output.snapshot_id}`",
        f"- Topic modeling snapshot: `{output.source_topic_modeling_snapshot_id}`",
        f"- Extraction snapshot: `{output.extraction_snapshot}`",
        f"- Topics included: {len(output.topics)}",
        f"- Examples per topic: {output.examples_per_topic}",
        "",
    ]
    for topic in output.topics:
        keywords = ", ".join(topic.keywords[:8]) if topic.keywords else "none"
        lines.extend(
            [
                f"## {topic.rank}. {topic.label}",
                "",
                f"- Topic ID: `{topic.topic_id}`",
                f"- Documents: {topic.document_count}",
                f"- Keywords: {keywords}",
            ]
        )
        if topic.guidance:
            lines.append(f"- Guidance: {topic.guidance}")
        lines.extend(["", "### Representative Examples", ""])
        if not topic.examples:
            lines.append("No representative examples available.")
        for example in topic.examples:
            lines.extend(_example_markdown(example))
        lines.append("")
    if output.warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in output.warnings)
    return "\n".join(lines).strip()


def _load_topic_modeling_output(*, corpus: Corpus, snapshot_id: str) -> TopicModelingOutput:
    path = corpus.analysis_dir / "topic-modeling" / snapshot_id / "output.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing topic modeling output: {path}")
    return TopicModelingOutput.model_validate_json(path.read_text(encoding="utf-8"))


def _rank_topic_candidates(
    *, topics: Sequence[TopicModelingTopic], include_outlier: bool
) -> List[TopicModelingTopic]:
    return sorted(
        [topic for topic in topics if include_outlier or topic.topic_id != -1],
        key=lambda topic: (-topic.document_count, topic.label.lower(), topic.topic_id),
    )


def _representative_examples(
    *,
    corpus: Corpus,
    catalog_items: Dict[str, CatalogItem],
    extraction_snapshot: ExtractionSnapshotReference,
    topic: TopicModelingTopic,
    examples_per_topic: int,
    summary_model: Optional[str],
    warnings: List[str],
) -> List[TopicContextExample]:
    extracted_texts: Dict[str, str] = {}
    for item_id in topic.document_ids:
        text = corpus.read_extracted_text(
            extractor_id=extraction_snapshot.extractor_id,
            snapshot_id=extraction_snapshot.snapshot_id,
            item_id=item_id,
        )
        if text is not None:
            extracted_texts[item_id] = text
    ranked_item_ids = _rank_representative_item_ids(
        item_ids=topic.document_ids,
        catalog_items=catalog_items,
        extracted_texts=extracted_texts,
    )
    examples: List[TopicContextExample] = []
    for item_id, centrality_score in ranked_item_ids[:examples_per_topic]:
        item = catalog_items.get(item_id)
        if item is None:
            warnings.append(f"Topic {topic.topic_id} references missing catalog item {item_id}")
            continue
        example = _build_example(
            item=item,
            extracted_text=extracted_texts.get(item_id, ""),
            centrality_score=centrality_score,
            summary_model=summary_model,
            warnings=warnings,
        )
        if example is not None:
            examples.append(example)
    return examples


def _rank_representative_item_ids(
    *,
    item_ids: Sequence[str],
    catalog_items: Dict[str, CatalogItem],
    extracted_texts: Dict[str, str],
) -> List[tuple[str, float]]:
    vectors = {
        item_id: _term_counts(_centrality_text(item_id, catalog_items, extracted_texts))
        for item_id in item_ids
    }
    scored: List[tuple[str, float]] = []
    for item_id in item_ids:
        score = _centrality_score(item_id=item_id, vectors=vectors)
        scored.append((item_id, round(score, 6)))
    return sorted(
        scored,
        key=lambda pair: (
            -pair[1],
            _title_for_sort(catalog_items.get(pair[0])),
            pair[0],
        ),
    )


def _centrality_text(
    item_id: str,
    catalog_items: Dict[str, CatalogItem],
    extracted_texts: Dict[str, str],
) -> str:
    item = catalog_items.get(item_id)
    if item is None:
        return extracted_texts.get(item_id, "")
    parts = [
        item.title or "",
        _metadata_text(item, "subtitle") or "",
        _metadata_text(item, "abstract") or "",
        _metadata_text(item, "summary") or "",
        _metadata_text(item, "description") or "",
        extracted_texts.get(item_id, ""),
    ]
    return "\n".join(part for part in parts if part)


def _term_counts(text: str) -> Counter[str]:
    tokens = [
        token for token in TOKEN_PATTERN.findall(text.lower()) if token not in CENTRALITY_STOPWORDS
    ]
    return Counter(tokens)


def _centrality_score(*, item_id: str, vectors: Dict[str, Counter[str]]) -> float:
    vector = vectors.get(item_id, Counter())
    peers = [peer for peer_id, peer in vectors.items() if peer_id != item_id]
    if not peers:
        return 1.0
    if not vector:
        return 0.0
    similarities = [_cosine_similarity(vector, peer) for peer in peers]
    return sum(similarities) / len(similarities) if similarities else 0.0


def _cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _build_example(
    *,
    item: CatalogItem,
    extracted_text: str,
    centrality_score: float,
    summary_model: Optional[str],
    warnings: List[str],
) -> Optional[TopicContextExample]:
    text_source, text = _example_text(
        item=item,
        extracted_text=extracted_text,
        summary_model=summary_model,
        warnings=warnings,
    )
    if not text:
        warnings.append(f"Item {item.id} has no abstract, summary, or extracted text for context")
        return None
    return TopicContextExample(
        item_id=item.id,
        title=_item_title(item),
        subtitle=_metadata_text(item, "subtitle"),
        source_uri=item.source_uri,
        published_at=item.dates.published_at if item.dates is not None else None,
        text_source=text_source,
        text=_truncate_text(text, MAX_EXAMPLE_CHARACTERS),
        centrality_score=centrality_score,
    )


def _example_text(
    *,
    item: CatalogItem,
    extracted_text: str,
    summary_model: Optional[str],
    warnings: List[str],
) -> tuple[str, str]:
    abstract = _metadata_text(item, "abstract")
    if abstract:
        return "abstract", abstract
    summary = _metadata_text(item, "summary")
    if summary:
        return "summary", summary
    description = _metadata_text(item, "description")
    if description:
        return "description", description
    if summary_model and extracted_text.strip():
        generated = _openai_completion(
            model=summary_model,
            messages=[
                {
                    "role": "system",
                    "content": "Write concise summaries for Biblicus report examples.",
                },
                {
                    "role": "user",
                    "content": (
                        "Write one example summary sentence for this item.\n\n"
                        f"Title: {_item_title(item)}\n\n"
                        f"Text:\n{_truncate_text(extracted_text, 4000)}"
                    ),
                },
            ],
        )
        if generated:
            return "llm_summary", generated
        warnings.append(f"OpenAI returned an empty example summary for item {item.id}")
    if extracted_text.strip():
        return "extracted_text", extracted_text.strip()
    return "missing", ""


def _topic_guidance(
    *,
    topic: TopicModelingTopic,
    examples: Sequence[TopicContextExample],
    summary_model: Optional[str],
    warnings: List[str],
) -> Optional[str]:
    if summary_model is None:
        return None
    example_lines = []
    for example in examples:
        example_lines.append(f"- {example.title}: {_truncate_text(example.text, 500)}")
    generated = _openai_completion(
        model=summary_model,
        messages=[
            {
                "role": "system",
                "content": "Write concise research-agent guidance for Biblicus topic reports.",
            },
            {
                "role": "user",
                "content": (
                    "Create topic context guidance in one or two sentences for a research agent.\n\n"
                    f"Topic label: {topic.label}\n"
                    f"Document count: {topic.document_count}\n"
                    f"Keywords: {', '.join(keyword.keyword for keyword in topic.keywords[:8])}\n"
                    "Representative examples:\n" + "\n".join(example_lines)
                ),
            },
        ],
    )
    if generated:
        return generated
    warnings.append(f"OpenAI returned empty topic guidance for topic {topic.topic_id}")
    return None


def _openai_completion(*, model: str, messages: Sequence[Dict[str, str]]) -> str:
    try:
        import openai
    except ImportError as import_error:
        raise ValueError(
            "OpenAI topic context summaries require the openai package. "
            'Install it with pip install "biblicus[openai]".'
        ) from import_error
    if not hasattr(openai, "OpenAI"):
        raise ValueError(
            "OpenAI topic context summaries require the openai package. "
            'Install it with pip install "biblicus[openai]".'
        )
    api_key = LlmClientConfig(provider="openai", model=model).resolve_api_key()
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=list(messages),
    )
    return str(response.choices[0].message.content or "").strip()


def _metadata_text(item: CatalogItem, key: str) -> Optional[str]:
    value = item.metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _item_title(item: CatalogItem) -> str:
    return item.title or _metadata_text(item, "title") or item.id


def _title_for_sort(item: Optional[CatalogItem]) -> str:
    if item is None:
        return ""
    return _item_title(item).lower()


def _truncate_text(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _topic_context_snapshot_id(*, inputs: Dict[str, Any]) -> str:
    payload = json.dumps(
        {"analysis_id": TOPIC_CONTEXT_ANALYSIS_ID, "inputs": inputs},
        sort_keys=True,
    )
    return hash_text(payload)


def _write_topic_context_artifacts(*, corpus: Corpus, output: TopicContextOutput) -> Dict[str, str]:
    run_dir = corpus.analysis_run_dir(
        analysis_id=TOPIC_CONTEXT_ANALYSIS_ID,
        snapshot_id=output.snapshot_id,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": run_dir / "manifest.json",
        "output": run_dir / "output.json",
        "report": run_dir / "report.md",
    }
    artifact_paths = {key: str(path) for key, path in paths.items()}
    final_output = output.model_copy(update={"artifact_paths": artifact_paths})
    paths["manifest"].write_text(
        json.dumps(
            {
                "schema_version": ANALYSIS_SCHEMA_VERSION,
                "analysis_id": TOPIC_CONTEXT_ANALYSIS_ID,
                "snapshot_id": final_output.snapshot_id,
                "generated_at": final_output.generated_at,
                "inputs": final_output.inputs,
                "artifact_paths": artifact_paths,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["output"].write_text(final_output.model_dump_json(indent=2) + "\n", encoding="utf-8")
    paths["report"].write_text(topic_context_markdown(final_output) + "\n", encoding="utf-8")
    latest_path = corpus.analysis_dir / TOPIC_CONTEXT_ANALYSIS_ID / "latest.json"
    latest_path.write_text(
        json.dumps(
            {"snapshot_id": final_output.snapshot_id, "generated_at": final_output.generated_at},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact_paths


def _example_markdown(example: TopicContextExample) -> List[str]:
    lines = [
        f"#### {example.title}",
        "",
        f"- Item ID: `{example.item_id}`",
        f"- Text source: {example.text_source}",
        f"- Centrality: {example.centrality_score:.3f}",
    ]
    if example.subtitle:
        lines.append(f"- Subtitle: {example.subtitle}")
    if example.source_uri:
        lines.append(f"- Source: {example.source_uri}")
    if example.published_at:
        lines.append(f"- Published: {example.published_at}")
    lines.extend(["", example.text, ""])
    return lines
