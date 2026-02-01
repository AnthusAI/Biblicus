"""
Embedding-index retrieval backend that loads the full embedding matrix into memory at query time.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
from pydantic import ConfigDict, Field

from ..corpus import Corpus
from ..models import Evidence, ExtractionRunReference, QueryBudget, RetrievalResult, RetrievalRun
from ..retrieval import apply_budget, create_recipe_manifest, create_run_manifest, hash_text
from ..time import utc_now_iso
from .embedding_index_common import (
    ChunkRecord,
    EmbeddingIndexRecipeConfig,
    artifact_paths_for_run,
    chunks_to_records,
    collect_chunks,
    cosine_similarity_scores,
    read_chunks_jsonl,
    read_embeddings,
    resolve_extraction_reference,
    write_chunks_jsonl,
    write_embeddings,
)
from .scan import _build_snippet


class EmbeddingIndexInMemoryRecipeConfig(EmbeddingIndexRecipeConfig):
    """
    Configuration for embedding-index-inmemory retrieval.

    :ivar max_chunks: Maximum chunks allowed for in-memory query loading.
    :vartype max_chunks: int
    """

    model_config = ConfigDict(extra="forbid")

    max_chunks: int = Field(default=25000, ge=1)


class EmbeddingIndexInMemoryBackend:
    """
    Embedding retrieval backend using an in-memory similarity scan.
    """

    backend_id = "embedding-index-inmemory"

    def build_run(
        self, corpus: Corpus, *, recipe_name: str, config: Dict[str, object]
    ) -> RetrievalRun:
        """
        Build an embedding index run by chunking text payloads and materializing embeddings.

        :param corpus: Corpus to build against.
        :type corpus: Corpus
        :param recipe_name: Human-readable recipe name.
        :type recipe_name: str
        :param config: Backend-specific configuration values.
        :type config: dict[str, object]
        :return: Run manifest describing the build.
        :rtype: biblicus.models.RetrievalRun
        """
        recipe_config = EmbeddingIndexInMemoryRecipeConfig.model_validate(config)
        chunks, text_items = collect_chunks(corpus, recipe_config=recipe_config)
        if len(chunks) > recipe_config.max_chunks:
            raise ValueError(
                "embedding-index-inmemory exceeded max_chunks. "
                "Use embedding-index-file or increase max_chunks."
            )

        provider = recipe_config.embedding_provider.build_provider()
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = provider.embed_texts(chunk_texts)
        embeddings = embeddings.astype(np.float32)

        recipe = create_recipe_manifest(
            backend_id=self.backend_id,
            name=recipe_name,
            config=recipe_config.model_dump(),
        )
        run = create_run_manifest(corpus, recipe=recipe, stats={}, artifact_paths=[])

        paths = artifact_paths_for_run(run_id=run.run_id, backend_id=self.backend_id)
        embeddings_path = corpus.root / paths["embeddings"]
        chunks_path = corpus.root / paths["chunks"]
        corpus.runs_dir.mkdir(parents=True, exist_ok=True)

        write_embeddings(embeddings_path, embeddings)
        write_chunks_jsonl(chunks_path, chunks_to_records(chunks))

        stats = {
            "items": len(corpus.load_catalog().items),
            "text_items": text_items,
            "chunks": len(chunks),
            "dimensions": (
                int(embeddings.shape[1])
                if embeddings.size
                else recipe_config.embedding_provider.dimensions
            ),
        }
        run = run.model_copy(
            update={"artifact_paths": [paths["embeddings"], paths["chunks"]], "stats": stats}
        )
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
        Query an embedding index run and return ranked evidence.

        :param corpus: Corpus associated with the run.
        :type corpus: Corpus
        :param run: Run manifest to use for querying.
        :type run: biblicus.models.RetrievalRun
        :param query_text: Query text to embed.
        :type query_text: str
        :param budget: Evidence selection budget.
        :type budget: biblicus.models.QueryBudget
        :return: Retrieval results containing evidence.
        :rtype: biblicus.models.RetrievalResult
        """
        recipe_config = EmbeddingIndexInMemoryRecipeConfig.model_validate(run.recipe.config)
        extraction_reference = resolve_extraction_reference(corpus, recipe_config)

        paths = artifact_paths_for_run(run_id=run.run_id, backend_id=self.backend_id)
        embeddings_path = corpus.root / paths["embeddings"]
        chunks_path = corpus.root / paths["chunks"]
        if not embeddings_path.is_file() or not chunks_path.is_file():
            raise FileNotFoundError("Embedding index artifacts are missing for this run")

        embeddings = read_embeddings(embeddings_path, mmap=False).astype(np.float32)
        chunk_records = read_chunks_jsonl(chunks_path)
        if embeddings.shape[0] != len(chunk_records):
            raise ValueError(
                "Embedding index artifacts are inconsistent: "
                "embeddings row count does not match chunk record count"
            )

        provider = recipe_config.embedding_provider.build_provider()
        query_embedding = provider.embed_texts([query_text]).astype(np.float32)
        if query_embedding.shape[0] != 1:
            raise ValueError("Embedding provider returned an invalid query embedding shape")
        scores = cosine_similarity_scores(embeddings, query_embedding[0])

        candidates = _top_indices(
            scores,
            limit=_candidate_limit(budget.max_total_items + budget.offset),
        )
        evidence_items = _build_evidence(
            corpus,
            run=run,
            recipe_config=recipe_config,
            candidates=candidates,
            scores=scores,
            chunk_records=chunk_records,
            extraction_reference=extraction_reference,
        )
        ranked = [
            item.model_copy(
                update={"rank": index, "recipe_id": run.recipe.recipe_id, "run_id": run.run_id}
            )
            for index, item in enumerate(evidence_items, start=1)
        ]
        evidence = apply_budget(ranked, budget)
        return RetrievalResult(
            query_text=query_text,
            budget=budget,
            run_id=run.run_id,
            recipe_id=run.recipe.recipe_id,
            backend_id=self.backend_id,
            generated_at=utc_now_iso(),
            evidence=evidence,
            stats={"candidates": len(evidence_items), "returned": len(evidence)},
        )


