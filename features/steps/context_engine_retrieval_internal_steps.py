from __future__ import annotations

from dataclasses import dataclass

from behave import then, when

from biblicus.context_engine.retrieval import _resolve_snapshot
from biblicus.models import ConfigurationManifest, RetrievalSnapshot
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
    Minimal corpus stub that tracks retrieval snapshots.
    """

    def __init__(self, snapshot):
        """
        Initialize the stub with a latest snapshot.

        :param snapshot: Retrieval snapshot to treat as latest.
        :type snapshot: RetrievalSnapshot
        """
        self.latest_snapshot_id = snapshot.snapshot_id
        self._snapshot = snapshot
        self._snapshots = {}

    def load_snapshot(self, snapshot_id: str) -> RetrievalSnapshot:
        """
        Load a retrieval snapshot by identifier.

        :param snapshot_id: Retrieval snapshot identifier.
        :type snapshot_id: str
        :return: Retrieval snapshot instance.
        :rtype: RetrievalSnapshot
        """
        if snapshot_id == self._snapshot.snapshot_id:
            return self._snapshot
        return self._snapshots[snapshot_id]

    def load_catalog(self):
        """
        Return a minimal catalog for this corpus.

        :return: Fake catalog instance.
        :rtype: FakeCatalog
        """
        return FakeCatalog(items={}, corpus_uri="corpus://test", generated_at=utc_now_iso())

    def write_snapshot(self, snapshot: RetrievalSnapshot) -> None:
        """
        Record a retrieval snapshot by identifier.

        :param snapshot: Retrieval snapshot to store.
        :type snapshot: RetrievalSnapshot
        :return: None.
        :rtype: None
        """
        self._snapshots[snapshot.snapshot_id] = snapshot


def _build_snapshot(retriever_id: str) -> RetrievalSnapshot:
    configuration = ConfigurationManifest(
        configuration_id=f"configuration-{retriever_id}",
        retriever_id=retriever_id,
        name="test",
        created_at=utc_now_iso(),
        configuration={},
    )
    return RetrievalSnapshot(
        snapshot_id=f"snapshot-{retriever_id}",
        configuration=configuration,
        corpus_uri="corpus://test",
        catalog_generated_at=utc_now_iso(),
        created_at=utc_now_iso(),
        snapshot_artifacts=[],
    )


@when("I resolve a context retrieval snapshot with a mismatched latest retriever")
def step_resolve_snapshot_mismatch(context) -> None:
    latest_snapshot = _build_snapshot("other")
    corpus = FakeCorpus(latest_snapshot)
    resolved = _resolve_snapshot(
        corpus,
        retriever_id="scan",
        snapshot_id=None,
        configuration_name="Context pack (scan)",
        configuration={},
    )
    context.resolved_snapshot = resolved


@then('the resolved snapshot retriever equals "{retriever_id}"')
def step_resolved_snapshot_retriever(context, retriever_id: str) -> None:
    assert context.resolved_snapshot.configuration.retriever_id == retriever_id
