from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

from behave import then, when

from biblicus.backends.base import RetrievalBackend
from biblicus.backends.sqlite_full_text_search import (
    _ensure_full_text_search_version_five,
    _resolve_run_db_path,
)
from biblicus.corpus import Corpus
from biblicus.models import QueryBudget, RecipeManifest, RetrievalResult, RetrievalRun


class _FailingConnection:
    def execute(self, _statement: str) -> None:
        raise sqlite3.OperationalError("full-text search version five unavailable")


class _AbstractBackend(RetrievalBackend):
    backend_id = "abstract"

    def build_run(
        self, corpus: Corpus, *, recipe_name: str, config: Dict[str, object]
    ) -> RetrievalRun:
        return super().build_run(corpus, recipe_name=recipe_name, config=config)

    def query(
        self,
        corpus: Corpus,
        *,
        run: RetrievalRun,
        query_text: str,
        budget: QueryBudget,
    ) -> RetrievalResult:
        return super().query(corpus, run=run, query_text=query_text, budget=budget)


@when("I check full-text search version five availability against a failing connection")
def step_check_full_text_search_version_five_failure(context) -> None:
    try:
        _ensure_full_text_search_version_five(_FailingConnection())
        context.backend_error = None
    except RuntimeError as exc:
        context.backend_error = exc


@then("a backend prerequisite error is raised")
def step_backend_error_raised(context) -> None:
    assert context.backend_error is not None


@when("I attempt to resolve a run without artifacts")
def step_resolve_run_without_artifacts(context) -> None:
    recipe = RecipeManifest(
        recipe_id="recipe",
        backend_id="sqlite-full-text-search",
        name="default",
        created_at="2025-01-01T00:00:00+00:00",
        config={},
        description=None,
    )
    run = RetrievalRun(
        run_id="run",
        recipe=recipe,
        corpus_uri="file:///tmp/corpus",
        catalog_generated_at="2025-01-01T00:00:00+00:00",
        created_at="2025-01-01T00:00:00+00:00",
        artifact_paths=[],
        stats={},
    )
    corpus = Corpus.init(Path(context.workdir / "corpus"))
    try:
        _resolve_run_db_path(corpus, run)
        context.backend_error = None
    except FileNotFoundError as exc:
        context.backend_error = exc


@then("a backend artifact error is raised")
def step_backend_artifact_error(context) -> None:
    assert context.backend_error is not None


@when("I call the abstract backend methods")
def step_call_abstract_backend(context) -> None:
    corpus = Corpus.init(Path(context.workdir / "abstract"))
    backend = _AbstractBackend()
    try:
        backend.build_run(corpus, recipe_name="default", config={})
        context.abstract_build_error = None
    except NotImplementedError as exc:
        context.abstract_build_error = exc

    recipe = RecipeManifest(
        recipe_id="recipe",
        backend_id="abstract",
        name="default",
        created_at="2025-01-01T00:00:00+00:00",
        config={},
        description=None,
    )
    run = RetrievalRun(
        run_id="run",
        recipe=recipe,
        corpus_uri="file:///tmp/corpus",
        catalog_generated_at="2025-01-01T00:00:00+00:00",
        created_at="2025-01-01T00:00:00+00:00",
        artifact_paths=[],
        stats={},
    )
    budget = QueryBudget(max_total_items=1, max_total_characters=1, max_items_per_source=1)
    try:
        backend.query(corpus, run=run, query_text="test", budget=budget)
        context.abstract_query_error = None
    except NotImplementedError as exc:
        context.abstract_query_error = exc


@then("the abstract backend errors are raised")
def step_abstract_backend_errors(context) -> None:
    assert context.abstract_build_error is not None
    assert context.abstract_query_error is not None
