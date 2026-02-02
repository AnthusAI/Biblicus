from behave import given, then, when
from context_engine_registry import RegistryBuilder

from biblicus.context_engine import ContextAssembler
from biblicus.context_engine.compaction import BaseCompactor, CompactionRequest


@given("a Context that references an unknown compactor")
def step_context_unknown_compactor(context):
    builder = RegistryBuilder()
    builder.register_context(
        "support_context",
        {
            "policy": {
                "compactor": "missing",
                "input_budget": {"max_tokens": 2},
                "overflow": "compact",
            },
            "messages": [
                {"type": "system", "content": "one two three four"},
                {"type": "user", "content": "Question"},
            ],
        },
    )
    context.registry = builder.registry
    context.context_name = "support_context"


@given("a Context that configures an unknown compactor type")
def step_context_unknown_compactor_type(context):
    builder = RegistryBuilder()
    builder.register_context(
        "support_context",
        {
            "policy": {
                "compactor": {"type": "invalid"},
                "input_budget": {"max_tokens": 2},
                "overflow": "compact",
            },
            "messages": [
                {"type": "system", "content": "one two three four"},
                {"type": "user", "content": "Question"},
            ],
        },
    )
    context.registry = builder.registry
    context.context_name = "support_context"


@given("a Context that references an unknown pack")
def step_context_unknown_pack(context):
    builder = RegistryBuilder()
    builder.register_context(
        "support_context",
        {
            "messages": [
                {"type": "system", "content": "Use this."},
                {"type": "context", "name": "missing_pack"},
                {"type": "user", "content": "Question"},
            ],
        },
    )
    context.registry = builder.registry
    context.context_name = "support_context"


@given("a base compactor instance")
def step_base_compactor_instance(context):
    context.compactor = BaseCompactor()


@when("I assemble that Context expecting an error")
def step_assemble_context_with_error(context):
    assembler = ContextAssembler(
        context.registry.contexts,
        retriever_registry=context.registry.retrievers,
        corpus_registry=context.registry.corpora,
        compactor_registry=context.registry.compactors,
    )
    context.error = None
    try:
        assembler.assemble(
            context_name=context.context_name,
            base_system_prompt="",
            history_messages=[],
            user_message="",
            template_context={"input": {}, "context": {}},
        )
    except Exception as exc:
        context.error = exc


@when("I compact text with the base compactor")
def step_base_compactor_compact(context):
    context.compactor_error = None
    try:
        context.compactor.compact(CompactionRequest(text="one two", max_tokens=1))
    except Exception as exc:
        context.compactor_error = exc


@then('the context error should mention "{message}"')
def step_context_error_mentions(context, message):
    assert context.error is not None
    assert message in str(context.error)


@then('the compactor error should mention "{message}"')
def step_compactor_error_mentions(context, message):
    assert context.compactor_error is not None
    assert message in repr(context.compactor_error)
