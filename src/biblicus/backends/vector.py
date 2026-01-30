"""
Deterministic term-frequency vector retrieval backend.
"""

from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..corpus import Corpus
from ..frontmatter import parse_front_matter
from ..models import (
    Evidence,
    ExtractionRunReference,
    QueryBudget,
    RetrievalResult,
    RetrievalRun,
    parse_extraction_run_reference,
)
from ..retrieval import apply_budget, create_recipe_manifest, create_run_manifest, hash_text
from ..time import utc_now_iso


class VectorRecipeConfig(BaseModel):
    """
    Configuration for the vector retrieval backend.

    :ivar snippet_characters: Maximum characters to include in evidence snippets.
    :vartype snippet_characters: int
    :ivar extraction_run: Optional extraction run reference in the form extractor_id:run_id.
    :vartype extraction_run: str or None
    """

    model_config = ConfigDict(extra="forbid")

    snippet_characters: int = Field(default=400, ge=1)
    extraction_run: Optional[str] = None


class VectorBackend:
    """
    Deterministic vector backend using term-frequency cosine similarity.

    :ivar backend_id: Backend identifier.
    :vartype backend_id: str
    """

    backend_id = "vector"

    def build_run(
        self, corpus: Corpus, *, recipe_name: str, config: Dict[str, object]
    ) -> RetrievalRun:
        """
        Register a vector backend run (no materialization).

        :param corpus: Corpus to build against.
        :type corpus: Corpus
        :param recipe_name: Human-readable recipe name.
        :type recipe_name: str
        :param config: Backend-specific configuration values.
        :type config: dict[str, object]
        :return: Run manifest describing the build.
        :rtype: RetrievalRun
        """
        recipe_config = VectorRecipeConfig.model_validate(config)
        catalog = corpus.load_catalog()
        recipe = create_recipe_manifest(
            backend_id=self.backend_id,
            name=recipe_name,
            config=recipe_config.model_dump(),
        )
        stats = {
            "items": len(catalog.items),
            "text_items": _count_text_items(corpus, catalog.items.values(), recipe_config),
        }
        run = create_run_manifest(corpus, recipe=recipe, stats=stats, artifact_paths=[])
        corpus.write_run(run)
        return run

    def query(
        self,
        corpus: Corpus,
        *,
        run: RetrievalRun,
        query_text: str,
        budget: QueryBudget,
    ) -> RetrievalResult:
        """
        Query the corpus using term-frequency cosine similarity.

        :param corpus: Corpus associated with the run.
        :type corpus: Corpus
        :param run: Run manifest to use for querying.
        :type run: RetrievalRun
        :param query_text: Query text to execute.
        :type query_text: str
        :param budget: Evidence selection budget.
        :type budget: QueryBudget
        :return: Retrieval results containing evidence.
        :rtype: RetrievalResult
        """
        recipe_config = VectorRecipeConfig.model_validate(run.recipe.config)
        query_tokens = _tokenize_text(query_text)
        if not query_tokens:
            return RetrievalResult(
                query_text=query_text,
                budget=budget,
                run_id=run.run_id,
                recipe_id=run.recipe.recipe_id,
                backend_id=self.backend_id,
                generated_at=utc_now_iso(),
                evidence=[],
                stats={"candidates": 0, "returned": 0},
            )
        query_vector = _term_frequencies(query_tokens)
        query_norm = _vector_norm(query_vector)
        catalog = corpus.load_catalog()
        extraction_reference = _resolve_extraction_reference(corpus, recipe_config)
        scored_candidates = _score_items(
            corpus,
            catalog.items.values(),
            query_tokens=query_tokens,
            query_vector=query_vector,
            query_norm=query_norm,
            snippet_characters=recipe_config.snippet_characters,
            extraction_reference=extraction_reference,
        )
        sorted_candidates = sorted(
            scored_candidates,
            key=lambda evidence_item: (-evidence_item.score, evidence_item.item_id),
        )
        ranked = [
            evidence_item.model_copy(
                update={
                    "rank": index,
                    "recipe_id": run.recipe.recipe_id,
                    "run_id": run.run_id,
                }
            )
            for index, evidence_item in enumerate(sorted_candidates, start=1)
        ]
        evidence = apply_budget(ranked, budget)
        stats = {"candidates": len(sorted_candidates), "returned": len(evidence)}
        return RetrievalResult(
            query_text=query_text,
            budget=budget,
            run_id=run.run_id,
            recipe_id=run.recipe.recipe_id,
            backend_id=self.backend_id,
            generated_at=utc_now_iso(),
            evidence=evidence,
            stats=stats,
        )


