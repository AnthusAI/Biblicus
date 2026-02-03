from __future__ import annotations

from dataclasses import dataclass

from behave import given, then, when

from biblicus.context import ContextPack
from biblicus.context_engine import ContextAssembler
from biblicus.context_engine.models import (
    ContextBudgetSpec,
    ContextDeclaration,
    ContextInsertSpec,
    ContextPackBudgetSpec,
    ContextPackSpec,
    ContextPolicySpec,
    CorpusDeclaration,
    HistoryInsertSpec,
    RetrieverDeclaration,
    SystemMessageSpec,
    UserMessageSpec,
)


@dataclass
class DummyCorpus:
    """
    Minimal corpus stub for Context engine internal tests.

    :param name: Corpus identifier used in registry.
    :type name: str
    """

    name: str

    def load_catalog(self):
        """
        Reject catalog access for internal tests.

        :raises AssertionError: Always raised because catalog access is not expected.
        :return: None. This helper never returns.
        :rtype: None
        """
        raise AssertionError("catalog not needed")


def _build_context_assembler() -> ContextAssembler:
    return ContextAssembler(context_registry={})


def _register_retriever_with_config(context, retriever_config: dict) -> None:
    corpus_registry = {"corpus": CorpusDeclaration(name="corpus", config={"retriever_id": "scan"})}
    retriever_registry = {
        "search": RetrieverDeclaration(
            name="search",
            corpus="corpus",
            config=retriever_config,
        )
    }
    context.assembler = ContextAssembler(
        context_registry={},
        retriever_registry=retriever_registry,
        corpus_registry=corpus_registry,
    )


@when("I assemble a missing Context")
def step_assemble_missing_context(context) -> None:
    assembler = _build_context_assembler()
    context.error = None
    try:
        assembler.assemble(
            context_name="missing",
            base_system_prompt="",
            history_messages=[],
            user_message="",
            template_context={"input": {}, "context": {}},
        )
    except Exception as exc:
        context.error = exc


@when("I extract a user message from messages without a user entry")
def step_extract_user_message_fallback(context) -> None:
    assembler = _build_context_assembler()
    message, remaining = assembler._extract_user_message(
        [{"role": "assistant", "content": "hi"}],
        "fallback",
    )
    context.extracted_user_message = message
    context.extracted_remaining = remaining


@when("I resolve a template with dotted fields")
def step_resolve_template(context) -> None:
    assembler = _build_context_assembler()
    template_context = {"input": {"query": "world"}, "context": {"greeting": "Hello"}}
    context.resolved_template = assembler._resolve_template(
        "{context.greeting} {input.query}", {}, template_context
    )


@when("I apply context budget trimming with compact overflow")
def step_apply_context_budget_compaction(context) -> None:
    assembler = _build_context_assembler()
    policy = ContextPolicySpec(
        input_budget=ContextBudgetSpec(max_tokens=2),
        overflow="compact",
        compactor={"type": "truncate"},
    )
    system_prompt, history, user_message, token_count, compacted = assembler._apply_context_budget(
        "one two three",
        [{"role": "user", "content": "alpha"}],
        "",
        policy,
    )
    context.compacted_system_prompt = system_prompt
    context.compacted_history = history
    context.compacted_user_message = user_message
    context.compacted_flag = compacted
    context.compacted_token_count = token_count


@given("a retriever registry with a corpus-backed retriever")
def step_retriever_registry(context) -> None:
    corpus_registry = {"corpus": CorpusDeclaration(name="corpus", config={"retriever_id": "scan"})}
    retriever_registry = {
        "search": RetrieverDeclaration(
            name="search",
            corpus="corpus",
            config={"query": "{input.query}", "limit": 1},
        )
    }
    context.assembler = ContextAssembler(
        context_registry={},
        retriever_registry=retriever_registry,
        corpus_registry=corpus_registry,
    )


