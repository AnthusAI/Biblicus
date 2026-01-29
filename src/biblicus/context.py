"""
Context pack building for Biblicus.

A context pack is the text that your application sends to a large language model.
Biblicus produces a context pack from structured retrieval results so that evidence remains a
stable contract while context formatting remains an explicit policy surface.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import RetrievalResult


class ContextPackPolicy(BaseModel):
    """
    Policy that controls how evidence becomes context pack text.

    :ivar join_with: Separator inserted between evidence text blocks.
    :vartype join_with: str
    """

    model_config = ConfigDict(extra="forbid")

    join_with: str = Field(default="\n\n")


class ContextPack(BaseModel):
    """
    Context pack derived from retrieval evidence.

    :ivar text: Context pack text suitable for inclusion in a model call.
    :vartype text: str
    :ivar evidence_count: Number of evidence blocks included in the context pack.
    :vartype evidence_count: int
    :ivar blocks: Structured blocks that produced the context pack.
    :vartype blocks: list[ContextPackBlock]
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    evidence_count: int = Field(ge=0)
    blocks: List["ContextPackBlock"] = Field(default_factory=list)


class ContextPackBlock(BaseModel):
    """
    A single context pack block derived from one evidence item.

    :ivar evidence_item_id: Item identifier that produced this block.
    :vartype evidence_item_id: str
    :ivar text: Text included in this block.
    :vartype text: str
    """

    model_config = ConfigDict(extra="forbid")

    evidence_item_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class TokenCounter(BaseModel):
    """
    Token counter configuration for token budget fitting.

    This is a lightweight model wrapper so token fitting remains explicit and testable even when
    the underlying tokenizer is provided by an optional dependency.

    :ivar tokenizer_id: Tokenizer identifier (for example, naive-whitespace).
    :vartype tokenizer_id: str
    """

    model_config = ConfigDict(extra="forbid")

    tokenizer_id: str = Field(default="naive-whitespace", min_length=1)


class TokenBudget(BaseModel):
    """
    Token budget for a context pack.

    :ivar max_tokens: Maximum tokens permitted for the final context pack text.
    :vartype max_tokens: int
    """

    model_config = ConfigDict(extra="forbid")

    max_tokens: int = Field(ge=1)


def build_context_pack(result: RetrievalResult, *, policy: ContextPackPolicy) -> ContextPack:
    """
    Build a context pack from a retrieval result using an explicit policy.

    :param result: Retrieval result containing ranked evidence.
    :type result: RetrievalResult
    :param policy: Policy controlling how evidence text is joined.
    :type policy: ContextPackPolicy
    :return: Context pack containing concatenated evidence text.
    :rtype: ContextPack
    """
    selected_blocks: List[ContextPackBlock] = []
    for evidence in result.evidence:
        if not isinstance(evidence.text, str):
            continue
        trimmed_text = evidence.text.strip()
        if not trimmed_text:
            continue
        selected_blocks.append(
            ContextPackBlock(evidence_item_id=evidence.item_id, text=trimmed_text)
        )

    return ContextPack(
        text=policy.join_with.join([block.text for block in selected_blocks]),
        evidence_count=len(selected_blocks),
        blocks=selected_blocks,
    )


def count_tokens(text: str, *, tokenizer_id: str) -> int:
    """
    Count tokens in a text using a tokenizer identifier.

    The default tokenizer is naive-whitespace, which counts whitespace-separated tokens.

    :param text: Text payload to count.
    :type text: str
    :param tokenizer_id: Tokenizer identifier.
    :type tokenizer_id: str
    :return: Token count.
    :rtype: int
    :raises KeyError: If the tokenizer identifier is unknown.
    """
    tokenizers = {
        "naive-whitespace": lambda value: len([token for token in value.split() if token]),
    }
    tokenizer = tokenizers[tokenizer_id]
    return int(tokenizer(text))


def fit_context_pack_to_token_budget(
    context_pack: ContextPack,
    *,
    policy: ContextPackPolicy,
    token_budget: TokenBudget,
    token_counter: Optional[TokenCounter] = None,
) -> ContextPack:
    """
    Fit a context pack to a token budget by dropping trailing blocks.

    This function is deterministic. It never rewrites block text. It only removes blocks from the
    end of the block list until the token budget is met.

    :param context_pack: Context pack to fit.
    :type context_pack: ContextPack
    :param policy: Policy controlling how blocks are joined into text.
    :type policy: ContextPackPolicy
    :param token_budget: Token budget to enforce.
    :type token_budget: TokenBudget
    :param token_counter: Optional token counter configuration.
    :type token_counter: TokenCounter or None
    :return: Fitted context pack.
    :rtype: ContextPack
    """
    token_counter = token_counter or TokenCounter()
    remaining_blocks: List[ContextPackBlock] = list(context_pack.blocks)

    while remaining_blocks:
        candidate_text = policy.join_with.join([block.text for block in remaining_blocks])
        candidate_tokens = count_tokens(candidate_text, tokenizer_id=token_counter.tokenizer_id)
        if candidate_tokens <= token_budget.max_tokens:
            return ContextPack(
                text=candidate_text,
                evidence_count=len(remaining_blocks),
                blocks=remaining_blocks,
            )
        remaining_blocks = remaining_blocks[:-1]

    return ContextPack(text="", evidence_count=0, blocks=[])
