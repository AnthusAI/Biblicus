from __future__ import annotations

import json
from pathlib import Path
from typing import List
from unittest.mock import patch

import numpy as np
from behave import then, when

from biblicus.chunking import (
    Chunker,
    ChunkerConfig,
    FixedCharWindowChunker,
    FixedTokenWindowChunker,
    TextChunk,
    Tokenizer,
    TokenizerConfig,
    TokenSpan,
    WhitespaceTokenizer,
)
from biblicus.corpus import Corpus
from biblicus.embedding_providers import (
    EmbeddingProvider,
    EmbeddingProviderConfig,
    HashEmbeddingProvider,
)
from biblicus.models import ExtractionSnapshotReference, QueryBudget
from biblicus.retrievers.embedding_index_common import (
    ChunkRecord,
    EmbeddingIndexConfiguration,
    _load_text_from_item,
    collect_chunks,
    iter_text_payloads,
    read_chunks_jsonl,
)
from biblicus.retrievers.embedding_index_file import (
    EmbeddingIndexFileRetriever,
    _top_indices_batched,
)
from biblicus.retrievers.embedding_index_inmemory import (
    EmbeddingIndexInMemoryRetriever,
    _top_indices,
)


@then("a NotImplementedError is raised")
def step_not_implemented_error_is_raised(context) -> None:
    exc = getattr(context, "last_error", None)
    assert exc is not None, "Expected an error but no error was raised"
    assert isinstance(exc, NotImplementedError), f"Expected NotImplementedError, got {type(exc)}"


@when("I attempt to validate an invalid token span")
def step_attempt_invalid_token_span(context) -> None:
    try:
        TokenSpan(token="x", span_start=5, span_end=5)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to validate an invalid text chunk")
def step_attempt_invalid_text_chunk(context) -> None:
    try:
        TextChunk(chunk_id=0, item_id="item", span_start=5, span_end=5, text="x")
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to validate a text chunk with empty text")
def step_attempt_text_chunk_empty_text(context) -> None:
    try:
        TextChunk(chunk_id=0, item_id="item", span_start=0, span_end=1, text="")
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to validate an invalid chunk record")
def step_attempt_invalid_chunk_record(context) -> None:
    try:
        ChunkRecord(item_id="item", span_start=5, span_end=5)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to construct a fixed-char-window chunker with invalid parameters")
def step_attempt_invalid_fixed_char_window_parameters(context) -> None:
    errors: List[Exception] = []
    for window_characters, overlap_characters in [(0, 0), (10, -1), (10, 10)]:
        try:
            FixedCharWindowChunker(
                window_characters=window_characters, overlap_characters=overlap_characters
            )
        except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
            errors.append(exc)
    if not errors:
        raise AssertionError("Expected FixedCharWindowChunker to reject invalid configuration")
    context.last_error = errors[-1]


@when("I attempt to construct a fixed-token-window chunker with invalid parameters")
def step_attempt_invalid_fixed_token_window_parameters(context) -> None:
    errors: List[Exception] = []
    for window_tokens, overlap_tokens in [(0, 0), (10, -1), (10, 10)]:
        try:
            FixedTokenWindowChunker(
                window_tokens=window_tokens,
                overlap_tokens=overlap_tokens,
                tokenizer=WhitespaceTokenizer(),
            )
        except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
            errors.append(exc)
    if not errors:
        raise AssertionError("Expected FixedTokenWindowChunker to reject invalid configuration")
    context.last_error = errors[-1]


@when("I attempt to construct a hash embedding provider with invalid dimensions")
def step_attempt_invalid_hash_embedding_dimensions(context) -> None:
    try:
        HashEmbeddingProvider(dimensions=0)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to build a tokenizer from an unknown tokenizer_id")
def step_attempt_build_unknown_tokenizer(context) -> None:
    try:
        TokenizerConfig(tokenizer_id="not-a-tokenizer").build_tokenizer()
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to build a chunker from an unknown chunker_id")
def step_attempt_build_unknown_chunker(context) -> None:
    try:
        ChunkerConfig(chunker_id="not-a-chunker").build_chunker(tokenizer=None)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to build a fixed-char-window chunker without required configuration")