@given("a retriever registry with pipeline query and index config")
def step_retriever_registry_pipeline_query(context) -> None:
    _register_retriever_with_config(
        context,
        {
            "retriever_id": "scan",
            "configuration": "legacy",
            "pipeline": {
                "query": {
                    "limit": 4,
                    "offset": 2,
                    "maximum_total_characters": 120,
                    "max_items_per_source": 3,
                    "include_metadata": True,
                    "metadata_fields": ["published"],
                    "join_with": "\n\n",
                },
                "index": {"snapshot_id": "snapshot-pipeline"},
            },
        },
    )


@given("a retriever registry with index-only config")
def step_retriever_registry_index_only(context) -> None:
    _register_retriever_with_config(
        context,
        {
            "retriever_id": "scan",
            "configuration": "legacy",
            "index": {"snapshot_id": "snapshot-index"},
        },
    )


@given("a retriever registry with pipeline query only")
def step_retriever_registry_pipeline_query_only(context) -> None:
    _register_retriever_with_config(
        context,
        {
            "retriever_id": "scan",
            "configuration": "legacy",
            "pipeline": {
                "query": "not-a-dict",
            },
        },
    )


@given("a retriever registry with pipeline query config missing limit")
def step_retriever_registry_query_without_limit(context) -> None:
    _register_retriever_with_config(
        context,
        {
            "retriever_id": "scan",
            "configuration": "legacy",
            "pipeline": {
                "query": {
                    "maximum_items_per_source": 2,
                }
            },
        },
    )


@when("I render that retriever pack with pipeline config")
def step_render_retriever_pack_with_pipeline(context) -> None:
    def fake_retrieve(request):
        context.retriever_request = request
        return ContextPack(text="pack text", evidence_count=1, blocks=[])

    context.assembler._render_retriever_pack(
        "search",
        {"input": {"query": "hello"}, "context": {}},
        fake_retrieve,
        pack_budget=None,
        policy=ContextPolicySpec(
            pack_budget=ContextPackBudgetSpec(default_max_tokens=10),
            input_budget=ContextBudgetSpec(max_tokens=20),
        ),
        tighten_pack_budget=False,
        weight=None,
    )


@when("I render that retriever pack with index config")
def step_render_retriever_pack_with_index(context) -> None:
    def fake_retrieve(request):
        context.retriever_request = request
        return ContextPack(text="pack text", evidence_count=1, blocks=[])

    context.assembler._render_retriever_pack(
        "search",
        {"input": {"query": "hello"}, "context": {}},
        fake_retrieve,
        pack_budget=None,
        policy=ContextPolicySpec(
            pack_budget=ContextPackBudgetSpec(default_max_tokens=10),
            input_budget=ContextBudgetSpec(max_tokens=20),
        ),
        tighten_pack_budget=False,
        weight=None,
    )


@when("I render that retriever pack with pipeline-only config")
def step_render_retriever_pack_with_pipeline_only(context) -> None:
    def fake_retrieve(request):
        context.retriever_request = request
        return ContextPack(text="pack text", evidence_count=1, blocks=[])

    context.assembler._render_retriever_pack(
        "search",
        {"input": {"query": "hello"}, "context": {}},
        fake_retrieve,
        pack_budget=None,
        policy=ContextPolicySpec(
            pack_budget=ContextPackBudgetSpec(default_max_tokens=10),
            input_budget=ContextBudgetSpec(max_tokens=20),
        ),
        tighten_pack_budget=False,
        weight=None,
    )


@when("I render that retriever pack with missing-limit query config")
def step_render_retriever_pack_with_missing_limit(context) -> None:
    def fake_retrieve(request):
        context.retriever_request = request
        return ContextPack(text="pack text", evidence_count=1, blocks=[])

    context.assembler._render_retriever_pack(
        "search",
        {"input": {"query": "hello"}, "context": {}},
        fake_retrieve,
        pack_budget=None,
        policy=ContextPolicySpec(
            pack_budget=ContextPackBudgetSpec(default_max_tokens=10),
            input_budget=ContextBudgetSpec(max_tokens=20),
        ),
        tighten_pack_budget=False,
        weight=None,
    )


