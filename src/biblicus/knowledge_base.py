"""
High-level knowledge base workflow for turnkey usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .backends import get_backend
from .context import (
    ContextPack,
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_token_budget,
)
from .corpus import Corpus
from .models import QueryBudget, RetrievalResult, RetrievalRun


class KnowledgeBaseDefaults(BaseModel):
    """
    Default configuration for a knowledge base workflow.

    :ivar backend_id: Backend identifier to use for retrieval.
    :vartype backend_id: str
    :ivar recipe_name: Human-readable retrieval recipe name.
    :vartype recipe_name: str
    :ivar query_budget: Default query budget to apply to retrieval.
    :vartype query_budget: QueryBudget
    :ivar tags: Tags to apply when importing the folder.
    :vartype tags: list[str]
    """

    model_config = ConfigDict(extra="forbid")

    backend_id: str = Field(default="scan", min_length=1)
    recipe_name: str = Field(default="Knowledge base", min_length=1)
    query_budget: QueryBudget = Field(
        default_factory=lambda: QueryBudget(
            max_total_items=5,
            max_total_characters=2000,
            max_items_per_source=None,
        )
    )
    tags: List[str] = Field(default_factory=list)


@dataclass
class KnowledgeBase:
    """
    High-level knowledge base wrapper for turnkey workflows.

    :ivar corpus: Corpus instance that stores the ingested items.
    :vartype corpus: Corpus
    :ivar backend_id: Backend identifier used for retrieval.
    :vartype backend_id: str
    :ivar run: Retrieval run manifest associated with the knowledge base.
    :vartype run: RetrievalRun
    :ivar defaults: Default configuration used for this knowledge base.
    :vartype defaults: KnowledgeBaseDefaults
    """

    corpus: Corpus
    backend_id: str
    run: RetrievalRun
    defaults: KnowledgeBaseDefaults
    _temp_dir: Optional[TemporaryDirectory]

    @classmethod
    def from_folder(
        cls,
        folder: str | Path,
        *,
        backend_id: Optional[str] = None,
        recipe_name: Optional[str] = None,
        query_budget: Optional[QueryBudget] = None,
        tags: Optional[Sequence[str]] = None,
        corpus_root: Optional[str | Path] = None,
    ) -> "KnowledgeBase":
        """
        Build a knowledge base from a folder of files.

        :param folder: Folder containing source files.
        :type folder: str or Path
        :param backend_id: Optional backend identifier override.
        :type backend_id: str or None
        :param recipe_name: Optional recipe name override.
        :type recipe_name: str or None
        :param query_budget: Optional query budget override.
        :type query_budget: QueryBudget or None
        :param tags: Optional tags to apply during import.
        :type tags: Sequence[str] or None
        :param corpus_root: Optional corpus root override.
        :type corpus_root: str or Path or None
        :return: Knowledge base instance.
        :rtype: KnowledgeBase
        :raises FileNotFoundError: If the folder does not exist.
        :raises NotADirectoryError: If the folder is not a directory.
        """
        source_root = Path(folder).resolve()
        if not source_root.exists():
            raise FileNotFoundError(f"Knowledge base folder does not exist: {source_root}")
        if not source_root.is_dir():
            raise NotADirectoryError(f"Knowledge base folder is not a directory: {source_root}")

        defaults = KnowledgeBaseDefaults()
        resolved_backend_id = backend_id or defaults.backend_id
        resolved_recipe_name = recipe_name or defaults.recipe_name
        resolved_query_budget = query_budget or defaults.query_budget
        resolved_tags = list(tags) if tags is not None else defaults.tags

        temp_dir: Optional[TemporaryDirectory] = None
        if corpus_root is None:
            temp_dir = TemporaryDirectory(prefix="biblicus-knowledge-base-")
            corpus_root_path = Path(temp_dir.name) / "corpus"
        else:
            corpus_root_path = Path(corpus_root).resolve()

        corpus = Corpus.init(corpus_root_path)
        corpus.import_tree(source_root, tags=resolved_tags)

        backend = get_backend(resolved_backend_id)
        run = backend.build_run(corpus, recipe_name=resolved_recipe_name, config={})

        return cls(
            corpus=corpus,
            backend_id=resolved_backend_id,
            run=run,
            defaults=KnowledgeBaseDefaults(
                backend_id=resolved_backend_id,
                recipe_name=resolved_recipe_name,
                query_budget=resolved_query_budget,
                tags=resolved_tags,
            ),
            _temp_dir=temp_dir,
        )

    def query(self, query_text: str, *, budget: Optional[QueryBudget] = None) -> RetrievalResult:
        """
        Query the knowledge base for evidence.

        :param query_text: Query text to execute.
        :type query_text: str
        :param budget: Optional budget override.
        :type budget: QueryBudget or None
        :return: Retrieval result containing evidence.
        :rtype: RetrievalResult
        """
        backend = get_backend(self.backend_id)
        resolved_budget = budget or self.defaults.query_budget
        return backend.query(
            self.corpus,
            run=self.run,
            query_text=query_text,
            budget=resolved_budget,
        )

    def context_pack(
        self,
        result: RetrievalResult,
        *,
        join_with: str = "\n\n",
        max_tokens: Optional[int] = None,
    ) -> ContextPack:
        """
        Build a context pack from a retrieval result.

        :param result: Retrieval result to convert into context.
        :type result: RetrievalResult
        :param join_with: Join string for evidence blocks.
        :type join_with: str
        :param max_tokens: Optional token budget for the context pack.
        :type max_tokens: int or None
        :return: Context pack text and metadata.
        :rtype: ContextPack
        """
        policy = ContextPackPolicy(join_with=join_with)
        context_pack = build_context_pack(result, policy=policy)
        if max_tokens is None:
            return context_pack
        return fit_context_pack_to_token_budget(
            context_pack,
            policy=policy,
            token_budget=TokenBudget(max_tokens=max_tokens),
        )
