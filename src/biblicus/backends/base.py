"""
Backend interface for Biblicus retrieval engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from ..corpus import Corpus
from ..models import QueryBudget, RetrievalResult, RetrievalRun


class RetrievalBackend(ABC):
    """
    Abstract interface for retrieval backends.

    :ivar backend_id: Identifier string for the backend.
    :vartype backend_id: str
    """

    backend_id: str

    @abstractmethod
    def build_run(
        self, corpus: Corpus, *, recipe_name: str, config: Dict[str, object]
    ) -> RetrievalRun:
        """
        Build or register a retrieval run for the backend.

        :param corpus: Corpus to build against.
        :type corpus: Corpus
        :param recipe_name: Human name for the recipe.
        :type recipe_name: str
        :param config: Backend-specific configuration values.
        :type config: dict[str, object]
        :return: Run manifest describing the build.
        :rtype: RetrievalRun
        """
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        corpus: Corpus,
        *,
        run: RetrievalRun,
        query_text: str,
        budget: QueryBudget,
    ) -> RetrievalResult:
        """
        Run a retrieval query against a backend.

        :param corpus: Corpus associated with the run.
        :type corpus: Corpus
        :param run: Run manifest to use for querying.
        :type run: RetrievalRun
        :param query_text: Query text to execute.
        :type query_text: str
        :param budget: Evidence selection budget.
        :type budget: QueryBudget
        :return: Retrieval results containing evidence.
        :rtype: RetrievalResult
        """
        raise NotImplementedError