def step_attempt_build_fixed_char_window_without_required_config(context) -> None:
    try:
        ChunkerConfig(chunker_id="fixed-char-window").build_chunker(tokenizer=None)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to build a fixed-token-window chunker without required configuration")
def step_attempt_build_fixed_token_window_without_required_config(context) -> None:
    try:
        ChunkerConfig(chunker_id="fixed-token-window", window_tokens=10).build_chunker(
            tokenizer=None
        )
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I chunk whitespace-only text with fixed window chunkers")
def step_chunk_whitespace_only_text(context) -> None:
    fixed_char = FixedCharWindowChunker(window_characters=10, overlap_characters=0)
    fixed_token = FixedTokenWindowChunker(
        window_tokens=5, overlap_tokens=0, tokenizer=WhitespaceTokenizer()
    )
    chunks = []
    chunks.extend(fixed_char.chunk_text(item_id="item", text=" " * 25, starting_chunk_id=0))
    chunks.extend(fixed_token.chunk_text(item_id="item", text="", starting_chunk_id=0))
    context.last_chunk_count = len(chunks)


@then("the chunk count is {count:d}")
def step_chunk_count(context, count: int) -> None:
    assert int(getattr(context, "last_chunk_count", -1)) == count


@when("I attempt to call a tokenizer base implementation")
def step_attempt_tokenizer_base_implementation(context) -> None:
    class TokenizerBaseImplementation(Tokenizer):
        tokenizer_id = "tokenizer-base-implementation"

        def tokenize(self, text: str) -> List[TokenSpan]:
            return super().tokenize(text)

    try:
        TokenizerBaseImplementation().tokenize("hello")
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to call a chunker base implementation")
def step_attempt_chunker_base_implementation(context) -> None:
    class ChunkerBaseImplementation(Chunker):
        chunker_id = "chunker-base-implementation"

        def chunk_text(self, *, item_id: str, text: str, starting_chunk_id: int) -> List[TextChunk]:
            return super().chunk_text(
                item_id=item_id, text=text, starting_chunk_id=starting_chunk_id
            )

    try:
        ChunkerBaseImplementation().chunk_text(item_id="item", text="hello", starting_chunk_id=0)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I attempt to call an embedding provider base implementation")
def step_attempt_embedding_provider_base_implementation(context) -> None:
    class EmbeddingProviderBaseImplementation(EmbeddingProvider):
        provider_id = "embedding-provider-base-implementation"

        def embed_texts(self, texts: List[str]) -> np.ndarray:
            return super().embed_texts(texts)

    try:
        EmbeddingProviderBaseImplementation().embed_texts(["hello"])
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when('I load markdown text "{filename}" with front matter and body')
def step_load_markdown_text_front_matter(context, filename: str) -> None:
    corpus_root = context.workdir / "markdown_corpus"
    corpus_root.mkdir(parents=True, exist_ok=True)
    relpath = filename
    raw = "---\n" "title: Example\n" "tags: [a, b]\n" "---\n\n" "Body line one.\nBody line two.\n"
    (corpus_root / relpath).write_text(raw, encoding="utf-8")

    corpus = Corpus(corpus_root)
    context.loaded_markdown_text = _load_text_from_item(
        corpus,
        item_id="item",
        relpath=relpath,
        media_type="text/markdown",
        extraction_reference=None,
    )
    extraction_reference = ExtractionSnapshotReference(
        extractor_id="extractor", snapshot_id="missing"
    )
    with patch.object(Corpus, "read_extracted_text", return_value=None):
        context.loaded_markdown_text_with_missing_extraction = _load_text_from_item(
            corpus,
            item_id="item",
            relpath=relpath,
            media_type="text/markdown",
            extraction_reference=extraction_reference,
        )
    context.non_text_payload = _load_text_from_item(
        corpus,
        item_id="item",
        relpath=relpath,
        media_type="application/octet-stream",
        extraction_reference=None,
    )


