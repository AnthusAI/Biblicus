"""
Biblicus public package interface.
"""

from .context_engine import (
    ContextAssembler,
    ContextBudgetSpec,
    ContextDeclaration,
    ContextExpansionSpec,
    ContextPackBudgetSpec,
    ContextPackSpec,
    ContextPolicySpec,
    ContextRetrieverRequest,
    retrieve_context_pack,
)
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
    "ContextAssembler",
    "ContextBudgetSpec",
    "ContextDeclaration",
    "ContextExpansionSpec",
    "ContextPackBudgetSpec",
    "ContextPackSpec",
    "ContextPolicySpec",
    "ContextRetrieverRequest",
    "retrieve_context_pack",
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

__version__ = "0.16.0"
