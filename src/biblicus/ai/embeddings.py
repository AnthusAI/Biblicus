"""
Provider-backed text embeddings.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Sequence

from .models import AiProvider, EmbeddingsClientConfig


def generate_embeddings(*, client: EmbeddingsClientConfig, text: str) -> List[float]:
    """
    Generate a single embedding vector.

    :param client: Embeddings client configuration.
    :type client: biblicus.ai.models.EmbeddingsClientConfig
    :param text: Input text to embed.
    :type text: str
    :return: Embedding vector.
    :rtype: list[float]
    """
    vectors = generate_embeddings_batch(client=client, texts=[text])
    return vectors[0]


def _chunks(texts: Sequence[str], batch_size: int) -> List[List[str]]:
    return [list(texts[idx : idx + batch_size]) for idx in range(0, len(texts), batch_size)]


def generate_embeddings_batch(
    *, client: EmbeddingsClientConfig, texts: Sequence[str]
) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.

    The implementation performs batched requests and can run requests concurrently.

    :param client: Embeddings client configuration.
    :type client: biblicus.ai.models.EmbeddingsClientConfig
    :param texts: Text inputs to embed.
    :type texts: Sequence[str]
    :return: Embedding vectors in input order.
    :rtype: list[list[float]]
    :raises ValueError: If required dependencies or credentials are missing.
    """
    if client.provider != AiProvider.OPENAI:
        raise ValueError(f"Unsupported provider: {client.provider}")
    if not texts:
        return []

    try:
        from openai import OpenAI
    except ImportError as import_error:
        raise ValueError(
            "OpenAI provider requires an optional dependency. "
            'Install it with pip install "biblicus[openai]".'
        ) from import_error

    api_key = client.resolve_api_key()
    client_instance = OpenAI(api_key=api_key)

    batches = _chunks(list(texts), client.batch_size)
    results: List[List[List[float]]] = [None for _ in range(len(batches))]  # type: ignore[list-item]

    def _embed_batch(batch_texts: List[str]) -> List[List[float]]:
        response = client_instance.embeddings.create(model=client.model, input=batch_texts)
        vectors: List[List[float]] = []
        for row in response.data:
            vectors.append([float(value) for value in row.embedding])
        return vectors

    with ThreadPoolExecutor(max_workers=client.parallelism) as executor:
        futures = {executor.submit(_embed_batch, batch): idx for idx, batch in enumerate(batches)}
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()

    flattened: List[List[float]] = []
    for batch_vectors in results:
        for vector in batch_vectors:
            flattened.append(vector)
    return flattened
