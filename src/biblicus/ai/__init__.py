"""
Provider-backed AI utilities for Biblicus.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "AiProvider",
    "EmbeddingsClientConfig",
    "LlmClientConfig",
    "generate_completion",
    "generate_embeddings",
    "generate_embeddings_batch",
]


def __getattr__(name: str) -> Any:
    if name in {"AiProvider", "EmbeddingsClientConfig", "LlmClientConfig"}:
        from .models import AiProvider, EmbeddingsClientConfig, LlmClientConfig

        return {"AiProvider": AiProvider, "EmbeddingsClientConfig": EmbeddingsClientConfig, "LlmClientConfig": LlmClientConfig}[name]
    if name in {"generate_completion"}:
        from .llm import generate_completion

        return generate_completion
    if name in {"generate_embeddings", "generate_embeddings_batch"}:
        from .embeddings import generate_embeddings, generate_embeddings_batch

        return {"generate_embeddings": generate_embeddings, "generate_embeddings_batch": generate_embeddings_batch}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
