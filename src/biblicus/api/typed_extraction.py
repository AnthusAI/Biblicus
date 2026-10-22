"""
Typed request and function for the ``extract typed-entities`` command.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field

from .. import typed_extraction as typed_extraction_module
from ..typed_extraction import TypedEntitiesOutput, load_registry
from ..typed_extraction_backends import create_backend
from ..typed_vocabulary import load_vocabulary
from ._common import ApiRequestModel, open_request_corpus


class TypedEntitiesRequest(ApiRequestModel):
    """
    Request to extract typed entities and relations from corpus items.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar vocabulary_path: Closed vocabulary file (YAML or JSON).
    :vartype vocabulary_path: str
    :ivar registry_path: Registry of accepted entities (JSON list), or None to propose every mention.
    :vartype registry_path: str or None
    :ivar backend: ``gliner2`` for the registry matcher followed by GLiNER2, or ``registry-only``.
    :vartype backend: str
    :ivar threshold: Score threshold for the backend, greater than 0 and at most 1.
    :vartype threshold: float
    :ivar item_ids: Items to process; empty for every item with extracted text.
    :vartype item_ids: list[str]
    :ivar extraction_snapshot: Extraction snapshot as ``extractor_id:snapshot_id``, or None for the
        latest snapshot.
    :vartype extraction_snapshot: str or None
    :ivar out_dir: Extra directory that receives ``output.json``, or None.
    :vartype out_dir: str or None
    """

    corpus_path: str = Field(min_length=1)
    vocabulary_path: str = Field(min_length=1)
    registry_path: Optional[str] = Field(default=None, min_length=1)
    backend: Literal["gliner2", "registry-only"] = "gliner2"
    threshold: float = Field(default=0.7, gt=0, le=1)
    item_ids: List[str] = Field(default_factory=list)
    extraction_snapshot: Optional[str] = Field(default=None, min_length=1)
    out_dir: Optional[str] = Field(default=None, min_length=1)


def extract_typed_entities(request: TypedEntitiesRequest) -> TypedEntitiesOutput:
    """
    Extract typed entities and relations from the extracted text of corpus items.

    :param request: Validated request.
    :type request: TypedEntitiesRequest
    :return: Typed entities and relations with evidence.
    :rtype: TypedEntitiesOutput
    :raises FileNotFoundError: If the vocabulary, registry or extraction snapshot is missing.
    :raises ValueError: If an input file is invalid or a requested item has no extracted text.
    """
    vocabulary = load_vocabulary(Path(request.vocabulary_path))
    registry = (
        load_registry(Path(request.registry_path), vocabulary) if request.registry_path else None
    )
    return typed_extraction_module.extract_typed_entities(
        corpus=open_request_corpus(request.corpus_path),
        vocabulary=vocabulary,
        registry=registry,
        backend=create_backend(request.backend),
        threshold=request.threshold,
        item_ids=request.item_ids,
        extraction_snapshot=request.extraction_snapshot,
        out_dir=Path(request.out_dir) if request.out_dir else None,
    )
