"""
Context retrieval helpers for the Biblicus Context Engine.
"""

from __future__ import annotations

from typing import Any, Optional

from biblicus.backends import get_backend
from biblicus.context import (
    ContextPack,
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_token_budget,
)
from biblicus.corpus import Corpus
from biblicus.models import QueryBudget, RetrievalRun

from .models import ContextRetrieverRequest


def _resolve_run(
    corpus: Corpus,
    *,
    backend_id: str,
    run_id: Optional[str],
    recipe_name: Optional[str],
    recipe_config: Optional[dict[str, Any]],
) -> RetrievalRun:
    if run_id:
        return corpus.load_run(run_id)

    latest_run_id = corpus.latest_run_id
    if latest_run_id:
        candidate = corpus.load_run(latest_run_id)
        if candidate.recipe.backend_id == backend_id:
            return candidate

    if recipe_config is None:
        raise ValueError(
            "No retrieval run available for the requested backend. "
            "Provide run_id or recipe_config to build one."
        )

    backend = get_backend(backend_id)
    resolved_name = recipe_name or f"Context pack ({backend_id})"
    return backend.build_run(corpus, recipe_name=resolved_name, config=recipe_config)


def retrieve_context_pack(
    *,
    request: ContextRetrieverRequest,
    corpus: Corpus,
    backend_id: str,
    run_id: Optional[str] = None,
    recipe_name: Optional[str] = None,
    recipe_config: Optional[dict[str, Any]] = None,
    join_with: str = "\n\n",
    max_items_per_source: Optional[int] = None,
    include_metadata: bool = False,
    metadata_fields: Optional[list[str]] = None,
) -> ContextPack:
    """
    Retrieve a context pack using a Biblicus backend.

    :param request: Context retrieval request.
    :type request: biblicus.context_engine.ContextRetrieverRequest
    :param corpus: Corpus instance to query.
    :type corpus: biblicus.corpus.Corpus
    :param backend_id: Retrieval backend identifier.
    :type backend_id: str
    :param run_id: Optional retrieval run identifier.
    :type run_id: str or None
    :param recipe_name: Optional recipe name for run builds.
    :type recipe_name: str or None
    :param recipe_config: Optional backend recipe configuration.
    :type recipe_config: dict[str, Any] or None
    :param join_with: Separator between context pack blocks.
    :type join_with: str
    :param max_items_per_source: Optional cap per source.
    :type max_items_per_source: int or None
    :param include_metadata: Whether to include metadata in context blocks.
    :type include_metadata: bool
    :param metadata_fields: Optional metadata fields to include in context blocks.
    :type metadata_fields: list[str] or None
    :return: Context pack derived from retrieval results.
    :rtype: biblicus.context.ContextPack
    :raises ValueError: If no compatible retrieval run is available.
    """
    run = _resolve_run(
        corpus,
        backend_id=backend_id,
        run_id=run_id,
        recipe_name=recipe_name,
        recipe_config=recipe_config,
    )

    maximum_total_characters = request.maximum_total_characters
    if maximum_total_characters is None and request.max_tokens is not None:
        maximum_total_characters = int(request.max_tokens * 4)

    budget = QueryBudget(
        max_total_items=request.limit,
        offset=request.offset,
        maximum_total_characters=maximum_total_characters,
        max_items_per_source=max_items_per_source,
    )
    backend = get_backend(backend_id)
    result = backend.query(
        corpus,
        run=run,
        query_text=request.query,
        budget=budget,
    )
    policy = ContextPackPolicy(
        join_with=join_with,
        include_metadata=include_metadata,
        metadata_fields=metadata_fields,
    )
    context_pack = build_context_pack(result, policy=policy)
    if request.max_tokens is None:
        return context_pack

    return fit_context_pack_to_token_budget(
        context_pack,
        policy=policy,
        token_budget=TokenBudget(max_tokens=int(request.max_tokens)),
    )
