from __future__ import annotations

from dataclasses import dataclass
from typing import List

from behave import then, when

from biblicus.ai.embeddings import generate_embeddings, generate_embeddings_batch
from biblicus.ai.models import AiProvider, EmbeddingsClientConfig


@when('I generate embeddings for texts "{texts}"')
def step_generate_embeddings_for_texts(context, texts: str) -> None:
    client = EmbeddingsClientConfig(
        provider=AiProvider.OPENAI,
        model="text-embedding-3-small",
        api_key="test-key",
        batch_size=16,
        parallelism=4,
    )
    items = [token.strip() for token in texts.split(",") if token.strip()]
    context.embeddings_vectors = generate_embeddings_batch(client=client, texts=items)


@when("I generate embeddings for no texts")
def step_generate_embeddings_for_no_texts(context) -> None:
    client = EmbeddingsClientConfig(
        provider=AiProvider.OPENAI,
        model="text-embedding-3-small",
        api_key="test-key",
        batch_size=16,
        parallelism=4,
    )
    context.embeddings_vectors = generate_embeddings_batch(client=client, texts=[])


@then("the embeddings output includes {count:d} vectors")
def step_embeddings_output_includes_count(context, count: int) -> None:
    vectors = getattr(context, "embeddings_vectors", None)
    assert vectors is not None
    assert len(vectors) == count


def _parse_vector(raw: str) -> List[float]:
    parsed: List[float] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        parsed.append(float(token))
    return parsed


@then('the first embedding vector equals "{vector}"')
def step_first_embedding_vector_equals(context, vector: str) -> None:
    vectors = getattr(context, "embeddings_vectors", None)
    assert vectors is not None
    assert vectors[0] == _parse_vector(vector)


@then('the second embedding vector equals "{vector}"')
def step_second_embedding_vector_equals(context, vector: str) -> None:
    vectors = getattr(context, "embeddings_vectors", None)
    assert vectors is not None
    assert vectors[1] == _parse_vector(vector)


@dataclass
class _Result:
    returncode: int
    stdout: str
    stderr: str


@when('I attempt to generate embeddings with provider "{provider}"')
def step_attempt_generate_embeddings_with_provider(context, provider: str) -> None:
    try:
        config = EmbeddingsClientConfig(
            provider=AiProvider(provider),
            model="text-embedding-3-small",
            api_key="test-key",
        )
        _ = generate_embeddings_batch(client=config, texts=["alpha"])
        context.last_result = _Result(returncode=0, stdout="", stderr="")
    except Exception as exc:  # noqa: BLE001
        context.last_result = _Result(returncode=2, stdout="", stderr=str(exc))


@when('I generate an embedding for text "{text}"')
def step_generate_embedding_for_text(context, text: str) -> None:
    client = EmbeddingsClientConfig(
        provider=AiProvider.OPENAI,
        model="text-embedding-3-small",
        api_key="test-key",
        batch_size=16,
        parallelism=4,
    )
    context.single_embedding_vector = generate_embeddings(client=client, text=text)


@then('the generated embedding equals "{vector}"')
def step_generated_embedding_equals(context, vector: str) -> None:
    embedding = getattr(context, "single_embedding_vector", None)
    assert embedding is not None
    assert embedding == _parse_vector(vector)


@when('I attempt to generate embeddings for texts "{texts}"')
def step_attempt_generate_embeddings_for_texts(context, texts: str) -> None:
    try:
        client = EmbeddingsClientConfig(
            provider=AiProvider.OPENAI,
            model="text-embedding-3-small",
            api_key="test-key",
            batch_size=16,
            parallelism=4,
        )
        items = [token.strip() for token in texts.split(",") if token.strip()]
        context.embeddings_vectors = generate_embeddings_batch(client=client, texts=items)
        context.last_result = _Result(returncode=0, stdout="", stderr="")
    except Exception as exc:  # noqa: BLE001
        context.last_result = _Result(returncode=2, stdout="", stderr=str(exc))
