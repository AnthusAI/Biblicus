"""
Context pack building for Biblicus.

A context pack is the text that your application sends to a large language model.
Biblicus produces a context pack from structured retrieval results so that evidence remains a
stable contract while context formatting remains an explicit policy surface.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import Evidence, RetrievalResult


class ContextPackPolicy(BaseModel):
    """
    Policy that controls how evidence becomes context pack text.

    :ivar join_with: Separator inserted between evidence text blocks.
    :vartype join_with: str
    :ivar ordering: Evidence ordering policy (rank, score, or source).
    :vartype ordering: str
    :ivar include_metadata: Whether to include evidence metadata lines in each block.
    :vartype include_metadata: bool
    :ivar metadata_fields: Optional evidence metadata fields to include.
    :vartype metadata_fields: list[str] or None
    """

    model_config = ConfigDict(extra="forbid")

    join_with: str = Field(default="\n\n")
    ordering: str = Field(default="rank", min_length=1)
    include_metadata: bool = Field(default=False)
    metadata_fields: Optional[List[str]] = None


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
    :ivar metadata: Optional metadata included with the block.
    :vartype metadata: dict[str, object] or None
    """

    model_config = ConfigDict(extra="forbid")

    evidence_item_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    metadata: Optional[Dict[str, object]] = None


class ContextBlock(BaseModel):
    """
    Ordered context block used outside retrieval-specific evidence flows.

    :ivar block_id: Stable block identifier.
    :vartype block_id: str
    :ivar section: Section key such as doctrine, taxonomy, desk_memory, or fresh_evidence.
    :vartype section: str
    :ivar text: Text payload for the block.
    :vartype text: str
    :ivar required: Whether this block is mandatory even when budgets are tight.
    :vartype required: bool
    :ivar priority: Higher values indicate more important blocks within the same order.
    :vartype priority: int
    :ivar metadata: Optional source/debug metadata for the block.
    :vartype metadata: dict[str, object] or None
    """

    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(min_length=1)
    section: str = Field(min_length=1)
    text: str = Field(min_length=1)
    required: bool = False
    priority: int = 0
    metadata: Optional[Dict[str, object]] = None


class ContextSectionBudget(BaseModel):
    """
    Token share budget for one logical section of an assembled context pack.

    :ivar section: Section key.
    :vartype section: str
    :ivar share: Fraction of the total token budget reserved for the section.
    :vartype share: float
    """

    model_config = ConfigDict(extra="forbid")

    section: str = Field(min_length=1)
    share: float = Field(gt=0, le=1)


class ContextBlockBuildRequest(BaseModel):
    """
    Request to build a budgeted context pack from ordered context blocks.

    :ivar blocks: Ordered context blocks.
    :vartype blocks: list[ContextBlock]
    :ivar join_with: Separator inserted between blocks.
    :vartype join_with: str
    :ivar max_tokens: Optional overall token budget.
    :vartype max_tokens: int or None
    :ivar max_characters: Optional overall character budget.
    :vartype max_characters: int or None
    :ivar section_budgets: Optional per-section token share budgets.
    :vartype section_budgets: list[ContextSectionBudget]
    :ivar token_counter: Token counter configuration.
    :vartype token_counter: TokenCounter
    """

    model_config = ConfigDict(extra="forbid")

    blocks: List[ContextBlock] = Field(default_factory=list)
    join_with: str = Field(default="\n\n")
    max_tokens: Optional[int] = Field(default=None, ge=1)
    max_characters: Optional[int] = Field(default=None, ge=1)
    section_budgets: List[ContextSectionBudget] = Field(default_factory=list)
    token_counter: TokenCounter = Field(default_factory=lambda: TokenCounter())


