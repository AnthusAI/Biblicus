from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from biblicus.context_engine import (
    CompactorDeclaration,
    ContextDeclaration,
    CorpusDeclaration,
    RetrieverDeclaration,
)


@dataclass
class ContextRegistry:
    """
    Registry container for Context engine test declarations.

    :ivar contexts: Registered Context declarations.
    :vartype contexts: dict[str, ContextDeclaration]
    :ivar retrievers: Registered Retriever declarations.
    :vartype retrievers: dict[str, RetrieverDeclaration]
    :ivar corpora: Registered Corpus declarations.
    :vartype corpora: dict[str, CorpusDeclaration]
    :ivar compactors: Registered Compactor declarations.
    :vartype compactors: dict[str, CompactorDeclaration]
    """

    contexts: dict[str, ContextDeclaration] = field(default_factory=dict)
    retrievers: dict[str, RetrieverDeclaration] = field(default_factory=dict)
    corpora: dict[str, CorpusDeclaration] = field(default_factory=dict)
    compactors: dict[str, CompactorDeclaration] = field(default_factory=dict)


class RegistryBuilder:
    """
    Simple builder for Context engine registry tests.
    """

    def __init__(self) -> None:
        """
        Initialize an empty registry.
        """
        self.registry = ContextRegistry()

    def register_context(self, name: str, config: dict[str, Any]) -> None:
        """
        Register a Context declaration for tests.

        :param name: Context name.
        :type name: str
        :param config: Context configuration payload.
        :type config: dict[str, Any]
        :return: None.
        :rtype: None
        """
        context_config = dict(config)
        context_config["name"] = name
        try:
            self.registry.contexts[name] = ContextDeclaration(**context_config)
        except ValidationError as exc:
            raise AssertionError(f"Invalid context '{name}': {exc}") from exc

    def register_corpus(self, name: str, config: dict[str, Any]) -> None:
        """
        Register a Corpus declaration for tests.

        :param name: Corpus name.
        :type name: str
        :param config: Corpus configuration payload.
        :type config: dict[str, Any]
        :return: None.
        :rtype: None
        """
        corpus_config = dict(config)
        try:
            self.registry.corpora[name] = CorpusDeclaration(name=name, config=corpus_config)
        except ValidationError as exc:
            raise AssertionError(f"Invalid corpus '{name}': {exc}") from exc

    def register_retriever(self, name: str, config: dict[str, Any]) -> None:
        """
        Register a Retriever declaration for tests.

        :param name: Retriever name.
        :type name: str
        :param config: Retriever configuration payload.
        :type config: dict[str, Any]
        :return: None.
        :rtype: None
        """
        retriever_config = dict(config)
        corpus_name = retriever_config.pop("corpus", None)
        try:
            self.registry.retrievers[name] = RetrieverDeclaration(
                name=name,
                corpus=corpus_name,
                config=retriever_config,
            )
        except ValidationError as exc:
            raise AssertionError(f"Invalid retriever '{name}': {exc}") from exc

    def register_compactor(self, name: str, config: dict[str, Any]) -> None:
        """
        Register a Compactor declaration for tests.

        :param name: Compactor name.
        :type name: str
        :param config: Compactor configuration payload.
        :type config: dict[str, Any]
        :return: None.
        :rtype: None
        """
        compactor_config = dict(config)
        try:
            self.registry.compactors[name] = CompactorDeclaration(
                name=name,
                config=compactor_config,
            )
        except ValidationError as exc:
            raise AssertionError(f"Invalid compactor '{name}': {exc}") from exc
