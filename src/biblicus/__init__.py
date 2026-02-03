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
    ConfigurationManifest,
    CorpusConfig,
    Evidence,
    IngestResult,
    QueryBudget,
    RetrievalResult,
    RetrievalSnapshot,
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
    "ConfigurationManifest",
    "RetrievalResult",
    "RetrievalSnapshot",
]

__version__ = "1.1.0"