class ContextBlockBuildResult(BaseModel):
    """
    Result of building a budgeted context pack from ordered context blocks.

    :ivar text: Final context-pack text.
    :vartype text: str
    :ivar included_blocks: Blocks included in the final output.
    :vartype included_blocks: list[ContextBlock]
    :ivar dropped_blocks: Blocks removed during budget fitting.
    :vartype dropped_blocks: list[ContextBlock]
    :ivar section_token_counts: Token counts per included section.
    :vartype section_token_counts: dict[str, int]
    :ivar total_tokens: Total token count for the final text.
    :vartype total_tokens: int
    :ivar total_characters: Total character count for the final text.
    :vartype total_characters: int
    :ivar max_tokens: Applied overall token budget.
    :vartype max_tokens: int or None
    :ivar max_characters: Applied overall character budget.
    :vartype max_characters: int or None
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    included_blocks: List[ContextBlock] = Field(default_factory=list)
    dropped_blocks: List[ContextBlock] = Field(default_factory=list)
    section_token_counts: Dict[str, int] = Field(default_factory=dict)
    total_tokens: int = Field(ge=0)
    total_characters: int = Field(ge=0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    max_characters: Optional[int] = Field(default=None, ge=1)


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


class CharacterBudget(BaseModel):
    """
    Character budget for a context pack.

    :ivar max_characters: Maximum characters permitted for the final context pack text.
    :vartype max_characters: int
    """

    model_config = ConfigDict(extra="forbid")

    max_characters: int = Field(ge=1)


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
    for evidence in _order_evidence(result.evidence, policy=policy):
        if not isinstance(evidence.text, str):
            continue
        trimmed_text = evidence.text.strip()
        if not trimmed_text:
            continue
        metadata = (
            _metadata_for_evidence(evidence, policy=policy) if policy.include_metadata else None
        )
        block_text = _format_block_text(trimmed_text, metadata=metadata)
        selected_blocks.append(
            ContextPackBlock(
                evidence_item_id=evidence.item_id,
                text=block_text,
                metadata=metadata,
            )
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


def fit_context_pack_to_character_budget(
    context_pack: ContextPack,
    *,
    policy: ContextPackPolicy,
    character_budget: CharacterBudget,
) -> ContextPack:
    """
    Fit a context pack to a character budget by dropping trailing blocks.

    :param context_pack: Context pack to fit.
    :type context_pack: ContextPack
    :param policy: Policy controlling how blocks are joined into text.
    :type policy: ContextPackPolicy
    :param character_budget: Character budget to enforce.
    :type character_budget: CharacterBudget
    :return: Fitted context pack.
    :rtype: ContextPack
    """
    remaining_blocks: List[ContextPackBlock] = list(context_pack.blocks)
    max_characters = character_budget.max_characters

    while remaining_blocks:
        candidate_text = policy.join_with.join([block.text for block in remaining_blocks])
        if len(candidate_text) <= max_characters:
            return ContextPack(
                text=candidate_text,
                evidence_count=len(remaining_blocks),
                blocks=remaining_blocks,
            )
        remaining_blocks = remaining_blocks[:-1]

    return ContextPack(text="", evidence_count=0, blocks=[])


def build_context_pack_from_blocks(request: ContextBlockBuildRequest) -> ContextBlockBuildResult:
    """
    Build a deterministic context pack from ordered context blocks.

    The algorithm preserves caller-provided order. It first enforces per-section
    token share budgets, then overall character and token budgets by dropping
    trailing non-required blocks.

    :param request: Context block build request.
    :type request: ContextBlockBuildRequest
    :return: Budgeted context-pack result.
    :rtype: ContextBlockBuildResult
    """
    included_blocks = [
        block.model_copy(update={"text": block.text.strip()})
        for block in request.blocks
        if isinstance(block.text, str) and block.text.strip()
    ]
    dropped_blocks: List[ContextBlock] = []

    if request.max_tokens is not None and request.section_budgets:
        for section_budget in request.section_budgets:
            section_cap = max(1, int(request.max_tokens * float(section_budget.share)))
            included_blocks, newly_dropped = _fit_blocks_for_section_budget(
                included_blocks,
                join_with=request.join_with,
                section=section_budget.section,
                max_tokens=section_cap,
                token_counter=request.token_counter,
            )
            dropped_blocks.extend(newly_dropped)

    if request.max_characters is not None:
        included_blocks, newly_dropped = _fit_blocks_to_character_budget(
            included_blocks,
            join_with=request.join_with,
            max_characters=request.max_characters,
        )
        dropped_blocks.extend(newly_dropped)

    if request.max_tokens is not None:
        included_blocks, newly_dropped = _fit_blocks_to_token_budget(
            included_blocks,
            join_with=request.join_with,
            max_tokens=request.max_tokens,
            token_counter=request.token_counter,
        )
        dropped_blocks.extend(newly_dropped)

    text = request.join_with.join([block.text for block in included_blocks])
    section_token_counts = _section_token_counts(
        included_blocks,
        tokenizer_id=request.token_counter.tokenizer_id,
    )
    return ContextBlockBuildResult(
        text=text,
        included_blocks=included_blocks,
        dropped_blocks=dropped_blocks,
        section_token_counts=section_token_counts,
        total_tokens=count_tokens(text, tokenizer_id=request.token_counter.tokenizer_id) if text else 0,
        total_characters=len(text),
        max_tokens=request.max_tokens,
        max_characters=request.max_characters,
    )


def _order_evidence(
    evidence: List[Evidence],
    *,
    policy: ContextPackPolicy,
) -> List[Evidence]:
    """
    Order evidence items according to the context pack policy.

    :param evidence: Evidence list to order.
    :type evidence: list[Evidence]
    :param policy: Context pack policy.
    :type policy: ContextPackPolicy
    :return: Ordered evidence list.
    :rtype: list[Evidence]
    """
    if policy.ordering == "rank":
        return sorted(evidence, key=lambda item: (item.rank, item.item_id))
    if policy.ordering == "score":
        return sorted(evidence, key=lambda item: (-item.score, item.item_id))
    if policy.ordering == "source":
        return sorted(
            evidence,
            key=lambda item: (
                item.source_uri or item.item_id,
                -item.score,
                item.item_id,
            ),
        )
    raise ValueError(f"Unknown context pack ordering: {policy.ordering}")


def _metadata_for_evidence(
    evidence: Evidence,
    *,
    policy: ContextPackPolicy,
) -> Dict[str, object]:
    """
    Build metadata for a context pack block.

    :param evidence: Evidence item to describe.
    :type evidence: Evidence
    :return: Metadata mapping.
    :rtype: dict[str, object]
    """
    metadata = {
        "item_id": evidence.item_id,
        "source_uri": evidence.source_uri or "none",
        "score": evidence.score,
        "stage": evidence.stage,
    }
    extra = evidence.metadata or {}
    if policy.metadata_fields is not None:
        extra = {key: extra.get(key) for key in policy.metadata_fields if key in extra}
    for key, value in extra.items():
        if key not in metadata:
            metadata[key] = value
    return metadata


def _format_block_text(text: str, *, metadata: Optional[Dict[str, object]]) -> str:
    """
    Format a context pack block text with optional metadata.

    :param text: Evidence text.
    :type text: str
    :param metadata: Optional metadata mapping.
    :type metadata: dict[str, object] or None
    :return: Formatted block text.
    :rtype: str
    """
    if not metadata:
        return text
    ordered_keys = ["item_id", "source_uri", "score", "stage"]
    metadata_lines = [f"{key}: {metadata[key]}" for key in ordered_keys if key in metadata]
    for key in sorted(metadata.keys()):
        if key in ordered_keys:
            continue
        metadata_lines.append(f"{key}: {metadata[key]}")
    metadata_text = "\n".join(metadata_lines)
    return f"{metadata_text}\n{text}"


def _fit_blocks_for_section_budget(
    blocks: List[ContextBlock],
    *,
    join_with: str,
    section: str,
    max_tokens: int,
    token_counter: TokenCounter,
) -> tuple[List[ContextBlock], List[ContextBlock]]:
    included = list(blocks)
    dropped: List[ContextBlock] = []
    while _section_token_count(included, section=section, join_with=join_with, tokenizer_id=token_counter.tokenizer_id) > max_tokens:
        drop_index = _last_droppable_block_index(included, section=section)
        if drop_index is None:
            break
        dropped.append(included.pop(drop_index))
    return included, dropped


def _fit_blocks_to_token_budget(
    blocks: List[ContextBlock],
    *,
    join_with: str,
    max_tokens: int,
    token_counter: TokenCounter,
) -> tuple[List[ContextBlock], List[ContextBlock]]:
    included = list(blocks)
    dropped: List[ContextBlock] = []
    while included:
        text = join_with.join([block.text for block in included])
        if count_tokens(text, tokenizer_id=token_counter.tokenizer_id) <= max_tokens:
            break
        drop_index = _last_droppable_block_index(included)
        if drop_index is None:
            break
        dropped.append(included.pop(drop_index))
    return included, dropped


def _fit_blocks_to_character_budget(
    blocks: List[ContextBlock],
    *,
    join_with: str,
    max_characters: int,
) -> tuple[List[ContextBlock], List[ContextBlock]]:
    included = list(blocks)
    dropped: List[ContextBlock] = []
    while included:
        text = join_with.join([block.text for block in included])
        if len(text) <= max_characters:
            break
        drop_index = _last_droppable_block_index(included)
        if drop_index is None:
            break
        dropped.append(included.pop(drop_index))
    return included, dropped


def _last_droppable_block_index(
    blocks: List[ContextBlock],
    *,
    section: Optional[str] = None,
) -> Optional[int]:
    for index in range(len(blocks) - 1, -1, -1):
        block = blocks[index]
        if section is not None and block.section != section:
            continue
        if block.required:
            continue
        return index
    return None


def _section_token_count(
    blocks: List[ContextBlock],
    *,
    section: str,
    join_with: str,
    tokenizer_id: str,
) -> int:
    section_blocks = [block.text for block in blocks if block.section == section]
    if not section_blocks:
        return 0
    return count_tokens(join_with.join(section_blocks), tokenizer_id=tokenizer_id)


def _section_token_counts(
    blocks: List[ContextBlock],
    *,
    tokenizer_id: str,
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for block in blocks:
        counts.setdefault(block.section, 0)
        counts[block.section] += count_tokens(block.text, tokenizer_id=tokenizer_id)
    return counts