@then("the loaded markdown text equals the body only")
def step_loaded_markdown_text_equals_body(context) -> None:
    loaded = getattr(context, "loaded_markdown_text", None)
    assert loaded == "Body line one.\nBody line two.\n"
    assert getattr(context, "loaded_markdown_text_with_missing_extraction", None) == loaded
    assert getattr(context, "non_text_payload", "missing") is None


@when("I write a chunks JSONL file with a blank line")
def step_write_chunks_jsonl_blank_line(context) -> None:
    path = context.workdir / "chunks.jsonl"
    record = ChunkRecord(item_id="item", span_start=0, span_end=1).model_dump()
    payload = json.dumps(record) + "\n\n"
    path.write_text(payload, encoding="utf-8")
    context.chunks_jsonl_path = path


@when("I read the chunks JSONL file")
def step_read_chunks_jsonl_file(context) -> None:
    path = getattr(context, "chunks_jsonl_path", None)
    assert isinstance(path, Path)
    context.chunk_records = read_chunks_jsonl(path)


@then("the chunk record count is {count:d}")
def step_chunk_record_count(context, count: int) -> None:
    records = getattr(context, "chunk_records", None)
    assert isinstance(records, list)
    assert len(records) == count


@when('I attempt to query retriever "{backend_id}" with an invalid query embedding shape')
def step_attempt_query_invalid_query_embedding_shape(context, backend_id: str) -> None:
    corpus_root = (context.workdir / "corpus").resolve()
    corpus = Corpus(corpus_root)
    snapshot = corpus.load_snapshot(str(getattr(context, "last_snapshot_id")))

    if backend_id == EmbeddingIndexFileRetriever.retriever_id:
        retriever = EmbeddingIndexFileRetriever()
    elif backend_id == EmbeddingIndexInMemoryRetriever.retriever_id:
        retriever = EmbeddingIndexInMemoryRetriever()
    else:
        raise AssertionError(f"Unsupported retriever in this scenario: {backend_id}")
    budget = QueryBudget(max_total_items=5, maximum_total_characters=1000, max_items_per_source=5)

    recipe_provider_config = EmbeddingProviderConfig.model_validate(
        snapshot.configuration.configuration["embedding_provider"]
    )

    class BadQueryShapeProvider(HashEmbeddingProvider):
        def embed_texts(self, texts):  # type: ignore[override]
            if len(list(texts)) == 1:
                return np.zeros((2, recipe_provider_config.dimensions), dtype=np.float32)
            return super().embed_texts(texts)

    try:
        with patch.object(
            EmbeddingProviderConfig,
            "build_provider",
            return_value=BadQueryShapeProvider(dimensions=recipe_provider_config.dimensions),
        ):
            retriever.query(corpus, snapshot=snapshot, query_text="United States", budget=budget)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when('I attempt to query retriever "{backend_id}" with inconsistent artifacts')
def step_attempt_query_inconsistent_artifacts(context, backend_id: str) -> None:
    corpus_root = (context.workdir / "corpus").resolve()
    corpus = Corpus(corpus_root)
    snapshot = corpus.load_snapshot(str(getattr(context, "last_snapshot_id")))

    if backend_id == EmbeddingIndexFileRetriever.retriever_id:
        retriever = EmbeddingIndexFileRetriever()
    elif backend_id == EmbeddingIndexInMemoryRetriever.retriever_id:
        retriever = EmbeddingIndexInMemoryRetriever()
    else:
        raise AssertionError(f"Unsupported retriever in this scenario: {backend_id}")

    chunks_relpath = next(
        (p for p in snapshot.snapshot_artifacts if p.endswith(".chunks.jsonl")), None
    )
    assert isinstance(chunks_relpath, str)
    chunks_path = corpus.root / chunks_relpath
    raw_lines = chunks_path.read_text(encoding="utf-8").splitlines()
    assert raw_lines
    chunks_path.write_text("\n".join(raw_lines[:-1]) + "\n", encoding="utf-8")

    budget = QueryBudget(max_total_items=5, maximum_total_characters=1000, max_items_per_source=5)
    try:
        retriever.query(corpus, snapshot=snapshot, query_text="United States", budget=budget)
        context.last_error = None
    except Exception as exc:  # noqa: BLE001 - BDD asserts error type and message explicitly
        context.last_error = exc


