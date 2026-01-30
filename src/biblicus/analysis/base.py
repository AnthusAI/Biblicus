"""
Analysis backend interface for Biblicus.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from pydantic import BaseModel

from ..corpus import Corpus
from ..models import ExtractionRunReference


class CorpusAnalysisBackend(ABC):
    """
    Abstract interface for analysis backends.

    :ivar analysis_id: Identifier string for the analysis backend.
    :vartype analysis_id: str
    """

    analysis_id: str

    @abstractmethod
    def run_analysis(
        self,
        corpus: Corpus,
        *,
        recipe_name: str,
        config: Dict[str, object],
        extraction_run: ExtractionRunReference,
    ) -> BaseModel:
        """
        Run an analysis pipeline for a corpus.

        :param corpus: Corpus to analyze.
        :type corpus: Corpus
        :param recipe_name: Human-readable recipe name.
        :type recipe_name: str
        :param config: Analysis configuration values.
        :type config: dict[str, object]
        :param extraction_run: Extraction run reference for text inputs.
        :type extraction_run: biblicus.models.ExtractionRunReference
        :return: Analysis output model.
        :rtype: pydantic.BaseModel
        """
        raise NotImplementedError