def _candidate_limit(max_total_items: int, *, multiplier: int = 10) -> int:
    return max(1, int(max_total_items) * int(multiplier))


def _top_indices(scores: np.ndarray, *, limit: int) -> List[int]:
    if scores.size == 0:
        return []
    limit = min(int(limit), int(scores.size))
    indices = np.argpartition(-scores, limit - 1)[:limit]
    sorted_indices = indices[np.argsort(-scores[indices])]
    return [int(index) for index in sorted_indices]


def _build_evidence(
    corpus: Corpus,
    *,
    run: RetrievalRun,
    recipe_config: EmbeddingIndexInMemoryRecipeConfig,
    candidates: List[int],
    scores: np.ndarray,
    chunk_records: List[ChunkRecord],
    extraction_reference: Optional[ExtractionRunReference],
) -> List[Evidence]:
    catalog = corpus.load_catalog()
    evidence_items: List[Evidence] = []
    for idx in candidates:
        record = chunk_records[idx]
        item_id = record.item_id
        span_start = record.span_start
        span_end = record.span_end
        catalog_item = catalog.items[item_id]
        relpath = str(getattr(catalog_item, "relpath"))
        media_type = str(getattr(catalog_item, "media_type"))
        text = _load_text_for_evidence(
            corpus,
            item_id=item_id,
            relpath=relpath,
            media_type=media_type,
            extraction_reference=extraction_reference,
        )
        snippet = _build_snippet(
            text, (span_start, span_end), max_chars=recipe_config.snippet_characters
        )
        evidence_items.append(
            Evidence(
                item_id=item_id,
                source_uri=getattr(catalog_item, "source_uri", None),
                media_type=media_type,
                score=float(scores[idx]),
                rank=1,
                text=snippet,
                content_ref=None,
                span_start=span_start,
                span_end=span_end,
                stage=EmbeddingIndexInMemoryBackend.backend_id,
                stage_scores=None,
                recipe_id=run.recipe.recipe_id,
                run_id=run.run_id,
                hash=hash_text(snippet),
            )
        )
    return evidence_items


def _load_text_for_evidence(
    corpus: Corpus,
    *,
    item_id: str,
    relpath: str,
    media_type: str,
    extraction_reference: Optional[ExtractionRunReference],
) -> Optional[str]:
    from .embedding_index_common import _load_text_from_item

    return _load_text_from_item(
        corpus,
        item_id=item_id,
        relpath=relpath,
        media_type=media_type,
        extraction_reference=extraction_reference,
    )