@when("I compute top indices with an empty score array")
def step_compute_top_indices_empty(context) -> None:
    context.last_top_indices = _top_indices(np.array([], dtype=np.float32), limit=5)


@when("I compute top indices in batches with limit 0")
def step_compute_top_indices_batched_limit_zero(context) -> None:
    embeddings = np.ones((4, 3), dtype=np.float32)
    query_vector = np.ones((3,), dtype=np.float32)
    context.last_top_indices = _top_indices_batched(
        embeddings=embeddings, query_vector=query_vector, limit=0, batch_rows=2
    )


@then("the top indices list is empty")
def step_top_indices_list_is_empty(context) -> None:
    indices = getattr(context, "last_top_indices", None)
    assert isinstance(indices, list)
    assert indices == []


@when("I iterate text payloads with invalid catalog items")
def step_iter_text_payloads_with_invalid_catalog_items(context) -> None:
    corpus_root = context.workdir / "iter_corpus"
    corpus_root.mkdir(parents=True, exist_ok=True)
    (corpus_root / "whitespace.txt").write_text("   \n\n", encoding="utf-8")
    corpus = Corpus(corpus_root)

    class CatalogLike:
        def __init__(self, items):
            self.items = items

    class ItemLike:
        def __init__(self, item_id: str, relpath: str, media_type: str):
            self.id = item_id
            self.relpath = relpath
            self.media_type = media_type

    catalog = CatalogLike(
        items={
            "missing-id": ItemLike(item_id="", relpath="whitespace.txt", media_type="text/plain"),
            "missing-media-type": ItemLike(
                item_id="item2", relpath="whitespace.txt", media_type=""
            ),
            "whitespace": ItemLike(
                item_id="item", relpath="whitespace.txt", media_type="text/plain"
            ),
        }
    )
    corpus.load_catalog = lambda: catalog  # type: ignore[method-assign]
    payloads = list(iter_text_payloads(corpus, extraction_reference=None))
    context.iter_text_payload_count = len(payloads)


@then("the iterated text payload count is {count:d}")
def step_iterated_text_payload_count(context, count: int) -> None:
    assert int(getattr(context, "iter_text_payload_count", -1)) == count


@when("I collect chunks when a chunker returns no chunks")
def step_collect_chunks_when_chunker_returns_no_chunks(context) -> None:
    corpus_root = context.workdir / "collect_corpus"
    corpus_root.mkdir(parents=True, exist_ok=True)
    (corpus_root / "text.txt").write_text("non-empty text\n", encoding="utf-8")
    corpus = Corpus(corpus_root)

    class CatalogLike:
        def __init__(self, items):
            self.items = items

    class ItemLike:
        def __init__(self, item_id: str, relpath: str, media_type: str):
            self.id = item_id
            self.relpath = relpath
            self.media_type = media_type

    catalog = CatalogLike(
        items={"text": ItemLike(item_id="item", relpath="text.txt", media_type="text/plain")}
    )
    corpus.load_catalog = lambda: catalog  # type: ignore[method-assign]

    recipe_config = EmbeddingIndexConfiguration.model_validate(
        {
            "chunker": {"chunker_id": "paragraph"},
            "embedding_provider": {"provider_id": "hash-embedding", "dimensions": 8},
        }
    )

    class ChunkerThatReturnsNoChunks(Chunker):
        chunker_id = "chunker-that-returns-no-chunks"

        def chunk_text(self, *, item_id: str, text: str, starting_chunk_id: int) -> List[TextChunk]:
            return []

    with patch.object(ChunkerConfig, "build_chunker", return_value=ChunkerThatReturnsNoChunks()):
        chunks, text_items = collect_chunks(corpus, configuration=recipe_config)
    assert text_items == 1
    context.last_chunk_count = len(chunks)
