"""
Hybrid retrieval backend combining lexical and vector results.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..corpus import Corpus
from ..models import Evidence, QueryBudget, RetrievalResult, RetrievalRun
from ..retrieval import apply_budget, create_recipe_manifest, create_run_manifest
from ..time import utc_now_iso


class HybridRecipeConfig(BaseModel):
    """
    Configuration for hybrid retrieval fusion.

    :ivar lexical_backend: Backend identifier for lexical retrieval.
    :vartype lexical_backend: str
    :ivar embedding_backend: Backend identifier for embedding retrieval.
    :vartype embedding_backend: str
    :ivar lexical_weight: Weight for lexical scores.
    :vartype lexical_weight: float
    :ivar embedding_weight: Weight for embedding scores.
    :vartype embedding_weight: float
    :ivar lexical_config: Optional lexical backend configuration.
    :vartype lexical_config: dict[str, object]
    :ivar embedding_config: Optional embedding backend configuration.
    :vartype embedding_config: dict[str, object]
    """

    model_config = ConfigDict(extra="forbid")

    lexical_backend: str = Field(default="sqlite-full-text-search", min_length=1)
    embedding_backend: str = Field(default="vector", min_length=1)
    lexical_weight: float = Field(default=0.5, ge=0, le=1)
    embedding_weight: float = Field(default=0.5, ge=0, le=1)
    lexical_config: Dict[str, object] = Field(default_factory=dict)
    embedding_config: Dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_weights(self) -> "HybridRecipeConfig":
        if abs((self.lexical_weight + self.embedding_weight) - 1.0) > 1e-6:
            raise ValueError("weights must sum to 1")
        return self


class HybridBackend:
    """
    Hybrid backend that fuses lexical and embedding retrieval.

    :ivar backend_id: Backend identifier.
    :vartype backend_id: str
    """

    backend_id = "hybrid"

    def build_run(
        self, corpus: Corpus, *, recipe_name: str, config: Dict[str, object]
    ) -> RetrievalRun:
        """
        Build or register a hybrid retrieval run.

        :param corpus: Corpus to build against.
        :type corpus: Corpus
        :param recipe_name: Human-readable recipe name.
        :type recipe_name: str
        :param config: Backend-specific configuration values.
        :type config: dict[str, object]
        :return: Run manifest describing the build.
        :rtype: RetrievalRun
        """
        recipe_config = HybridRecipeConfig.model_validate(config)
        _ensure_backend_supported(recipe_config)
        lexical_backend = _resolve_backend(recipe_config.lexical_backend)
        embedding_backend = _resolve_backend(recipe_config.embedding_backend)
        lexical_run = lexical_backend.build_run(
            corpus, recipe_name=f"{recipe_name}-lexical", config=recipe_config.lexical_config
        )
        embedding_run = embedding_backend.build_run(
            corpus, recipe_name=f"{recipe_name}-embedding", config=recipe_config.embedding_config
        )
        recipe = create_recipe_manifest(
            backend_id=self.backend_id,
            name=recipe_name,
            config=recipe_config.model_dump(),
        )
        stats = {
            "lexical_run_id": lexical_run.run_id,
            "embedding_run_id": embedding_run.run_id,
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
        Query using both lexical and embedding backends and fuse scores.

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
        recipe_config = HybridRecipeConfig.model_validate(run.recipe.config)
        _ensure_backend_supported(recipe_config)
        lexical_backend = _resolve_backend(recipe_config.lexical_backend)
        embedding_backend = _resolve_backend(recipe_config.embedding_backend)
        lexical_run_id = run.stats.get("lexical_run_id")
        embedding_run_id = run.stats.get("embedding_run_id")
        if not lexical_run_id or not embedding_run_id:
            raise ValueError("Hybrid run missing lexical or embedding run identifiers")
        lexical_run = corpus.load_run(str(lexical_run_id))
        embedding_run = corpus.load_run(str(embedding_run_id))
        component_budget = _expand_component_budget(budget)
        lexical_result = lexical_backend.query(
            corpus, run=lexical_run, query_text=query_text, budget=component_budget
        )
        embedding_result = embedding_backend.query(
            corpus, run=embedding_run, query_text=query_text, budget=component_budget
        )
        candidates = _fuse_evidence(
            lexical_result.evidence,
            embedding_result.evidence,
            lexical_weight=recipe_config.lexical_weight,
            embedding_weight=recipe_config.embedding_weight,
        )
        sorted_candidates = sorted(
            candidates,
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
        stats = {
            "candidates": len(sorted_candidates),
            "returned": len(evidence),
            "fusion_weights": {
                "lexical": recipe_config.lexical_weight,
                "embedding": recipe_config.embedding_weight,
            },
        }
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


def _ensure_backend_supported(recipe_config: HybridRecipeConfig) -> None:
    """
    Validate that hybrid backends do not reference the hybrid backend itself.

    :param recipe_config: Parsed hybrid recipe configuration.
    :type recipe_config: HybridRecipeConfig
    :return: None.
    :rtype: None
    :raises ValueError: If hybrid is used as a component backend.
    """
    if recipe_config.lexical_backend == HybridBackend.backend_id:
        raise ValueError("Hybrid backend cannot use itself as the lexical backend")
    if recipe_config.embedding_backend == HybridBackend.backend_id:
        raise ValueError("Hybrid backend cannot use itself as the embedding backend")


def _resolve_backend(backend_id: str):
    """
    Resolve a backend by identifier.

    :param backend_id: Backend identifier.
    :type backend_id: str
    :return: Backend instance.
    :rtype: object
    """
    from . import get_backend

    return get_backend(backend_id)


def _expand_component_budget(budget: QueryBudget, *, multiplier: int = 5) -> QueryBudget:
    """
    Expand a final budget to collect more candidates for fusion.

    :param budget: Final evidence budget.
    :type budget: QueryBudget
    :param multiplier: Candidate expansion multiplier.
    :type multiplier: int
    :return: Expanded budget for component backends.
    :rtype: QueryBudget
    """
    max_total_characters = budget.max_total_characters
    expanded_characters = (
        max_total_characters * multiplier if max_total_characters is not None else None
    )
    return QueryBudget(
        max_total_items=budget.max_total_items * multiplier,
        max_total_characters=expanded_characters,
        max_items_per_source=budget.max_items_per_source,
    )


def _fuse_evidence(
    lexical: List[Evidence],
    embedding: List[Evidence],
    *,
    lexical_weight: float,
    embedding_weight: float,
) -> List[Evidence]:
    """
    Fuse lexical and embedding evidence lists into hybrid candidates.

    :param lexical: Lexical evidence list.
    :type lexical: list[Evidence]
    :param embedding: Embedding evidence list.
    :type embedding: list[Evidence]
    :param lexical_weight: Lexical score weight.
    :type lexical_weight: float
    :param embedding_weight: Embedding score weight.
    :type embedding_weight: float
    :return: Hybrid evidence list.
    :rtype: list[Evidence]
    """
    merged: Dict[str, Dict[str, Optional[Evidence]]] = {}
    for evidence_item in lexical:
        merged.setdefault(evidence_item.item_id, {})["lexical"] = evidence_item
    for evidence_item in embedding:
        merged.setdefault(evidence_item.item_id, {})["embedding"] = evidence_item

    candidates: List[Evidence] = []
    for item_id, sources in merged.items():
        lexical_evidence = sources.get("lexical")
        embedding_evidence = sources.get("embedding")
        lexical_score = lexical_evidence.score if lexical_evidence else 0.0
        embedding_score = embedding_evidence.score if embedding_evidence else 0.0
        combined_score = (lexical_score * lexical_weight) + (embedding_score * embedding_weight)
        base_evidence = lexical_evidence or embedding_evidence
        candidates.append(
            Evidence(
                item_id=item_id,
                source_uri=base_evidence.source_uri,
                media_type=base_evidence.media_type,
                score=combined_score,
                rank=1,
                text=base_evidence.text,
                content_ref=base_evidence.content_ref,
                span_start=base_evidence.span_start,
                span_end=base_evidence.span_end,
                stage="hybrid",
                stage_scores={"lexical": lexical_score, "embedding": embedding_score},
                recipe_id="",
                run_id="",
                hash=base_evidence.hash,
            )
        )
    return candidates
