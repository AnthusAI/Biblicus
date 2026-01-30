"""
Biblicus public package interface.
"""

from .corpus import Corpus
from .knowledge_base import KnowledgeBase
from .models import (
    CorpusConfig,
    Evidence,
    IngestResult,
    QueryBudget,
    RecipeManifest,
    RetrievalResult,
    RetrievalRun,
)

__all__ = [
    "__version__",
    "Corpus",
    "CorpusConfig",
    "Evidence",
    "IngestResult",
    "KnowledgeBase",
    "QueryBudget",
    "RecipeManifest",
    "RetrievalResult",
    "RetrievalRun",
]

__version__ = "0.10.0"
