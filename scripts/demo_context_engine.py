"""
Demonstrate the Biblicus Context Engine with the WikiText fixture corpus.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from features.steps.context_engine_registry import RegistryBuilder


def _ensure_repo_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


_ensure_repo_on_path()


def _print_section(title: str) -> None:
    bar = "=" * len(title)
    print(f"\n{title}\n{bar}")


def _shorten(text: str, max_len: int = 160) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _summarize_lines(lines: Iterable[str], limit: int = 5) -> list[str]:
    summaries = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        summaries.append(_shorten(stripped, 140))
        if len(summaries) >= limit:
            break
    return summaries


@dataclass
class DemoResult:
    """
    Container for assembled Context outputs.

    :param label: Context label identifier.
    :type label: str
    :param system_prompt: Assembled system prompt.
    :type system_prompt: str
    :param history: Assembled history messages.
    :type history: list[dict[str, str]]
    :param user_message: Final user message.
    :type user_message: str
    :param token_count: Estimated token count.
    :type token_count: int
    """

    label: str
    system_prompt: str
    history: list[dict[str, str]]
    user_message: str
    token_count: int


def _assemble_context(
    builder: RegistryBuilder,
    context_name: str,
    base_system_prompt: str,
    history_messages: list[dict[str, str]],
    user_message: str,
    template_context: dict,
    retriever_override=None,
) -> DemoResult:
    from biblicus.context_engine import ContextAssembler
    from features.steps.context_engine_retriever import retrieve_wikitext2

    assembler = ContextAssembler(
        builder.registry.contexts,
        retriever_registry=builder.registry.retrievers,
        corpus_registry=builder.registry.corpora,
        default_retriever=retrieve_wikitext2,
    )
    assembled = assembler.assemble(
        context_name=context_name,
        base_system_prompt=base_system_prompt,
        history_messages=history_messages,
        user_message=user_message,
        template_context=template_context,
        retriever_override=retriever_override,
    )
    return DemoResult(
        label=context_name,
        system_prompt=assembled.system_prompt,
        history=assembled.history,
        user_message=assembled.user_message,
        token_count=assembled.token_count,
    )


def _print_demo_result(result: DemoResult) -> None:
    print(f"Context: {result.label}")
    print(f"Token estimate: {result.token_count}")
    print("System prompt:")
    print(_shorten(result.system_prompt, 400))
    if result.history:
        print("History:")
        for entry in result.history:
            print(f"- {entry.get('role')}: {_shorten(entry.get('content', ''), 120)}")
    if result.user_message:
        print("User message:")
        print(_shorten(result.user_message, 200))


def main() -> None:
    """
    Run the Context engine demo for the WikiText fixture.
    """
    from biblicus.context_engine import ContextRetrieverRequest
    from features.steps.context_engine_registry import RegistryBuilder
    from features.steps.context_engine_retriever import (
        ensure_wikitext2_raw,
        load_wikitext_texts,
        retrieve_wikitext2,
    )

    _print_section("Context Engine Demo (Biblicus)")
    ensure_wikitext2_raw()
    print("WikiText fixture ready")

    _print_section("Corpus snapshot")
    sample_lines = load_wikitext_texts("train", limit=200)
    summaries = _summarize_lines(sample_lines, limit=5)
    for idx, summary in enumerate(summaries, start=1):
        print(f"{idx}. {summary}")

    _print_section("Direct retrieval")
    request = ContextRetrieverRequest(
        query="Valkyria Chronicles III",
        limit=3,
        maximum_total_characters=600,
        metadata={"split": "train", "maximum_cache_total_items": 2000},
    )
    pack = retrieve_wikitext2(request)
    print(f"Evidence count: {pack.evidence_count}")
    for block in pack.blocks:
        print(f"- {block.evidence_item_id}: {_shorten(block.text, 160)}")

    _print_section("Dual concept retrieval (full corpus)")
    concept_queries = [
        ("Valkyria Chronicles III", "gaming"),
        ("United States", "geopolitics"),
    ]
    for query_text, label in concept_queries:
        concept_request = ContextRetrieverRequest(
            query=query_text,
            limit=2,
            maximum_total_characters=400,
            metadata={"split": "train"},
        )
        concept_pack = retrieve_wikitext2(concept_request)
        print(f"Query ({label}): {query_text}")
        for block in concept_pack.blocks:
            print(f"- {block.evidence_item_id}: {_shorten(block.text, 140)}")

    builder = RegistryBuilder()
    builder.register_corpus(
        "wikitext",
        {"source": "wikitext2", "split": "train", "maximum_cache_total_items": 2000},
    )
    builder.register_retriever(
        "wikitext_search",
        {
            "corpus": "wikitext",
            "query": "Valkyria Chronicles III",
            "limit": 3,
            "maximum_total_characters": 600,
        },
    )

    builder.register_context(
        "default_context",
        {
            "policy": {
                "input_budget": {"max_tokens": 120},
                "pack_budget": {"default_ratio": 0.6},
                "overflow": "compact",
            },
            "packs": [{"name": "wikitext_search"}],
        },
    )

    builder.register_context(
        "explicit_context",
        {
            "policy": {
                "input_budget": {"max_tokens": 120},
                "pack_budget": {"default_ratio": 0.6},
                "overflow": "compact",
            },
            "messages": [
                {"type": "system", "content": "You are a researcher."},
                {"type": "context", "name": "wikitext_search"},
                {"type": "history"},
                {"type": "user", "content": "Summarize the evidence."},
            ],
        },
    )

    _print_section("Default context assembly")
    default_result = _assemble_context(
        builder,
        "default_context",
        base_system_prompt="You are a support agent.",
        history_messages=[],
        user_message="",
        template_context={"input": {}, "context": {}},
    )
    _print_demo_result(default_result)

    _print_section("Explicit context assembly with history")
    history = [
        {"role": "user", "content": "What is Valkyria Chronicles?"},
        {"role": "assistant", "content": "It is a tactical RPG series."},
    ]
    explicit_result = _assemble_context(
        builder,
        "explicit_context",
        base_system_prompt="",
        history_messages=history,
        user_message="",
        template_context={"input": {}, "context": {}},
    )
    _print_demo_result(explicit_result)

    _print_section("Expansion and pagination")
    builder.register_retriever(
        "paged_retriever",
        {
            "corpus": "wikitext",
            "query": "the",
            "limit": 1,
            "maximum_total_characters": 600,
        },
    )
    builder.register_context(
        "expanding_context",
        {
            "policy": {
                "input_budget": {"max_tokens": 400},
                "pack_budget": {"default_ratio": 1.0},
                "overflow": "compact",
                "expansion": {"max_pages": 3, "min_fill_ratio": 0.9},
            },
            "messages": [
                {"type": "system", "content": "Evidence:"},
                {"type": "context", "name": "paged_retriever"},
                {"type": "user", "content": "Give highlights."},
            ],
        },
    )

    expansion_calls: list[int] = []

    def logging_retriever(request: ContextRetrieverRequest):
        expansion_calls.append(request.offset)
        return retrieve_wikitext2(request)

    expanding_result = _assemble_context(
        builder,
        "expanding_context",
        base_system_prompt="",
        history_messages=[],
        user_message="",
        template_context={"input": {}, "context": {}},
        retriever_override=logging_retriever,
    )
    print(f"Offsets requested: {expansion_calls}")
    _print_demo_result(expanding_result)

    _print_section("Regeneration and compaction")
    builder.register_context(
        "compact_context",
        {
            "policy": {
                "input_budget": {"max_tokens": 20},
                "pack_budget": {"default_ratio": 1.0},
                "overflow": "compact",
                "max_iterations": 3,
            },
            "messages": [
                {
                    "type": "system",
                    "content": "Evidence: Please summarize the evidence with precision.",
                },
                {"type": "context", "name": "wikitext_search"},
                {"type": "user", "content": "Summarize quickly and focus on the key facts."},
            ],
        },
    )

    compaction_calls: list[int | None] = []

    def compacting_retriever(request: ContextRetrieverRequest):
        compaction_calls.append(request.maximum_total_characters)
        return retrieve_wikitext2(request)

    compact_result = _assemble_context(
        builder,
        "compact_context",
        base_system_prompt="",
        history_messages=[],
        user_message="",
        template_context={"input": {}, "context": {}},
        retriever_override=compacting_retriever,
    )
    print(f"Pack budgets: {compaction_calls}")
    _print_demo_result(compact_result)


if __name__ == "__main__":
    main()
