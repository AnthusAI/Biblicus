from __future__ import annotations

from pathlib import Path

from behave import given, then, when

from biblicus.context_engine import ContextRetrieverRequest, retrieve_context_pack
from biblicus.corpus import Corpus


def _corpus_path(context, name: str) -> Path:
    return (context.workdir / name).resolve()


@given('I ingest text items into corpus "{name}":')
def step_ingest_text_items(context, name: str) -> None:
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    for row in context.table:
        filename = row["filename"]
        contents = row["contents"]
        corpus.ingest_item(
            contents.encode("utf-8"),
            filename=filename,
            media_type="text/plain",
            tags=["context-engine"],
            title=None,
            source_uri=f"bdd:{filename}",
        )


@when(
    'I retrieve a context pack from corpus "{name}" with retriever "{retriever_id}" for query "{query}"'
)
def step_retrieve_context_pack(context, name: str, retriever_id: str, query: str) -> None:
    corpus_path = _corpus_path(context, name)
    request = ContextRetrieverRequest(
        query=query,
        limit=1,
        maximum_total_characters=200,
        metadata={
            "retriever_id": retriever_id,
            "corpus_root": str(corpus_path),
            "configuration": {
                "embedding_provider": {"provider_id": "hash-embedding", "dimensions": 32},
                "maximum_cache_total_items": 100,
            },
        },
    )
    context.context_pack = retrieve_context_pack(
        request=request,
        corpus=Corpus.open(corpus_path),
        retriever_id=retriever_id,
        configuration_name="Context engine test",
        configuration=request.metadata["configuration"],
    )
    context.previous_context_pack_text = context.context_pack.text


@when(
    'I retrieve a context pack from corpus "{name}" with retriever "{retriever_id}" for query "{query}" and store the snapshot id'
)
def step_retrieve_context_pack_store_snapshot(
    context, name: str, retriever_id: str, query: str
) -> None:
    step_retrieve_context_pack(context, name, retriever_id, query)
    corpus_path = _corpus_path(context, name)
    corpus = Corpus.open(corpus_path)
    context.retrieval_snapshot_id = corpus.latest_snapshot_id


@when(
    'I retrieve a context pack from corpus "{name}" with retriever "{retriever_id}" for query "{query}" without a configuration config'
)
def step_retrieve_context_pack_without_configuration(
    context, name: str, retriever_id: str, query: str
) -> None:
    corpus_path = _corpus_path(context, name)
    request = ContextRetrieverRequest(
        query=query,
        limit=1,
        maximum_total_characters=200,
        metadata={"retriever_id": retriever_id, "corpus_root": str(corpus_path)},
    )
    context.context_pack_error = None
    try:
        context.context_pack = retrieve_context_pack(
            request=request,
            corpus=Corpus.open(corpus_path),
            retriever_id=retriever_id,
        )
    except Exception as exc:
        context.context_pack_error = exc


@when(
    'I retrieve a context pack from corpus "{name}" with retriever "{retriever_id}" for query "{query}" using snapshot id with max tokens {max_tokens:d}'
)
def step_retrieve_context_pack_with_snapshot_id(
    context, name: str, retriever_id: str, query: str, max_tokens: int
) -> None:
    corpus_path = _corpus_path(context, name)
    request = ContextRetrieverRequest(
        query=query,
        limit=1,
        max_tokens=max_tokens,
        metadata={"retriever_id": retriever_id, "corpus_root": str(corpus_path)},
    )
    context.context_pack = retrieve_context_pack(
        request=request,
        corpus=Corpus.open(corpus_path),
        retriever_id=retriever_id,
        snapshot_id=context.retrieval_snapshot_id,
    )


@then('the context pack text contains "{text}"')
def step_context_pack_text_contains(context, text: str) -> None:
    assert text in context.context_pack.text


@then('the context pack error should mention "{message}"')
def step_context_pack_error_mentions(context, message: str) -> None:
    error = getattr(context, "context_pack_error", None)
    assert error is not None
    assert message in str(error)


@then("the context pack text matches the previous result")
def step_context_pack_text_matches_previous(context) -> None:
    assert context.context_pack.text == context.previous_context_pack_text
