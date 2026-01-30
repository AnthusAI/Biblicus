from __future__ import annotations

from behave import then, when

from biblicus.evidence_processing import (
    EvidenceFilterMinimumScoreConfig,
    apply_evidence_filter,
    apply_evidence_reranker,
)


@when('I rerank the retrieval result evidence using "{reranker_id}"')
def when_rerank_retrieval_result_evidence(context, reranker_id: str) -> None:
    context.retrieval_result = context.retrieval_result.model_copy(
        update={
            "evidence": apply_evidence_reranker(
                reranker_id=reranker_id,
                query_text=context.retrieval_result.query_text,
                evidence=context.retrieval_result.evidence,
            )
        }
    )


@when(
    'I filter the retrieval result evidence using "{filter_id}" with minimum score {minimum_score:f}'
)
def when_filter_retrieval_result_evidence(context, filter_id: str, minimum_score: float) -> None:
    configuration = EvidenceFilterMinimumScoreConfig(minimum_score=minimum_score)
    context.retrieval_result = context.retrieval_result.model_copy(
        update={
            "evidence": apply_evidence_filter(
                filter_id=filter_id,
                query_text=context.retrieval_result.query_text,
                evidence=context.retrieval_result.evidence,
                config=configuration.model_dump(),
            )
        }
    )


@then("the evidence text order is:")
def then_evidence_text_order_is(context) -> None:
    expected_text_values = [row["text"] for row in context.table]
    actual_text_values = [evidence_item.text for evidence_item in context.retrieval_result.evidence]
    assert actual_text_values == expected_text_values