def _resolve_extraction_reference(
    corpus: Corpus, recipe_config: VectorRecipeConfig
) -> Optional[ExtractionRunReference]:
    """
    Resolve an extraction run reference from a recipe config.

    :param corpus: Corpus associated with the recipe.
    :type corpus: Corpus
    :param recipe_config: Parsed vector recipe configuration.
    :type recipe_config: VectorRecipeConfig
    :return: Parsed extraction reference or None.
    :rtype: ExtractionRunReference or None
    :raises FileNotFoundError: If an extraction run is referenced but not present.
    """
    if not recipe_config.extraction_run:
        return None
    extraction_reference = parse_extraction_run_reference(recipe_config.extraction_run)
    run_dir = corpus.extraction_run_dir(
        extractor_id=extraction_reference.extractor_id,
        run_id=extraction_reference.run_id,
    )
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Missing extraction run: {extraction_reference.as_string()}")
    return extraction_reference


def _count_text_items(
    corpus: Corpus, items: Iterable[object], recipe_config: VectorRecipeConfig
) -> int:
    """
    Count catalog items that represent text content.

    :param corpus: Corpus containing the items.
    :type corpus: Corpus
    :param items: Catalog items to inspect.
    :type items: Iterable[object]
    :param recipe_config: Parsed vector recipe configuration.
    :type recipe_config: VectorRecipeConfig
    :return: Number of text items.
    :rtype: int
    """
    text_item_count = 0
    extraction_reference = _resolve_extraction_reference(corpus, recipe_config)
    for catalog_item in items:
        item_id = str(getattr(catalog_item, "id", ""))
        if extraction_reference and item_id:
            extracted_text = corpus.read_extracted_text(
                extractor_id=extraction_reference.extractor_id,
                run_id=extraction_reference.run_id,
                item_id=item_id,
            )
            if isinstance(extracted_text, str) and extracted_text.strip():
                text_item_count += 1
                continue
        media_type = getattr(catalog_item, "media_type", "")
        if media_type == "text/markdown" or str(media_type).startswith("text/"):
            text_item_count += 1
    return text_item_count


def _tokenize_text(text: str) -> List[str]:
    """
    Tokenize text into lowercase word tokens.

    :param text: Input text.
    :type text: str
    :return: Token list.
    :rtype: list[str]
    """
    return re.findall(r"[a-z0-9]+", text.lower())


def _term_frequencies(tokens: List[str]) -> Dict[str, float]:
    """
    Build term frequency weights from tokens.

    :param tokens: Token list.
    :type tokens: list[str]
    :return: Term frequency mapping.
    :rtype: dict[str, float]
    """
    frequencies: Dict[str, float] = {}
    for token in tokens:
        frequencies[token] = frequencies.get(token, 0.0) + 1.0
    return frequencies


def _vector_norm(vector: Dict[str, float]) -> float:
    """
    Compute the Euclidean norm of a term-frequency vector.

    :param vector: Term frequency mapping.
    :type vector: dict[str, float]
    :return: Vector norm.
    :rtype: float
    """
    return math.sqrt(sum(value * value for value in vector.values()))


def _cosine_similarity(
    left: Dict[str, float],
    *,
    left_norm: float,
    right: Dict[str, float],
    right_norm: float,
) -> float:
    """
    Compute cosine similarity between two term-frequency vectors.

    :param left: Left term-frequency vector.
    :type left: dict[str, float]
    :param left_norm: Precomputed left vector norm.
    :type left_norm: float
    :param right: Right term-frequency vector.
    :type right: dict[str, float]
    :param right_norm: Precomputed right vector norm.
    :type right_norm: float
    :return: Cosine similarity score.
    :rtype: float
    """
    dot = 0.0
    if len(left) < len(right):
        for token, value in left.items():
            dot += value * right.get(token, 0.0)
    else:
        for token, value in right.items():
            dot += value * left.get(token, 0.0)
    return dot / (left_norm * right_norm)


