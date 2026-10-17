"""
Typed requests and functions for the ``query`` and ``reindex`` commands.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from ..evidence_processing import apply_evidence_filter, apply_evidence_reranker
from ..models import QueryBudget, RetrievalResult
from ..retrievers import get_retriever
from ._common import ApiRequestModel, ApiResponseModel, open_request_corpus


class QueryRequest(ApiRequestModel):
    """
    Request to run a retrieval query against a built snapshot.

    The query never builds a snapshot. When ``snapshot_id`` is absent the corpus latest snapshot
    is used, and a corpus without one is an error.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    :ivar query_text: Query text.
    :vartype query_text: str
    :ivar snapshot_id: Snapshot identifier, or None for the corpus latest snapshot.
    :vartype snapshot_id: str or None
    :ivar retriever_id: Retriever the snapshot must use, or None to accept the snapshot retriever.
    :vartype retriever_id: str or None
    :ivar budget: Evidence selection budget.
    :vartype budget: QueryBudget
    :ivar reranker_id: Optional reranker applied after retrieval.
    :vartype reranker_id: str or None
    :ivar minimum_score: Optional minimum score threshold applied after retrieval.
    :vartype minimum_score: float or None
    """

    corpus_path: str = Field(min_length=1)
    query_text: str
    snapshot_id: Optional[str] = Field(default=None, min_length=1)
    retriever_id: Optional[str] = Field(default=None, min_length=1)
    budget: QueryBudget
    reranker_id: Optional[str] = Field(default=None, min_length=1)
    minimum_score: Optional[float] = None


class ReindexRequest(ApiRequestModel):
    """
    Request to rebuild the corpus catalog from the on-disk corpus.

    :ivar corpus_path: Corpus path or uniform resource identifier.
    :vartype corpus_path: str
    """

    corpus_path: str = Field(min_length=1)


class ReindexResponse(ApiResponseModel):
    """
    Catalog rebuild statistics.

    :ivar scanned: Files examined.
    :vartype scanned: int
    :ivar skipped: Files skipped.
    :vartype skipped: int
    :ivar inserted: Catalog entries added.
    :vartype inserted: int
    :ivar updated: Catalog entries refreshed.
    :vartype updated: int
    """

    scanned: int = Field(ge=0)
    skipped: int = Field(ge=0)
    inserted: int = Field(ge=0)
    updated: int = Field(ge=0)


def query(request: QueryRequest) -> RetrievalResult:
    """
    Run a retrieval query and return structured evidence.

    :param request: Validated request.
    :type request: QueryRequest
    :return: Retrieval result with evidence.
    :rtype: RetrievalResult
    :raises ValueError: If no snapshot is available or the retriever does not match the snapshot.
    """
    corpus = open_request_corpus(request.corpus_path)
    snapshot_id = request.snapshot_id or corpus.latest_snapshot_id
    if not snapshot_id:
        raise ValueError(
            "No snapshot identifier provided and no latest snapshot is recorded for this corpus"
        )
    snapshot = corpus.load_snapshot(snapshot_id)
    if request.retriever_id and request.retriever_id != snapshot.configuration.retriever_id:
        raise ValueError(
            "Retriever mismatch: snapshot uses "
            f"{snapshot.configuration.retriever_id!r} but {request.retriever_id!r} was requested"
        )
    retriever = get_retriever(snapshot.configuration.retriever_id)
    result = retriever.query(
        corpus, snapshot=snapshot, query_text=request.query_text, budget=request.budget
    )
    processed_evidence = result.evidence
    if request.reranker_id:
        processed_evidence = apply_evidence_reranker(
            reranker_id=request.reranker_id,
            query_text=result.query_text,
            evidence=processed_evidence,
        )
    if request.minimum_score is not None:
        processed_evidence = apply_evidence_filter(
            filter_id="filter-minimum-score",
            query_text=result.query_text,
            evidence=processed_evidence,
            config={"minimum_score": float(request.minimum_score)},
        )
    if processed_evidence is not result.evidence:
        result = result.model_copy(update={"evidence": processed_evidence})
    return result


def reindex(request: ReindexRequest) -> ReindexResponse:
    """
    Rebuild the corpus catalog from the on-disk corpus.

    :param request: Validated request.
    :type request: ReindexRequest
    :return: Catalog rebuild statistics.
    :rtype: ReindexResponse
    """
    return ReindexResponse.model_validate(open_request_corpus(request.corpus_path).reindex())