@then("the retriever request should include pipeline query values")
def step_assert_retriever_request_pipeline_query(context) -> None:
    request = context.retriever_request
    assert request.limit == 4
    assert request.offset == 2
    assert request.maximum_total_characters == 40
    assert request.metadata["maximum_items_per_source"] == 3
    assert request.metadata["include_metadata"] is True
    assert request.metadata["metadata_fields"] == ["published"]


@then("the retriever request should include pipeline index configuration")
def step_assert_retriever_request_pipeline_index(context) -> None:
    request = context.retriever_request
    assert request.metadata["configuration"] == {"snapshot_id": "snapshot-pipeline"}


@then("the retriever request should include index configuration")
def step_assert_retriever_request_index_config(context) -> None:
    request = context.retriever_request
    assert request.metadata["configuration"] == {"snapshot_id": "snapshot-index"}


@then("the retriever request should include empty configuration")
def step_assert_retriever_request_empty_config(context) -> None:
    request = context.retriever_request
    assert request.metadata["configuration"] == {}


@then("the retriever request should include query settings without limit")
def step_assert_retriever_request_missing_limit(context) -> None:
    request = context.retriever_request
    assert request.limit == 3
    assert request.offset == 0
    assert request.metadata["maximum_items_per_source"] == 2
    assert request.metadata["include_metadata"] is False


@when("I render that retriever pack with a template query")
def step_render_retriever_pack(context) -> None:
    def fake_retrieve(request):
        return ContextPack(text="pack text", evidence_count=1, blocks=[])

    context.rendered_pack = context.assembler._render_retriever_pack(
        "search",
        {"input": {"query": "hello"}, "context": {}},
        fake_retrieve,
        pack_budget=None,
        policy=ContextPolicySpec(
            pack_budget=ContextPackBudgetSpec(default_max_tokens=10),
            input_budget=ContextBudgetSpec(max_tokens=20),
        ),
        tighten_pack_budget=False,
        weight=None,
    )


@when("I assemble messages with an empty context pack")
def step_assemble_messages_with_empty_pack(context) -> None:
    def fake_retrieve(_request):
        return ContextPack(text="", evidence_count=0, blocks=[])

    context_spec = ContextDeclaration(
        name="ctx",
        policy=ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=5),
        ),
        messages=[ContextInsertSpec(type="context", name="search")],
    )
    context.assembled_messages = context.assembler._build_messages(
        context_spec,
        history_messages=[],
        template_context={"input": {"query": "hello"}, "context": {}},
        retriever_override=fake_retrieve,
        policy=context_spec.policy,
        tighten_pack_budget=False,
        total_pack_budget_override=None,
    )


@then("the assembled messages should be empty")
def step_assert_assembled_messages_empty(context) -> None:
    assert context.assembled_messages == []


@when("I assemble messages with a non-empty context pack")
def step_assemble_messages_with_pack_content(context) -> None:
    def fake_retrieve(_request):
        return ContextPack(text="pack content", evidence_count=1, blocks=[])

    context_spec = ContextDeclaration(
        name="ctx",
        policy=ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=5),
        ),
        messages=[ContextInsertSpec(type="context", name="search")],
    )
    context.assembled_messages = context.assembler._build_messages(
        context_spec,
        history_messages=[],
        template_context={"input": {"query": "hello"}, "context": {}},
        retriever_override=fake_retrieve,
        policy=context_spec.policy,
        tighten_pack_budget=False,
        total_pack_budget_override=None,
    )


@then("the assembled messages should include the pack content")
def step_assert_assembled_messages_include_pack(context) -> None:
    assert context.assembled_messages == [{"role": "system", "content": "pack content"}]


