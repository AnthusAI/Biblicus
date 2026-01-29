"""
Shared retrieval helpers for Biblicus backends.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional

from .corpus import Corpus
from .models import Evidence, QueryBudget, RecipeManifest, RetrievalRun
from .time import utc_now_iso


def create_recipe_manifest(
    *,
    backend_id: str,
    name: str,
    config: Dict[str, Any],
    description: Optional[str] = None,
) -> RecipeManifest:
    """
    Create a deterministic recipe manifest from a backend configuration.

    :param backend_id: Backend identifier for the recipe.
    :type backend_id: str
    :param name: Human-readable recipe name.
    :type name: str
    :param config: Backend-specific configuration values.
    :type config: dict[str, Any]
    :param description: Optional recipe description.
    :type description: str or None
    :return: Deterministic recipe manifest.
    :rtype: RecipeManifest
    """
    config_json = json.dumps(config, sort_keys=True, separators=(",", ":"))
    recipe_seed = f"{backend_id}:{config_json}"
    recipe_id = hashlib.sha256(recipe_seed.encode("utf-8")).hexdigest()
    return RecipeManifest(
        recipe_id=recipe_id,
        backend_id=backend_id,
        name=name,
        created_at=utc_now_iso(),
        config=config,
        description=description,
    )


def create_run_manifest(
    corpus: Corpus,
    *,
    recipe: RecipeManifest,
    stats: Dict[str, Any],
    artifact_paths: Optional[List[str]] = None,
) -> RetrievalRun:
    """
    Create a retrieval run manifest tied to the current catalog snapshot.

    :param corpus: Corpus used to generate the run.
    :type corpus: Corpus
    :param recipe: Recipe manifest for the run.
    :type recipe: RecipeManifest
    :param stats: Backend-specific run statistics.
    :type stats: dict[str, Any]
    :param artifact_paths: Optional relative paths to materialized artifacts.
    :type artifact_paths: list[str] or None
    :return: Run manifest.
    :rtype: RetrievalRun
    """
    catalog = corpus.load_catalog()
    created_at = utc_now_iso()
    run_id = hashlib.sha256(f"{recipe.recipe_id}:{created_at}".encode("utf-8")).hexdigest()
    return RetrievalRun(
        run_id=run_id,
        recipe=recipe,
        corpus_uri=catalog.corpus_uri,
        catalog_generated_at=catalog.generated_at,
        created_at=created_at,
        artifact_paths=list(artifact_paths or []),
        stats=stats,
    )


def hash_text(text: str) -> str:
    """
    Hash a text payload for provenance.

    :param text: Text to hash.
    :type text: str
    :return: Secure Hash Algorithm 256 hex digest.
    :rtype: str
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_budget(evidence: Iterable[Evidence], budget: QueryBudget) -> List[Evidence]:
    """
    Apply a query budget to a ranked evidence list.

    :param evidence: Ranked evidence iterable (highest score first).
    :type evidence: Iterable[Evidence]
    :param budget: Budget constraints to enforce.
    :type budget: QueryBudget
    :return: Evidence list respecting the budget.
    :rtype: list[Evidence]
    """
    selected_evidence: List[Evidence] = []
    source_counts: Dict[str, int] = {}
    total_characters = 0

    for candidate_evidence in evidence:
        if len(selected_evidence) >= budget.max_total_items:
            break

        source_key = candidate_evidence.source_uri or candidate_evidence.item_id
        if budget.max_items_per_source is not None:
            if source_counts.get(source_key, 0) >= budget.max_items_per_source:
                continue

        text_character_count = len(candidate_evidence.text or "")
        if budget.max_total_characters is not None:
            if total_characters + text_character_count > budget.max_total_characters:
                continue

        selected_evidence.append(candidate_evidence)
        source_counts[source_key] = source_counts.get(source_key, 0) + 1
        total_characters += text_character_count

    return [
        evidence_item.model_copy(update={"rank": index})
        for index, evidence_item in enumerate(selected_evidence, start=1)
    ]
