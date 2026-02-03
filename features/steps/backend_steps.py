from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

from behave import then, when

from biblicus.corpus import Corpus
from biblicus.models import (
    ConfigurationManifest,
    QueryBudget,
    RetrievalResult,
    RetrievalSnapshot,
)
from biblicus.retrievers.base import Retriever
from biblicus.retrievers.sqlite_full_text_search import (
    _ensure_full_text_search_version_five,
    _resolve_snapshot_db_path,
)


class _FailingConnection:
    def execute(self, _statement: str) -> None:
        raise sqlite3.OperationalError("full-text search version five unavailable")


class _AbstractRetriever(Retriever):
    retriever_id = "abstract"

    def build_snapshot(
        self, corpus: Corpus, *, configuration_name: str, configuration: Dict[str, object]
    ) -> RetrievalSnapshot:
        return super().build_snapshot(
            corpus, configuration_name=configuration_name, configuration=configuration
        )

    def query(
        self,
        corpus: Corpus,
        *,
        snapshot: RetrievalSnapshot,
        query_text: str,
        budget: QueryBudget,
    ) -> RetrievalResult:
        return super().query(corpus, snapshot=snapshot, query_text=query_text, budget=budget)


@when("I check full-text search version five availability against a failing connection")
def step_check_full_text_search_version_five_failure(context) -> None:
    try:
        _ensure_full_text_search_version_five(_FailingConnection())
        context.backend_error = None
    except RuntimeError as exc:
        context.backend_error = exc


@then("a retriever prerequisite error is raised")
def step_backend_error_raised(context) -> None:
    assert context.backend_error is not None


@when("I attempt to resolve a snapshot without artifacts")
def step_resolve_snapshot_without_artifacts(context) -> None:
    configuration = ConfigurationManifest(
        configuration_id="configuration",
        retriever_id="sqlite-full-text-search",
        name="default",
        created_at="2025-01-01T00:00:00+00:00",
        configuration={},
        description=None,
    )
    snapshot = RetrievalSnapshot(
        snapshot_id="snapshot",
        configuration=configuration,
        corpus_uri="file:///tmp/corpus",
        catalog_generated_at="2025-01-01T00:00:00+00:00",
        created_at="2025-01-01T00:00:00+00:00",
        snapshot_artifacts=[],
        stats={},
    )
    corpus = Corpus.init(Path(context.workdir / "corpus"))
    try:
        _resolve_snapshot_db_path(corpus, snapshot)
        context.backend_error = None
    except FileNotFoundError as exc:
        context.backend_error = exc


@then("a retriever artifact error is raised")
def step_backend_artifact_error(context) -> None:
    assert context.backend_error is not None


@when("I call the abstract retriever methods")
def step_call_abstract_backend(context) -> None:
    corpus = Corpus.init(Path(context.workdir / "abstract"))
    retriever = _AbstractRetriever()
    try:
        retriever.build_snapshot(corpus, configuration_name="default", configuration={})
        context.abstract_build_error = None
    except NotImplementedError as exc:
        context.abstract_build_error = exc

    configuration = ConfigurationManifest(
        configuration_id="configuration",
        retriever_id="abstract",
        name="default",
        created_at="2025-01-01T00:00:00+00:00",
        configuration={},
        description=None,
    )
    snapshot = RetrievalSnapshot(
        snapshot_id="snapshot",
        configuration=configuration,
        corpus_uri="file:///tmp/corpus",
        catalog_generated_at="2025-01-01T00:00:00+00:00",
        created_at="2025-01-01T00:00:00+00:00",
        snapshot_artifacts=[],
        stats={},
    )
    budget = QueryBudget(max_total_items=1, maximum_total_characters=1, max_items_per_source=1)
    try:
        retriever.query(corpus, snapshot=snapshot, query_text="test", budget=budget)
        context.abstract_query_error = None
    except NotImplementedError as exc:
        context.abstract_query_error = exc


@then("the abstract retriever errors are raised")
def step_abstract_retriever_errors(context) -> None:
    assert context.abstract_build_error is not None
    assert context.abstract_query_error is not None