@when("I render that retriever pack without a retriever function")
def step_render_retriever_pack_no_fn(context) -> None:
    context.error = None
    try:
        context.assembler._render_retriever_pack(
            "search",
            {"input": {"query": "hello"}, "context": {}},
            None,
            pack_budget=None,
            policy=None,
            tighten_pack_budget=False,
            weight=None,
        )
    except Exception as exc:
        context.error = exc


@when("I render a nested Context pack that includes history")
def step_render_nested_history(context) -> None:
    context.error = None
    nested_context = ContextDeclaration(
        name="nested",
        messages=[
            SystemMessageSpec(type="system", content="hello"),
            HistoryInsertSpec(type="history"),
        ],
    )
    assembler = ContextAssembler(context_registry={"nested": nested_context})
    try:
        assembler._render_nested_context_pack(
            nested_context,
            {"input": {}, "context": {}},
            pack_budget=None,
            policy=None,
            tighten_pack_budget=False,
            retriever_override=None,
        )
    except Exception as exc:
        context.error = exc


@when("I assemble default and explicit Context paths")
def step_assemble_default_and_explicit(context) -> None:
    def fake_retrieve(request):  # noqa: ARG001 - interface placeholder
        return ContextPack(text="pack text", evidence_count=1, blocks=[])

    default_context = ContextDeclaration(
        name="default",
        packs=[ContextPackSpec(name="search", weight=1.0)],
        policy=ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=10),
            pack_budget=ContextPackBudgetSpec(default_max_tokens=5),
        ),
    )
    explicit_context = ContextDeclaration(
        name="explicit",
        messages=[
            SystemMessageSpec(type="system", content="base system"),
            ContextInsertSpec(type="context", name="search"),
            UserMessageSpec(type="user", content="explicit user"),
        ],
        policy=ContextPolicySpec(
            input_budget=ContextBudgetSpec(max_tokens=5),
            pack_budget=ContextPackBudgetSpec(default_ratio=0.5),
            overflow="compact",
            compactor={"type": "truncate"},
        ),
    )
    assembler = ContextAssembler(
        context_registry={"default": default_context, "explicit": explicit_context},
        retriever_registry={
            "search": RetrieverDeclaration(name="search", corpus=None, config={"limit": 1})
        },
        corpus_registry={},
        default_retriever=fake_retrieve,
    )
    default_result = assembler._assemble_default(
        default_context,
        base_system_prompt="base system",
        history_messages=[{"role": "user", "content": "history"}],
        user_message="user",
        template_context={"input": {}, "context": {}},
    )
    explicit_result = assembler._assemble_explicit_with_regeneration(
        explicit_context,
        history_messages=[],
        user_message="fallback",
        template_context={"input": {}, "context": {}},
        retriever_override=fake_retrieve,
    )
    context.default_system_prompt = default_result.system_prompt
    context.explicit_user_message = explicit_result.user_message


@then('the extracted user message equals "{expected}"')
def step_extracted_user_message_equals(context, expected: str) -> None:
    assert context.extracted_user_message == expected


@then('the resolved template equals "{expected}"')
def step_resolved_template_equals(context, expected: str) -> None:
    assert context.resolved_template == expected


@then('the compacted system prompt equals "{expected}"')
def step_compacted_system_prompt_equals(context, expected: str) -> None:
    assert context.compacted_system_prompt == expected


@then('the rendered retriever pack equals "{expected}"')
def step_rendered_pack_equals(context, expected: str) -> None:
    assert context.rendered_pack == expected


@then('the explicit user message equals "{expected}"')
def step_explicit_user_message_equals(context, expected: str) -> None:
    assert context.explicit_user_message == expected


@then('the default system prompt includes "{expected}"')
def step_default_system_prompt_includes(context, expected: str) -> None:
    assert expected in context.default_system_prompt
