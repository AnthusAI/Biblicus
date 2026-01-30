from __future__ import annotations

from behave import given, then, when

from biblicus.context import (
    CharacterBudget,
    ContextPackPolicy,
    TokenBudget,
    build_context_pack,
    fit_context_pack_to_character_budget,
    fit_context_pack_to_token_budget,
)
from biblicus.models import Evidence, QueryBudget, RetrievalResult
from biblicus.time import utc_now_iso


@given("a retrieval result exists with evidence text:")
def given_retrieval_result_exists_with_evidence_text(context) -> None:
    evidence_items = []
    for index, row in enumerate(context.table, start=1):
        text_value = row["text"]
        trimmed_text_value = text_value.strip() if isinstance(text_value, str) else ""
        content_ref_value = "content-ref" if not trimmed_text_value else None
        evidence_items.append(
            Evidence(
                item_id=f"item-{index}",
                source_uri="text",
                media_type="text/plain",
                score=float(100 - index),
                rank=index,
                text=text_value,
                content_ref=content_ref_value,
                stage="scan",
                recipe_id="recipe",
                run_id="run",
            )
        )

    context.retrieval_result = RetrievalResult(
        query_text="query",
        budget=QueryBudget(max_total_items=10),
        run_id="run",
        recipe_id="recipe",
        backend_id="scan",
        generated_at=utc_now_iso(),
        evidence=evidence_items,
        stats={},
    )


@given("a retrieval result exists with scored evidence:")
def given_retrieval_result_exists_with_scored_evidence(context) -> None:
    evidence_items = []
    for rank_value, row in enumerate(context.table, start=1):
        score_value = float(row["score"])
        text_value = row["text"]
        content_ref_value = None if str(text_value).strip() else "content-ref"
        evidence_items.append(
            Evidence(
                item_id=f"item-{rank_value}",
                source_uri="text",
                media_type="text/plain",
                score=score_value,
                rank=rank_value,
                text=text_value,
                content_ref=content_ref_value,
                stage="scan",
                recipe_id="recipe",
                run_id="run",
            )
        )

    context.retrieval_result = RetrievalResult(
        query_text="query",
        budget=QueryBudget(max_total_items=10),
        run_id="run",
        recipe_id="recipe",
        backend_id="scan",
        generated_at=utc_now_iso(),
        evidence=evidence_items,
        stats={},
    )


@given("a retrieval result exists with sourced evidence:")
def given_retrieval_result_exists_with_sourced_evidence(context) -> None:
    evidence_items = []
    for rank_value, row in enumerate(context.table, start=1):
        score_value = float(row["score"])
        source_uri_value = row["source_uri"]
        text_value = row["text"]
        content_ref_value = None if str(text_value).strip() else "content-ref"
        evidence_items.append(
            Evidence(
                item_id=f"item-{rank_value}",
                source_uri=source_uri_value,
                media_type="text/plain",
                score=score_value,
                rank=rank_value,
                text=text_value,
                content_ref=content_ref_value,
                stage="scan",
                recipe_id="recipe",
                run_id="run",
            )
        )

    context.retrieval_result = RetrievalResult(
        query_text="query",
        budget=QueryBudget(max_total_items=10),
        run_id="run",
        recipe_id="recipe",
        backend_id="scan",
        generated_at=utc_now_iso(),
        evidence=evidence_items,
        stats={},
    )


@given("the second evidence item has no text payload")
def given_second_evidence_item_has_no_text_payload(context) -> None:
    context.retrieval_result.evidence[1] = context.retrieval_result.evidence[1].model_copy(
        update={"text": None, "content_ref": "content-ref"}
    )


@when('I build a context pack from that retrieval result joining with "{join_with}"')
def when_build_context_pack_from_retrieval_result(context, join_with: str) -> None:
    decoded_join_with = bytes(join_with, "utf-8").decode("unicode_escape")
    context.context_pack_policy = ContextPackPolicy(join_with=decoded_join_with)
    context.context_pack = build_context_pack(
        context.retrieval_result, policy=context.context_pack_policy
    )


@when("I build a context pack from that retrieval result with policy:")
def when_build_context_pack_from_retrieval_result_with_policy(context) -> None:
    settings = {}
    for row in context.table:
        if "key" in row.headings and "value" in row.headings:
            key = row["key"]
            value = row["value"]
        else:
            key = row[0]
            value = row[1]
        settings[str(key).strip()] = str(value).strip()
    join_with_raw = settings.get("join_with", "\\n\\n")
    ordering = settings.get("ordering", "rank")
    include_metadata = settings.get("include_metadata", "false").lower() == "true"
    decoded_join_with = bytes(join_with_raw, "utf-8").decode("unicode_escape")
    context.context_pack_policy = ContextPackPolicy(
        join_with=decoded_join_with,
        ordering=ordering,
        include_metadata=include_metadata,
    )
    context.context_pack = build_context_pack(
        context.retrieval_result, policy=context.context_pack_policy
    )


@then("the context pack text equals:")
def then_context_pack_text_equals(context) -> None:
    assert context.context_pack.text == context.text


@when("I fit the context pack to a token budget of {max_tokens:d} tokens")
def when_fit_context_pack_to_token_budget(context, max_tokens: int) -> None:
    context.context_pack = fit_context_pack_to_token_budget(
        context.context_pack,
        policy=context.context_pack_policy,
        token_budget=TokenBudget(max_tokens=max_tokens),
    )


@when("I fit the context pack to a character budget of {max_characters:d} characters")
def when_fit_context_pack_to_character_budget(context, max_characters: int) -> None:
    context.context_pack = fit_context_pack_to_character_budget(
        context.context_pack,
        policy=context.context_pack_policy,
        character_budget=CharacterBudget(max_characters=max_characters),
    )


@when('I attempt to build a context pack with invalid ordering "{ordering}"')
def when_attempt_build_context_pack_with_invalid_ordering(context, ordering: str) -> None:
    policy = ContextPackPolicy(join_with="\n\n").model_copy(update={"ordering": ordering})
    try:
        _ = build_context_pack(context.retrieval_result, policy=policy)
        context.ordering_error = None
    except ValueError as exc:
        context.ordering_error = exc


@then('the context pack ordering error mentions "{message}"')
def then_context_pack_ordering_error_mentions(context, message: str) -> None:
    error = getattr(context, "ordering_error", None)
    assert error is not None
    assert message in str(error)


@then("the context pack text is empty")
def then_context_pack_text_is_empty(context) -> None:
    assert context.context_pack.text == ""
