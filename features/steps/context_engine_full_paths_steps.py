from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from behave import then, when

from biblicus.context import ContextPack, ContextPackBlock
from biblicus.context_engine.assembler import ContextAssembler
from biblicus.context_engine.models import (
    AssistantMessageSpec,
    ContextBudgetSpec,
    ContextDeclaration,
    ContextExpansionSpec,
    ContextInsertSpec,
    ContextPackBudgetSpec,
    ContextPackSpec,
    ContextPolicySpec,
    HistoryInsertSpec,
    SystemMessageSpec,
    UserMessageSpec,
)


@dataclass
class _RegistrySpec:
    config: dict[str, object]


@dataclass
class _NestedObject:
    value: str


@dataclass
class _BudgetHolder:
    max_tokens: int | None = None
    ratio: float | None = None


def _make_retriever():
    calls = []

    def _retriever(request):
        calls.append(request)
        if request.offset >= 3:
            return None
        evidence_count = request.limit if request.offset == 0 else max(0, request.limit - 1)
        text = f"chunk-{request.offset}"
        blocks = [
            ContextPackBlock(
                evidence_item_id=f"id-{request.offset}",
                text=text,
                metadata={"offset": request.offset},
            )
        ]
        return ContextPack(text=text, evidence_count=evidence_count, blocks=blocks)

    return _retriever, calls


class _NoopCompactionAssembler(ContextAssembler):
    def _apply_compaction_policy(self, text, policy, max_tokens_override=None):  # type: ignore[override]
        return text


class _ForcedCompactionAssembler(ContextAssembler):
    def _apply_context_budget(self, system_prompt, history, user_message, policy):  # type: ignore[override]
        token_count = self._estimate_total_tokens(system_prompt, history, user_message)
        return system_prompt, history, user_message, token_count, True


