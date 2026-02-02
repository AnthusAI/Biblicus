from __future__ import annotations

from dataclasses import dataclass

from behave import then, when

from biblicus.context_engine.retrieval import _resolve_run
from biblicus.models import RecipeManifest, RetrievalRun
from biblicus.time import utc_now_iso


@dataclass
class FakeCatalog:
    """
    Minimal catalog stub for Context retrieval tests.

    :ivar items: Catalog items mapping.
    :vartype items: dict
    :ivar corpus_uri: Corpus identifier.
    :vartype corpus_uri: str
    :ivar generated_at: Catalog timestamp.
    :vartype generated_at: str
    """

    items: dict
    corpus_uri: str
    generated_at: str


class FakeCorpus:
    """
    Minimal corpus stub that tracks retrieval runs.
    """

    def __init__(self, run):
        """
        Initialize the stub with a latest run.

        :param run: Retrieval run to treat as latest.
        :type run: RetrievalRun
        """
        self.latest_run_id = run.run_id
        self._run = run
        self._runs = {}

    def load_run(self, run_id: str) -> RetrievalRun:
        """
        Load a retrieval run by identifier.

        :param run_id: Retrieval run identifier.
        :type run_id: str
        :return: Retrieval run instance.
        :rtype: RetrievalRun
        """
        if run_id == self._run.run_id:
            return self._run
        return self._runs[run_id]

    def load_catalog(self):
        """
        Return a minimal catalog for this corpus.

        :return: Fake catalog instance.
        :rtype: FakeCatalog
        """
        return FakeCatalog(items={}, corpus_uri="corpus://test", generated_at=utc_now_iso())

    def write_run(self, run: RetrievalRun) -> None:
        """
        Record a retrieval run by identifier.

        :param run: Retrieval run to store.
        :type run: RetrievalRun
        :return: None.
        :rtype: None
        """
        self._runs[run.run_id] = run


def _build_run(backend_id: str) -> RetrievalRun:
    recipe = RecipeManifest(
        recipe_id=f"recipe-{backend_id}",
        backend_id=backend_id,
        name="test",
        created_at=utc_now_iso(),
        config={},
    )
    return RetrievalRun(
        run_id=f"run-{backend_id}",
        recipe=recipe,
        corpus_uri="corpus://test",
        catalog_generated_at=utc_now_iso(),
        created_at=utc_now_iso(),
    )


@when("I resolve a context retrieval run with a mismatched latest backend")
def step_resolve_run_mismatch(context) -> None:
    latest_run = _build_run("other")
    corpus = FakeCorpus(latest_run)
    resolved = _resolve_run(
        corpus,
        backend_id="scan",
        run_id=None,
        recipe_name="Context pack (scan)",
        recipe_config={},
    )
    context.resolved_run = resolved


@then('the resolved run backend equals "{backend_id}"')
def step_resolved_run_backend(context, backend_id: str) -> None:
    assert context.resolved_run.recipe.backend_id == backend_id