def _load_text_from_item(
    corpus: Corpus,
    *,
    item_id: str,
    relpath: str,
    media_type: str,
    extraction_reference: Optional[ExtractionRunReference],
) -> Optional[str]:
    """
    Load a text payload from a catalog item.

    :param corpus: Corpus containing the item.
    :type corpus: Corpus
    :param item_id: Item identifier.
    :type item_id: str
    :param relpath: Relative path to the stored content.
    :type relpath: str
    :param media_type: Media type for the stored content.
    :type media_type: str
    :param extraction_reference: Optional extraction run reference.
    :type extraction_reference: ExtractionRunReference or None
    :return: Text payload or None if not decodable as text.
    :rtype: str or None
    """
    if extraction_reference:
        extracted_text = corpus.read_extracted_text(
            extractor_id=extraction_reference.extractor_id,
            run_id=extraction_reference.run_id,
            item_id=item_id,
        )
        if isinstance(extracted_text, str) and extracted_text.strip():
            return extracted_text

    content_path = corpus.root / relpath
    raw_bytes = content_path.read_bytes()
    if media_type == "text/markdown":
        markdown_text = raw_bytes.decode("utf-8")
        parsed_document = parse_front_matter(markdown_text)
        return parsed_document.body
    if media_type.startswith("text/"):
        return raw_bytes.decode("utf-8")
    return None


def _find_first_match(text: str, tokens: List[str]) -> Optional[Tuple[int, int]]:
    """
    Locate the earliest token match span in a text payload.

    :param text: Text to scan.
    :type text: str
    :param tokens: Query tokens.
    :type tokens: list[str]
    :return: Start/end span for the earliest match, or None if no matches.
    :rtype: tuple[int, int] or None
    """
    lower_text = text.lower()
    best_start: Optional[int] = None
    best_end: Optional[int] = None
    for token in tokens:
        if not token:
            continue
        token_start = lower_text.find(token)
        if token_start == -1:
            continue
        token_end = token_start + len(token)
        if best_start is None or token_start < best_start:
            best_start = token_start
            best_end = token_end
    if best_start is None or best_end is None:
        return None
    return best_start, best_end


def _build_snippet(text: str, span: Optional[Tuple[int, int]], *, max_chars: int) -> str:
    """
    Build a snippet around a match span, constrained by a character budget.

    :param text: Source text to slice.
    :type text: str
    :param span: Match span to center on.
    :type span: tuple[int, int] or None
    :param max_chars: Maximum snippet length.
    :type max_chars: int
    :return: Snippet text.
    :rtype: str
    """
    if not text:
        return ""
    if span is None:
        return text[:max_chars]
    span_start, span_end = span
    half_window = max_chars // 2
    snippet_start = max(span_start - half_window, 0)
    snippet_end = min(span_end + half_window, len(text))
    return text[snippet_start:snippet_end]


def _score_items(
    corpus: Corpus,
    items: Iterable[object],
    *,
    query_tokens: List[str],
    query_vector: Dict[str, float],
    query_norm: float,
    snippet_characters: int,
    extraction_reference: Optional[ExtractionRunReference],
) -> List[Evidence]:
    """
    Score catalog items and return evidence candidates.

    :param corpus: Corpus containing the items.
    :type corpus: Corpus
    :param items: Catalog items to score.
    :type items: Iterable[object]
    :param query_tokens: Tokenized query text.
    :type query_tokens: list[str]
    :param query_vector: Query term-frequency vector.
    :type query_vector: dict[str, float]
    :param query_norm: Query vector norm.
    :type query_norm: float
    :param snippet_characters: Snippet length budget.
    :type snippet_characters: int
    :param extraction_reference: Optional extraction run reference.
    :type extraction_reference: ExtractionRunReference or None
    :return: Evidence candidates with provisional ranks.
    :rtype: list[Evidence]
    """
    evidence_items: List[Evidence] = []
    for catalog_item in items:
        media_type = getattr(catalog_item, "media_type", "")
        relpath = getattr(catalog_item, "relpath", "")
        item_id = str(getattr(catalog_item, "id", ""))
        item_text = _load_text_from_item(
            corpus,
            item_id=item_id,
            relpath=relpath,
            media_type=str(media_type),
            extraction_reference=extraction_reference,
        )
        if item_text is None:
            continue
        tokens = _tokenize_text(item_text)
        if not tokens:
            continue
        vector = _term_frequencies(tokens)
        similarity = _cosine_similarity(
            query_vector, left_norm=query_norm, right=vector, right_norm=_vector_norm(vector)
        )
        if similarity <= 0:
            continue
        span = _find_first_match(item_text, query_tokens)
        snippet = _build_snippet(item_text, span, max_chars=snippet_characters)
        span_start = span[0] if span else None
        span_end = span[1] if span else None
        evidence_items.append(
            Evidence(
                item_id=str(getattr(catalog_item, "id")),
                source_uri=getattr(catalog_item, "source_uri", None),
                media_type=str(media_type),
                score=float(similarity),
                rank=1,
                text=snippet,
                content_ref=None,
                span_start=span_start,
                span_end=span_end,
                stage="vector",
                recipe_id="",
                run_id="",
                hash=hash_text(snippet),
            )
        )
    return evidence_items
