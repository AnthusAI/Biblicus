"""
Backend registry for Biblicus retrieval engines.
"""

from __future__ import annotations

from typing import Dict, Type

from .base import RetrievalBackend
from .scan import ScanBackend
from .sqlite_full_text_search import SqliteFullTextSearchBackend


def available_backends() -> Dict[str, Type[RetrievalBackend]]:
    """
    Return the registered retrieval backends.

    :return: Mapping of backend identifiers to backend classes.
    :rtype: dict[str, Type[RetrievalBackend]]
    """
    return {
        ScanBackend.backend_id: ScanBackend,
        SqliteFullTextSearchBackend.backend_id: SqliteFullTextSearchBackend,
    }


def get_backend(backend_id: str) -> RetrievalBackend:
    """
    Instantiate a retrieval backend by identifier.

    :param backend_id: Backend identifier.
    :type backend_id: str
    :return: Backend instance.
    :rtype: RetrievalBackend
    :raises KeyError: If the backend identifier is unknown.
    """
    registry = available_backends()
    backend_class = registry.get(backend_id)
    if backend_class is None:
        known = ", ".join(sorted(registry))
        raise KeyError(f"Unknown backend '{backend_id}'. Known backends: {known}")
    return backend_class()