@when("I exercise context assembly helpers")
def step_exercise_context_assembly_helpers(context) -> None:
    retriever_fn, calls = _make_retriever()

    compactor_registry = {
        "summary": _RegistrySpec(config={"type": "summary"}),
        "truncate": _RegistrySpec(config={"type": "truncate"}),
    }
    retriever_registry = {
        "retriever_pack": _RegistrySpec(
            config={
                "query": "Query {input.query}",
                "limit": 3,
                "offset": 0,
                "maximum_total_characters": 50,
                "maximum_items_per_source": 2,
                "include_metadata": True,
                "metadata_fields": ["published"],
                "retriever_id": "retriever-one",
                "snapshot_id": "snapshot-1",
                "configuration_name": "configuration",
                "configuration": {"type": "example"},
                "corpus": "corpus-one",
                "join_with": " | ",
            }
        ),
        "fallback_pack": _RegistrySpec(config={}),
    }
    corpus_registry = {
        "corpus-one": _RegistrySpec(
            config={
                "split": "train",
                "maximum_cache_total_items": 11,
                "maximum_cache_total_characters": 1200,
                "retriever_id": "retriever-corpus",
                "corpus_root": "/tmp/corpus",
                "snapshot_id": "snapshot-2",
                "configuration_name": "configuration-corpus",
                "configuration": {"source": "fixture"},
            }
        )
    }

    policy = ContextPolicySpec(
        input_budget=ContextBudgetSpec(max_tokens=20),
        pack_budget=ContextPackBudgetSpec(default_ratio=0.5),
        overflow="compact",
        compactor="summary",
        max_iterations=2,
        expansion=ContextExpansionSpec(max_pages=2, min_fill_ratio=0.4),
    )

    nested_default = ContextDeclaration(
        name="nested_default",
        policy=policy,
        packs=[ContextPackSpec(name="fallback_pack")],
    )
    nested_explicit = ContextDeclaration(
        name="nested_explicit",
        policy=policy,
        messages=[
            SystemMessageSpec(type="system", content="Nested system"),
            UserMessageSpec(type="user", content="Nested user"),
        ],
    )
    nested_history = ContextDeclaration(
        name="nested_history",
        messages=[HistoryInsertSpec(type="history")],
    )

    default_context = ContextDeclaration(
        name="default",
        policy=policy,
        packs=[
            ContextPackSpec(name="retriever_pack", weight=2.0),
            ContextPackSpec(name="nested_default", weight=1.0),
        ],
    )
    explicit_context = ContextDeclaration(
        name="explicit",
        policy=policy,
        messages=[
            SystemMessageSpec(type="system", content="System message"),
            ContextInsertSpec(type="context", name="retriever_pack", budget={"ratio": 0.5}),
            HistoryInsertSpec(type="history"),
            UserMessageSpec(type="user", template="Question {input.message}"),
            AssistantMessageSpec(type="assistant", content="Assist"),
        ],
    )

    assembler = ContextAssembler(
        context_registry={
            "default": default_context,
            "explicit": explicit_context,
            "nested_default": nested_default,
            "nested_explicit": nested_explicit,
            "nested_history": nested_history,
        },
        retriever_registry=retriever_registry,
        corpus_registry=corpus_registry,
        compactor_registry=compactor_registry,
        default_retriever=retriever_fn,
    )

    template_context = {
        "input": {"query": "cats", "message": "Tell me"},
        "obj": _NestedObject("ok"),
    }

    assembler._resolve_template("Hello {input.query}", {}, template_context)
    assembler._resolve_template("Value {obj.value}", {}, template_context)
    assembler._resolve_template("", {}, template_context)
    assembler._resolve_template("Override {answer}", {"answer": "ok"}, template_context)

    assembler._render_retriever_pack(
        "retriever_pack",
        template_context=template_context,
        retriever_override=None,
        pack_budget={"max_tokens": 10},
        policy=policy,
        tighten_pack_budget=False,
        weight=1.0,
    )
    assembler._render_retriever_pack(
        "retriever_pack",
        template_context=template_context,
        retriever_override=None,
        pack_budget=None,
        policy=policy,
        tighten_pack_budget=False,
        weight=1.0,
    )
    assembler._render_retriever_pack(
        "fallback_pack",
        template_context={"input": {"message": "Fallback query"}},
        retriever_override=None,
        pack_budget={"ratio": 0.5},
        policy=policy,
        tighten_pack_budget=True,
        weight=None,
    )
    assembler._render_retriever_pack(
        "fallback_pack",
        template_context={"input": {"message": "Fallback query"}},
        retriever_override=None,
        pack_budget={"ratio": 0.5},
        policy=policy,
        tighten_pack_budget=True,
        weight=None,
    )

    assembler._assemble_default_with_regeneration(
        default_context,
        base_system_prompt="Base",
        history_messages=[{"role": "user", "content": "History"}],
        user_message="User",
        template_context=template_context,
        retriever_override=None,
        total_budget_override=5,
    )
    assembler._assemble_default_with_regeneration(
        ContextDeclaration(name="empty_default_regen", policy=policy, packs=[]),
        base_system_prompt="Base",
        history_messages=[],
        user_message="User",
        template_context=template_context,
        retriever_override=None,
    )
    assembler._assemble_default(
        ContextDeclaration(name="empty_default", policy=policy, packs=[]),
        base_system_prompt="",
        history_messages=[],
        user_message="",
        template_context=template_context,
        total_budget_override=None,
    )
    assembler._assemble_default_with_regeneration(
        ContextDeclaration(
            name="tight_default",
            policy=ContextPolicySpec(
                input_budget=ContextBudgetSpec(max_tokens=1),
                overflow="truncate",
                max_iterations=1,
            ),
            packs=[ContextPackSpec(name="fallback_pack")],
        ),
        base_system_prompt="Base",
        history_messages=[{"role": "user", "content": "History too long"}],
        user_message="User message",
        template_context=template_context,
        retriever_override=None,
        total_budget_override=1,
    )
    assembler._assemble_explicit_with_regeneration(
        explicit_context,
        history_messages=[{"role": "assistant", "content": "History"}],
        user_message="Fallback",
        template_context=template_context,
        retriever_override=None,
    )
    assembler._assemble_explicit_with_regeneration(
        ContextDeclaration(
            name="explicit_truncate",
            policy=ContextPolicySpec(
                input_budget=ContextBudgetSpec(max_tokens=1),
                overflow="truncate",
                max_iterations=1,
            ),
            messages=[
                SystemMessageSpec(type="system", content="System"),
                UserMessageSpec(type="user", content="User message"),
            ],
        ),
        history_messages=[{"role": "assistant", "content": "History"}],
        user_message="Fallback",
        template_context=template_context,
        retriever_override=None,
    )

    forced_assembler = _ForcedCompactionAssembler(
        context_registry={
            "forced_default": default_context,
            "forced_explicit": explicit_context,
        },
        retriever_registry=retriever_registry,
        corpus_registry=corpus_registry,
        compactor_registry=compactor_registry,
        default_retriever=retriever_fn,
    )
    forced_assembler._assemble_default_with_regeneration(
        ContextDeclaration(
            name="forced_default",
            policy=ContextPolicySpec(
                input_budget=ContextBudgetSpec(max_tokens=1), overflow="truncate"
            ),
            packs=[ContextPackSpec(name="fallback_pack")],
        ),
        base_system_prompt="Base",
        history_messages=[{"role": "user", "content": "History"}],
        user_message="User",
        template_context=template_context,
        retriever_override=None,
    )
    forced_assembler._assemble_explicit_with_regeneration(
        ContextDeclaration(
            name="forced_explicit",
            policy=ContextPolicySpec(
                input_budget=ContextBudgetSpec(max_tokens=1), overflow="truncate"
            ),
            messages=[SystemMessageSpec(type="system", content="System")],
        ),
        history_messages=[{"role": "assistant", "content": "History"}],
        user_message="Fallback",
        template_context=template_context,
        retriever_override=None,
    )

    try:
        assembler._render_pack("missing", template_context, None, None, policy)
    except NotImplementedError:
        pass

    try:
        assembler._resolve_compactor(
            ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=10), compactor="missing")
        )
    except ValueError:
        pass

    empty_pack = ContextPack(text="orphan", evidence_count=1, blocks=[])
    assembler._merge_context_packs([empty_pack], join_with=" | ")
    assembler._merge_context_packs(
        [
            ContextPack(
                text="",
                evidence_count=1,
                blocks=[ContextPackBlock(evidence_item_id="b", text="block", metadata=None)],
            )
        ],
        join_with=" | ",
    )
    assembler._merge_context_packs(
        [ContextPack(text="", evidence_count=0, blocks=[])], join_with=" | "
    )
    assembler._merge_context_packs([], join_with=" | ")

    assembler._apply_compaction_policy(
        "one two three",
        ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=2), overflow="compact"),
        max_tokens_override=2,
    )
    assembler._apply_compaction_policy("short", None)
    assembler._apply_compaction_policy(
        "short",
        ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=10), overflow="truncate"),
    )
    assembler._apply_compaction_policy(
        "short",
        ContextPolicySpec(input_budget=ContextBudgetSpec(ratio=0.5), overflow="compact"),
    )
    assembler._apply_compaction_policy(
        "one two",
        ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=1), overflow="truncate"),
        max_tokens_override=1,
    )

    assembler._apply_context_budget(
        "sys",
        [{"role": "user", "content": "history one"}],
        "user",
        ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=1), overflow="compact"),
    )
    assembler._apply_context_budget(
        "sys",
        [{"role": "user", "content": "history"}],
        "user",
        ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=100), overflow="compact"),
    )
    assembler._apply_context_budget(
        "sys",
        [],
        "user",
        ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=1), overflow="truncate"),
    )
    assembler._apply_context_budget(
        "sys",
        [],
        "two tokens",
        ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=1), overflow="compact"),
    )
    assembler._apply_context_budget(
        "sys",
        [],
        "user",
        ContextPolicySpec(input_budget=ContextBudgetSpec(ratio=0.5), overflow="compact"),
    )

    _NoopCompactionAssembler(context_registry={})._apply_context_budget(
        "system",
        [],
        "one two three",
        ContextPolicySpec(input_budget=ContextBudgetSpec(max_tokens=1), overflow="compact"),
    )

    assembler._allocate_pack_budget({"ratio": 0.5}, policy, weight=None)
    assembler._allocate_pack_budget({"ratio": None}, policy, weight=None)
    assembler._allocate_pack_budget(ContextBudgetSpec(max_tokens=5), policy, weight=2.0)
    assembler._allocate_pack_budget(ContextBudgetSpec(ratio=0.5), policy, weight=None)
    assembler._allocate_pack_budget(_BudgetHolder(ratio=0.5), policy, weight=None)
    assembler._allocate_pack_budget(_BudgetHolder(), policy, weight=None)
    assembler._allocate_pack_budget(None, None, weight=None)
    assembler._allocate_pack_budget(
        None,
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=4),
        ),
        weight=None,
    )
    assembler._allocate_pack_budget(
        None,
        ContextPolicySpec(pack_budget=ContextPackBudgetSpec(default_ratio=0.5)),
        weight=None,
    )
    assembler._allocate_pack_budget(
        None,
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(ratio=0.5),
            pack_budget=ContextPackBudgetSpec(default_ratio=0.5),
        ),
        weight=None,
    )
    assembler._allocate_pack_budget(
        None,
        ContextPolicySpec.model_construct(pack_budget=ContextPackBudgetSpec.model_construct()),
        weight=None,
    )

    assembler._resolve_ratio_budget(0.5, policy)
    assembler._resolve_ratio_budget(0.5, None)
    assembler._resolve_ratio_budget(
        0.5, ContextPolicySpec(input_budget=ContextBudgetSpec(ratio=0.5))
    )

    assembler._allocate_directive_budgets([], policy, None)
    assembler._allocate_directive_budgets(
        [ContextInsertSpec(type="context", name="retriever_pack")],
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=5),
        ),
        None,
    )
    assembler._allocate_directive_budgets(
        [ContextInsertSpec(type="context", name="retriever_pack")],
        ContextPolicySpec.model_construct(pack_budget=ContextPackBudgetSpec.model_construct()),
        None,
    )
    assembler._allocate_directive_budgets(
        [ContextInsertSpec(type="context", name="retriever_pack", weight=100.0)],
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=1),
        ),
        total_budget_override=0,
    )
    assembler._allocate_directive_budgets(
        [ContextInsertSpec(type="context", name="retriever_pack")],
        ContextPolicySpec(pack_budget=ContextPackBudgetSpec(default_ratio=0.5)),
        None,
    )
    assembler._allocate_directive_budgets(
        [ContextInsertSpec(type="context", name="retriever_pack")],
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(ratio=0.5),
            pack_budget=ContextPackBudgetSpec(default_ratio=0.5),
        ),
        None,
    )

    assembler._allocate_default_pack_budgets(
        [ContextPackSpec(name="retriever_pack")],
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=5),
        ),
        None,
    )
    assembler._allocate_default_pack_budgets(
        [ContextPackSpec(name="retriever_pack")],
        ContextPolicySpec.model_construct(pack_budget=ContextPackBudgetSpec.model_construct()),
        None,
    )
    assembler._allocate_default_pack_budgets(
        [],
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=5),
        ),
        None,
    )
    assembler._allocate_default_pack_budgets(
        [ContextPackSpec(name="retriever_pack", weight=100.0)],
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=1),
        ),
        total_budget_override=0,
    )
    assembler._allocate_default_pack_budgets(
        [ContextPackSpec(name="retriever_pack")],
        ContextPolicySpec(pack_budget=ContextPackBudgetSpec(default_ratio=0.5)),
        None,
    )
    assembler._allocate_default_pack_budgets(
        [ContextPackSpec(name="retriever_pack")],
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(ratio=0.5),
            pack_budget=ContextPackBudgetSpec(default_ratio=0.5),
        ),
        None,
    )

    assembler._resolve_default_pack_total_budget(policy)
    assembler._resolve_default_pack_total_budget(
        ContextPolicySpec.model_construct(pack_budget=ContextPackBudgetSpec.model_construct())
    )
    assembler._resolve_default_pack_total_budget(
        ContextPolicySpec(
            pack_budget=ContextPackBudgetSpec(default_ratio=0.5),
        )
    )
    assembler._resolve_default_pack_total_budget(
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(ratio=0.5),
            pack_budget=ContextPackBudgetSpec(default_ratio=0.5),
        )
    )
    assembler._extract_pack_budget_max_tokens({"max_tokens": 4}, policy)
    assembler._extract_pack_budget_max_tokens({"ratio": 0.5}, policy)
    assembler._extract_pack_budget_max_tokens({"ratio": None}, policy)
    assembler._extract_pack_budget_max_tokens(ContextBudgetSpec(ratio=0.5), policy)
    assembler._extract_pack_budget_max_tokens(_BudgetHolder(ratio=0.5), policy)
    assembler._extract_pack_budget_max_tokens(_BudgetHolder(), policy)
    assembler._extract_pack_budget_max_tokens(None, policy)

    assembler._split_leading_system(
        [
            {"role": "system", "content": "one"},
            {"role": "system", "content": "two"},
            {"role": "user", "content": "three"},
        ]
    )
    assembler._extract_user_message(
        [{"role": "assistant", "content": "a"}, {"role": "user", "content": "b"}],
        "fallback",
    )
    assembler._extract_user_message(
        [{"role": "assistant", "content": "a"}],
        "fallback",
    )

    assembler._compact_pack_text("pack text", {"max_tokens": 1}, policy, tighten_pack_budget=True)
    assembler._compact_pack_text(
        "pack text", ContextBudgetSpec(max_tokens=1), policy, tighten_pack_budget=False
    )
    assembler._compact_pack_text(
        "pack text", _BudgetHolder(max_tokens=1), policy, tighten_pack_budget=False
    )
    assembler._compact_pack_text("pack text", _BudgetHolder(), policy, tighten_pack_budget=False)
    assembler._compact_pack_text("pack text", SimpleNamespace(), policy, tighten_pack_budget=False)
    assembler._compact_pack_text("pack text", None, policy, tighten_pack_budget=False)

    try:
        assembler._render_nested_context_pack(
            nested_history,
            template_context,
            pack_budget=None,
            policy=policy,
            tighten_pack_budget=False,
            retriever_override=None,
        )
    except ValueError:
        pass

    assembler._render_nested_context_pack(
        nested_explicit,
        template_context,
        pack_budget={"max_tokens": 2},
        policy=policy,
        tighten_pack_budget=True,
        retriever_override=None,
    )

    dummy_policy = SimpleNamespace()
    assembler._resolve_compactor(dummy_policy)

    non_dict_compactor_registry = {
        "bad": _RegistrySpec(config="not-a-dict"),
    }
    ContextAssembler(
        context_registry={},
        compactor_registry=non_dict_compactor_registry,
    )._resolve_compactor(
        ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=2),
            compactor="bad",
        )
    )

    empty_retriever_registry = {"empty_pack": _RegistrySpec(config="not-a-dict")}
    empty_assembler = ContextAssembler(
        context_registry={},
        retriever_registry=empty_retriever_registry,
        corpus_registry={"corpus-two": _RegistrySpec(config="not-a-dict")},
        default_retriever=lambda _req: ContextPack(text="", evidence_count=0, blocks=[]),
    )
    empty_context = ContextDeclaration(
        name="empty_explicit",
        messages=[ContextInsertSpec(type="context", name="empty_pack")],
    )
    empty_retriever_registry["empty_pack"].corpus = "corpus-two"
    empty_assembler._build_messages(
        empty_context,
        history_messages=[],
        template_context=template_context,
        retriever_override=None,
        policy=None,
    )
    empty_assembler._build_messages(
        ContextDeclaration(
            name="assistant_only",
            messages=[AssistantMessageSpec(type="assistant", content="Assistant")],
        ),
        history_messages=[],
        template_context=template_context,
        retriever_override=None,
        policy=None,
    )
    empty_assembler._build_messages(
        ContextDeclaration(
            name="assistant_mixed",
            messages=[
                UserMessageSpec(type="user", content="User"),
                AssistantMessageSpec(type="assistant", content="Assistant"),
            ],
        ),
        history_messages=[],
        template_context=template_context,
        retriever_override=None,
        policy=None,
    )
    empty_assembler._build_messages(
        SimpleNamespace(messages=[AssistantMessageSpec(type="assistant", content="Assistant")]),
        history_messages=[],
        template_context=template_context,
        retriever_override=None,
        policy=None,
    )
    empty_assembler._build_messages(
        SimpleNamespace(messages=[SimpleNamespace()]),
        history_messages=[],
        template_context=template_context,
        retriever_override=None,
        policy=None,
    )
    empty_assembler._render_retriever_pack(
        "empty_pack",
        template_context=template_context,
        retriever_override=None,
        pack_budget=None,
        policy=None,
        tighten_pack_budget=True,
        weight=None,
    )

    context.helper_calls = calls
    context.helper_done = True


@then("the helper execution completes")
def step_helper_execution_completes(context) -> None:
    assert context.helper_done
    assert context.helper_calls
