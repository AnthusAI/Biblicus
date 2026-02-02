from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
from behave import then, when

from biblicus.backends.embedding_index_common import (
    ChunkRecord,
    EmbeddingIndexRecipeConfig,
)
from biblicus.backends.embedding_index_file import _build_evidence as build_file_evidence
from biblicus.backends.embedding_index_inmemory import _build_evidence as build_inmemory_evidence
from biblicus.embedding_providers import EmbeddingProviderConfig
from biblicus.models import RecipeManifest, RetrievalRun
from biblicus.time import utc_now_iso


@dataclass
class FakeCatalog:
    """
    Minimal catalog stub for evidence-building tests.

    :ivar items: Catalog item mapping.
    :vartype items: dict[str, object]
    """

    items: dict[str, object]


class FakeCorpus:
    """
    Minimal corpus stub that exposes a catalog.
    """

    def __init__(self, catalog):
        """
        Initialize the stub with a catalog.

        :param catalog: Catalog object to expose.
        :type catalog: FakeCatalog
        """
        self._catalog = catalog

    def load_catalog(self):
        """
        Return the stored catalog.

        :return: Catalog instance.
        :rtype: FakeCatalog
        """
        return self._catalog


def _build_run() -> RetrievalRun:
    recipe = RecipeManifest(
        recipe_id="recipe",
        backend_id="embedding-index-inmemory",
        name="test",
        created_at=utc_now_iso(),
        config={},
    )
    return RetrievalRun(
        run_id="run",
        recipe=recipe,
        corpus_uri="corpus://test",
        catalog_generated_at=utc_now_iso(),
        created_at=utc_now_iso(),
    )


def _build_recipe_config() -> EmbeddingIndexRecipeConfig:
    return EmbeddingIndexRecipeConfig(
        embedding_provider=EmbeddingProviderConfig(provider_id="hash-embedding", dimensions=8)
    )


def _build_fake_corpus() -> FakeCorpus:
    catalog_item = SimpleNamespace(
        relpath="file.bin",
        media_type="application/pdf",
        source_uri="source",
        metadata={},
    )
    catalog = FakeCatalog(items={"item-1": catalog_item})
    return FakeCorpus(catalog)


@when("I build in-memory evidence for a non-text item")
def step_build_inmemory_evidence(context) -> None:
    import biblicus.backends.embedding_index_inmemory as inmemory_module

    corpus = _build_fake_corpus()
    recipe_config = _build_recipe_config()
    scores = np.array([1.0], dtype=np.float32)
    chunk_records = [ChunkRecord(item_id="item-1", span_start=0, span_end=1)]
    original_snippet = inmemory_module._build_snippet
    original_loader = inmemory_module._load_text_for_evidence
    try:
        inmemory_module._build_snippet = lambda *_args, **_kwargs: None  # type: ignore[assignment]
        inmemory_module._load_text_for_evidence = lambda *args, **kwargs: "alpha"  # type: ignore[assignment]
        evidence = build_inmemory_evidence(
            corpus,
            run=_build_run(),
            recipe_config=recipe_config,
            candidates=[0],
            scores=scores,
            chunk_records=chunk_records,
            extraction_reference=None,
        )
    finally:
        inmemory_module._build_snippet = original_snippet  # type: ignore[assignment]
        inmemory_module._load_text_for_evidence = original_loader  # type: ignore[assignment]
    context.evidence_text = evidence[0].text


@when("I build file-backed evidence for a non-text item")
def step_build_file_evidence(context) -> None:
    import biblicus.backends.embedding_index_file as file_module

    corpus = _build_fake_corpus()
    recipe_config = _build_recipe_config()
    embeddings = np.array([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    query_vector = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    chunk_records = [ChunkRecord(item_id="item-1", span_start=0, span_end=1)]
    original_snippet = file_module._build_snippet
    original_loader = file_module._load_text_for_evidence
    try:
        file_module._build_snippet = lambda *_args, **_kwargs: None  # type: ignore[assignment]
        file_module._load_text_for_evidence = lambda *args, **kwargs: "alpha"  # type: ignore[assignment]
        evidence = build_file_evidence(
            corpus,
            run=_build_run(),
            recipe_config=recipe_config,
            candidates=[0],
            embeddings=embeddings,
            query_vector=query_vector,
            chunk_records=chunk_records,
            extraction_reference=None,
        )
    finally:
        file_module._build_snippet = original_snippet  # type: ignore[assignment]
        file_module._load_text_for_evidence = original_loader  # type: ignore[assignment]
    context.evidence_text = evidence[0].text


@then('the evidence text equals "{expected}"')
def step_evidence_text_equals(context, expected: str) -> None:
    assert context.evidence_text == expected
